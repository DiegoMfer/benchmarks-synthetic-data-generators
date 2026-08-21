"""Single-pass RDF metric computation over compact integer IDs.

Ported essentially unchanged from the original ``generate_csv_metrics.py`` --
this design is what makes 35M-triple datasets measurable on a workstation, and
changing it would change the published numbers.

Three deliberate memory choices, all load-bearing:

* every distinct URI/literal is interned to an ``int`` the first time it is
  seen, so the degree maps and type sets hold ints rather than long strings;
* ``__slots__`` avoids a per-instance ``__dict__``;
* :meth:`MetricsAccumulator.finalize` frees each structure the moment it has
  been consumed, because peak memory occurs during finalisation, not parsing.

Coherence is the structuredness measure of Duan et al., *Apples and Oranges: A
Comparison of RDF Benchmarks and Real RDF Datasets* (SIGMOD 2011). For a type
``t`` with instance set ``I(t)`` and predicate set ``P(t)``::

    CV(t) = sum(|properties(s)| for s in I(t)) / (|P(t)| * |I(t)|)

Two aggregations are reported: instance-weighted (``RDF_Coherence``) and the
plain mean over types (``RDF_Type_Coverage_Avg``).
"""

from __future__ import annotations

import gc
from collections import defaultdict
from typing import Any

#: rdf:type in both the forms it can arrive in. N-Triples parsing yields the
#: angle-bracketed spelling while rdflib's ``str()`` yields the bare IRI; both
#: must intern to the same ID or class counts differ by serialisation format.
RDF_TYPE_BRACKETED = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
RDF_TYPE_PLAIN = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

#: Metric column names produced by :meth:`MetricsAccumulator.finalize`.
METRIC_FIELDS = (
    "RDF_Triples",
    "RDF_Subjects",
    "RDF_Predicates",
    "RDF_Objects",
    "RDF_Classes",
    "RDF_Mean_Outdegree",
    "RDF_Mean_Indegree",
    "RDF_Coherence",
    "RDF_Coherence_TypeIncl",
    "RDF_Type_Coverage_Avg",
)


class MetricsAccumulator:
    """Accumulate RDF metrics one triple at a time.

    Feed triples with :meth:`add_triple`, then call :meth:`finalize` exactly
    once. The instance is not reusable afterwards -- finalisation deletes its
    internal state to release memory.
    """

    __slots__ = (
        "num_triples",
        "_str_to_id",
        "_next_id",
        "_rdf_type_id",
        "subject_ids",
        "predicate_ids",
        "object_ids",
        "class_ids",
        "out_degrees",
        "in_degrees",
        "type_instances",
        "instance_properties",
    )

    def __init__(self) -> None:
        self.num_triples = 0
        self._str_to_id: dict[str, int] = {}
        self._next_id = 0

        rt_id = self._intern(RDF_TYPE_BRACKETED)
        self._str_to_id[RDF_TYPE_PLAIN] = rt_id
        self._rdf_type_id = rt_id

        self.subject_ids: set[int] = set()
        self.predicate_ids: set[int] = set()
        self.object_ids: set[int] = set()
        self.class_ids: set[int] = set()

        self.out_degrees: dict[int, int] = defaultdict(int)
        self.in_degrees: dict[int, int] = defaultdict(int)
        self.type_instances: dict[int, set[int]] = defaultdict(set)
        self.instance_properties: dict[int, set[int]] = defaultdict(set)

    # -- helpers ----------------------------------------------------------

    def _intern(self, s: str) -> int:
        uid = self._str_to_id.get(s)
        if uid is None:
            uid = self._next_id
            self._str_to_id[s] = uid
            self._next_id += 1
        return uid

    # -- public API -------------------------------------------------------

    def add_triple(self, s_str: str, p_str: str, o_str: str) -> None:
        s_id = self._intern(s_str)
        p_id = self._intern(p_str)
        o_id = self._intern(o_str)

        self.num_triples += 1
        self.subject_ids.add(s_id)
        self.predicate_ids.add(p_id)
        self.object_ids.add(o_id)

        self.out_degrees[s_id] += 1
        self.in_degrees[o_id] += 1
        self.instance_properties[s_id].add(p_id)

        if p_id == self._rdf_type_id:
            self.class_ids.add(o_id)
            self.type_instances[o_id].add(s_id)

    def finalize(self) -> dict[str, Any]:
        """Return the metrics dict and free heavy internal structures."""
        if self.num_triples == 0:
            return {}

        num_triples = self.num_triples
        num_subjects = len(self.subject_ids)
        num_predicates = len(self.predicate_ids)
        num_objects = len(self.object_ids)
        num_classes = len(self.class_ids)

        del self.subject_ids, self.predicate_ids, self.object_ids, self.class_ids

        mean_out = (
            sum(self.out_degrees.values()) / len(self.out_degrees) if self.out_degrees else 0.0
        )
        mean_in = (
            sum(self.in_degrees.values()) / len(self.in_degrees) if self.in_degrees else 0.0
        )
        del self.out_degrees, self.in_degrees

        # --- Structuredness / coherence ---------------------------------
        #
        # Duan et al.'s coherence, as implemented by the LDBC reference procedure
        # published with it. Two details of that procedure are easy to get wrong
        # and this code got both wrong until they were checked against it:
        #
        #   1. rdf:type is EXCLUDED from a type's property set. The reference SQL
        #      filters it in both the numerator and the property count
        #      (`t2.P <> iri_to_id('rdf:type')`). Including it inflates the score,
        #      because it is present on every instance of a type by construction
        #      -- in the limit, a graph thinned to nothing but rdf:type scores a
        #      perfect 1.0.
        #
        #   2. Each type is weighted by (|P(t)| + |I(t)|), not by |I(t)| alone.
        #      The stated rationale is to give more weight to types with many
        #      instances *and* many properties.
        #
        #      CV(t)  = sum_s |props(s)| / (|P(t)| * |I(t)|)
        #      CH(D)  = sum_t w(t) * CV(t),
        #               w(t) = (|P(t)| + |I(t)|) / sum_t' (|P(t')| + |I(t')|)
        #
        # `RDF_Coherence_TypeIncl` preserves the earlier definition -- rdf:type
        # counted, weighted by instances alone -- so numbers published before the
        # correction remain reproducible and the two can be compared directly.
        total_pi = 0
        total_instances = 0
        per_type: list[tuple[float, float, int, int]] = []

        for _t_id, instances in self.type_instances.items():
            i_t_size = len(instances)
            if i_t_size == 0:
                continue

            p_t: set[int] = set()
            numerator = 0
            numerator_incl = 0
            for s_id in instances:
                props = self.instance_properties.get(s_id, set())
                p_t.update(props)
                numerator_incl += len(props)
                numerator += len(props) - (1 if self._rdf_type_id in props else 0)

            p_incl = len(p_t)
            p_size = p_incl - (1 if self._rdf_type_id in p_t else 0)

            cv_t = numerator / (p_size * i_t_size) if p_size else 0.0
            cv_incl = numerator_incl / (p_incl * i_t_size) if p_incl else 0.0

            per_type.append((cv_t, cv_incl, p_size, i_t_size))
            total_pi += p_size + i_t_size
            total_instances += i_t_size

        coherence = 0.0
        coherence_incl = 0.0
        cv_values = [cv for cv, _, _, _ in per_type]
        for cv_t, cv_incl, p_size, i_t_size in per_type:
            if total_pi:
                coherence += ((p_size + i_t_size) / total_pi) * cv_t
            if total_instances:
                coherence_incl += (i_t_size / total_instances) * cv_incl

        del self.type_instances, self.instance_properties, self._str_to_id
        gc.collect()

        return {
            "RDF_Triples": num_triples,
            "RDF_Subjects": num_subjects,
            "RDF_Predicates": num_predicates,
            "RDF_Objects": num_objects,
            "RDF_Classes": num_classes,
            "RDF_Mean_Outdegree": mean_out,
            "RDF_Mean_Indegree": mean_in,
            "RDF_Coherence": coherence,
            "RDF_Coherence_TypeIncl": coherence_incl,
            "RDF_Type_Coverage_Avg": sum(cv_values) / len(cv_values) if cv_values else 0.0,
        }
