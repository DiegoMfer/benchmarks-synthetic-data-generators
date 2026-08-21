"""Shared container entrypoint scaffolding.

Every generator image runs a tiny ``entrypoint.py`` that defines *only* what is
specific to its tool: which flags it accepts, and how to invoke it. Timing,
output accounting, error handling and report writing live here and are written
once.

This is the mechanism that removes the host-side schema guessing. Each container
emits the canonical report itself, using the very same ``report.py`` the host
validates with -- the file is copied into the image, so the two cannot drift.

A generator's ``entrypoint.py`` looks like::

    from entry import GenerationResult, run_generator

    def add_arguments(parser):
        parser.add_argument("--products", type=int, default=1000)

    def generate(out, args):
        sh(["java", "-cp", "bsbm.jar", ..., "-fn", str(out / "dataset")])
        return GenerationResult(files=["dataset.ttl"], rdf_format="turtle")

    run_generator("bsbm", tool="bsbmtools", add_arguments=..., generate=generate)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, "/app")

from rdfbench.report import BenchmarkReport, OutputInfo, ToolInfo  # noqa: E402


@dataclass
class GenerationResult:
    """What a generator's ``generate()`` reports back.

    ``triples_reported`` must be left ``None`` when the tool does not print a
    trustworthy count. Guessing here is exactly the failure mode this rewrite
    exists to remove -- the host measures the real number regardless.
    """

    files: list[str]
    rdf_format: str
    triples_reported: int | None = None
    notes: list[str] = field(default_factory=list)
    tool_version: str | None = None
    #: Optional schema-conformance figures, keyed by
    #: :data:`rdfbench.report.CONFORMANCE_KEYS`. Only a generator that consumes
    #: a schema can fill this; leave it empty otherwise.
    conformance: dict[str, float] = field(default_factory=dict)


class GeneratorFailed(RuntimeError):
    """Raised when the underlying generator binary fails."""


def sh(
    cmd: Sequence[str],
    *,
    cwd: str | Path | None = None,
    echo: bool = True,
    check: bool = True,
    capture_to: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run a command, streaming nothing but capturing everything.

    Raises :class:`GeneratorFailed` on a non-zero exit so the entrypoint does not
    have to check return codes.

    Pass ``check=False`` only for a tool whose exit status is known to be
    unreliable, and verify success some other way (that its output exists). Do
    not use it to paper over a real failure -- a generator that silently
    produces nothing must fail the run, not report an empty dataset.

    Pass ``capture_to`` for a tool that writes its dataset to stdout (WatDiv
    does). Output is streamed straight to that file rather than buffered in
    memory, which matters when the dataset is millions of triples.
    """
    if echo:
        print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)

    if capture_to is not None:
        capture_to.parent.mkdir(parents=True, exist_ok=True)
        with capture_to.open("wb") as sink:
            proc = subprocess.run(
                [str(c) for c in cmd],
                cwd=str(cwd) if cwd else None,
                stdout=sink,
                stderr=subprocess.PIPE,
                text=False,
            )
        stderr = (proc.stderr or b"").decode("utf-8", "replace")
        proc = subprocess.CompletedProcess(proc.args, proc.returncode, "", stderr)
        print(f"  wrote stdout to {capture_to} ({capture_to.stat().st_size / 1e6:.1f} MB)", flush=True)
    else:
        proc = subprocess.run(
            [str(c) for c in cmd], cwd=str(cwd) if cwd else None, capture_output=True, text=True
        )
        if proc.stdout:
            print(proc.stdout, flush=True)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr, flush=True)
        if check:
            raise GeneratorFailed(
                f"{cmd[0]} exited {proc.returncode}\n{proc.stderr.strip()[-2000:]}"
            )
        print(f"(exit {proc.returncode} ignored; verifying via output files)", flush=True)
    return proc


def find_int(text: str, pattern: str) -> int | None:
    """Extract the first integer captured by *pattern*, or ``None``.

    Used by generators whose only triple count is printed to stdout. Returning
    ``None`` on no match is deliberate: an absent count must stay absent rather
    than defaulting to zero.
    """
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", "").replace(".", ""))
    except (IndexError, ValueError):
        return None


def run_generator(
    name: str,
    *,
    tool: str,
    generate: Callable[[Path, argparse.Namespace], GenerationResult],
    add_arguments: Callable[[argparse.ArgumentParser], None] | None = None,
    description: str = "",
) -> None:
    """Parse args, time the generation, and write the canonical report."""
    parser = argparse.ArgumentParser(prog=f"{name}-generator", description=description)
    parser.add_argument(
        "--out", required=True, type=Path, help="output directory (bind-mounted by the host)"
    )
    if add_arguments:
        add_arguments(parser)
    args = parser.parse_args()

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    params = {k: v for k, v in vars(args).items() if k != "out"}
    started_at = datetime.now(timezone.utc).isoformat()
    start = datetime.now(timezone.utc)

    print(f"=== {name} ===", flush=True)
    for key, value in sorted(params.items()):
        print(f"  {key}: {value}", flush=True)

    try:
        result = generate(out, args)
    except Exception as exc:  # noqa: BLE001 - the report must record any failure
        traceback.print_exc()
        print(f"\n!! {name} failed: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    duration = (datetime.now(timezone.utc) - start).total_seconds()

    missing = [f for f in result.files if not (out / f).exists()]
    if missing:
        print(
            f"!! {name} reported files it did not write: {', '.join(missing)}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    bytes_total = sum((out / f).stat().st_size for f in result.files)

    report = BenchmarkReport(
        generator=name,
        params=params,
        started_at=started_at,
        duration_seconds=round(duration, 4),
        output=OutputInfo(
            files=list(result.files),
            rdf_format=result.rdf_format,
            triples_reported=result.triples_reported,
            bytes_total=bytes_total,
        ),
        tool=ToolInfo(name=tool, version=result.tool_version),
        exit_code=0,
        notes=list(result.notes),
        conformance=dict(result.conformance),
    )
    report.write(out / "report.json")

    reported = result.triples_reported
    print(
        f"\n=== done in {duration:.2f}s | "
        f"{len(result.files)} file(s), {bytes_total / 1e6:.1f} MB | "
        f"triples reported: {reported if reported is not None else 'not available'} ===",
        flush=True,
    )


def collect(out: Path, *patterns: str) -> list[str]:
    """Return sorted names of files in *out* matching any glob, excluding metadata."""
    names: list[str] = []
    for pattern in patterns:
        names.extend(
            p.name for p in out.glob(pattern) if p.is_file() and p.name != "report.json"
        )
    return sorted(set(names))
