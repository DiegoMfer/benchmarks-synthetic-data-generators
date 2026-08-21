"""Export measured runs to CSV.

Column names for the RDF metrics match the original ``metrics_comparison.csv``
so existing plots and any numbers already written into the paper stay
comparable. The performance columns are new: instead of a single
``Perf_Total_Triples`` whose provenance varied per generator, the tool's claim
and the independent measurement are separate columns, so a discrepancy is
visible in the table rather than hidden behind whichever value was picked.

Written with the stdlib ``csv`` module -- there is no reason to pull pandas into
the write path.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from ..metrics.accumulator import METRIC_FIELDS
from ..metrics.compute import CONFORMANCE_FIELDS, RunMetrics
from ..metrics.fhir import FHIR_FIELDS

IDENTITY_FIELDS = ("Experiment", "Generator", "Run")
PERF_FIELDS = (
    "Duration_Seconds",
    "Triples_Reported",
    "Triples_Measured",
    "Throughput_Reported",
    "Throughput_Measured",
    "Tool",
    "Tool_Version",
)
TRAILING_FIELDS = ("Params", "Notes", "Error")

#: Blank for every generator that consumes no schema, which is most of them.
CONFORMANCE_COLUMNS = tuple(CONFORMANCE_FIELDS.values())

#: Blank for every profile but the FHIR case study.
DOMAIN_COLUMNS = tuple(FHIR_FIELDS.values())

FIELDNAMES = (
    *IDENTITY_FIELDS,
    *PERF_FIELDS,
    *METRIC_FIELDS,
    *CONFORMANCE_COLUMNS,
    *DOMAIN_COLUMNS,
    *TRAILING_FIELDS,
)


def write_metrics_csv(metrics: Iterable[RunMetrics], path: Path) -> Path:
    """Write one row per run. Failed runs are kept, with ``Error`` populated."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for metric in metrics:
            writer.writerow(_row(metric))
    return path


def _row(metric: RunMetrics) -> dict[str, object]:
    row: dict[str, object] = {
        "Experiment": metric.experiment,
        "Generator": metric.generator,
        "Run": metric.run,
        "Params": json.dumps(metric.params, sort_keys=True),
        "Notes": " | ".join(metric.notes),
        "Error": metric.error,
    }
    for field in PERF_FIELDS:
        row[field] = metric.perf.get(field)
    for field in METRIC_FIELDS:
        row[field] = metric.rdf.get(field)
    for field in CONFORMANCE_COLUMNS:
        row[field] = metric.conformance.get(field)
    for field in DOMAIN_COLUMNS:
        row[field] = metric.domain.get(field)
    return row


def read_metrics_csv(path: Path) -> list[dict[str, str]]:
    """Read a metrics CSV back, e.g. for the parity check against the old repo."""
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
