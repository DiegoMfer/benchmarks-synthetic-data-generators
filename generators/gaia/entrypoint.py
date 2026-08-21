#!/usr/bin/env python3
"""GAIA ontology instance generator, driven by the LUBM univ-bench ontology."""

from __future__ import annotations

import argparse
from pathlib import Path

from entry import GenerationResult, run_generator, sh

ONTOLOGY = "/schemas/lubm/univ-bench.owl"
OUTPUT = "gaia_instances.owl"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--instances", type=int, default=100, help="instances per class")
    parser.add_argument(
        "--materialization",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="materialise inferred statements",
    )
    parser.add_argument("--limit", type=int, default=None, help="cap instances per class")
    parser.add_argument("--threads", type=int, default=None)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    cmd = [
        "java",
        "-Xmx8g",
        "-jar",
        "/app/OWLGenerator.jar",
        "-F",
        ONTOLOGY,
        "-O",
        out / OUTPUT,
        "-N",
        args.instances,
    ]
    if args.limit:
        cmd.extend(["-L", args.limit])
    if args.materialization:
        cmd.append("-M")
    if args.threads:
        cmd.extend(["-T", args.threads])

    sh(cmd, cwd="/app")

    # GAIA reports only an instance count, never a triple count. The old
    # pipeline multiplied that by 3 and published the result as if measured;
    # leaving it None means the host's independently measured figure is the only
    # triple count that ever reaches the results table.
    return GenerationResult(
        files=[OUTPUT],
        rdf_format="xml",
        triples_reported=None,
        tool_version="3.1",
        notes=["GAIA does not report a triple count; use the measured value"],
    )


if __name__ == "__main__":
    run_generator(
        "gaia",
        tool="GAIA OWLGenerator",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate ontology instances over the LUBM univ-bench ontology",
    )
