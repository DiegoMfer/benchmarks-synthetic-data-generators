#!/usr/bin/env python3
"""LEMMING - example-mimicking knowledge graph generator.

LEMMING is *data-driven*: instead of a schema it takes an existing RDF graph and
generates a synthetic one that mimics its structure at a requested number of
vertices. It therefore has no high/low coherence axis in the sense the other
generators do -- it reproduces whatever structuredness its input exhibits. The
configurable dimension exposed here is the generation mode instead.

The same repository ships SimplexKG, selected with ``-m Simplex``, so this image
covers both generators; ``--mode`` chooses between them.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from entry import GenerationResult, run_generator, sh

JAR = Path("/app/target/lemming.jar")
WORK = Path("/tmp/lemming")
SCHEMAS = Path("/schemas")
#: Shipped with the repository; lets the container be smoke-tested without
#: first having to generate a seed graph. email-Eu-core is used rather than
#: snippet_linkedgeo.nt, which is only four triples -- too small for the simplex
#: analysis, which fails with "bound must be positive" on it.
BUILTIN_SEED = Path("/app/testdata/email-Eu-core.n3")
OUTPUT = "generated_data.ttl"


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--seed-graph",
        default="builtin",
        help="RDF graph to mimic, relative to /schemas, or 'builtin' for the bundled sample",
    )
    parser.add_argument("--vertices", type=int, default=1000, help="target vertex count")
    parser.add_argument(
        "--mode",
        choices=["Binary", "Simplex", "Baseline"],
        default="Binary",
        help="Binary = LEMMING, Simplex = SimplexKG",
    )
    parser.add_argument("--threads", type=int, default=2)
    # Simplex mode resolves its sampler beans from these; without them the
    # SimplexGraphGeneratorFactory fails to construct a generator.
    parser.add_argument("--simplex-property-sampling", choices=["BP", "UP"], default="UP")
    parser.add_argument("--simplex-class-sampling", choices=["BC", "UC"], default="UC")
    parser.add_argument("--optimization-iterations", type=int, default=0)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    seed = _resolve_seed(args.seed_graph)

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    dataset = "bench"
    sh(
        [
            "java", "-jar", JAR,
            "single-graph",
            "-ds", dataset,
            "-dp", seed,
            "-nv", args.vertices,
            "-thrs", args.threads,
            "-m", args.mode,
            "-op", args.optimization_iterations,
            *(["-sp", args.simplex_property_sampling,
               "-sc", args.simplex_class_sampling] if args.mode == "Simplex" else []),
        ],
        # LEMMING resolves its output directory relative to the working
        # directory, so the run happens in a scratch dir we control.
        cwd=WORK,
    )

    produced = WORK / "output" / "single" / f"Mimic_{dataset}.ttl"
    if not produced.exists():
        found = sorted(p.name for p in (WORK / "output").rglob("*")) if (WORK / "output").exists() else []
        raise RuntimeError(
            f"LEMMING wrote no graph at {produced}. Present: {', '.join(found) or '(nothing)'}"
        )
    shutil.copy2(produced, out / OUTPUT)

    return GenerationResult(
        files=[OUTPUT],
        rdf_format="turtle",
        triples_reported=None,
        notes=[
            f"data-driven: mimics {seed.name} at {args.vertices} vertices",
            f"mode {args.mode}" + (" (SimplexKG)" if args.mode == "Simplex" else " (LEMMING)"),
        ],
    )


def _resolve_seed(name: str) -> Path:
    if name == "builtin":
        return BUILTIN_SEED
    path = SCHEMAS / name
    if path.is_file():
        return path
    available = ", ".join(
        sorted(str(p.relative_to(SCHEMAS)) for p in SCHEMAS.rglob("*") if p.suffix in {".nt", ".ttl"})
    )
    raise FileNotFoundError(f"seed graph {name!r} not found under /schemas. Available: {available}")


if __name__ == "__main__":
    run_generator(
        "lemming",
        tool="LEMMING / SimplexKG",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate a synthetic graph mimicking the structure of an input graph",
    )
