#!/usr/bin/env python3
"""Run the whole benchmark.

    python3 main.py                  # smoke profile: tiny, fast, proves everything works
    python3 main.py --profile e2     # one of the five experiments

One invocation does all four stages -- build the generator images, generate every
dataset in the profile, measure the RDF, and write the CSV and charts. The
``--skip-*`` flags exist so a long sweep can be resumed or re-measured without
regenerating; by default nothing is skipped.

There is one subcommand, ``extract``, which sits outside that pipeline:

    python3 main.py extract --profile e3_sources --into schemas/extracted/

It mines ShEx schemas out of datasets a previous run produced, which is what
connects E3's two phases. It is a subcommand rather than a fifth stage because
it writes into ``schemas/`` -- version-controlled input to a later experiment --
rather than into the disposable ``data/``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT / "src"))

from rdfbench.config import ConfigError, Workspace  # noqa: E402
from rdfbench.extract import (  # noqa: E402
    DEFAULT_INTO,
    DEFAULT_THRESHOLD,
    extract_directory,
    extract_profile,
)
from rdfbench.pipeline import run_pipeline  # noqa: E402
from rdfbench.runner import DockerError  # noqa: E402


#: The profiles that produce the paper, cheapest first. Order is deliberate: a
#: bad parameter surfaces in seconds on e4 rather than three hours into e2.
ALL_PROFILES = ("e4", "e5", "e2")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Generate synthetic RDF datasets, measure them, and plot the comparison.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python3 main.py                              run the full smoke pipeline
  python3 main.py --profile paper              run the real benchmark
  python3 main.py --only bsbm_high_coherence   one experiment, end to end
  python3 main.py --runs 1                     override the profile's repeat count
  python3 main.py --skip-generate              re-measure data already on disk
  python3 main.py --all                        run every profile the paper needs
  python3 main.py --all --smoke                the same, at smoke scale (~2 min)
  python3 main.py --list                       show available profiles and generators
  python3 main.py extract --profile e2        mine ShEx schemas from a finished run
        """,
    )
    parser.add_argument(
        "--profile", "-p", default="smoke",
        help="profile in profiles/ to run (default: smoke)",
    )
    parser.add_argument(
        "--only", "-o", nargs="+", metavar="EXPERIMENT",
        help="run only these experiments from the profile",
    )
    parser.add_argument(
        "--runs", "-r", type=int, metavar="N",
        help="override the number of runs per experiment",
    )
    parser.add_argument("--skip-build", action="store_true", help="assume images are built")
    parser.add_argument(
        "--skip-generate", action="store_true",
        help="reuse datasets already in data/runs/ (implies --skip-build)",
    )
    parser.add_argument("--skip-metrics", action="store_true", help="generate only, do not measure")
    parser.add_argument("--skip-plots", action="store_true", help="write the CSV but no charts")
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="stop at the first failed run instead of continuing the sweep",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="run every profile the paper depends on, cheapest first "
             f"({', '.join(ALL_PROFILES)}), instead of a single --profile",
    )
    parser.add_argument(
        "--smoke", action="store_true",
        help="with --all, run the _smoke variant of each profile",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="list available profiles and generators, then exit",
    )
    return parser


def build_extract_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py extract",
        description="Mine ShEx schemas from the datasets a finished profile produced. "
                    "This is E3's bridge: the schema comes from each generator's own "
                    "output, so nobody authors it.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--profile", "-p",
        help="extract one schema per experiment in this finished profile",
    )
    source.add_argument(
        "--from", dest="src", type=Path, metavar="DIR",
        help="extract from any directory of RDF -- a real dataset with no "
             "generator behind it. Requires --name.",
    )
    parser.add_argument(
        "--name", help="schema name, required with --from",
    )
    parser.add_argument(
        "--format", dest="rdf_format",
        help="input serialisation for --from (inferred from file suffixes if omitted)",
    )
    parser.add_argument(
        "--into", type=Path, default=DEFAULT_INTO,
        help=f"parent directory for the extracted schemas (default: {DEFAULT_INTO}). "
             "The source profile's name is appended, so smoke extractions never "
             "overwrite full-scale ones.",
    )
    parser.add_argument(
        "--only", "-o", nargs="+", metavar="EXPERIMENT",
        help="extract from only these experiments",
    )
    parser.add_argument(
        "--run", type=int, default=1,
        help="which run to extract from (default: 1). Fixed on purpose -- PyGraft "
             "draws a new schema per run, so mining across runs is not meaningful.",
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help=f"sheXer acceptance threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument("--skip-build", action="store_true", help="assume the image is built")
    return parser


def run_extract(workspace: Workspace, argv: list[str]) -> int:
    parser = build_extract_parser()
    args = parser.parse_args(argv)
    if args.src and not args.name:
        parser.error("--from requires --name (the stem of the .shex to write)")

    try:
        if args.src:
            result = extract_directory(
                workspace,
                args.src,
                args.name,
                into=args.into,
                rdf_format=args.rdf_format,
                threshold=args.threshold,
                skip_build=args.skip_build,
            )
        else:
            result = extract_profile(
                workspace,
                args.profile,
                into=args.into,
                only=args.only,
                run=args.run,
                threshold=args.threshold,
                skip_build=args.skip_build,
            )
    except ConfigError as exc:
        print(f"\nconfiguration error: {exc}", file=sys.stderr)
        return 2
    except DockerError as exc:
        print(f"\ndocker error: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    return 0 if result.ok else 1


def list_available(workspace: Workspace) -> int:
    profiles = sorted(p.stem for p in workspace.profiles_dir.glob("*.yaml"))
    print("profiles:")
    for name in profiles:
        print(f"  {name}")
    if not profiles:
        print("  (none)")

    print("\ngenerators:")
    try:
        specs = workspace.load_generators()
    except ConfigError as exc:
        print(f"  error: {exc}")
        return 1
    for name, spec in sorted(specs.items()):
        params = ", ".join(sorted(spec.params)) or "(none)"
        print(f"  {name:<14} service={spec.service:<12} params: {params}")
    if not specs:
        print("  (none)")
    return 0


def run_all(workspace: Workspace, args: argparse.Namespace) -> int:
    """Run every profile the paper depends on, and summarise at the end.

    A failure does not stop the sweep. Finding out that e2 succeeded and e5 did
    not is worth more than aborting at the first problem, since the profiles are
    independent and a partial result is still usable.
    """
    names = [f"{n}_smoke" if args.smoke else n for n in ALL_PROFILES]
    scale = "smoke" if args.smoke else "full"
    print(f"running {len(names)} profile(s) at {scale} scale: {', '.join(names)}", flush=True)

    outcomes: list[tuple[str, str]] = []
    for name in names:
        try:
            result = run_pipeline(
                workspace, name,
                runs_override=args.runs,
                skip_build=args.skip_build or args.skip_generate,
                skip_generate=args.skip_generate,
                skip_metrics=args.skip_metrics,
                skip_plots=args.skip_plots,
                keep_going=not args.fail_fast,
            )
            outcomes.append((name, "ok" if result.ok else "INCOMPLETE"))
        except (ConfigError, DockerError) as exc:
            outcomes.append((name, f"FAILED: {exc}"))
            if args.fail_fast:
                break
        except KeyboardInterrupt:
            outcomes.append((name, "interrupted"))
            break

    print("\n" + "=" * 78 + f"\nall profiles ({scale})\n" + "=" * 78, flush=True)
    for name, status in outcomes:
        print(f"  {name:<14} {status}", flush=True)

    failed = [n for n, s in outcomes if s != "ok"]
    if failed:
        print(f"\n{len(failed)} profile(s) did not complete: {', '.join(failed)}", flush=True)
        return 1
    print("\nall profiles completed. Charts are under data/results/<profile>/charts/.",
          flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    workspace = Workspace(ROOT)

    # Dispatched by hand rather than with subparsers so that the bare
    # `main.py --profile e2` form keeps working exactly as before. Adding a
    # subparser would have made a subcommand mandatory.
    if argv and argv[0] == "extract":
        return run_extract(workspace, argv[1:])

    args = build_parser().parse_args(argv)

    if args.list:
        return list_available(workspace)

    if args.all:
        return run_all(workspace, args)

    try:
        result = run_pipeline(
            workspace,
            args.profile,
            only=args.only,
            runs_override=args.runs,
            skip_build=args.skip_build or args.skip_generate,
            skip_generate=args.skip_generate,
            skip_metrics=args.skip_metrics,
            skip_plots=args.skip_plots,
            keep_going=not args.fail_fast,
        )
    except ConfigError as exc:
        print(f"\nconfiguration error: {exc}", file=sys.stderr)
        return 2
    except DockerError as exc:
        print(f"\ndocker error: {exc}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130

    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
