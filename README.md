# Synthetic RDF Data Generators — Benchmark

A benchmark suite for comparing synthetic RDF data generators. Every generator
runs in its own Docker container for reproducibility.

**Author:** DiegoMfer (diegomartin.research@gmail.com)

The project has two independent parts:

| Part | What it does | Generates | Compared by | Output |
|------|--------------|-----------|-------------|--------|
| **1 — Benchmark** | General-purpose RDF generators on domain benchmarks | `1-Datasets/` | `generate_csv_metrics.py` | `metrics_comparison.csv` |
| **2 — FHIR use case** | Two generators producing FHIR R4 healthcare RDF | `2-fhir/` | `compare_fhir_quality.py` | chart in `output_charts/` |

The two parts mirror each other: a "generate all" script fills a numbered
dataset folder, and a comparison script reads that folder and writes metrics.

## Requirements

- Python 3.8+ (`pip install -r requirements.txt`)
- Docker & Docker Compose — every generator runs containerized, so no Java or
  other local dependencies are needed.
- Linux / macOS / WSL

---

## Part 1 — Benchmark

```bash
# Generate every benchmark dataset into 1-Datasets/
python3 generate_all_benchmark_datasets.py --generators ALL

# Or only some generators
python3 generate_all_benchmark_datasets.py --generators BSBM LUBM

# Compute metrics from 1-Datasets/ into metrics_comparison.csv
python3 generate_csv_metrics.py
```

`run_benchmark.sh` runs the whole part-1 pipeline (generate → metrics). Plot the
results with the `metrics_histogram.ipynb` notebook (charts are written to
`output_charts/`).

### Generators

| Generator | Domain | Approach | Source |
|-----------|--------|----------|--------|
| BSBM | E-commerce | Products, vendors, offers, reviews | [berlinsparqlbenchmark](http://wbsg.informatik.uni-mannheim.de/bizer/berlinsparqlbenchmark/) |
| LUBM | University | Departments, professors, students, courses | [swat.cse.lehigh.edu/projects/lubm](http://swat.cse.lehigh.edu/projects/lubm/) |
| GAIA | University | Instance generator over the LUBM `univ-bench` ontology | — |
| LINKGEN | Linked data | Configurable distributions (Zipf / Gaussian) | [github.com/akjoshi/linkgen](https://github.com/akjoshi/linkgen) |
| PyGraft | Knowledge graph | RDFS / OWL constructs | [github.com/nicolas-hbt/pygraft](https://github.com/nicolas-hbt/pygraft) |
| RDFGraphGen | Schema-driven | Generates data from SHACL shapes | [github.com/cadmiumkitty/rdfgraphgen](https://github.com/cadmiumkitty/rdfgraphgen) |
| RUDOF Generate | Schema-driven | Generates data from ShEx / SHACL schemas | [github.com/rudof-project/rudof](https://github.com/rudof-project/rudof) |

LUBM variants (`*_LUBM_SHEX`, `*_LUBM_SHACL`, …) run RDFGraphGen and RUDOF
Generate against LUBM shapes so schema-driven output can be compared against the
LUBM benchmark on the same ontology. Per-generator configuration is documented
in `CONFIG_SUMMARY/` and in each generator's own `README.md`.

### Dataset layout

```
1-Datasets/
├── INDEX.md                 # auto-generated overview of all runs
├── BSBM/
│   └── run_1/
│       ├── metadata.json    # configuration + generation metadata
│       ├── dataset.ttl      # generated RDF
│       └── benchmark_report.json
└── ...                      # one folder per generator, one run_N/ per run
```

---

## Part 2 — FHIR use case

A healthcare use case comparing two ways of producing FHIR R4 RDF: a
schema-driven generator (RUDOF Generate, from a FHIR ShEx schema) and a
clinical simulator ([Synthea](https://github.com/synthetichealth/synthea),
converted to RDF with [org.hl7.fhir.core](https://github.com/hapifhir/org.hl7.fhir.core)).
Both emit [FHIR R4](https://hl7.org/fhir/R4/) Turtle, so they can be compared directly.

```bash
# Generate both FHIR datasets into 2-fhir/
python3 generate_all_fhir_datasets.py --generators ALL

# Or run a single generator
python3 generate_all_fhir_datasets.py --generators RUDOFGENERATE
python3 generate_all_fhir_datasets.py --generators SYNTHEA --population 100

# Compare data quality -> chart + numbers
python3 compare_fhir_quality.py
```

`run_fhir.sh` runs the whole part-2 pipeline (generate → compare). The
comparison writes `output_charts/fhir_quality_comparison.pdf` (the chart) and
`2-fhir/quality_comparison.json` (the numbers behind it).

Only metrics with a published source are reported. Conformance, completeness and
plausibility follow the [Kahn et al. (2016)](https://doi.org/10.5334/egems.218)
harmonized data-quality framework; terminology binding and clinical-quality-measure
(CQM) feasibility follow [Chen et al. (2019)](https://doi.org/10.1186/s12911-019-0793-0).

### Dataset layout

```
2-fhir/
├── INDEX.md                      # auto-generated overview of all runs
├── RUDOFGENERATE_FHIR/run_1/     # ShEx-driven FHIR R4 RDF
├── SYNTHEA_FHIR/run_1/           # Synthea clinical FHIR R4 RDF
└── quality_comparison.json       # metrics behind the chart
```

---

## Running a generator on its own

Each generator has its own Docker Compose setup, for example:

```bash
cd BSBM && docker compose run --rm bsbm-benchmark --products 10000 --format ttl
cd LUBM && docker compose run --rm lubm-benchmark --universities 10
cd RUDOFGENERATE && docker compose run --rm rudof --entity-count 100000
```

See each generator folder's `README.md` and `DOCKER_SETUP.md` for details.

## Other folders

- `Auxiliar_folder/` — scripts to extract ShEx/SHACL shapes from LUBM data (see its `README.md`).
- `CONFIG_SUMMARY/` — per-generator configuration reference.
- `output_charts/` — charts produced by the benchmark notebook.
