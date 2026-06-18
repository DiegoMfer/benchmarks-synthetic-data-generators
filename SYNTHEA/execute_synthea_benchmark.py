#!/usr/bin/env python3
"""
Synthea FHIR Benchmark / Generation Script

Pipeline (runs inside the Docker container):
  1. Generate a synthetic patient population with Synthea -> FHIR R4 JSON bundles.
  2. Convert every FHIR bundle to RDF Turtle with the official
     org.hl7.fhir.core validator CLI (`-convert ... -output *.ttl`).
  3. Merge the per-bundle Turtle files into a single `generated_data.ttl`
     with rdflib, and emit stats + a benchmark report.

The output layout mirrors RUDOFGENERATE so the two FHIR datasets are
directly comparable:
    output/generated_data.ttl
    output/generated_data.stats.json
    output/benchmark_report.json
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

SYNTHEA_JAR = '/app/synthea-with-dependencies.jar'
# validator_cli.jar bundles org.hl7.fhir.core; FhirJsonToTurtle (compiled into
# /app/classes) uses its org.hl7.fhir.r4.formats.RdfParser for JSON -> Turtle.
HL7_CORE_JAR = '/app/validator_cli.jar'
CONVERTER_CLASSPATH = f'/app/classes:{HL7_CORE_JAR}'
CONVERTER_CLASS = 'FhirJsonToTurtle'
FHIR_VERSION = '4.0'  # Synthea default export is FHIR R4


def run_synthea(population, seed, raw_dir):
    """Generate FHIR R4 bundles with Synthea into raw_dir/fhir/."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        'java', '-jar', SYNTHEA_JAR,
        '-p', str(population),
        '-s', str(seed),
        '--exporter.baseDirectory', str(raw_dir),
        '--exporter.fhir.export', 'true',
        '--exporter.hospital.fhir.export', 'true',
        '--exporter.practitioner.fhir.export', 'true',
        # Keep the run lean: disable formats we don't convert.
        '--exporter.csv.export', 'false',
        '--exporter.text.export', 'false',
        '--exporter.ccda.export', 'false',
    ]
    print(f"Running Synthea: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(f"Synthea stderr:\n{result.stderr[-4000:]}")
        raise RuntimeError(f"Synthea failed with exit code {result.returncode}")

    fhir_dir = raw_dir / 'fhir'
    bundles = sorted(fhir_dir.glob('*.json')) if fhir_dir.exists() else []
    if not bundles:
        raise RuntimeError(f"No FHIR bundles found in {fhir_dir}")
    print(f"Synthea produced {len(bundles)} FHIR bundle(s) in {fhir_dir}")
    return bundles


def convert_bundles_to_ttl(json_files, ttl_dir):
    """Convert all FHIR JSON bundles to Turtle in a single JVM via
    org.hl7.fhir.core's RdfParser. Returns the list of produced .ttl files."""
    pairs = []
    expected = []
    for json_file in json_files:
        ttl_file = ttl_dir / f'{json_file.stem}.ttl'
        pairs.extend([str(json_file), str(ttl_file)])
        expected.append(ttl_file)

    cmd = ['java', '-cp', CONVERTER_CLASSPATH, CONVERTER_CLASS, *pairs]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Print full output so failures are never silently truncated.
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())

    return [t for t in expected if t.exists() and t.stat().st_size > 0]


def merge_turtle(ttl_files, merged_path):
    """Concatenate per-bundle Turtle into one file and count triples/subjects.

    Done one file at a time to bound memory (the full dataset is millions of
    triples and would OOM if loaded into a single in-memory rdflib graph).
    Each per-bundle file is self-contained Turtle using only anonymous (blank)
    subjects, so triple and subject counts are exact when summed across files.
    """
    from rdflib import Graph

    total_triples = 0
    total_subjects = 0
    with open(merged_path, 'wb') as out:
        for ttl in ttl_files:
            data = ttl.read_bytes()
            out.write(data)
            out.write(b'\n')
            try:
                g = Graph()
                g.parse(data=data, format='turtle')
                total_triples += len(g)
                total_subjects += len(set(g.subjects()))
                del g
            except Exception as e:
                print(f"  ⚠️  Could not parse {ttl.name}: {e}")
    return total_triples, total_subjects


def main():
    parser = argparse.ArgumentParser(description='Generate a Synthea FHIR dataset and convert it to Turtle')
    parser.add_argument('--population', type=int, default=20, help='Number of patients to generate')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducible generation')
    parser.add_argument('--output-dir', type=str, default='output', help='Directory for output files')
    parser.add_argument('--output-format', type=str, default='turtle', help='Output format (only turtle supported)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_dir = script_dir / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / 'synthea_raw'
    ttl_dir = output_dir / 'ttl_bundles'
    ttl_dir.mkdir(parents=True, exist_ok=True)

    merged_ttl = output_dir / 'generated_data.ttl'
    stats_file = output_dir / 'generated_data.stats.json'
    report_file = output_dir / 'benchmark_report.json'

    print(f"\n{'='*70}")
    print(f"Synthea FHIR -> Turtle Benchmark")
    print(f"{'='*70}")
    print(f"Population : {args.population}")
    print(f"Seed       : {args.seed}")
    print(f"FHIR ver.  : R{FHIR_VERSION} (Synthea default)")
    print(f"Converter  : org.hl7.fhir.core validator_cli.jar")
    print(f"{'='*70}\n")

    start = time.time()

    # 1. Generate
    bundles = run_synthea(args.population, args.seed, raw_dir)

    # 2. Convert all bundles to Turtle (single JVM, org.hl7.fhir.core RdfParser)
    print(f"\nConverting {len(bundles)} bundle(s) to Turtle via org.hl7.fhir.core RdfParser ...")
    patient_bundles = sum(
        1 for b in bundles
        if not (b.stem.startswith('hospitalInformation') or b.stem.startswith('practitionerInformation'))
    )
    ttl_files = convert_bundles_to_ttl(bundles, ttl_dir)
    print(f"Converted {len(ttl_files)}/{len(bundles)} bundle(s) successfully")

    if not ttl_files:
        raise RuntimeError("No bundles were successfully converted to Turtle")

    # 3. Merge into a single Turtle file
    print(f"\nMerging {len(ttl_files)} Turtle file(s) into {merged_ttl.name} ...")
    total_triples, total_subjects = merge_turtle(ttl_files, merged_ttl)
    elapsed = time.time() - start

    file_size_mb = merged_ttl.stat().st_size / (1024 * 1024) if merged_ttl.exists() else 0.0

    # Stats (mirrors the RUDOFGENERATE stats schema where it makes sense)
    stats = {
        'total_triples': total_triples,
        'total_subjects': total_subjects,
        'total_bundles': len(bundles),
        'patient_bundles': patient_bundles,
        'converted_bundles': len(ttl_files),
        'generation_time': f"{elapsed:.2f}s",
        'fhir_version': f"R{FHIR_VERSION}",
        'generator': 'Synthea',
        'converter': 'org.hl7.fhir.core validator_cli',
        'config_summary': {
            'population': args.population,
            'seed': args.seed,
        },
    }
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    triples_per_second = total_triples / elapsed if elapsed > 0 else 0
    report = {
        'benchmark': 'Synthea FHIR (JSON -> Turtle via org.hl7.fhir.core)',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'configuration': {
            'population': args.population,
            'seed': args.seed,
            'fhir_version': f"R{FHIR_VERSION}",
            'output_format': 'turtle',
        },
        'execution': {
            'time_seconds': elapsed,
            'success': True,
        },
        'generated_data': {
            'triples_total': total_triples,
            'file_size_mb': file_size_mb,
            'output_file': merged_ttl.name,
            'bundles': len(bundles),
            'patient_bundles': patient_bundles,
        },
        'performance_metrics': {
            'triples_per_second': triples_per_second,
        },
    }
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    # The container runs as root; ensure the host user can read the outputs
    # (rdflib's serialize() writes mode 0600 by default).
    for p in (merged_ttl, stats_file, report_file):
        try:
            os.chmod(p, 0o644)
        except OSError:
            pass

    print(f"\n✓ Done!")
    print(f"  Patients/bundles : {patient_bundles}/{len(bundles)}")
    print(f"  Total triples    : {total_triples:,}")
    print(f"  Output size      : {file_size_mb:.2f} MB")
    print(f"  Elapsed          : {elapsed:.2f}s")
    print(f"  Merged Turtle    : {merged_ttl}")
    print(f"  Report           : {report_file}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
