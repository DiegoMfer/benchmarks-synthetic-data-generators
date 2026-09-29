# benchmarks-synthetic-data-generators
[![DOI](https://zenodo.org/badge/1085678027.svg)](https://doi.org/10.5281/zenodo.23045647)

Benchmark suite for synthetic RDF data generators, and the reproducibility
artefact for *Schema-driven RDF synthetic data generation based on validation
languages*. Every generator runs in its own Docker container; one command
generates the datasets, measures them, and writes the comparison.

```bash
python3 main.py --all --smoke   # every profile at tiny scale, ~2 min: verifies everything
python3 main.py --all           # the real benchmark: 542 runs, hours
```

That single command runs all four stages — build images, generate datasets,
compute metrics, render charts. Nothing else needs to be invoked.

Each of the three experiments in [EXPERIMENTS.md](EXPERIMENTS.md) is a profile
and runs independently of the others.

## Requirements

- Python 3.10+ — `pip install -e .` (PyYAML, rdflib, matplotlib, pySHACL)
- Docker with Compose v2. Every generator is containerised, so no Java, Maven or
  per-generator Python environment is needed on the host.

## What it produces

```
data/
  runs/<profile>/<experiment>/run_N/    generated RDF + report.json + container.log
  results/<profile>/metrics.csv         one row per run
  results/<profile>/charts/*.pdf        see "Charts" below
```

`data/runs/` is gitignored — generated datasets are never committed (a full
run produces roughly 200 GB). `data/results/` *is* committed: the metrics and
charts of the published runs ship with the repository.

## Generators

| Generator | Input | Approach | Used in |
|---|---|---|---|
| `rudof` | ShEx / SHACL schema | Generates data from the schema (pinned to the published 0.3.21 release) | E2, E4, E5 |
| `rdfgraphgen` | SHACL shapes | Generates data from the shapes | E2 |
| `gaia` | OWL ontology | Instance generator over the LUBM `univ-bench` ontology | E2 |
| `linkgen` | OWL ontology | Configurable Zipf / Gaussian degree distributions | E2 |
| `lubm` | Built-in (university) | Departments, professors, students, courses | E2 |
| `bsbm` | Built-in (e-commerce) | Products, vendors, offers, reviews | E2 |
| `watdiv` | WatDiv dataset-description language | Tunable structuredness via its own DSL | E2 |
| `pygraft` | None (invents its schema) | RDFS / OWL constructs, schema and data generated together | E2 |
| `lemming` | Example graph | Mimics a seed graph; the same image runs **LEMMING** (`mode: Binary`) and **SimplexKG** (`mode: Simplex`) | E2 |
| `synthea` | Built-in (healthcare) | Clinical records exported as FHIR R4 Turtle | E5 |

E2 splits these in two: generators that can be fed the shared LUBM schema form
the controlled comparison, and the rest (`ref_*` experiments) appear as
reference points on the same scale. See [EXPERIMENTS.md](EXPERIMENTS.md).

`generators/evogen/` is **not** wired into any profile. EvoGen was packaged and
compiles, but crashes before producing a complete dataset on every parameter
combination its README documents; the Dockerfile is kept so the attempt is
reproducible. `generators/_extractors/shexer/` is the schema extractor used by
the `extract` command, not a generator.

## Profiles

One profile per experiment, each with a `_smoke` counterpart at minimum scale.

| Profile | Experiment | Question |
|---|---|---|
| `e2` | Controllability | Which generators respond to a coherence configuration, and where does every generator sit? |
| `e4` | Conformance | How much of a schema survives translation into the IR? |
| `e5` | FHIR case study | Does the approach generalise to an independent domain? |

Every `_smoke` profile defines the *same experiments* as its full counterpart
and differs only in its numbers, so the fast one exercises exactly the code path
the real one uses. A test enforces that they stay in sync.

The `extract` command mines ShEx schemas out of a finished run, using sheXer:

```bash
python3 main.py extract --profile e2 --only ref_bsbm_high   # from a benchmark run
python3 main.py extract --from /path/to/dataset --name x    # or any directory of RDF
```

Extracted schemas land in `schemas/extracted/`. No profile in this repository
depends on them; the command is retained because mining a schema from real data
is the natural way to extend the conformance experiment to inputs nobody
authored.

## Useful invocations

```bash
python3 main.py --list                            # profiles and generators
python3 main.py --only bsbm_high_coherence        # one experiment, end to end
python3 main.py --runs 3                          # override the repeat count
python3 main.py --skip-generate                   # re-measure data already on disk
python3 main.py --all                             # every profile the paper needs
python3 main.py --profile e2 --fail-fast          # stop at the first failure
python3 main.py extract --profile e2 --only ref_bsbm_high   # mine a schema from a finished run
python3 main.py extract --from data/real --name dbpedia   # ... or from any RDF directory
python3 -m pytest tests/                          # unit tests, no Docker needed
```

## How it is put together

Three files carry the design; everything else follows from them.

**1. One container contract.** Every generator image accepts `--out /out` plus
its own parameters, and writes a canonical `report.json`:

```json
{
  "generator": "bsbm",
  "params": { "products": 100 },
  "duration_seconds": 3.19,
  "output": { "files": ["dataset.ttl"], "rdf_format": "turtle", "triples_reported": 75550 },
  "tool": { "name": "bsbmtools", "version": null },
  "schema_version": "1.0"
}
```

Report normalisation happens *inside* each container, where the knowledge about
that tool lives. The host validates the schema and reads plain fields — it never
guesses at layout. `src/rdfbench/report.py` is copied into every image, so host
and container cannot drift.

`triples_reported` is what the tool *claims* and may be `null`; the metrics
engine always computes `triples_measured` independently from the actual RDF.
Both reach the CSV, so a tool that miscounts shows up as a discrepancy instead
of silently becoming the published number.

**Build context.** `.dockerignore` is load-bearing. The compose build context is
the project root, so every image can copy the shared `generators/_common/`
library and `src/rdfbench/report.py`. Without `.dockerignore` that also ships
`data/` to the Docker daemon on every build -- it reaches several GB after a few
runs, which made cached builds take minutes. Keep `data/` excluded.

**2. One compose file.** `docker-compose.yml` uses a YAML anchor for the shared
volume/user/environment, so a generator is three lines. The build context is the
project root, which is what lets every image copy the shared entry library.

**3. Generators are data, not code.** Each `generators/<name>/generator.yaml`
declares the compose service, output files, RDF format, and the parameter→flag
mapping. Adding a generator needs no host-side Python.

```yaml
name: bsbm
service: bsbm
data_files: ["dataset.*"]
rdf_format: turtle
params:
  products: { flag: --products, type: int }
```

Container-side, `generators/_common/entry.py` handles timing, output accounting,
error handling and report writing once, so each `entrypoint.py` only expresses
what is specific to its tool.

## Charts

Which charts a profile gets is decided from its data rather than declared:

| File | Profiles | What it shows |
|---|---|---|
| `coherence_by_generator.pdf` | `e2`, `e5` | RDF coherence per experiment, mean ± std over runs |
| `throughput_by_generator.pdf` | `e2`, `e5` | Same, for measured throughput |
| `execution_time_by_generator.pdf` | `e2`, `e5` | Same, for wall-clock generation time |
| `schema_conformance.pdf` | `e4` | Constraints kept vs lost per schema, validity annotated |
| `fhir_coverage_vs_conformance.pdf` | `e5` | Coverage of the FHIR specification against conformance to it, per tool |

A profile in which every experiment reports conformance gets the conformance
figure; one comparing two or more tools on a domain schema gets the FHIR
trade-off figure; every other profile gets the per-generator bars.

In E2 the benchmark's question is whether a generator *responds* to its
coherence configuration, and that question lives in the HIGH/LOW pair — so the
two configurations sit side by side under one generator label rather than
becoming independent bars. Generators fed the shared schema come first; the
reference generators follow after a visible gap.

**Y-scale is chosen from the data**, not hardcoded. Throughput spans orders of
magnitude. `_scale_for()` picks:

- **linear** when the dynamic range is under 50×;
- **a broken axis** when the values split into two tight clusters;
- **a log axis with a dot plot** when values spread continuously across orders
  of magnitude, since no single break helps. Dots rather than bars, because bar
  length on a log axis is not proportional to value.

Colour is a validated blue/orange pair that passes contrast and colour-vision
deficiency checks.

## Metrics

Computed in a single streaming pass (`src/rdfbench/metrics/`). N-Triples is read
line by line; other formats go through an rdflib `Store` that forwards each
triple and stores nothing, so no graph is ever materialised. Strings are interned
to integers. This is what makes 35M-triple datasets measurable on a workstation.

Coherence is the structuredness measure of Duan et al. (SIGMOD 2011). For a type
`t` with instances `I(t)` and predicates `P(t)`:

```
CV(t) = Σ |properties(s)| for s ∈ I(t)  /  (|P(t)| × |I(t)|)
```

Reported instance-weighted as `RDF_Coherence` and as a plain mean over types in
`RDF_Type_Coverage_Avg`.

The metrics engine is a direct port of the previous implementation and was
verified to produce **bit-identical** results on the same datasets across all
three parse paths.

## Caveats worth knowing

- **GAIA reports no triple count.** It only prints an instance count. Its
  `Triples_Reported` is `null` by design; use the measured value. (The previous
  pipeline multiplied the instance count by 3 and published that as if measured.)
- **GAIA has no seed parameter**, so its output differs between runs of the same
  configuration. The 30-run spread in `e2` captures this.
- **LINKGEN exits non-zero even on success.** Its entrypoint judges success by
  whether the data files exist, and says so in a comment.
- **PyGraft crashes below ~1000 entities** (`classes × avg_instances`) with a
  `ZeroDivisionError` in its own sampler. The smoke profile sits just above that
  threshold.
- **PyGraft writes RDF/XML**, because its internal reasoner cannot re-read the
  Turtle it emits.
- **LEMMING builds from a vendored jar.** Its source build depends on
  artifacts hosted only on maven.aksw.org, which stopped responding in 2026, so
  the prebuilt 96 MiB shaded jar is committed under `generators/lemming/vendor/`.
  The source build path is still in the Dockerfile; see
  `generators/lemming/BUILD_ISSUE.txt`.
- **rudof runs from its published release.** The `rudof_0.3.21_amd64.deb`
  release asset is vendored and pinned by filename (its sha256 is in the
  Dockerfile), so every run traces to one upstream release.
- **`.dockerignore` is load-bearing.** The compose build context is the project
  root, so images can copy the shared entry library — without the file, all the
  generated data under `data/` is uploaded to the Docker daemon on every build.
  That turned cached builds into multi-minute operations and made the smoke
  profiles look like they had hung.
- **BSBM stamps prices with a custom datatype** (`bsbm:USD`), and rudof refuses
  a schema naming a datatype it cannot generate. The sheXer extractor rewrites
  non-XSD datatypes to `xsd:string` and records which ones in
  `extraction.json`; see EXPERIMENTS.md §9.1 for why that is sound for what E3
  measures.

## License and citation

The code in this repository is released under the [MIT License](LICENSE).
Third-party generators, vendored binaries and schemas keep their own licenses.

To cite this software, use the metadata in [CITATION.cff](CITATION.cff) (GitHub's
"Cite this repository" button reads it).
