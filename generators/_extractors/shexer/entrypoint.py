#!/usr/bin/env python3
"""Extract a ShEx schema from a generated dataset.

This is the bridge between the two phases of E3. Phase 1 produces a dataset from
a generator that cannot be given a schema; sheXer mines the shapes actually
present in that dataset; phase 2 feeds those shapes to rudof. The point is that
nobody authors the schema -- it comes from the generator's own output -- which
is what makes the comparison fair for generators with no schema input at all.

Contract, deliberately narrower than the generator one:

    --in  /in    a completed run directory, read-only
    --out /out   where <name>.shex is written
    --name       the stem of the output file

It emits a small ``extraction.json`` beside the schema rather than a
``report.json``: an extraction has no triple count, no RDF format and no
throughput, so reusing the generator report would mean filling required fields
with fiction.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from shexer.consts import NT, RDF_XML, SHEXC, TURTLE
from shexer.shaper import Shaper

#: Report file suffixes and other metadata that are never RDF payload.
NON_RDF = {"report.json", "container.log", "extraction.json"}

#: rdflib format name -> sheXer input constant.
FORMATS = {"turtle": TURTLE, "ttl": TURTLE, "nt": NT, "n3": NT, "xml": RDF_XML}

#: Prefixes worth naming in the output. sheXer falls back to full IRIs for
#: anything not listed, which is verbose but never wrong.
NAMESPACES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
    "http://www.w3.org/2001/XMLSchema#": "xsd",
    "http://www.w3.org/2002/07/owl#": "owl",
    "http://xmlns.com/foaf/0.1/": "foaf",
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://purl.org/dc/terms/": "dct",
    "http://schema.org/": "schema",
    "http://swat.cse.lehigh.edu/onto/univ-bench.owl#": "ub",
    "http://www4.wiwiss.fu-berlin.de/bizer/bsbm/v01/vocabulary/": "bsbm",
    "http://db.uwaterloo.ca/~galuc/wsdbm/": "wsdbm",
    "http://pygraf.t/": "pgt",
    "http://weso.es/shapes/": "wsh",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shexer-extractor",
        description="Mine a ShEx schema from the RDF in a completed run directory",
    )
    parser.add_argument("--in", dest="src", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--name", required=True, help="stem of the written .shex file")
    parser.add_argument(
        "--format", default="turtle", help="rdflib format name of the input files"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.1,
        help="minimum share of a class's instances that must exhibit a constraint "
             "for it to enter the shape (sheXer acceptance_threshold)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="stop after this many input files (0 = all); a guard for generators "
             "that emit hundreds of small files",
    )
    parser.add_argument(
        "--map-unknown-datatypes", action=argparse.BooleanOptionalAction, default=True,
        help="rewrite non-XSD datatypes to xsd:string (default: on). See "
             "_normalise_datatypes for why.",
    )
    args = parser.parse_args(argv)

    files = _inputs(args.src, args.limit)
    if not files:
        print(f"!! no RDF files under {args.src}", file=sys.stderr)
        return 1

    input_format = FORMATS.get(args.format.lower())
    if input_format is None:
        print(
            f"!! unsupported input format {args.format!r}; known: {', '.join(sorted(FORMATS))}",
            file=sys.stderr,
        )
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"{args.name}.shex"

    print(f"=== shexer: {args.name} ===", flush=True)
    print(f"  {len(files)} file(s), format {args.format}, threshold {args.threshold}", flush=True)
    for path in files:
        print(f"    {path.name} ({path.stat().st_size / 1e6:.1f} MB)", flush=True)

    started = time.monotonic()
    shaper = Shaper(
        graph_list_of_files_input=[str(p) for p in files],
        input_format=input_format,
        namespaces_dict=NAMESPACES,
        all_classes_mode=True,
        disable_comments=True,
    )
    shaper.shex_graph(
        output_file=str(target),
        acceptance_threshold=args.threshold,
        output_format=SHEXC,
    )
    elapsed = time.monotonic() - started

    if not target.exists() or target.stat().st_size == 0:
        print(f"!! sheXer wrote no schema to {target}", file=sys.stderr)
        return 1

    mapped = _normalise_datatypes(target) if args.map_unknown_datatypes else {}
    if mapped:
        print(
            "  mapped non-XSD datatype(s) to xsd:string: "
            + ", ".join(f"{dt} ({n}x)" for dt, n in sorted(mapped.items())),
            flush=True,
        )

    shapes = _count_shapes(target)
    (args.out / f"{args.name}.extraction.json").write_text(
        json.dumps(
            {
                "name": args.name,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(elapsed, 3),
                "source_files": [p.name for p in files],
                "input_format": args.format,
                "acceptance_threshold": args.threshold,
                "shapes": shapes,
                "schema_bytes": target.stat().st_size,
                # Recorded so the approximation is reportable rather than
                # invisible: the paper can state exactly how many datatypes were
                # normalised, per source.
                "mapped_datatypes": mapped,
                "tool": "shexer",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"=== wrote {target.name}: {shapes} shape(s), "
        f"{target.stat().st_size / 1e3:.1f} kB, in {elapsed:.1f}s ===",
        flush=True,
    )
    return 0


def _inputs(src: Path, limit: int) -> list[Path]:
    """RDF payload files in a run directory, in stable order."""
    files = sorted(
        p for p in src.rglob("*")
        if p.is_file() and p.name not in NON_RDF and not p.name.endswith(".stats.json")
    )
    return files[:limit] if limit > 0 else files


#: ShExC node-constraint keywords that occupy the same slot as a datatype but
#: are not one.
NODE_KINDS = {".", "IRI", "BNODE", "LITERAL", "NONLITERAL"}

XSD = "http://www.w3.org/2001/XMLSchema#"


def _normalise_datatypes(schema: Path) -> dict[str, int]:
    """Rewrite datatypes outside the XSD namespace to ``xsd:string``.

    Real data carries custom datatypes -- BSBM stamps its prices with
    ``bsbm:USD`` -- and no generator has a value generator for a datatype it has
    never seen, so rudof refuses the schema outright. Without this the whole
    round-trip fails on a single line out of six hundred.

    This is an approximation and is recorded as one in ``extraction.json``. It
    is defensible for what E3 measures: a custom datatype constrains the *value
    space* of a literal, while coherence is computed from which properties each
    type carries. Substituting ``xsd:string`` changes the literals written into
    the object position and leaves the graph structure -- the measured quantity
    -- untouched.

    Returns the datatypes rewritten and how many times each occurred.
    """
    lines = schema.read_text(encoding="utf-8").splitlines(keepends=True)
    prefixes = _prefixes(lines)
    mapped: dict[str, int] = {}
    out: list[str] = []

    for line in lines:
        tokens = line.split()
        # A constraint line is `predicate constraint [cardinality] [;]`, and only
        # the second token can be a datatype.
        if len(tokens) < 2 or line.lstrip().startswith(("PREFIX", "#")):
            out.append(line)
            continue

        constraint = tokens[1]
        expanded = _expand(constraint, prefixes)
        is_datatype = (
            expanded is not None
            and not constraint.startswith(("@", "[", "{"))
            and constraint.upper() not in NODE_KINDS
            and not expanded.startswith(XSD)
        )
        if is_datatype:
            mapped[expanded] = mapped.get(expanded, 0) + 1
            # Replace the token in place so indentation and the trailing
            # cardinality/separator survive untouched.
            out.append(line.replace(constraint, "xsd:string", 1))
        else:
            out.append(line)

    if mapped:
        schema.write_text("".join(out), encoding="utf-8")
    return mapped


def _prefixes(lines: list[str]) -> dict[str, str]:
    """Prefix -> namespace, read from the schema's own PREFIX declarations."""
    out: dict[str, str] = {}
    for line in lines:
        tokens = line.split()
        if len(tokens) >= 3 and tokens[0].upper() == "PREFIX" and tokens[2].startswith("<"):
            out[tokens[1].rstrip(":")] = tokens[2].strip("<>")
    return out


def _expand(token: str, prefixes: dict[str, str]) -> str | None:
    """Expand a prefixed name or IRI to a full IRI, or ``None`` if it is neither."""
    if token.startswith("<") and token.endswith(">"):
        return token.strip("<>")
    prefix, sep, local = token.partition(":")
    if not sep or "/" in prefix:
        return None
    namespace = prefixes.get(prefix)
    return namespace + local if namespace is not None else None


def _count_shapes(schema: Path) -> int:
    """Number of shape declarations, for the sanity check in the log.

    sheXer writes each shape label at column 0 -- ``:UniversityType0`` or a full
    ``<IRI>`` -- with its constraint block indented beneath. Constraint lines are
    therefore excluded by the indentation alone, and PREFIX lines by their
    keyword.
    """
    lines = schema.read_text(encoding="utf-8").splitlines()
    return sum(
        1 for line in lines
        if (line.startswith(":") or line.startswith("<"))
        and not line.upper().startswith("PREFIX")
    )


if __name__ == "__main__":
    sys.exit(main())
