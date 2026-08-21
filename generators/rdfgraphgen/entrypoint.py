#!/usr/bin/env python3
"""RDFGraphGen - generates RDF from SHACL shape definitions."""

from __future__ import annotations

import argparse
from pathlib import Path

from entry import GenerationResult, run_generator, sh

OUTPUT = "output-graph.ttl"
SCHEMAS = Path("/schemas")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--shape",
        default="lubm/lubm_shacl.ttl",
        help="SHACL shape file, relative to the mounted schemas/ directory",
    )
    parser.add_argument("--scale-factor", type=int, default=100)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    shape = SCHEMAS / args.shape
    if not shape.exists():
        available = ", ".join(sorted(str(p.relative_to(SCHEMAS)) for p in SCHEMAS.rglob("*.ttl")))
        raise FileNotFoundError(f"shape {args.shape!r} not found. Available: {available}")

    sh(["rdfgen", shape, out / OUTPUT, args.scale_factor])

    return GenerationResult(
        files=[OUTPUT],
        rdf_format="turtle",
        # rdfgen prints no triple count, and counting the file here would just
        # duplicate the host's measurement pass.
        triples_reported=None,
    )


if __name__ == "__main__":
    run_generator(
        "rdfgraphgen",
        tool="rdf-graph-gen",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate RDF conforming to a SHACL shape",
    )
