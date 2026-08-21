#!/usr/bin/env python3
"""PyGraft - schema and knowledge graph generator with RDFS/OWL constructs."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from entry import GenerationResult, run_generator

SCHEMA_NAME = "graph"
#: PyGraft's own reasoner reloads the schema it just wrote via owlready2, which
#: rejects the Turtle it emits. RDF/XML round-trips cleanly, so the pipeline
#: generates and measures XML rather than converting formats afterwards.
OUTPUT = "full_graph.rdf"
RDF_FORMAT = "xml"

CONFIG_TEMPLATE = """\
schema_name: {schema_name}
format: xml
verbose: false

num_classes: {classes}
max_hierarchy_depth: {max_depth}
avg_class_depth: {avg_class_depth}
class_inheritance_ratio: {inheritance_ratio}
avg_disjointness: {p_disjoint}

num_relations: {relations}
relation_specificity: 2.5
prop_profiled_relations: 0.9
profile_side: both
prop_symmetric_relations: {p_symmetric}
prop_inverse_relations: {p_inverse}
prop_transitive_relations: {p_transitive}
prop_asymmetric_relations: {p_asymmetric}
prop_reflexive_relations: {p_reflexive}
prop_irreflexive_relations: {p_irreflexive}
prop_functional_relations: {p_functional}
prop_inverse_functional_relations: {p_inverse_functional}
prop_subproperties: {p_subproperty}

num_entities: {num_entities}
num_triples: {num_triples}
fast_gen: true
oversample: false
relation_balance_ratio: 0.9
prop_untyped_entities: 0.0
avg_depth_specific_class: {avg_depth_specific}
multityping: false
avg_multityping: 1.5
"""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--classes", type=int, default=30)
    parser.add_argument("--relations", type=int, default=20)
    parser.add_argument("--avg-instances", type=int, default=80)
    parser.add_argument("--std-instances", type=int, default=10)
    parser.add_argument("--avg-relations", type=int, default=3)
    parser.add_argument("--std-relations", type=int, default=1)
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--p-subclass", type=float, default=0.15)
    parser.add_argument("--p-disjoint", type=float, default=0.05)
    parser.add_argument("--p-inverse", type=float, default=0.2)
    parser.add_argument("--p-functional", type=float, default=0.2)
    parser.add_argument("--p-inverse-functional", type=float, default=0.0)
    parser.add_argument("--p-symmetric", type=float, default=0.1)
    parser.add_argument("--p-transitive", type=float, default=0.1)
    parser.add_argument("--p-asymmetric", type=float, default=0.0)
    parser.add_argument("--p-reflexive", type=float, default=0.0)
    parser.add_argument("--p-irreflexive", type=float, default=0.0)
    parser.add_argument("--p-subproperty", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    import random

    import pygraft

    # PyGraft has no seed parameter of its own; seeding the interpreter's RNG
    # before the call is what makes a run reproducible.
    random.seed(args.seed)

    work = Path("/tmp/pygraft")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    config = work / "config.yml"
    config.write_text(
        CONFIG_TEMPLATE.format(
            schema_name=SCHEMA_NAME,
            classes=args.classes,
            relations=args.relations,
            max_depth=args.max_depth,
            avg_class_depth=args.max_depth / 2,
            inheritance_ratio=args.p_subclass * 10,
            p_disjoint=args.p_disjoint,
            p_symmetric=args.p_symmetric,
            p_inverse=args.p_inverse,
            p_transitive=args.p_transitive,
            p_asymmetric=args.p_asymmetric,
            p_reflexive=args.p_reflexive,
            p_irreflexive=args.p_irreflexive,
            p_functional=args.p_functional,
            p_inverse_functional=args.p_inverse_functional,
            p_subproperty=args.p_subproperty,
            num_entities=args.avg_instances * args.classes,
            num_triples=args.avg_relations * args.avg_instances * args.classes,
            avg_depth_specific=max(1.0, min(args.max_depth / 2.0, 2.0)),
        ),
        encoding="utf-8",
    )

    # PyGraft resolves its output directory relative to the working directory.
    import os

    os.chdir(work)
    pygraft.generate(str(config))

    produced = work / "output" / SCHEMA_NAME
    graph = _find_graph(produced)
    shutil.copy2(graph, out / OUTPUT)

    return GenerationResult(
        files=[OUTPUT],
        rdf_format=RDF_FORMAT,
        triples_reported=None,
        tool_version=getattr(pygraft, "__version__", None),
    )


def _find_graph(produced: Path) -> Path:
    """Locate PyGraft's merged schema+instances graph.

    It has shipped the file under several names across versions, so match on the
    known candidates rather than assuming one.
    """
    for name in ("full_graph.rdf", "full_graph.ttl", f"{SCHEMA_NAME}.rdf"):
        candidate = produced / name
        if candidate.exists():
            return candidate
    found = sorted(p.name for p in produced.glob("*")) if produced.exists() else []
    raise FileNotFoundError(
        f"no PyGraft graph file in {produced}. Present: {', '.join(found) or '(nothing)'}"
    )


if __name__ == "__main__":
    run_generator(
        "pygraft",
        tool="pygraft",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate a synthetic schema and knowledge graph with OWL constructs",
    )
