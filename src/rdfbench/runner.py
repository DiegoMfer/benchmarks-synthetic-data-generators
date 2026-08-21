"""The one Docker runner.

The old codebase had eight ``DatasetGenerator`` subclasses that were ~85%
identical: build the image, ``docker compose run``, glob the outputs into place,
write metadata. The only genuine variance -- service name, CLI flags, output
filenames -- is now declared in ``generator.yaml``, so a single class covers
every generator and adding one requires no Python at all.

Two structural simplifications versus the old flow:

* The run directory is bind-mounted straight to ``/out``, so the container
  writes its final location directly. There is no generate-then-copy step and
  therefore no glob patterns to keep in sync.
* The container writes the canonical ``report.json`` itself. The host reads it
  with :meth:`rdfbench.report.BenchmarkReport.read`, which validates it, rather
  than guessing at its shape.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Experiment, GeneratorSpec, Workspace
from .report import BenchmarkReport, ReportError


class DockerError(RuntimeError):
    """Raised when Docker itself is unusable (missing, daemon down, build failed)."""


@dataclass
class RunOutcome:
    """Result of a single container invocation."""

    experiment: str
    generator: str
    run: int
    run_dir: Path
    ok: bool
    duration_seconds: float
    report: BenchmarkReport | None = None
    error: str = ""


@dataclass
class ExtractOutcome:
    """Result of running the extractor over one source dataset."""

    name: str
    src_dir: Path
    schema_path: Path
    ok: bool
    duration_seconds: float
    error: str = ""


class DockerRunner:
    def __init__(self, workspace: Workspace, *, timeout: int = 3600, quiet: bool = False):
        self.ws = workspace
        self.timeout = timeout
        self.quiet = quiet
        self._built: set[str] = set()

    # -- preflight --------------------------------------------------------

    def preflight(self) -> None:
        """Fail early and clearly if Docker is not usable."""
        if shutil.which("docker") is None:
            raise DockerError("`docker` not found on PATH. Install Docker to run generators.")
        probe = subprocess.run(
            ["docker", "compose", "version"], capture_output=True, text=True
        )
        if probe.returncode != 0:
            raise DockerError(
                "`docker compose` is unavailable (needs Docker Compose v2).\n"
                f"{probe.stderr.strip()}"
            )
        daemon = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if daemon.returncode != 0:
            raise DockerError(
                "Cannot reach the Docker daemon. Is it running, and is your user in the "
                f"`docker` group?\n{daemon.stderr.strip()}"
            )
        if not self.ws.compose_file.exists():
            raise DockerError(f"missing {self.ws.compose_file}")

    # -- build ------------------------------------------------------------

    def build(self, spec: GeneratorSpec, *, force: bool = False) -> None:
        """Build a generator image, at most once per process unless *force*."""
        if spec.service in self._built and not force:
            return
        self._log(f"  building image for {spec.name} ...")
        result = self._compose(["build", spec.service], out_dir=None, capture=True)
        if result.returncode != 0:
            raise DockerError(
                f"docker compose build {spec.service} failed:\n{_tail(result.stderr or result.stdout)}"
            )
        self._built.add(spec.service)

    # -- run --------------------------------------------------------------

    def run(
        self,
        spec: GeneratorSpec,
        experiment: Experiment,
        run: int,
        profile: str,
    ) -> RunOutcome:
        run_dir = self.ws.run_dir(profile, experiment.name, run)
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        argv = ["run", "--rm", spec.service, "--out", "/out"]
        argv.extend(spec.render_args(experiment.params))

        started = time.monotonic()
        result = self._compose(argv, out_dir=run_dir, capture=True)
        elapsed = time.monotonic() - started

        # Container stdout/stderr is kept next to the data: when a run fails
        # during an overnight sweep this is the only forensic trail there is.
        (run_dir / "container.log").write_text(
            f"$ docker compose {' '.join(argv)}\n\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}\n",
            encoding="utf-8",
        )

        if result.returncode != 0:
            return RunOutcome(
                experiment=experiment.name,
                generator=spec.name,
                run=run,
                run_dir=run_dir,
                ok=False,
                duration_seconds=elapsed,
                error=f"exit {result.returncode}: {_tail(result.stderr or result.stdout)}",
            )

        try:
            report = BenchmarkReport.read(run_dir / "report.json")
        except ReportError as exc:
            return RunOutcome(
                experiment=experiment.name,
                generator=spec.name,
                run=run,
                run_dir=run_dir,
                ok=False,
                duration_seconds=elapsed,
                error=str(exc),
            )

        missing = [f for f in report.output.files if not (run_dir / f).exists()]
        if missing:
            return RunOutcome(
                experiment=experiment.name,
                generator=spec.name,
                run=run,
                run_dir=run_dir,
                ok=False,
                duration_seconds=elapsed,
                error=f"report lists file(s) that were not written: {', '.join(missing)}",
            )

        return RunOutcome(
            experiment=experiment.name,
            generator=spec.name,
            run=run,
            run_dir=run_dir,
            ok=True,
            duration_seconds=elapsed,
            report=report,
        )

    # -- extract ----------------------------------------------------------

    def build_service(self, service: str, *, force: bool = False) -> None:
        """Build a compose service that has no ``generator.yaml`` (the extractor)."""
        if service in self._built and not force:
            return
        self._log(f"  building image for {service} ...")
        result = self._compose(["build", service], out_dir=None, capture=True)
        if result.returncode != 0:
            raise DockerError(
                f"docker compose build {service} failed:\n{_tail(result.stderr or result.stdout)}"
            )
        self._built.add(service)

    def extract(
        self, src_dir: Path, out_dir: Path, name: str, *, rdf_format: str, threshold: float
    ) -> ExtractOutcome:
        """Run sheXer over *src_dir*, writing ``<name>.shex`` into *out_dir*.

        Kept separate from :meth:`run` rather than folded into it: an extraction
        produces a schema, not a dataset, so it has no report to validate, no
        triples to count, and no place in a profile.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        argv = [
            "run", "--rm", "shexer",
            "--in", "/in", "--out", "/out", "--name", name,
            "--format", rdf_format, "--threshold", str(threshold),
        ]

        started = time.monotonic()
        result = self._compose(argv, out_dir=out_dir, in_dir=src_dir, capture=True)
        elapsed = time.monotonic() - started

        schema = out_dir / f"{name}.shex"
        (out_dir / f"{name}.extraction.log").write_text(
            f"$ docker compose {' '.join(argv)}\n\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}\n",
            encoding="utf-8",
        )

        if result.returncode != 0:
            return ExtractOutcome(
                name, src_dir, schema, False, elapsed,
                error=f"exit {result.returncode}: {_tail(result.stderr or result.stdout)}",
            )
        if not schema.exists() or schema.stat().st_size == 0:
            return ExtractOutcome(
                name, src_dir, schema, False, elapsed,
                error=f"sheXer exited 0 but wrote no schema to {schema}",
            )
        return ExtractOutcome(name, src_dir, schema, True, elapsed)

    # -- internals --------------------------------------------------------

    def _compose(
        self,
        argv: list[str],
        *,
        out_dir: Path | None,
        capture: bool,
        in_dir: Path | None = None,
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        # Bind target for /out. Compose requires it to be set even for `build`,
        # since the volume is declared on the shared service anchor.
        env["RDFBENCH_OUT"] = str(out_dir.resolve()) if out_dir else str(self.ws.root / "data")
        # Bind target for /in, used only by the extractor service. It too must
        # be set for `build`, because compose interpolates every service's
        # volumes regardless of which one is being built.
        env["RDFBENCH_IN"] = str(in_dir.resolve()) if in_dir else str(self.ws.root / "data")
        # Run as the invoking user so generated files are not root-owned.
        env["RDFBENCH_UID"] = str(os.getuid())
        env["RDFBENCH_GID"] = str(os.getgid())

        cmd = ["docker", "compose", "-f", str(self.ws.compose_file), *argv]
        try:
            return subprocess.run(
                cmd,
                cwd=self.ws.root,
                env=env,
                capture_output=capture,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                cmd, returncode=124, stdout=exc.stdout or "", stderr=f"timed out after {self.timeout}s"
            )

    def _log(self, message: str) -> None:
        if not self.quiet:
            print(message, flush=True)


def _tail(text: str | None, lines: int = 20) -> str:
    if not text:
        return "(no output)"
    kept = text.strip().splitlines()[-lines:]
    return "\n".join(kept)
