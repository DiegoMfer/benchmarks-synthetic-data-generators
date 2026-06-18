# SYNTHEA — Synthetic FHIR Patient Data → Turtle

Dockerized [Synthea](https://github.com/synthetichealth/synthea) generator that
produces a synthetic patient population as **FHIR R4** bundles and converts them
to **RDF Turtle** using the official **`org.hl7.fhir.core`** validator/converter
CLI. The Turtle output mirrors the `RUDOFGENERATE` FHIR dataset so the two can be
compared.

## Pipeline

1. **Synthea** generates FHIR R4 JSON bundles (one per patient, plus
   hospital/practitioner information bundles).
2. The **`org.hl7.fhir.core` `validator_cli.jar`** converts each bundle to Turtle
   (`-convert -version 4.0 -output *.ttl`).
3. **rdflib** merges the per-bundle Turtle files into a single `generated_data.ttl`
   and emits `generated_data.stats.json` + `benchmark_report.json`.

Both jars are downloaded at image-build time, and the FHIR R4 package cache is
pre-warmed so conversion runs without needing network access.

## Usage

Driven by the repo-root orchestration script (recommended):

```bash
python3 ../generate_synthea_dataset.py --population 20 --seed 42
# → output written to ../2-fhir/SYNTHEA_FHIR/run_N/ (alongside RUDOFGENERATE_FHIR)
```

Or directly via docker compose:

```bash
POPULATION=20 SEED=42 docker compose run --rm synthea
# → output/generated_data.ttl, output/generated_data.stats.json, output/benchmark_report.json
```
