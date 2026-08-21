"""Tests for the metric accumulator.

Coherence is the number the paper reports, so it is pinned against graphs whose
expected value is computed by hand rather than against a recorded output.
"""

from __future__ import annotations

import pytest

from rdfbench.metrics.accumulator import (
    RDF_TYPE_BRACKETED,
    RDF_TYPE_PLAIN,
    MetricsAccumulator,
)

TYPE = RDF_TYPE_PLAIN


def build(triples: list[tuple[str, str, str]]) -> dict:
    acc = MetricsAccumulator()
    for triple in triples:
        acc.add_triple(*triple)
    return acc.finalize()


def test_empty_graph_yields_no_metrics():
    assert MetricsAccumulator().finalize() == {}


def test_counts_distinct_terms():
    metrics = build(
        [
            ("s1", "p1", "o1"),
            ("s1", "p2", "o2"),
            ("s2", "p1", "o1"),
        ]
    )
    assert metrics["RDF_Triples"] == 3
    assert metrics["RDF_Subjects"] == 2
    assert metrics["RDF_Predicates"] == 2
    assert metrics["RDF_Objects"] == 2


def test_duplicate_triples_count_once_per_occurrence():
    """Triples are counted as emitted; only *terms* are deduplicated."""
    metrics = build([("s", "p", "o"), ("s", "p", "o")])
    assert metrics["RDF_Triples"] == 2
    assert metrics["RDF_Subjects"] == 1


def test_degrees():
    # s1 has out-degree 2, s2 out-degree 1; o1 has in-degree 2, o2 in-degree 1.
    metrics = build([("s1", "p", "o1"), ("s1", "p", "o2"), ("s2", "p", "o1")])
    assert metrics["RDF_Mean_Outdegree"] == pytest.approx(1.5)  # (2 + 1) / 2
    assert metrics["RDF_Mean_Indegree"] == pytest.approx(1.5)  # (2 + 1) / 2


def test_perfect_coherence_when_all_instances_share_all_properties():
    """Two instances of one type, identical property sets -> CV = 1."""
    triples = []
    for subject in ("a", "b"):
        triples.append((subject, TYPE, "Person"))
        triples.append((subject, "name", f"{subject}-name"))
        triples.append((subject, "age", "30"))
    metrics = build(triples)

    # P(t) = {type, name, age} = 3, I(t) = 2, sum|props| = 3 + 3 = 6
    # CV = 6 / (3 * 2) = 1.0
    assert metrics["RDF_Coherence"] == pytest.approx(1.0)
    assert metrics["RDF_Type_Coverage_Avg"] == pytest.approx(1.0)
    assert metrics["RDF_Classes"] == 1


def test_partial_coherence_is_computed_by_the_duan_formula():
    """One instance carries an extra property the other lacks.

    rdf:type is not one of the properties: the LDBC reference procedure filters
    it out of both the numerator and the property count.
    """
    triples = [
        ("a", TYPE, "Person"),
        ("a", "name", "a-name"),
        ("a", "age", "30"),
        ("b", TYPE, "Person"),
        ("b", "name", "b-name"),
    ]
    metrics = build(triples)

    # P(t) = {name, age} = 2, I(t) = 2
    # sum|props| = 2 (a: name,age) + 1 (b: name) = 3
    # CV = 3 / (2 * 2) = 0.75
    assert metrics["RDF_Coherence"] == pytest.approx(3 / 4)
    # Counting rdf:type instead: P = 3, sum = 5, CV = 5/6.
    assert metrics["RDF_Coherence_TypeIncl"] == pytest.approx(5 / 6)


def test_coherence_weights_each_type_by_its_properties_plus_instances():
    """Duan weights by (|P(t)| + |I(t)|), not by instance count alone.

    The rationale in the source is to give more influence to types that are both
    populous and wide. Weighting by instances alone -- which this code did before
    the definition was checked against the LDBC reference procedure -- shifts the
    result whenever the two skew differently. The fixture is chosen so that all
    three plausible aggregations give different answers, which is the only way
    this assertion can distinguish them.
    """
    triples = [
        # Type A: 6 instances, one property each, perfectly regular.
        *[(f"a{i}", TYPE, "A") for i in range(6)],
        *[(f"a{i}", "p", "v") for i in range(6)],
        # Type B: 2 instances, one holding a property the other lacks.
        ("b0", TYPE, "B"), ("b0", "q", "v"), ("b0", "r", "v"),
        ("b1", TYPE, "B"), ("b1", "q", "v"),
    ]
    metrics = build(triples)

    # Excluding rdf:type:
    #   A: P = {p} = 1, I = 6, sum = 6     -> CV_A = 6 / 6  = 1.0,  weight 1+6 = 7
    #   B: P = {q, r} = 2, I = 2, sum = 3  -> CV_B = 3 / 4  = 0.75, weight 2+2 = 4
    cv_a, cv_b = 1.0, 0.75
    duan = (7 / 11) * cv_a + (4 / 11) * cv_b        # 0.9091
    unweighted = (cv_a + cv_b) / 2                   # 0.8750
    instance_weighted = (6 / 8) * cv_a + (2 / 8) * cv_b  # 0.9375

    assert metrics["RDF_Coherence"] == pytest.approx(duan)
    assert metrics["RDF_Type_Coverage_Avg"] == pytest.approx(unweighted)
    # The two aggregations this could be confused with, both excluded.
    assert metrics["RDF_Coherence"] != pytest.approx(unweighted)
    assert metrics["RDF_Coherence"] != pytest.approx(instance_weighted)


def test_untyped_data_has_zero_coherence():
    """With no rdf:type triples there are no types to be coherent about."""
    metrics = build([("s", "p", "o")])
    assert metrics["RDF_Classes"] == 0
    assert metrics["RDF_Coherence"] == 0.0
    assert metrics["RDF_Type_Coverage_Avg"] == 0.0


def test_rdf_type_is_recognised_in_both_serialisation_forms():
    """N-Triples yields <...#type>; rdflib yields the bare IRI.

    Both must intern to the same predicate, otherwise class counts would depend
    on which serialisation a generator happened to emit.
    """
    bracketed = build([("<s>", RDF_TYPE_BRACKETED, "<C>")])
    plain = build([("s", RDF_TYPE_PLAIN, "C")])

    assert bracketed["RDF_Classes"] == 1
    assert plain["RDF_Classes"] == 1
    assert bracketed["RDF_Coherence"] == plain["RDF_Coherence"]


def test_multityped_instance_counts_toward_every_type():
    triples = [
        ("s", TYPE, "A"),
        ("s", TYPE, "B"),
        ("s", "p", "v"),
    ]
    metrics = build(triples)
    assert metrics["RDF_Classes"] == 2
    # Each type has one instance holding both properties, so both are perfectly
    # coherent in isolation.
    assert metrics["RDF_Coherence"] == pytest.approx(1.0)


def test_finalize_releases_internal_state():
    """finalize() deletes its heavy structures; the instance is single-use."""
    acc = MetricsAccumulator()
    acc.add_triple("s", "p", "o")
    acc.finalize()
    with pytest.raises(AttributeError):
        _ = acc.type_instances


# -- rdf:type as a property, or not ---------------------------------------


def test_a_type_only_graph_scores_zero_not_one():
    """Why excluding rdf:type is the correct reading.

    Every instance has rdf:type and nothing else. Counting it, P(t) is
    {rdf:type}, every instance holds all of it, and the score is a perfect 1.0
    for a graph carrying no information -- which also made coherence non-monotone
    in property fill. Excluding it, as the reference procedure does, the same
    graph correctly scores 0.0.
    """
    metrics = build([("s1", TYPE, "A"), ("s2", TYPE, "A"), ("s3", TYPE, "A")])
    assert metrics["RDF_Coherence"] == pytest.approx(0.0)
    assert metrics["RDF_Coherence_TypeIncl"] == pytest.approx(1.0)


def test_the_two_variants_agree_only_when_every_property_is_held_by_everyone():
    """A fully populated type scores 1.0 either way; a partial one does not."""
    full = build([
        ("s1", TYPE, "A"), ("s1", "p", "v"), ("s1", "q", "v"),
        ("s2", TYPE, "A"), ("s2", "p", "v"), ("s2", "q", "v"),
    ])
    assert full["RDF_Coherence"] == pytest.approx(1.0)
    assert full["RDF_Coherence_TypeIncl"] == pytest.approx(1.0)

    # s2 drops q: 5 of 6 property slots filled with rdf:type, 3 of 4 without.
    partial = build([
        ("s1", TYPE, "A"), ("s1", "p", "v"), ("s1", "q", "v"),
        ("s2", TYPE, "A"), ("s2", "p", "v"),
    ])
    assert partial["RDF_Coherence"] == pytest.approx(3 / 4)
    assert partial["RDF_Coherence_TypeIncl"] == pytest.approx(5 / 6)
