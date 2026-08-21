#!/usr/bin/env python3
"""WatDiv - RDF generation from a dataset-description model.

WatDiv accepts neither OWL nor shapes: its schema is its own dataset-description
language. The LUBM model is therefore supplied as a template under
``/schemas/lubm/``, and this entrypoint substitutes the structuredness knob into
it before generating.

That knob is ``--property-fill``. WatDiv exposes structuredness in two places --
the ``<pgroup>`` probability, which is the fraction of instances carrying a group
of literal properties, and an association's ``left_cover``, which is the fraction
carrying a relation. Both take the same value here, so one parameter spans the
coherence range in the same way rudof's property-fill does.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from entry import GenerationResult, run_generator, sh

WATDIV = Path("/opt/watdiv")
#: The binary resolves ../../files/*.txt relative to its own directory, so it
#: can only be run from here.
RUN_DIR = WATDIV / "bin" / "Release"
SCHEMAS = Path("/schemas")
OUTPUT = "dataset.nt"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--model",
        default="lubm/lubm-watdiv.txt.template",
        help="model template under /schemas, or 'builtin' for WatDiv's own e-commerce model",
    )
    parser.add_argument("--scale-factor", type=int, default=1)
    parser.add_argument(
        "--property-fill",
        type=float,
        default=1.0,
        help="probability substituted for {fill}: 1.0 gives maximal structuredness",
    )


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    model = _resolve_model(args)
    dataset = out / OUTPUT

    # WatDiv writes N-Triples to stdout, so the run is redirected rather than
    # given an output path.
    proc = sh(
        ["./watdiv", "-d", str(model), str(args.scale_factor)],
        cwd=RUN_DIR,
        capture_to=dataset,
    )

    triples = sum(1 for _ in dataset.open("r", encoding="utf-8", errors="replace"))
    if triples == 0:
        raise RuntimeError(f"WatDiv produced no triples\n{proc.stderr[-2000:]}")

    return GenerationResult(
        files=[OUTPUT],
        rdf_format="nt",
        # N-Triples is one triple per line, so this count is exact rather than
        # an estimate; the host still measures it independently.
        triples_reported=triples,
        tool_version="v0.6",
        notes=[f"property fill {args.property_fill} substituted into the model"],
    )


def _resolve_model(args: argparse.Namespace) -> Path:
    if args.model == "builtin":
        return WATDIV / "model" / "wsdbm-data-model.txt"

    template = SCHEMAS / args.model
    if not template.is_file():
        available = ", ".join(sorted(str(p.relative_to(SCHEMAS)) for p in SCHEMAS.rglob("*watdiv*")))
        raise FileNotFoundError(f"model {args.model!r} not found. Available: {available or 'none'}")

    # The model must be writable and is regenerated per run, so it goes to /tmp.
    rendered = Path("/tmp/model.txt")
    rendered.write_text(
        template.read_text(encoding="utf-8").replace("{fill}", str(args.property_fill)),
        encoding="utf-8",
    )
    print(f"rendered {template} with fill={args.property_fill} -> {rendered}", flush=True)
    return rendered


if __name__ == "__main__":
    run_generator(
        "watdiv",
        tool="WatDiv",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate RDF from a WatDiv dataset-description model",
    )
