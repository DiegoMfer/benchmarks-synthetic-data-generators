"""Validate generated data against the schema it was generated from.

Every other conformance figure in this suite is the generator's own account of
its output: ``rudof`` reports how much of the source schema reached its
intermediate representation and how much of what it emitted satisfies that
representation. Neither says whether the data satisfies the schema the user
supplied, and a tool cannot settle that question about itself.

This module answers it with pySHACL, which knows nothing about any intermediate
representation and reads the original shapes file.

One measurement deserves its own note. A SHACL shape selects the nodes it
governs by target class, so data typed with anything else is selected by
nothing, validated against nothing, and reported as conforming. An empty
violation list is therefore ambiguous, and the fields below report how many
nodes were *selected* alongside how many conformed, so that a vacuous pass is
visible as one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

#: CSV columns this module contributes. Blank for every run that declares no
#: schema to validate against, which is most of them.
EXTERNAL_FIELDS: dict[str, str] = {
    "conforms": "External_Conforms",
    "focus_nodes_selected": "External_Focus_Nodes_Selected",
    "focus_nodes_conforming": "External_Focus_Nodes_Conforming",
    "conformance_pct": "External_Conformance_Pct",
    "violations": "External_Violations",
    "violations_by_component": "External_Violations_By_Component",
    "validator": "External_Validator",
}

SH = "http://www.w3.org/ns/shacl#"


def analyse(paths: Iterable[Path], rdf_format: str, shapes_path: Path) -> dict[str, Any]:
    """Validate the graph in *paths* against *shapes_path*.

    Returns a row keyed by :data:`EXTERNAL_FIELDS` values. A missing validator
    is reported in the row rather than swallowed: a blank column reads like a
    measurement that found nothing, which is precisely the confusion this
    metric exists to prevent.
    """
    try:
        import pyshacl  # noqa: F401
        import rdflib
    except ImportError:
        print(
            "    pyshacl is not installed, so the output was NOT validated "
            "against its schema; install it with `pip install -e .`",
            flush=True,
        )
        return {EXTERNAL_FIELDS["validator"]: "unavailable (pyshacl not installed)"}

    data = rdflib.Graph()
    for path in paths:
        data.parse(str(path), format=rdf_format)

    shapes = rdflib.Graph()
    shapes.parse(str(shapes_path), format="turtle")

    conforms, report, _ = pyshacl.validate(
        data,
        shacl_graph=shapes,
        inference="none",
        abort_on_first=False,
        allow_infos=False,
        allow_warnings=False,
    )

    # Which nodes the shapes actually govern, so that "no violations" can be
    # told apart from "nothing was checked".
    target_classes = {
        str(o) for _s, _p, o in shapes.triples((None, rdflib.URIRef(SH + "targetClass"), None))
    }
    selected = {
        str(s)
        for s, _p, o in data.triples((None, rdflib.RDF.type, None))
        if str(o) in target_classes
    }

    failing = {
        str(n) for _s, _p, n in report.triples((None, rdflib.URIRef(SH + "focusNode"), None))
    }
    components: dict[str, int] = {}
    for _s, _p, comp in report.triples((None, rdflib.URIRef(SH + "sourceConstraintComponent"), None)):
        key = str(comp).replace(SH, "sh:").replace("ConstraintComponent", "")
        components[key] = components.get(key, 0) + 1

    conforming = len(selected - failing)
    pct = (100.0 * conforming / len(selected)) if selected else None

    return {
        EXTERNAL_FIELDS["conforms"]: bool(conforms),
        EXTERNAL_FIELDS["focus_nodes_selected"]: len(selected),
        EXTERNAL_FIELDS["focus_nodes_conforming"]: conforming,
        EXTERNAL_FIELDS["conformance_pct"]: pct,
        EXTERNAL_FIELDS["violations"]: sum(components.values()),
        EXTERNAL_FIELDS["violations_by_component"]: "; ".join(
            f"{k} {v}" for k, v in sorted(components.items(), key=lambda kv: -kv[1])
        ),
        EXTERNAL_FIELDS["validator"]: f"pySHACL {_pyshacl_version()}",
    }


def _pyshacl_version() -> str:
    try:
        import pyshacl

        return getattr(pyshacl, "__version__", "unknown")
    except ImportError:  # pragma: no cover - analyse() already returned {}
        return "unavailable"
