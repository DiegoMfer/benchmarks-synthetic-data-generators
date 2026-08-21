#!/usr/bin/env python3
"""LINKGEN - synthetic linked data with configurable statistical distributions."""

from __future__ import annotations

import argparse
from pathlib import Path

from entry import GenerationResult, run_generator, sh

SCHEMAS = Path("/schemas")
DATA_PREFIX = "data"

CONFIG_TEMPLATE = """\
namespace=http://edu.wright.daselab.linkgen/generator/

debug.mode=false
stream.mode=false
quad.format=false
max.thread={threads}

file.basedir=/app
file.log4j.properties=/app/log4j.properties
file.input.ontology={ontology}

file.output.prefix={out}
file.output.data.prefix={out}/{prefix}_
file.output.log={out}/out.log
file.output.void={out}/void.ttl

num.distinct.triples={triples}
num.triples.per.stream=10000
num.triples.per.output={triples_per_file}
max.file.size={max_file_size}
num.avg.frequency.subject={avg_frequency}

distribution.function={distribution}
zipf.exponent={zipf_exponent}
gaussian.mean={gaussian_mean}
gaussian.deviation={gaussian_deviation}

gen.noise=false
noise.data.total=0
noise.data.num.notype=0
noise.data.num.invalid=0
noise.data.num.duplicate=0

gen.sameas=false
file.entity=/app/entity.nt

randseed.xsd.string=10
randseed.xsd.boolean=1
randseed.xsd.int=2
randseed.xsd.float=1
randseed.xsd.double=2
randseed.xsd.long=2
randseed.xsd.others=5

num.string=100
num.float=10
num.int=10
num.double=10
num.long=10
num.others=10
"""


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--triples", type=int, default=100_000)
    parser.add_argument(
        "--ontology",
        default="univ-bench.owl",
        help="ontology filename; resolved under /schemas",
    )
    parser.add_argument("--distribution", choices=["zipf", "gaussian"], default="zipf")
    parser.add_argument("--zipf-exponent", type=float, default=2.1)
    parser.add_argument("--gaussian-mean", type=float, default=200)
    parser.add_argument("--gaussian-deviation", type=float, default=15)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--triples-per-file", type=int, default=500_000)
    parser.add_argument("--max-file-size", type=int, default=500)
    parser.add_argument("--avg-frequency", type=int, default=10)


def generate(out: Path, args: argparse.Namespace) -> GenerationResult:
    ontology = _resolve_ontology(args.ontology)

    config = out / "linkgen.properties"
    config.write_text(
        CONFIG_TEMPLATE.format(
            threads=args.threads,
            ontology=ontology,
            out=out,
            prefix=DATA_PREFIX,
            triples=args.triples,
            triples_per_file=args.triples_per_file,
            max_file_size=args.max_file_size,
            avg_frequency=args.avg_frequency,
            distribution=args.distribution,
            zipf_exponent=args.zipf_exponent,
            gaussian_mean=int(args.gaussian_mean),
            gaussian_deviation=int(args.gaussian_deviation),
        ),
        encoding="utf-8",
    )

    classpath = ":".join(["/app/linkgen.jar", "/app/lib/*"])
    # linkgen exits non-zero even after printing "Generation Complete", so its
    # status carries no information. Success is decided by whether the data
    # files exist, checked immediately below.
    sh(
        [
            "java",
            "-Xmx4G",
            "-cp",
            classpath,
            "edu.wright.daselab.linkgen.Generator",
            "-c",
            config,
        ],
        cwd="/app",
        check=False,
    )

    files = sorted(p.name for p in out.glob(f"{DATA_PREFIX}_*") if p.is_file())
    if not files:
        raise RuntimeError("LINKGEN produced no data_* files")

    return GenerationResult(
        files=files,
        rdf_format="nt",
        triples_reported=_void_triples(out / "void.ttl"),
        notes=[f"{len(files)} N-Triples file(s)"],
    )


def _resolve_ontology(name: str) -> Path:
    """Accept either a bare filename or a path relative to /schemas."""
    candidates = [SCHEMAS / name, *SCHEMAS.rglob(name)]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    available = ", ".join(sorted(p.name for p in SCHEMAS.rglob("*.owl")))
    raise FileNotFoundError(f"ontology {name!r} not found. Available: {available}")


def _void_triples(void_file: Path) -> int | None:
    """LINKGEN records its own triple total in the VoID description it emits."""
    if not void_file.exists():
        return None
    import re

    match = re.search(r"void:triples\s+(\d+)", void_file.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else None


if __name__ == "__main__":
    run_generator(
        "linkgen",
        tool="linkgen",
        generate=generate,
        add_arguments=add_arguments,
        description="Generate linked data with Zipf or Gaussian property distributions",
    )
