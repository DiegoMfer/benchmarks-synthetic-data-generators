"""Compute metrics for a completed run directory.

This replaces two functions from the old codebase:

``_discover_files``
    An if/elif chain hardcoding each generator's output filename, duplicated
    from the generator classes 600 lines away. Now the filenames come from the
    run's own ``report.json`` (authoritative -- the container listed what it
    actually wrote), falling back to the ``data_files`` declared in
    ``generator.yaml``.

``extract_performance_metrics``
    A 100-line waterfall probing five possible JSON layouts. Now a plain field
    read, because the container emits the canonical schema.
"""

from __future__ import annotations

import gc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import GeneratorSpec
from ..report import BenchmarkReport, ReportError
from . import fhir
from .accumulator import METRIC_FIELDS, MetricsAccumulator
from .parsers import parse_into

#: CSV column name for each canonical conformance key. Only generators that
#: consume a schema populate these; everything else leaves the columns blank,
#: which is the honest representation of "this question does not apply".
CONFORMANCE_FIELDS: dict[str, str] = {
    "triple_validity_pct": "Triple_Validity_Pct",
    "shape_translation_loss_pct": "Shape_Translation_Loss_Pct",
    "schema_constraints": "Schema_Constraints",
    "constraints_represented": "Constraints_Represented",
    "valid_triples": "Valid_Triples",
    "generated_triples": "Generated_Triples",
}


@dataclass
class RunMetrics:
    """Everything measured for one run, ready to become one CSV row."""

    experiment: str
    generator: str
    run: int
    rdf: dict[str, Any] = field(default_factory=dict)
    perf: dict[str, Any] = field(default_factory=dict)
    #: Domain-specific metrics, populated only when the data warrants them.
    #: Empty for every profile but the FHIR case study.
    domain: dict[str, Any] = field(default_factory=dict)
    #: Schema-conformance figures, empty for generators that consume no schema.
    #: Kept separate from ``rdf`` because these are the generator's own claims
    #: about its input, not something measured from the output graph.
    conformance: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.rdf)


def compute_run_metrics(
    run_dir: Path,
    spec: GeneratorSpec,
    experiment: str,
    run: int,
    *,
    verbose: bool = True,
) -> RunMetrics:
    """Measure one run directory: RDF structure plus reported performance."""
    result = RunMetrics(experiment=experiment, generator=spec.name, run=run)

    try:
        report = BenchmarkReport.read(run_dir / "report.json")
    except ReportError as exc:
        result.error = str(exc)
        return result

    result.params = report.params
    result.notes = list(report.notes)
    result.conformance = _conformance_row(report)

    files, rdf_format = _resolve_data_files(run_dir, report, spec)
    if not files:
        result.error = f"no data files found in {run_dir}"
        return result

    if verbose:
        print(f"  {experiment} run_{run}: reading {len(files)} file(s) ...", flush=True)

    acc = MetricsAccumulator()
    for path in files:
        parse_into(path, rdf_format, acc, verbose=verbose)

    result.rdf = acc.finalize()
    del acc
    gc.collect()

    # A second, typed pass, and only when the data is actually FHIR. The shared
    # sink flattens terms to strings, and every FHIR metric turns on telling a
    # blank node from an IRI from a literal.
    result.domain = fhir.analyse(files, rdf_format)
    if result.domain and verbose:
        print(f"    FHIR: {result.domain.get('FHIR_Resource_Types')} resource type(s), "
              f"{result.domain.get('FHIR_R4_Coverage_Pct', 0):.1f}% of R4", flush=True)

    measured = result.rdf.get("RDF_Triples")
    reported = report.output.triples_reported
    result.perf = {
        "Duration_Seconds": report.duration_seconds,
        "Triples_Reported": reported,
        "Triples_Measured": measured,
        "Throughput_Reported": report.throughput_reported,
        "Throughput_Measured": (
            measured / report.duration_seconds
            if measured and report.duration_seconds > 0
            else None
        ),
        "Tool": report.tool.name,
        "Tool_Version": report.tool.version or "",
    }

    # A tool that miscounts its own output is a finding, not a crash. Surface it
    # rather than silently publishing whichever number happened to be picked.
    if reported is not None and measured and abs(reported - measured) > max(1, 0.01 * measured):
        result.notes.append(
            f"tool reported {reported:,} triples but {measured:,} were measured"
        )

    if not result.rdf:
        result.error = "parsed 0 triples"

    return result


def _conformance_row(report: BenchmarkReport) -> dict[str, Any]:
    """Map the report's conformance block onto its CSV column names."""
    return {
        column: report.conformance[key]
        for key, column in CONFORMANCE_FIELDS.items()
        if report.conformance.get(key) is not None
    }


def _resolve_data_files(
    run_dir: Path, report: BenchmarkReport, spec: GeneratorSpec
) -> tuple[list[Path], str]:
    """Find the RDF files for a run.

    The report is authoritative because the container listed exactly what it
    wrote -- including for generators like LUBM that emit a variable number of
    files. ``generator.yaml`` supplies the fallback so a run whose report
    predates a filename change is still measurable.
    """
    files = [run_dir / name for name in report.output.files]
    existing = [f for f in files if f.exists()]

    if not existing:
        for pattern in spec.data_files:
            existing.extend(sorted(run_dir.glob(pattern)))

    # report.json and container.log are metadata, never RDF payload.
    return [f for f in existing if f.name not in {"report.json", "container.log"}], (
        report.output.rdf_format or spec.rdf_format
    )


__all__ = ["RunMetrics", "compute_run_metrics", "METRIC_FIELDS", "CONFORMANCE_FIELDS"]
