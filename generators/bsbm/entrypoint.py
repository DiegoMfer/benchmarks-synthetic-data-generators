#!/usr/bin/env python3
"""BSBM (Berlin SPARQL Benchmark) e-commerce data generator."""

from __future__ import annotations

import argparse
from pathlib import Path

from entry import GenerationResult, find_int, run_generator, sh

#: bsbmtools' ``-s`` values mapped to the rdflib parser name the metrics layer
#: needs. Keeping this here rather than on the host is the point of the design:
#: only this file knows anything about bsbmtools.
FORMATS = {"ttl": "turtle", "nt": "nt", "n3": "n3", "trig": "trig"}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--products", type=int, default=1000)
    parser.add_argument("--format", choices=sorted(FORMATS), default="ttl")
    # BooleanOptionalAction defines both --forward-chaining and
    # --no-forward-chaining, matching the true/false flags in generator.yaml.
    parser.add_argument(
        "--forward-chaining",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="RDFS forward chaining",
    )


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    stem = "dataset"
    cmd = [
        "java",
        "-cp",
        "/app/bsbm.jar:/app/ssj.jar",
        "-Xmx2G",
        "benchmark.generator.Generator",
        "-pc",
        args.products,
        "-s",
        args.format,
        "-fn",
        out / stem,
    ]
    if args.forward_chaining:
        cmd.append("-fc")

    # bsbmtools resolves its dictionaries relative to the working directory.
    proc = sh(cmd, cwd="/app")

    return GenerationResult(
        files=[f"{stem}.{args.format}"],
        rdf_format=FORMATS[args.format],
        triples_reported=find_int(proc.stdout, r"([\d,]+)\s+triples generated"),
    )


if __name__ == "__main__":
    run_generator(
        "bsbm",
        tool="bsbmtools",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate synthetic e-commerce RDF (products, vendors, offers, reviews)",
    )
