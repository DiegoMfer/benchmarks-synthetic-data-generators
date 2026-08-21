"""Tests for the canonical report contract.

The whole point of the schema is that a malformed report fails loudly instead of
silently degrading into missing metrics, so most of these assert on rejection.
"""

from __future__ import annotations

import json

import pytest

from rdfbench.report import (
    SCHEMA_VERSION,
    BenchmarkReport,
    OutputInfo,
    ReportError,
    ToolInfo,
)


def valid_raw(**overrides) -> dict:
    raw = {
        "generator": "bsbm",
        "params": {"products": 100},
        "started_at": "2026-07-28T12:00:00+00:00",
        "duration_seconds": 3.5,
        "output": {
            "files": ["dataset.ttl"],
            "rdf_format": "turtle",
            "triples_reported": 700,
            "bytes_total": 1234,
        },
        "tool": {"name": "bsbmtools", "version": "0.2"},
        "exit_code": 0,
        "schema_version": SCHEMA_VERSION,
        "notes": [],
    }
    raw.update(overrides)
    return raw


def test_round_trips_through_disk(tmp_path):
    report = BenchmarkReport(
        generator="bsbm",
        params={"products": 100},
        started_at="2026-07-28T12:00:00+00:00",
        duration_seconds=3.5,
        output=OutputInfo(files=["dataset.ttl"], rdf_format="turtle", triples_reported=700),
        tool=ToolInfo(name="bsbmtools", version="0.2"),
    )
    path = tmp_path / "report.json"
    report.write(path)

    loaded = BenchmarkReport.read(path)
    assert loaded.generator == "bsbm"
    assert loaded.output.files == ["dataset.ttl"]
    assert loaded.output.triples_reported == 700
    assert loaded.tool.name == "bsbmtools"


def test_throughput_is_derived_from_the_reported_count():
    report = BenchmarkReport.from_dict(valid_raw())
    assert report.throughput_reported == pytest.approx(700 / 3.5)


def test_throughput_is_none_when_the_tool_reports_no_count():
    """A tool that cannot count its output must not get a fabricated rate."""
    raw = valid_raw()
    raw["output"]["triples_reported"] = None
    assert BenchmarkReport.from_dict(raw).throughput_reported is None


def test_throughput_is_none_for_a_zero_duration():
    raw = valid_raw(duration_seconds=0)
    assert BenchmarkReport.from_dict(raw).throughput_reported is None


@pytest.mark.parametrize(
    "field", ["generator", "params", "started_at", "duration_seconds", "output", "tool"]
)
def test_missing_required_field_is_rejected(field):
    raw = valid_raw()
    del raw[field]
    with pytest.raises(ReportError, match=field):
        BenchmarkReport.from_dict(raw)


def test_schema_version_mismatch_is_rejected():
    """A stale image must fail rather than be read with the wrong assumptions."""
    with pytest.raises(ReportError, match="schema_version"):
        BenchmarkReport.from_dict(valid_raw(schema_version="0.9"))


def test_unknown_rdf_format_is_rejected():
    raw = valid_raw()
    raw["output"]["rdf_format"] = "turtle-ish"
    with pytest.raises(ReportError, match="rdf_format"):
        BenchmarkReport.from_dict(raw)


def test_empty_file_list_is_rejected():
    raw = valid_raw()
    raw["output"]["files"] = []
    with pytest.raises(ReportError, match="files"):
        BenchmarkReport.from_dict(raw)


def test_negative_duration_is_rejected():
    with pytest.raises(ReportError, match="duration_seconds"):
        BenchmarkReport.from_dict(valid_raw(duration_seconds=-1))


def test_tool_name_is_required():
    with pytest.raises(ReportError, match="tool.name"):
        BenchmarkReport.from_dict(valid_raw(tool={"version": "1.0"}))


def test_unreadable_file_is_reported_with_its_path(tmp_path):
    path = tmp_path / "missing.json"
    with pytest.raises(ReportError, match="missing.json"):
        BenchmarkReport.read(path)


def test_malformed_json_is_reported_with_its_path(tmp_path):
    path = tmp_path / "report.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ReportError, match="report.json"):
        BenchmarkReport.read(path)


def test_notes_survive_a_round_trip(tmp_path):
    raw = valid_raw(notes=["GAIA does not report a triple count"])
    path = tmp_path / "report.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert BenchmarkReport.read(path).notes == ["GAIA does not report a triple count"]


# -- conformance (E4) -----------------------------------------------------


def test_conformance_defaults_to_empty_for_a_generator_that_reports_none():
    """Most generators consume no schema, so the block is absent, not zeroed."""
    assert BenchmarkReport.from_dict(valid_raw()).conformance == {}


def test_conformance_survives_a_round_trip(tmp_path):
    block = {"triple_validity_pct": 100.0, "shape_translation_loss_pct": 16.19}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(valid_raw(conformance=block)), encoding="utf-8")
    assert BenchmarkReport.read(path).conformance == block


def test_unknown_conformance_key_is_rejected():
    """These numbers are published, so a misspelled key must fail loudly."""
    with pytest.raises(ReportError, match="validty_pct"):
        BenchmarkReport.from_dict(valid_raw(conformance={"validty_pct": 100.0}))


def test_non_numeric_conformance_value_is_rejected():
    with pytest.raises(ReportError, match="triple_validity_pct"):
        BenchmarkReport.from_dict(valid_raw(conformance={"triple_validity_pct": "100%"}))
