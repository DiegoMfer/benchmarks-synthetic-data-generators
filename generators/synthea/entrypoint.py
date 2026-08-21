#!/usr/bin/env python3
"""Synthea - synthetic clinical records exported as FHIR R4 Turtle.

Synthea emits FHIR JSON bundles; the official org.hl7.fhir.core RdfParser turns
each into Turtle, and the bundles are concatenated into a single file. The
concatenation is valid because every bundle uses only blank-node subjects, so
there is nothing to collide across files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from entry import GenerationResult, run_generator, sh

SYNTHEA_JAR = "/app/synthea-with-dependencies.jar"
CONVERTER_CLASSPATH = "/app/classes:/app/validator_cli.jar"
CONVERTER_CLASS = "FhirJsonToTurtle"
OUTPUT = "generated_data.ttl"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--population", type=int, default=20, help="number of patients")
    parser.add_argument("--seed", type=int, default=42)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    raw = Path("/tmp/synthea_raw")
    ttl_dir = Path("/tmp/ttl_bundles")
    ttl_dir.mkdir(parents=True, exist_ok=True)

    sh(
        [
            "java",
            "-jar",
            SYNTHEA_JAR,
            "-p",
            args.population,
            "-s",
            args.seed,
            "--exporter.baseDirectory",
            raw,
            "--exporter.fhir.export",
            "true",
            "--exporter.hospital.fhir.export",
            "true",
            "--exporter.practitioner.fhir.export",
            "true",
            # Formats we do not convert; disabling them keeps the run lean.
            "--exporter.csv.export",
            "false",
            "--exporter.text.export",
            "false",
            "--exporter.ccda.export",
            "false",
        ]
    )

    bundles = sorted((raw / "fhir").glob("*.json"))
    if not bundles:
        raise RuntimeError(f"Synthea produced no FHIR bundles in {raw / 'fhir'}")
    print(f"converting {len(bundles)} FHIR bundle(s) to Turtle ...", flush=True)

    pairs: list[str] = []
    expected: list[Path] = []
    for bundle in bundles:
        target = ttl_dir / f"{bundle.stem}.ttl"
        pairs.extend([str(bundle), str(target)])
        expected.append(target)

    # One JVM for all bundles: process startup dominates otherwise.
    sh(["java", "-cp", CONVERTER_CLASSPATH, CONVERTER_CLASS, *pairs], check=False)

    produced = [p for p in expected if p.exists() and p.stat().st_size > 0]
    if not produced:
        raise RuntimeError("the FHIR-to-Turtle converter produced no output")

    merged = out / OUTPUT
    with merged.open("wb") as fh:
        for ttl in produced:
            fh.write(ttl.read_bytes())
            fh.write(b"\n")

    return GenerationResult(
        files=[OUTPUT],
        rdf_format="turtle",
        # Counting here would just duplicate the host's measurement pass.
        triples_reported=None,
        notes=[f"{len(produced)}/{len(bundles)} FHIR bundles converted to Turtle"],
    )


if __name__ == "__main__":
    run_generator(
        "synthea",
        tool="Synthea + org.hl7.fhir.core",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate synthetic patient records as FHIR R4 Turtle",
    )
