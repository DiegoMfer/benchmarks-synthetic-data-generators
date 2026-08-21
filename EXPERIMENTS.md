# Experiment plan

Working document for the evaluation in *Schema-driven RDF synthetic data
generation based on validation languages*. Records what each experiment
measures, why its control holds, and what is still open.

---

## 1. What the evaluation has to establish

| # | Question | Experiment |
|---|---|---|
| Q1 | Can a single constraint model serve both ShEx and SHACL? | E1 |
| Q2 | Is *consuming* a schema sufficient for structural control? | E2 |
| Q3 | Is the reachable structuredness range a property of the tool or of the schema? | E3 |
| Q4 | How much of the source schema survives translation into the IR? | E4 |
| Q5 | Does the approach generalise to an independent domain schema? | E5 |

Coherence (Duan et al., SIGMOD 2011) is the primary metric throughout.
Throughput and execution time are reported as the *cost* of control, in E2/E3
only.

---

## 2. Generator taxonomy

Organised by the artefact that drives generation. This is the same taxonomy used
in the paper's Related Work, and it determines experiment membership.

| Category | Generators | Input artefact |
|---|---|---|
| **Fixed-schema** | LUBM, BSBM, EvoGen†, PoDiGG† | domain compiled into the tool |
| **Schema-driven** | rudof, RDFGraphGen, GAIA, LinkGen, PyGraft‡ | external declarative schema |
| **Specification-driven** | WatDiv, GRR† | bespoke generation language |
| **Data-driven** | LEMMING, SimplexKG, RDFMutate† | an existing graph |

† discussed in Related Work, not evaluated — see §6.
‡ degenerate case: PyGraft generates its own schema on every run.

---

## 3. Design decisions

These were reached by working through problems that the first design did not
survive. They are recorded because each one is a question a reviewer will ask.

### 3.1 "Same schema" only holds for three generators

Of the generators evaluated, only rudof(ShEx), rudof(SHACL) and RDFGraphGen
consume a common input. Everything else consumes a translation, an
approximation, a different domain, or no schema at all:

| Input actually consumed | Generators | Classes produced |
|---|---|---|
| a *different domain* | BSBM | 29 |
| `univ-bench.owl` directly | LUBM, GAIA, LinkGen | 15, **50**, 13 |
| sheXer approximation of it | RDFGraphGen, rudof ×2 | 15 |
| hand-written translation | WatDiv | 11 |
| no schema at all | PyGraft, LEMMING, SimplexKG | 16/8, — |

GAIA produces **50 classes from the same `univ-bench.owl` that LUBM's own
generator turns into 15**. Coherence averages per-type coverage, so those two
numbers are computed over structurally different partitions. Experiments are
therefore stratified rather than presented as one controlled comparison.

### 3.2 No claim of achievable range

rudof exposes at least seven structural parameters, plus per-shape overrides —
an unbounded configuration space. No sweep or search establishes a true minimum
or maximum, so the evaluation does **not** claim one. It reports *response to a
named parameter, all else fixed*, which is a partial derivative and fully
defensible.

### 3.3 One stated rule for high/low

This rule governs E2. E3 no longer uses a high/low pair -- it sweeps
`property_fill` across its full range for every schema -- and its source
generators run at their defaults.

Where two configurations are reported, they are derived by a single rule applied
uniformly, not tuned per tool:

> The **high** configuration is the setting of the generator's documented
> parameters that maximises property completeness; the **low** configuration the
> setting that minimises it. Where a generator exposes no such parameter, a
> single configuration is reported.

| Generator | high | low |
|---|---|---|
| rudof | `property_fill = 1.0` | `property_fill = 0.1` |
| WatDiv | `property_fill = 1.0`† | `property_fill = 0.1`† |
| GAIA | `materialization = true` | `false` |
| LinkGen | `gaussian` | `zipf` |
| PyGraft | `avg_relations = 5` | `avg_relations = 2` |
| RDFGraphGen | — | — (no such parameter) |
| LUBM, BSBM | — | — (no such parameter) |

The blank rows are results, not omissions.

† **WatDiv's parameter is analogous, not identical.** rudof's `property_fill` is a
runtime setting applied per instance *per property* — with the `Random` strategy
each instance receives exactly `round(fill × total_properties)` of them. WatDiv has
no such runtime parameter: `--property-fill` is a string substituted into a
hand-written model template at 23 sites (11 `<pgroup>` probabilities and 12
association `left_cover` values), and a `<pgroup>` fires a whole *group* of
properties per instance rather than choosing properties individually. At fill 0.5
rudof gives every instance about half its properties; WatDiv gives about half the
instances a whole group and the rest none of it — the same mean over a different
distribution, and coherence measures precisely that difference.

Collapsing WatDiv's independent per-group probabilities onto a single parameter is
an authoring decision of ours, not WatDiv's design, and is an instance of the
hand-written-translation confound in §3.1. The pairing is defensible but must be
described as *analogous mechanisms made comparable*, never as one shared
parameter. The only genuine same-parameter comparison in the benchmark is
rudof(ShEx) vs rudof(SHACL) in E1.

**Consequence:** the current rudof low config changes six settings at once
(`property_selection_strategy`, `ignore_min_cardinality`, `quality`, plus
per-type overrides). Under this rule it varies one, which moves the reported
span from +0.184 to about +0.238 and makes it attributable to a named parameter.

---

## 4. The experiments

### E1 — Language equivalence
**Q1.** Does one constraint model serve both ShEx and SHACL?

* **Members:** rudof(ShEx), rudof(SHACL)
* **Varied:** `property_fill` 0.1 → 1.0
* **Control:** perfect — one tool, schemas extracted from the same data, one variable
* **Runs:** 20 configs × 10 = **200**
* **Profile:** `profiles/e1.yaml` — rename of the existing `sweep.yaml`, restricted to the two rudof variants (drop the WatDiv entries) and `runs: 10`
* **Configs:** `rudof_shex_fill_{010..100}`, `rudof_shacl_fill_{010..100}`; base `lubm/benchmark_config_sweep.toml`, `seed: 42`, only `property_fill` varies
* **Figure:** sweep curves, two lines expected to coincide
* **Needs no competitor**, so it is immune to every stratification concern above.

Smoke result: agreement at all ten points, diverging 0.001 once.

### E2 — Controllability, and where every generator sits
**Q2.** Among generators that can be fed the same schema, which can move
structuredness? And where does everything else fall on the same scale?

**One figure, two claims, separated by a divider.** This is the chart the
evaluation is built around.

**Left — the controlled comparison.** rudof(ShEx), rudof(SHACL), RDFGraphGen,
GAIA, LinkGen, all fed the LUBM schema; rudof and RDFGraphGen read the
byte-identical `lubm_shacl.ttl`. Same input, same domain, so a difference here is
a difference between tools. The only genuinely controlled cross-tool comparison
in the benchmark.

**Right (`ref_`) — generators that cannot be given that schema.** BSBM and LUBM
have their domain compiled in, WatDiv reads a bespoke DSL, PyGraft invents its
own schema per run, LEMMING and SimplexKG consume a graph. Placing them left of
the divider would destroy the control; they appear instead as reference points on
the same normalised scale — which is exactly Duan et al.'s own protocol, since
the metric normalises per dataset and needs no shared input to be meaningful.
They are hatched, and keep their own HIGH/LOW configuration where they have one.

* **Runs:** 18 configs × 10 = **180**
* **Profile:** `e2.yaml` — also the source of E3's schemas, so no separate profile exists for those

**Measured (smoke, corrected metric):**

| | high | low | span | |
|---|---:|---:|---:|---|
| rudof (ShEx / SHACL) | 0.819 | 0.429 | **0.390** | compared |
| RDFGraphGen | 0.998 | — | — | compared, no parameter |
| LinkGen | 0.528 | 0.529 | 0.001 | compared |
| GAIA | 0.067 | 0.063 | 0.004 | compared |
| WatDiv | 0.999 | 0.510 | **0.489** | reference |
| BSBM | 0.948 | 0.958 | 0.010 | reference |
| PyGraft | 0.371 | 0.367 | 0.004 | reference |
| LUBM | 0.893 | — | — | reference |
| LEMMING / SimplexKG | 0.616 / 0.567 | — | — | reference |

**Two results, and the second must not be buried.** Among generators fed the
shared schema, only rudof moves: RDFGraphGen reads the same SHACL and exposes
nothing to turn, LinkGen and GAIA shift by less than 0.005. But **WatDiv spans
0.489, wider than rudof's 0.390**, and is a genuine competitor on
controllability.

Do not contest that number. The two spans are measured on *different schemas* and
are therefore not comparable — which is precisely what E3 establishes. The
defensible claim is about the input: rudof is driven by a standard, validatable,
extractable schema; WatDiv by a bespoke DSL that must be hand-authored per domain
and that no other tool reads. That distinction survives WatDiv having the wider
range, and stating it first is stronger than having a reviewer find it.

**GAIA at 0.067** is low but uncontrolled — it lands there, it cannot be aimed
there. The difference between landing and aiming is the thesis.

### E3 — What determines the reachable coherence range?
**Q3.** Is a schema-driven generator's achievable structuredness a property of
the *tool*, or of the *schema* it is given?

**The claim, and the only one E3 makes:**

> Holding the generator, its configuration, the entity count and the seed fixed,
> and varying only the input schema, rudof's coherence floor moves from 0.38 to
> 0.97 and its span by a factor of eight.

E3 makes **no competitive claim**, and this is deliberate. Every attempt at one —
bracketing, round-trip fidelity, a shared schema — broke on the same rock: these
generators cannot be given a common input, so a controlled comparison against
them does not exist (§3.1). E3 is a statement about rudof and schemas; the other
generators appear descriptively.

**Why it is load-bearing.** Without it the evaluation reports that rudof floors
at 0.744 on LUBM, a reader holds that against Duan et al.'s ~0.45 real-data band,
and concludes the tool cannot reach realistic structuredness. E3 answers: 0.744
is *LUBM's* floor — LUBM is an unusually regular schema — and the same binary
reaches 0.379 given a different one. That misreading is the natural one, and it
is the reason this experiment exists.

**Design.** `rudof × property_fill 0.1..1.0 × {schema}`. One binary, one config
file, one entity count, one seed; the schema is the only variable, and three
tests assert that control rather than trusting it to review.

* **Schemas:** `lubm.shex` (hand-written) plus six mined by sheXer from E2's reference-side output
* **Runs:** 7 schemas × 5 fill points × 3 = **105** (the datasets come from E2)
* **Profiles:** `e2.yaml` → `extract --profile e2 --only ref_*` → `e3.yaml` (no separate source profile)

**Measured (smoke, 3 000 entities, 45/45 runs):**

| schema | floor | ceiling | span |
|---|---:|---:|---:|
| bsbm_high-derived | **0.3790** | 0.9770 | 0.5980 |
| bsbm_low-derived | 0.3969 | 0.9728 | 0.5760 |
| simplexkg-derived | 0.6660 | 0.8566 | 0.1906 |
| watdiv_high-derived | 0.6758 | 0.9585 | 0.2827 |
| watdiv_low-derived | 0.7180 | 0.9523 | 0.2344 |
| **lubm (authored)** | **0.7436** | 0.9825 | 0.2388 |
| lemming-derived | 0.8231 | 1.0000 | 0.1769 |
| pygraft_high-derived | 0.9526 | 0.8512 | **−0.1014** |
| pygraft_low-derived | 0.9673 | 0.8896 | −0.0777 |

**Figures**

| file | role |
|---|---|
| `e3/charts/sweep_rdf_coherence.pdf` | **the claim** — one curve per schema |
| `e3_sources/charts/coherence_by_generator.pdf` | **coverage** — the five generators absent from E2, HIGH vs LOW |
| `e3/charts/coherence_bracketing.pdf` | **supporting**, for the discussion point below |

Phase 1 earns its place independently: it is the descriptive comparison Duan et
al.'s own protocol licenses — measure each dataset, plot on the normalised scale,
no shared input required — and without it BSBM, WatDiv, PyGraft, LEMMING and
SimplexKG appear nowhere in the evaluation.

**Phase 1 result — two of the five do control structuredness.**

| source | high | low | Δ |
|---|---:|---:|---:|
| **WatDiv** (`property_fill` 1.0/0.1) | 0.9994 | 0.5958 | **+0.4036** |
| PyGraft (`avg_relations` 5/2) | 0.5003 | 0.4455 | +0.0549 |
| BSBM (`forward_chaining` on/off) | 0.9612 | 0.9684 | −0.0072 |
| LEMMING, SimplexKG | — | — | no such parameter |

WatDiv is a genuine competitor on controllability and must be reported as one.
BSBM's `forward_chaining` turns out not to be a coherence parameter at all.

**For the discussion, not the results — extraction discards frequency.**
WatDiv moves its own coherence by 0.40; after sheXer extraction the two bands
rudof reaches from those datasets differ by ≤0.04, about a 90% loss. The cause is
structural: ShEx cardinality is qualitative. `?` and `*` state that a property is
optional and cannot state that it appears on a tenth of instances, so extraction
preserves *which* properties exist and discards *how often they were used*; rudof
then refills them from its own `property_fill`.

This is a second kind of translation loss, distinct from E4's — not constraints
dropped, but frequency the target language cannot express — and it explains why
bracketing succeeds for only 3 of 8 sources. Keep it to a short passage: it is a
limitation of *extraction*, which is E3's own method, not of schema-driven
generation, and led with it would be misread as the latter.

**Bracketing is not a claim.** 3 of 8, several within 0.02 of the boundary, and
now fully accounted for by the paragraph above. The figure supports that
explanation; it is not a test rudof passes.

**Superseded.** `e3_rudof.yaml` (the two-point round-trip) has been deleted. Its
band was read from the endpoint fills, which is wrong now that coherence is known
to be non-monotone in fill, and `e3` supersedes it with a five-point measured
band from the same runs.

**Outstanding — a schema mined from real data.** `extract --from <dir>` is built
and works, but no suitable dataset is available in the repository (the only
candidate, `email-Eu-core.n3`, carries one predicate and no `rdf:type`). This is
the highest-value run left: if a schema mined from a real graph puts rudof in
Duan's ~0.45 band, it closes the argument from their complaint to this tool in
one figure, with no generator involved and therefore no comparability question.

### E4 — Conformance metrics
**Q4.** How much of the source schema survives translation into the IR?

* **Measures:** `TripleValidity%`, `ShapeTranslationLoss%`
* **Inputs:** LUBM ShEx, LUBM SHACL, FHIR R4 ShEx (as published, and the tuned variant used in E5)
* **Runs:** 3 — translation loss is a function of the schema alone and cannot vary; validity depends on the data and could
* **Profiles:** `e4.yaml`, `e4_smoke.yaml`
* **Figure:** `schema_conformance.pdf` — one stacked bar per schema, constraints kept vs lost, validity annotated

These two metrics are **defined in the paper and never reported**. That gap is
now closed: `rudof_generate` already computes both and writes them to its
`generated_data.stats.json` sidecar. No Rust work was needed — only plumbing
them through the report contract into the CSV.

Because loss is computed from the schema before any triple is generated, the
smoke profile reports the *same* percentages as the full one, which makes it a
genuine check of the number rather than only of the wiring.

**Measured — full profile, 3 runs each (10 m 31 s, 12/12 ok):**

| Input | constraints | represented | loss | validity | triples |
|---|---:|---:|---:|---:|---:|
| LUBM ShEx | 105 | 88 | 16.19% | 100.00% | 632 233 |
| LUBM SHACL | 221 | 221 | 0.00% | 48.72% | 632 267 |
| FHIR R4 ShEx | 24 190 | 23 543 | 2.67% | 49.53% | 1 546 094 |
| FHIR R4 ShEx (tuned) | 24 190 | 23 543 | 2.67% | 41.53% | 2 218 462 |

The smoke run at 2 000 entities reproduces every loss figure to the decimal and
every validity figure to within 0.4 points, which is the predicted behaviour:
loss is computed from the schema before any triple exists, and validity is a
proportion that stabilises quickly. Translation loss also has **zero** variance
across the three runs, so it needs no repetition at all — the runs exist only to
show that validity does not drift.

The two FHIR rows carry identical constraint counts because the tuning replaces
shape references with datatypes (701 lines) without adding or removing a single
triple constraint. Reporting both keeps E5's tuning honest: it shows what the
tuning cost in validity rather than quoting only the better number.

**Open question — the SHACL asymmetry.** LUBM SHACL translates with *zero* loss
yet only 48.7% of its output validates, while LUBM ShEx loses 16.2% of its
constraints and validates at 100%. E1 established that the two languages produce
structurally near-identical data (max divergence 0.001 in coherence), so this is
not a difference in the graphs. The likely explanation is that the SHACL shapes
graph states roughly twice as many constraints (221 vs 105), and that rudof's
validator checks constraints its generator does not act on. This needs settling
before the number is published — as it stands it is a statement about rudof's
internal consistency, not about SHACL.

### E5 — FHIR case study
**Q5.** Does the approach generalise to an independently designed schema?

* **Members:** Synthea, rudof over FHIR R4 ShEx
* **Runs:** 2 configs × 10 = **20**
* **Profile:** `fhir_paper.yaml` (exists)

---

## 5. Established findings

### 5.1 Scale does not move coherence; structural parameters do

From the existing published data, grouped by what was varied:

| Generator | varied | Δ coherence |
|---|---|---|
| RDFGraphGen | scale 3000 → 2500 | **0.0000** |
| BSBM | 100k → 50k products (2× data) | **−0.0035** |
| PyGraft | `avg_relations` 5 → 2 | **+0.061** |
| GAIA | materialization on → off | **+0.066** |
| LinkGen | gaussian → zipf | **+0.141** |
| rudof | fill / selection | **+0.184** |

The two groups separate by roughly **20×**. Practical consequence: structuredness
cannot be tuned by scaling a dataset, in any of the generators tested.

This rests on two points per generator, so it is an observation rather than a
demonstration of invariance. Stating it as "scale did not move coherence in these
configurations" is supported; stating it as "coherence is invariant to scale"
would need a scale sweep, which is out of scope.

### 5.2 The published LUBM data point is invalid

| | universities | triples reported |
|---|---|---|
| `LUBM_HIGH_COHERENCE` | 65 | 9,884,335 |
| `LUBM_LOW_COHERENCE` | 45 | 9,872,444 |
| ratio | 1.44× | **1.001×** |

Verified independently that LUBM scales linearly (2 → 237k, 4 → 494k,
8 → 1,036k triples), so the two configurations should differ by ~44%. They
differ by 0.1%, meaning both runs almost certainly used the same university
count. The LUBM invariance result is currently unsupported.

**LUBM must therefore be re-run as part of E2**, where it supplies the reference line. Without E4 there is no other experiment that would have caught this.

The current harness prevents a silent recurrence: `report.json` records the
parameters actually used, and they reach the results CSV.

### 5.3 Only two generators expose continuous structural control

| Generator | parameter governing structure | Type |
|---|---|---|
| rudof | `property_fill_probability` (+6 more) | **continuous** |
| WatDiv | `<pgroup>` prob / association `left_cover` | **continuous** |
| GAIA | `materialization` | binary |
| LinkGen | `distribution` | categorical, 2 |
| PyGraft | `avg_relations` | numeric, indirect |
| RDFGraphGen, BSBM, LUBM | — | **none** |
| LEMMING, SimplexKG | — | inherited from input |

Verifiable from each tool's CLI — **no experiment required**. This table carries
Q2 and costs nothing.

---

### 5.4 Most generators are deterministic, so run counts differ

Measured over the published 10-run data:

| Configuration | σ (coherence) | distinct values in 10 runs |
|---|---|---|
| BSBM, LUBM, LinkGen, RDFGraphGen | **0.000000** | 1 |
| rudof HIGH | **0.000000** | 3–4 (variation below 1e-6) |
| GAIA | 0.00004 | 10 |
| rudof LOW | 0.0004 | 10 |
| **PyGraft** | **0.031 / 0.016** | 10 |

Twelve of sixteen configurations return the *same number every run*. Since the
standard error is σ/√n, no amount of repetition changes a reported value when
σ = 0, and for GAIA and rudof σ is already four orders of magnitude below the
three decimals reported. Uniform run counts would therefore buy nothing.

**Run counts are set from measured variance:**

| Case | Generators | n | Why |
|---|---|---|---|
| deterministic | BSBM, LUBM, LinkGen, RDFGraphGen, rudof HIGH | **3** | enough to *demonstrate* determinism |
| low variance | GAIA, rudof LOW | **10** | matches the published table; already excessive |
| stochastic | PyGraft | **30** | the only case where n changes a reported value |
| unmeasured | WatDiv, LEMMING, SimplexKG | **5, then decide** | never run more than once; WatDiv calls `rand()` with no seed exposed |

This is also a **result worth reporting**: given a fixed seed, every evaluated
generator except PyGraft produces identical output across runs. PyGraft does not,
because it regenerates its schema on every invocation — which is schema variance,
not parameter response, and the two must not appear in the same column.

---

## 6. Generators excluded, and why

| Generator | Reason |
|---|---|
| **EvoGen** | Fixed-schema (its `-onto` sets only a namespace IRI; the university domain is compiled in), so it adds a third fixed-schema reference rather than a schema language. Independently, it cannot complete a run: `GRAD_COURSE_NUM` is fixed at 100 while its faculty configuration can demand 104, after which it fails in `_AssignGraduateCourse`. See `generators/evogen/Dockerfile`. |
| **RDFMutate** | Data-driven: mutates an existing graph rather than generating from a schema. Including it would measure its mutation operators applied to another tool's output. |
| **PoDiGG** | Domain-locked to public transport; cannot consume the LUBM model. BSBM and LUBM already supply the fixed-schema reference points. |
| **GRR** | Specification-driven, and its object values must be supplied by hand, so it cannot be driven from the extracted schema the other generators receive. |

All four are obtainable — none is excluded for unavailability.

---

## 7. Open questions

0. ~~**Which coherence definition is correct?**~~ **Settled, and the
   implementation was wrong on two counts. Both are now fixed.**

   The LDBC reference procedure published alongside Duan's metric settles it
   directly:

   ```sql
   where t1.S = t2.S and t2.P <> iri_to_id('rdf:type')
   ```

   That filter appears in *both* the numerator and the property count, so:

   1. **`rdf:type` is excluded** from a type's property set. Counting it inflates
      every score — it is present on every instance of a type by construction, so
      in the limit a graph thinned to nothing but `rdf:type` scored a perfect 1.0.
      That artefact is what made coherence non-monotone in property fill.
   2. **Each type is weighted by (|P(t)| + |I(t)|)**, not by instance count alone.

   An earlier reading of this document concluded the opposite on point 1, from a
   formalisation that defines a *graph-level* `σ_Cov(D)` over all of `P(D)`. That
   is a different function from the per-type coherence `CH(D)` this benchmark
   computes, and it was the wrong source to generalise from.

   **Calibration.** Against BSBM's published 0.94, the four candidate variants
   give 0.9612 / 0.9511 / 0.9582 / **0.9482**; the closest is the reference
   definition, and the previous implementation was the furthest.

   `RDF_Coherence` is now the corrected metric. `RDF_Coherence_TypeIncl`
   preserves the previous definition so numbers published before the correction
   remain reproducible and the two can be compared row by row.

   **Every previously reported coherence number is superseded.** The shifts are
   not uniform — they depend on how many properties each type carries — so
   rankings move, not just values:

   | | corrected | previous |
   |---|---:|---:|
   | rudof ShEx high (E2) | 0.8199 | 0.9824 |
   | rudof ShEx low (E2) | **0.4305** | 0.7437 |
   | GAIA high (E2) | 0.0668 | 0.3913 |
   | LUBM reference (E2) | 0.8926 | 0.9266 |
   | E1 span, fill 0.1→1.0 | **0.3908** | 0.2385 |
   | E3 floor spread across schemas | 0.2055 | 0.5999 |

   Two consequences worth stating plainly:

   * **rudof's controllable span grew, from 0.239 to 0.391.** The correction
     helps the central claim rather than weakening it.
   * **rudof's low configuration now lands at 0.4305 on LUBM**, inside the band
     Duan reports for real-world data (at or below ~0.6) and below the 0.79 floor
     of their benchmark range. The tool moves LUBM data out of synthetic-looking
     territory and into real-looking territory — measurable on the hand-written
     schema, with no extraction step required.

   E3's floor spread shrank from 0.60 to 0.21. Still an order of magnitude above
   run-to-run noise, so the claim holds; the number in it changes.

0b. ~~**Is rudof's coherence floor a limit of the tool?**~~ **Settled: no, it is
   the schema.** Holding the tool, config, entity count and seed fixed and
   varying only the schema moves the floor from 0.377 to 0.893 and the span by
   8.5x (E3). The 0.744 floor measured on LUBM is a property of LUBM. Still open:
   whether a schema mined from a *real* dataset lands in Duan et al.'s ~0.45
   band -- the BSBM-derived schema reaches 0.377, so there is headroom, but no
   real dataset has been run through it yet.
1. **Is LUBM a member of E2 or only a reference line?** It is fixed-schema, so it
   cannot participate in a controllability comparison, but its coherence anchors
   the scale. Recommendation: draw it as a horizontal reference line.
2. ~~**Is E4 in scope?**~~ **Settled: yes.** `rudof_generate` already computes
   both metrics. E4 runs end to end. What is *not* settled is the SHACL
   asymmetry it exposed — see E4 above.
3. **Does sheXer scale to the E3 source datasets?** Still open at full scale.
   At smoke scale all five extractions finish in under 2 s each. BSBM at 35M
   triples is the binding case; if sampling is required, the extracted shapes
   approximate a sample rather than the dataset, and that must be stated.
4. **Does the bracketing claim hold?** *(now future work -- superseded by E3)*
   **Unsettled, and less stable than expected.** The smoke chain was run twice from scratch. It did not give the
   same answer:

   | source | run A: own | run A: rudof range | | run B: own | run B: rudof range | |
   |---|---:|---|:--|---:|---|:--|
   | BSBM | 0.9612 | [0.3777, 0.9770] | in | 0.9612 | [0.3774, 0.9770] | in |
   | SimplexKG | 0.7711 | [0.6704, 0.8611] | in | 0.7906 | [0.6868, 0.7888] | **out** by 0.0018 |
   | LEMMING | 0.8069 | [0.8155, 0.9919] | out by 0.009 | 0.8107 | [0.8339, 1.0000] | out |
   | PyGraft | 0.5001 | [0.8543, 0.9508] | out | 0.5887 | [0.8926, 0.9634] | out |
   | WatDiv | 0.9994 | [0.6789, 0.9585] | out | 0.9994 | [0.6762, 0.9585] | out |

   **Why it moved.** BSBM and WatDiv are seed-fixed and reproduce exactly.
   LEMMING, SimplexKG and PyGraft are not: their phase-1 output differs between
   runs, so the extracted shapes differ, so rudof's range differs. SimplexKG
   crossed the boundary on a 0.02 shift in its own coherence.

   **What this means for the design.** Extraction is pinned to run 1 (§E3), which
   was justified as reproducibility — PyGraft draws a new schema each run, so
   mining across runs is meaningless. But for the non-deterministic generators it
   also means the *whole phase-2 range* is conditional on one arbitrary draw.
   With `runs: 10` in phase 2, the error bars measure rudof's variance, not the
   variance in the schema it was given. That is a real limitation and has to be
   stated rather than averaged away.

   **Provisional reading.** WatDiv is above rudof's ceiling in both runs
   (0.9994 vs 0.9585) and PyGraft far below its floor in both — those two look
   like genuine limits rather than noise. LEMMING and SimplexKG sit within
   ~0.02 of the boundary, which is the same order as their own run-to-run
   spread, so neither run answers the question for them.

   PyGraft is separately interesting: its low-fill run is *more* coherent than
   its high-fill run in both chains. That is possible because dropping a rare
   property removes it from `P(t)` — the denominator — as well as from the
   numerator. If it survives at full scale it is a finding about the metric, not
   a bug.

   The claim as stated ("for every generator X") is already too strong for what
   the data shows. Either it weakens to a per-generator report, or the failures
   become the finding. Both are defensible; fabricating a clean result is not.

## 8. Cost

| Profile | Runs | Smoke wall-clock | Notes |
|---|---:|---:|---|
| `e1` | 200 | 23 s | 20 configs × 10 |
| `e2` | 180 | 1 m 17 s | 18 configs × 10, incl. every reference generator |
| `e3` | 105 | 49 s | 7 schemas × 5 fill points × 3, plus 6 extractions |
| `e4` | 12 | 15 s | deterministic; 4 schemas × 3 |
| `e5` | 20 | 3 m 58 s | Synthea dominates |
| **total** | **517** | **~4 min** | |

Every profile passes at smoke scale. At publication scale E2 and E3 dominate:
BSBM at 100k products is 35M triples, and *measuring* 35M triples takes longer
than generating them. E3 additionally runs sheXer over datasets of that size,
which is the one cost with no smoke-scale evidence behind it — extraction takes
under 2 s at 100k triples, but that says nothing about 35M. Estimate an
overnight run for E2 + E3, minutes to an hour for the rest.

Order: **E1** → **E4** (both cheap and already verified) → **E3** (needs
`e3_sources` and the extraction first) → **E2** → **E5**.

**Build the images before timing anything.** The compose build context is the
project root, so a cold build of all eleven images takes several minutes and
will otherwise be attributed to whichever profile runs first.

---

## 9. Harness changes

The pipeline was four stages — build, generate, metrics, charts — over a single
profile, with no dependency between profiles. E3 needed three additions; all
three are now in place.

### 9.1 An extractor stage — **done**

sheXer does not fit the generator contract: it consumes a dataset and emits a
schema, not RDF plus a `report.json`. It lives outside `generators/` for a
reason the loader depends on — `Workspace.load_generators` globs
`generators/*/generator.yaml`, one level deep, so an extractor placed a level
deeper is invisible to it:

```
generators/_extractors/shexer/          Dockerfile + entrypoint.py
    input : /in   (a completed run directory, read-only)
    output: /out/<name>.shex + <name>.extraction.json
```

sheXer is pip-installable, so the image is a single install line. Driven by a
CLI verb that sits outside the generate/measure loop:

```bash
python3 main.py extract --profile e3_sources
```

The source profile's name is appended to the output directory
(`schemas/extracted/e3_sources/`), so a smoke extraction can never overwrite a
full-scale one — those differ by three orders of magnitude in input size and
would otherwise collide under the same filename.

It emits `extraction.json` rather than `report.json`: an extraction has no
triple count, no RDF format and no throughput, so reusing the generator report
would mean filling required fields with fiction.

**Custom datatypes.** BSBM stamps its prices with `bsbm:USD`, and rudof refuses
a schema naming a datatype it has no generator for — one line out of six hundred
killed the whole round trip. The extractor now rewrites non-XSD datatypes to
`xsd:string` and records exactly which ones in `extraction.json`
(`mapped_datatypes`). This is an approximation, and a stated one: a custom
datatype constrains the *value space* of a literal, whereas coherence is
computed from which properties each type carries, so the substitution changes
the literals and leaves the measured quantity untouched. Across the five source
datasets, exactly one datatype was mapped, once.

### 9.2 Profiles that reference generated artefacts — **done**

`e3_rudof.yaml` names schemas that do not exist until phase 1 and the extraction
have run. No loader change was needed: the schema path is an opaque string on
the host and is resolved inside the container, which already fails with the list
of available schemas if it is missing. The ordering is documented in the profile
header, and a test asserts each phase-2 schema path points at its own phase-1
extraction rather than the other scale's.

### 9.3 A bracketing chart — **done**

`coherence_bracketing.pdf`: one triplet per generator, `[source, rudof-low,
rudof-high]`, with the rudof interval drawn as a span behind the bars and a
per-generator "bracketed"/"outside" verdict above them. The naming convention is
as suggested — `src_<name>` in phase 1, `rudof_<name>_{high,low}` in phase 2.

The chart spans two profiles, which the pipeline had no way to express. Phase 2
declares its counterpart in the profile itself:

```yaml
compare_with: e3_sources
```

Declarative rather than inferred, so the dependency is visible in the profile
that has it. A missing baseline is not an error — the two phases are run
separately by design, so plotting phase 2 first produces the chart without it.

### 9.4 Build context

`.dockerignore` must exclude `data/`. The compose build context is the project
root so images can copy the shared entry library, which means the generated
datasets are otherwise uploaded to the Docker daemon on every build. Measured at
2.0 GB, this turned cached builds into multi-minute operations and made the
smoke profiles appear to hang. Context is 56 MB with the file in place.

**LEMMING's build is separately fragile** and this is not the same problem. It
is the only generator compiled at image-build time — `git clone` plus a Maven
package — and the clone has hung indefinitely more than once, observed wedged at
24 minutes with no CPU inside the container. Git low-speed timeouts now convert
that into a fast failure instead of a silent stall. Vendoring the artefact would
remove the risk entirely but the shaded jar is 97 MB, too large to commit, so
the operational rule stands instead: **build all images once before any timing
run, then pass `--skip-build`.** With that, the full E3 chain — phase 1,
extraction, phase 2 — completes in 47 s at smoke scale.

### 9.5 Conformance columns — **done**

E4 needed no work inside `rudof_generate` after all. The report gained an
optional `conformance` block, filled by the rudof entrypoint from the stats
sidecar and rejected at read time if it carries an unknown key — these numbers
are published, so a misspelling must fail rather than yield a column of blanks.
Six new CSV columns, blank for every generator that consumes no schema.

### 9.6 Not required

E1, E2 and E5 need no harness changes — only profile files.
