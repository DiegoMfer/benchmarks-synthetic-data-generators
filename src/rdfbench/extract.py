"""The extraction stage: datasets in, schemas out.

This exists because E3 has a dependency the generate/measure pipeline cannot
express. Phase 1 produces one dataset per generator that cannot be given a
schema; sheXer mines the shapes present in each; phase 2 hands those shapes to
rudof and asks whether it can reproduce -- and then move away from -- the
structure they describe.

The stage is deliberately outside :func:`rdfbench.pipeline.run_pipeline` rather
than a fifth stage inside it. An extraction consumes a *completed* profile and
writes into ``schemas/``, which is version-controlled input, not ``data/``,
which is disposable output. Making it a separate verb keeps that asymmetry
visible: re-running a profile is free, re-extracting changes the inputs to a
later experiment.

    python3 main.py extract --profile e3_sources --into schemas/extracted/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import ConfigError, Profile, Workspace
from .report import BenchmarkReport, ReportError
from .runner import DockerRunner, ExtractOutcome

#: Where extracted schemas go by default. Relative to the workspace root so they
#: sit beside the hand-written schemas rather than under ``data/`` -- they are
#: inputs to a later experiment, not disposable output.
#:
#: The source profile's name is always appended, so ``e3_sources_smoke`` can
#: never overwrite the schemas ``e3_sources`` extracted. Those two differ by
#: three orders of magnitude in input size and would silently produce very
#: different shapes under the same filename.
DEFAULT_INTO = Path("schemas/extracted")

#: sheXer's acceptance threshold. 0.1 keeps a constraint that holds for at least
#: a tenth of a class's instances. Lower would admit noise from generators that
#: emit rare one-off properties; higher would drop optional properties entirely
#: and overstate the regularity of the source, which is exactly the quantity E3
#: is measuring.
DEFAULT_THRESHOLD = 0.1


@dataclass
class ExtractionResult:
    profile: str
    into: Path
    outcomes: list[ExtractOutcome] = field(default_factory=list)

    @property
    def failed(self) -> list[ExtractOutcome]:
        return [o for o in self.outcomes if not o.ok]

    @property
    def ok(self) -> bool:
        return bool(self.outcomes) and not self.failed


def extract_profile(
    workspace: Workspace,
    profile_name: str,
    *,
    into: Path | None = None,
    only: list[str] | None = None,
    run: int = 1,
    threshold: float = DEFAULT_THRESHOLD,
    skip_build: bool = False,
) -> ExtractionResult:
    """Extract one schema per experiment in *profile_name*.

    Shapes come from a single run (``run``, default the first) rather than from
    all of them. This is a stated requirement, not a shortcut: PyGraft draws a
    new random schema on every run, so shapes mined from run 1 and run 2 would
    describe different vocabularies. Fixing the run makes the extracted schema
    reproducible and the phase-2 comparison well defined.
    """
    profile = Profile.load(workspace.profile_path(profile_name))
    specs = workspace.load_generators()
    experiments = profile.select(only)
    into = _resolve_into(workspace, into) / profile.name

    result = ExtractionResult(profile=profile.name, into=into)

    runner = DockerRunner(workspace, timeout=profile.timeout_seconds)
    runner.preflight()
    if not skip_build:
        runner.build_service("shexer")

    print(f"\nextracting {len(experiments)} schema(s) into {into}", flush=True)

    for index, experiment in enumerate(experiments, start=1):
        src_dir = workspace.run_dir(profile.name, experiment.name, run)
        name = _schema_name(experiment.name)

        if not src_dir.exists():
            result.outcomes.append(
                ExtractOutcome(
                    name, src_dir, into / f"{name}.shex", False, 0.0,
                    error=f"no run directory at {src_dir}. Run `--profile {profile.name}` first.",
                )
            )
            print(f"[{index}/{len(experiments)}] {name}: SKIPPED (no data)", flush=True)
            continue

        rdf_format = _rdf_format(src_dir, specs[experiment.generator].rdf_format)
        print(f"[{index}/{len(experiments)}] {name} <- {src_dir.name} ({rdf_format}) ...",
              flush=True)

        outcome = runner.extract(
            src_dir, into, name, rdf_format=rdf_format, threshold=threshold
        )
        result.outcomes.append(outcome)
        if outcome.ok:
            size = outcome.schema_path.stat().st_size
            print(f"    ok in {outcome.duration_seconds:.1f}s -> {size / 1e3:.1f} kB", flush=True)
        else:
            print(f"    FAILED: {outcome.error}", flush=True)

    _summary(result)
    return result


#: File suffix -> rdflib format, for a directory that carries no ``report.json``.
#: Only used by :func:`extract_directory`; a run directory declares its own.
SUFFIX_FORMATS = {
    ".ttl": "turtle", ".turtle": "turtle",
    ".nt": "nt", ".ntriples": "nt",
    ".n3": "n3",
    ".rdf": "xml", ".owl": "xml", ".xml": "xml",
    ".jsonld": "json-ld",
    ".trig": "trig",
}


def extract_directory(
    workspace: Workspace,
    src: Path,
    name: str,
    *,
    into: Path | None = None,
    rdf_format: str | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    skip_build: bool = False,
) -> ExtractionResult:
    """Extract a schema from any directory of RDF, not just a benchmark run.

    This is the door for **real** datasets. E3's claim is about what determines a
    generator's reachable coherence range, and the sharpest evidence for it is a
    schema mined from data nobody generated -- a real graph sitting wherever the
    user downloaded it, with no ``report.json`` and no generator behind it.

    Output lands in ``schemas/extracted/external/<name>.shex`` so it does not
    collide with a profile's extractions.
    """
    src = Path(src).resolve()
    if not src.is_dir():
        raise ConfigError(f"{src} is not a directory")

    target = _resolve_into(workspace, into) / "external"
    rdf_format = rdf_format or _sniff_format(src)

    runner = DockerRunner(workspace)
    runner.preflight()
    if not skip_build:
        runner.build_service("shexer")

    print(f"\nextracting {name!r} from {src} ({rdf_format}) into {target}", flush=True)
    outcome = runner.extract(src, target, name, rdf_format=rdf_format, threshold=threshold)

    if outcome.ok:
        print(f"    ok in {outcome.duration_seconds:.1f}s -> "
              f"{outcome.schema_path.stat().st_size / 1e3:.1f} kB", flush=True)
    else:
        print(f"    FAILED: {outcome.error}", flush=True)

    result = ExtractionResult(profile=f"external:{name}", into=target, outcomes=[outcome])
    _summary(result)
    return result


def _sniff_format(src: Path) -> str:
    """Infer the serialisation from file suffixes, requiring agreement.

    A mixed directory is rejected rather than guessed at: sheXer parses every
    input with one parser, so picking the majority format would silently drop
    whatever did not match.
    """
    found = {
        SUFFIX_FORMATS[p.suffix.lower()]
        for p in src.rglob("*")
        if p.is_file() and p.suffix.lower() in SUFFIX_FORMATS
    }
    if not found:
        raise ConfigError(
            f"no recognised RDF files under {src}. "
            f"Known suffixes: {', '.join(sorted(SUFFIX_FORMATS))}"
        )
    if len(found) > 1:
        raise ConfigError(
            f"{src} mixes {', '.join(sorted(found))}. Pass --format to choose one, "
            "or split the directory -- sheXer parses every input with a single parser."
        )
    return found.pop()


def _resolve_into(workspace: Workspace, into: Path | None) -> Path:
    path = Path(into) if into is not None else DEFAULT_INTO
    if not path.is_absolute():
        path = workspace.root / path
    return path


#: Prefixes that mark an experiment's role in its own profile rather than
#: anything about the schema mined from it.
ROLE_PREFIXES = ("src_", "ref_")


def _schema_name(experiment: str) -> str:
    """``ref_bsbm_high`` -> ``bsbm_high``.

    The prefix says how the experiment is used in the profile that produced it —
    a reference bar, a phase-1 source — which is a fact about that profile, not
    about the schema. E3 names these schemas by generator, so it is stripped.
    """
    for prefix in ROLE_PREFIXES:
        if experiment.startswith(prefix):
            return experiment[len(prefix):]
    return experiment


def _rdf_format(src_dir: Path, fallback: str) -> str:
    """Read the serialisation from the run's own report, as the metrics do.

    The report is authoritative because the container declared what it wrote.
    ``generator.yaml`` is the fallback for a run predating a format change.
    """
    try:
        return BenchmarkReport.read(src_dir / "report.json").output.rdf_format or fallback
    except ReportError:
        return fallback


def _summary(result: ExtractionResult) -> None:
    good = len(result.outcomes) - len(result.failed)
    print(f"\nextracted {good}/{len(result.outcomes)} schema(s) into {result.into}", flush=True)
    for outcome in result.failed:
        print(f"  FAILED {outcome.name}: {outcome.error}", flush=True)


__all__ = [
    "ExtractionResult",
    "extract_profile",
    "extract_directory",
    "DEFAULT_INTO",
    "DEFAULT_THRESHOLD",
]
