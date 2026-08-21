"""Canonical benchmark report.

Every generator container writes exactly one ``report.json`` in this shape. The
host never inspects generator-specific fields, so adding a generator can never
require touching host code -- which is what the old
``extract_performance_metrics`` if/elif waterfall existed to work around.

The important distinction this schema enforces:

``triples_reported``
    What the generator *claims* it produced. Nullable, because some tools do not
    report a trustworthy number (GAIA only prints an instance count).

``triples_measured``
    Computed independently by :mod:`rdfbench.metrics` from the actual RDF. Never
    supplied by a container.

Keeping both means a tool that lies about its output shows up as a discrepancy
in the results table instead of silently becoming the published number.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"

#: Values accepted for ``output.rdf_format``. These are rdflib parser names so
#: the metrics layer can pass them straight through.
RDF_FORMATS = frozenset({"turtle", "nt", "xml", "json-ld", "n3", "trig"})


class ReportError(ValueError):
    """Raised when a container produced a report that does not meet the contract."""


@dataclass
class ToolInfo:
    """Which underlying generator binary ran, and at what version."""

    name: str
    version: str | None = None


@dataclass
class OutputInfo:
    """What the generator wrote into the mounted output directory."""

    files: list[str]
    rdf_format: str
    triples_reported: int | None = None
    bytes_total: int = 0


#: Keys a generator may report under ``conformance``. All optional: a generator
#: that does not translate a schema has nothing to say here, and an empty dict
#: is the correct answer rather than a zero.
CONFORMANCE_KEYS = (
    "generated_triples",
    "valid_triples",
    "triple_validity_pct",
    "schema_constraints",
    "constraints_represented",
    "shape_translation_loss_pct",
)


@dataclass
class BenchmarkReport:
    generator: str
    params: dict[str, Any]
    started_at: str
    duration_seconds: float
    output: OutputInfo
    tool: ToolInfo
    exit_code: int = 0
    schema_version: str = SCHEMA_VERSION
    #: Free-text caveats that belong with the data, e.g. GAIA's inability to
    #: report a true triple count. Surfaced in the results CSV.
    notes: list[str] = field(default_factory=list)
    #: How much of the input schema survived translation into the generator's
    #: internal representation, and how much of the output satisfies it. Only a
    #: schema-driven generator can fill this in; everything else leaves it empty.
    #: Keys are :data:`CONFORMANCE_KEYS`.
    conformance: dict[str, Any] = field(default_factory=dict)

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> BenchmarkReport:
        """Load and validate a report written by a container."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReportError(f"{path}: unreadable report ({exc})") from exc
        return cls.from_dict(raw, source=str(path))

    @classmethod
    def from_dict(cls, raw: dict[str, Any], source: str = "<dict>") -> BenchmarkReport:
        if not isinstance(raw, dict):
            raise ReportError(f"{source}: report must be a JSON object")

        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ReportError(
                f"{source}: schema_version {version!r}, expected {SCHEMA_VERSION!r}. "
                "Rebuild the generator image."
            )

        missing = [
            key
            for key in ("generator", "params", "started_at", "duration_seconds", "output", "tool")
            if key not in raw
        ]
        if missing:
            raise ReportError(f"{source}: missing required field(s): {', '.join(missing)}")

        out = raw["output"]
        if not isinstance(out, dict):
            raise ReportError(f"{source}: 'output' must be an object")
        for key in ("files", "rdf_format"):
            if key not in out:
                raise ReportError(f"{source}: output.{key} is required")
        if out["rdf_format"] not in RDF_FORMATS:
            raise ReportError(
                f"{source}: output.rdf_format {out['rdf_format']!r} not one of "
                f"{sorted(RDF_FORMATS)}"
            )
        if not isinstance(out["files"], list) or not out["files"]:
            raise ReportError(f"{source}: output.files must be a non-empty list")

        duration = raw["duration_seconds"]
        if not isinstance(duration, (int, float)) or duration < 0:
            raise ReportError(f"{source}: duration_seconds must be a non-negative number")

        tool = raw["tool"]
        if not isinstance(tool, dict) or "name" not in tool:
            raise ReportError(f"{source}: tool.name is required")

        return cls(
            generator=raw["generator"],
            params=raw["params"],
            started_at=raw["started_at"],
            duration_seconds=float(duration),
            output=OutputInfo(
                files=list(out["files"]),
                rdf_format=out["rdf_format"],
                triples_reported=out.get("triples_reported"),
                bytes_total=int(out.get("bytes_total", 0)),
            ),
            tool=ToolInfo(name=tool["name"], version=tool.get("version")),
            exit_code=int(raw.get("exit_code", 0)),
            schema_version=version,
            notes=list(raw.get("notes", [])),
            conformance=_conformance(raw.get("conformance"), source),
        )

    # -- derived ----------------------------------------------------------

    @property
    def throughput_reported(self) -> float | None:
        """Triples/second according to the tool's own count, if it gave one."""
        triples = self.output.triples_reported
        if triples is None or self.duration_seconds <= 0:
            return None
        return triples / self.duration_seconds


def _conformance(raw: Any, source: str) -> dict[str, Any]:
    """Validate the optional conformance block.

    Unknown keys are rejected rather than carried through: this block feeds
    published percentages, so a generator inventing its own key names must fail
    at read time instead of quietly contributing a column of blanks.
    """
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ReportError(f"{source}: 'conformance' must be an object")
    unknown = set(raw) - set(CONFORMANCE_KEYS)
    if unknown:
        raise ReportError(
            f"{source}: conformance has unknown key(s): {', '.join(sorted(unknown))}. "
            f"Known: {', '.join(CONFORMANCE_KEYS)}"
        )
    for key, value in raw.items():
        if value is not None and not isinstance(value, (int, float)):
            raise ReportError(f"{source}: conformance.{key} must be a number, got {value!r}")
    return dict(raw)
