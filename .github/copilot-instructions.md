<!-- Copilot instructions for AI coding agents in this repository -->
# Project-specific guidance for AI coding agents

Purpose
- Help an AI contributor become productive quickly in this benchmark suite.

Big picture
- This repo collects RDF synthetic data generators and orchestration scripts, split into two parts.
- Part 1 (general benchmark): `generate_all_benchmark_datasets.py` calls per-generator
  `execute_benchmark*.py` scripts, copies outputs into `1-Datasets/<GEN>/run_N/`, and
  `generate_csv_metrics.py` reads `1-Datasets/` to write `metrics_comparison.csv`.
- Part 2 (FHIR use case): `generate_all_fhir_datasets.py` runs both FHIR generators
  (RUDOF and Synthea, selectable via `--generators`) into `2-fhir/<GEN>_FHIR/run_N/`;
  `compare_fhir_quality.py` reads `2-fhir/` and writes `2-fhir/quality_comparison.json`
  plus the chart `output_charts/fhir_quality_comparison.pdf`. It reports only metrics
  with a published source (Kahn et al. 2016; Chen et al. 2019). `run_fhir.sh` runs this
  pipeline end to end.
- Each generator folder (e.g. `BSBM`, `LUBM`, `GAIA`, `LINKGEN`, `PYGRAFT`, `RDFGRAPHGEN`, `RUDOFGENERATE`, `SYNTHEA`) contains
  a generator runner (`execute_benchmark.py` or `execute_benchmark_binary.py`), an `output/` directory and a `benchmark_report.json`.

Essential workflows (examples you can run)
- Generate everything: `python3 generate_all_benchmark_datasets.py` (uses Python 3.8+).
- Generate one generator: `python3 BSBM/execute_benchmark.py --products 10000 --format ttl`.
- RUDOF binary run: `python3 RUDOFGENERATE/execute_benchmark_binary.py --entity-count 100000` (may require `rudof` binary or Docker).
- Repeat full-run script: `./run_benchmark.sh` (runs `generate_all_benchmark_datasets.py` and `generate_csv_metrics.py`); `./run_fhir.sh` does the FHIR pipeline.
- Produce metrics CSV: `python3 generate_csv_metrics.py` (reads `1-Datasets/` and writes `metrics_comparison.csv`).

Project conventions & patterns
- Outputs: generators write to `output/` inside their folder; `generate_all_benchmark_datasets.py` copies selected files into `1-Datasets/<GEN>/run_N/` and writes `metadata.json` and `benchmark_report.json`.
- Report shapes: `benchmark_report.json` commonly contains keys like `execution`, `generated_data`, `performance_metrics` (triples, triples_per_second). Use these keys when extracting metrics.
- Large-data handling: `LINKGEN` produces very large files — the metrics script intentionally processes LINKGEN last to avoid OOM.
- Java-based generators: several generators (BSBM, LUBM, GAIA, LINKGEN) call Java jars; assume Java 8+ is required.
- Docker usage: `PYGRAFT` uses Docker images; `RUDOFGENERATE` provides a `docker-compose.yml` and a binary fallback.

Integration points to watch
- `generate_all_benchmark_datasets.py` builds run folders and invokes per-generator scripts with subprocess; changes here affect the whole pipeline.
- `generate_csv_metrics.py` loads `benchmark_report.json` fields and parses RDF with `rdflib` — ensure parsers/format args match generator outputs (`.owl` -> xml, `.ttl` -> turtle, LINKGEN -> nt).
- Conversion: some generators produce `.rdf`; `generate_all_benchmark_datasets.py` contains an RDF->Turtle conversion step using `rdflib` (catch exceptions).

Common pitfalls for contributors
- Do not assume a uniform filename: generators use different output names (`dataset.ttl`, `generated_data.ttl`, `gaia_instances.owl`, `University*.owl`, etc.). Look at the generator's `copy_files` patterns in `generate_all_benchmark_datasets.py`.
- External binaries: test locally that `java`, `docker`, or `rudof` are available; failing to provide them is the most common runtime issue.
- Resource limits: large runs need increased memory/timeout; tests that invoke LINKGEN or RUDOF at scale may OOM or take hours.

How to add/modify a generator
- Implement a runner in the generator folder (follow the `execute_benchmark.py` examples in `BSBM` and `LUBM`).
- Ensure the runner produces `benchmark_report.json` with `execution` and `generated_data` keys, and writes generated files into `output/`.
- Update `generate_all_benchmark_datasets.py` to copy the generator's output patterns and to save `metadata.json` for the run.

Where to look first (quick links)
- Top-level orchestrator: `generate_all_benchmark_datasets.py`
- Metrics exporter: `generate_csv_metrics.py`
- Full-run helpers: `run_benchmark.sh` (part 1), `run_fhir.sh` (part 2)
- Example generators: `BSBM/execute_benchmark.py`, `LUBM/execute_benchmark.py`, `RUDOFGENERATE/execute_benchmark_binary.py`, `GAIA/execute_benchmark.py`.

If you need more
- Ask for specific examples (small dataset run, reporting format changes, or adding a new generator). Provide the generator folder name and desired CLI inputs.

— end —
