#!/usr/bin/env python3
"""RUDOF Generate - ShEx/SHACL-driven RDF generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from entry import GenerationResult, run_generator, sh

SCHEMAS = Path("/schemas")
OUTPUT = "generated_data.ttl"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--schema",
        default="lubm/lubm.shex",
        help="ShEx or SHACL schema, relative to the mounted schemas/ directory",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="rudof TOML config, relative to the mounted schemas/ directory",
    )
    parser.add_argument(
        "--property-fill",
        type=float,
        default=None,
        help="override property_fill_probability in the config; used for the coherence sweep",
    )
    parser.add_argument("--entities", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--parallel", type=int, default=None)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    schema = _resolve(args.schema, "schema")
    output_file = out / OUTPUT

    cmd = ["rudof_generate", "--schema", schema, "--output", output_file]
    if args.config:
        config = _resolve(args.config, "config")
        if args.property_fill is not None:
            config = _override_fill(config, args.property_fill)
        cmd.extend(["--config", config])
    if args.entities is not None:
        cmd.extend(["--entities", args.entities])
    if args.seed is not None:
        cmd.extend(["--seed", args.seed])
    if args.parallel is not None:
        cmd.extend(["--parallel", args.parallel])

    sh(cmd)

    stats = _stats(output_file.with_suffix(".stats.json"))

    return GenerationResult(
        files=[OUTPUT],
        rdf_format="turtle",
        triples_reported=_int(stats.get("total_triples")),
        conformance=_conformance(stats),
        tool_version=_version(),
    )


def _resolve(relative: str, kind: str) -> Path:
    path = SCHEMAS / relative
    if path.is_file():
        return path
    available = ", ".join(
        sorted(
            str(p.relative_to(SCHEMAS))
            for p in SCHEMAS.rglob("*")
            if p.suffix in {".shex", ".ttl", ".toml"}
        )
    )
    raise FileNotFoundError(f"{kind} {relative!r} not found under /schemas. Available: {available}")


def _override_fill(config: Path, fill: float) -> Path:
    """Rewrite property_fill_probability, leaving every other setting untouched.

    The sweep varies exactly one parameter. The shipped high- and low-coherence
    configs differ in several settings at once, so sweeping from one of them as a
    base would confound fill with those other changes; only this line is replaced.
    """
    import re

    text = config.read_text(encoding="utf-8")
    text, n = re.subn(
        r"^property_fill_probability\s*=.*$",
        f"property_fill_probability = {fill}",
        text,
        flags=re.MULTILINE,
    )
    if n == 0:
        raise ValueError(f"{config} has no property_fill_probability to override")
    rendered = Path("/tmp/config.toml")
    rendered.write_text(text, encoding="utf-8")
    print(f"property_fill_probability -> {fill} ({n} occurrence(s))", flush=True)
    return rendered


def _stats(stats_file: Path) -> dict:
    """rudof writes a sidecar stats file next to its output when it can."""
    if not stats_file.exists():
        print(f"(no stats sidecar at {stats_file})", flush=True)
        return {}
    try:
        return json.loads(stats_file.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"(unreadable stats sidecar {stats_file}: {exc})", flush=True)
        return {}


def _conformance(stats: dict) -> dict[str, float]:
    """Translate rudof's ``conformance_metrics`` block into the canonical keys.

    These are the two figures the paper defines but has never reported:
    ``triple_validity_pct`` -- the share of generated triples that satisfy the
    schema -- and ``shape_translation_loss_pct`` -- the share of the source
    schema's constraints that did not survive translation into rudof's unified
    intermediate representation.

    Renaming here rather than in the metrics layer keeps the knowledge of
    rudof's field names inside rudof's own image, which is the whole point of
    the container-side report contract.
    """
    block = stats.get("conformance_metrics")
    if not isinstance(block, dict):
        return {}
    mapping = {
        "total_generated_triples": "generated_triples",
        "valid_triples": "valid_triples",
        "triple_validity_percentage": "triple_validity_pct",
        "original_schema_constraints": "schema_constraints",
        "represented_constraints_in_unified": "constraints_represented",
        "shape_translation_loss_percentage": "shape_translation_loss_pct",
    }
    out = {
        canonical: block[native]
        for native, canonical in mapping.items()
        if isinstance(block.get(native), (int, float))
    }
    if out:
        print(
            f"conformance: validity {out.get('triple_validity_pct')}% | "
            f"translation loss {out.get('shape_translation_loss_pct')}%",
            flush=True,
        )
    return out


def _int(value) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _version() -> str | None:
    try:
        return sh(["rudof_generate", "--version"], echo=False).stdout.strip() or None
    except Exception:
        return None


if __name__ == "__main__":
    run_generator(
        "rudof",
        tool="rudof_generate",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate RDF conforming to a ShEx or SHACL schema",
    )
