#!/usr/bin/env python3
"""LUBM (Lehigh University Benchmark) university-domain generator."""

from __future__ import annotations

import argparse
from pathlib import Path

from entry import GenerationResult, run_generator, sh

#: The generator embeds this IRI in the data it writes; it is a namespace, not a
#: URL that gets fetched, so runs stay offline and reproducible.
ONTOLOGY_IRI = "http://www.lehigh.edu/~yug2/Research/SemanticWeb/LUBM/univ-bench.owl"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--universities", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--index", type=int, default=0, help="starting university index")


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    # UBA writes University*.owl into its working directory, so run it in the
    # mounted output directory rather than generating then copying.
    proc = sh(
        [
            "java",
            "-cp",
            "/app/lubm-generator-fixed.jar",
            "edu.lehigh.swat.bench.uba.Generator",
            "-univ",
            args.universities,
            "-index",
            args.index,
            "-seed",
            args.seed,
            "-onto",
            ONTOLOGY_IRI,
        ],
        cwd=out,
    )

    files = sorted(p.name for p in out.glob("University*.owl"))
    if not files:
        raise RuntimeError("UBA produced no University*.owl files")

    return GenerationResult(
        files=files,
        rdf_format="xml",
        triples_reported=_total_triples(proc.stdout),
        notes=[f"{len(files)} RDF/XML files"],
    )


def _total_triples(stdout: str) -> int | None:
    """Sum UBA's running class- and property-instance totals.

    UBA prints a cumulative total per category; the last of each is the final
    count. Returns ``None`` when neither line appeared, so an absent count stays
    absent rather than being reported as zero.
    """
    import re

    classes = re.findall(r"CLASS INSTANCE #: \d+, TOTAL SO FAR: (\d+)", stdout)
    properties = re.findall(r"PROPERTY INSTANCE #: \d+, TOTAL SO FAR: (\d+)", stdout)
    if not classes and not properties:
        return None
    return (int(classes[-1]) if classes else 0) + (int(properties[-1]) if properties else 0)


if __name__ == "__main__":
    run_generator(
        "lubm",
        tool="LUBM UBA",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate university-domain RDF (departments, professors, students, courses)",
    )
