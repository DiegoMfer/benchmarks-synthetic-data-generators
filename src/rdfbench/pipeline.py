"""The full benchmark pipeline, start to finish.

One call to :func:`run_pipeline` does everything: build the generator images,
run every experiment in the profile, measure the resulting RDF, and write the
CSV and charts. ``main.py`` is a thin argument parser over this function.

Stages are separable only so a long sweep can be resumed (``--skip-generate``
re-measures data already on disk); the default is to run all of them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .analysis import csv_export, plots
from .config import ConfigError, Experiment, GeneratorSpec, Profile, Workspace
from .metrics.compute import RunMetrics, compute_run_metrics
from .runner import DockerError, DockerRunner, RunOutcome


@dataclass
class PipelineResult:
    profile: str
    outcomes: list[RunOutcome] = field(default_factory=list)
    metrics: list[RunMetrics] = field(default_factory=list)
    csv_path: Path | None = None
    chart_paths: list[Path] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def failed_runs(self) -> list[RunOutcome]:
        return [o for o in self.outcomes if not o.ok]

    @property
    def failed_metrics(self) -> list[RunMetrics]:
        return [m for m in self.metrics if not m.ok]

    @property
    def ok(self) -> bool:
        return not self.failed_runs and not self.failed_metrics and bool(self.metrics)


def run_pipeline(
    workspace: Workspace,
    profile_name: str,
    *,
    only: list[str] | None = None,
    runs_override: int | None = None,
    skip_build: bool = False,
    skip_generate: bool = False,
    skip_metrics: bool = False,
    skip_plots: bool = False,
    keep_going: bool = True,
) -> PipelineResult:
    started = time.monotonic()

    profile = Profile.load(workspace.profile_path(profile_name))
    specs = workspace.load_generators()
    experiments = profile.select(only)

    if runs_override is not None:
        experiments = [
            Experiment(e.name, e.generator, e.params, runs_override, e.description)
            for e in experiments
        ]

    _validate(experiments, specs)

    result = PipelineResult(profile=profile.name)
    total = sum(e.runs for e in experiments)

    _banner(
        f"profile {profile.name!r}: {len(experiments)} experiment(s), {total} run(s)",
        profile.description,
    )

    # -- stage 1+2: build and generate ------------------------------------
    if not skip_generate:
        runner = DockerRunner(workspace, timeout=profile.timeout_seconds)
        runner.preflight()

        if not skip_build:
            _banner("building generator images")
            for spec in _unique_specs(experiments, specs):
                runner.build(spec)

        _banner("generating datasets")
        done = 0
        for experiment in experiments:
            spec = specs[experiment.generator]
            for run in range(1, experiment.runs + 1):
                done += 1
                print(f"[{done}/{total}] {experiment.name} run_{run} ...", flush=True)
                outcome = runner.run(spec, experiment, run, profile.name)
                result.outcomes.append(outcome)
                if outcome.ok:
                    print(f"    ok in {outcome.duration_seconds:.1f}s", flush=True)
                else:
                    print(f"    FAILED: {outcome.error}", flush=True)
                    if not keep_going:
                        raise DockerError(f"{experiment.name} run_{run} failed: {outcome.error}")
    else:
        print("skipping generation (--skip-generate)", flush=True)

    # -- stage 3: metrics --------------------------------------------------
    if not skip_metrics:
        _banner("computing metrics")
        for experiment in experiments:
            spec = specs[experiment.generator]
            for run in range(1, experiment.runs + 1):
                run_dir = workspace.run_dir(profile.name, experiment.name, run)
                if not run_dir.exists():
                    continue
                result.metrics.append(
                    compute_run_metrics(run_dir, spec, experiment.name, run)
                )

        results_dir = workspace.results_dir(profile.name)
        results_dir.mkdir(parents=True, exist_ok=True)
        result.csv_path = csv_export.write_metrics_csv(result.metrics, results_dir / "metrics.csv")
        print(f"  wrote {result.csv_path}", flush=True)

    # -- stage 4: charts ---------------------------------------------------
    if not skip_plots and result.csv_path and result.metrics:
        _banner("plotting")
        result.chart_paths = plots.render_all(
            result.metrics,
            workspace.results_dir(profile.name) / "charts",
            baseline=_baseline(workspace, profile),
        )
        for path in result.chart_paths:
            print(f"  wrote {path}", flush=True)

    result.elapsed_seconds = time.monotonic() - started
    _summary(result, total)
    return result


def _baseline(workspace: Workspace, profile: Profile) -> dict[str, list[float]]:
    """Coherence of the profile this one declares itself compared against.

    Returns ``{experiment: [coherence per run]}``. Missing is not an error: the
    two E3 phases are run separately and by design, so plotting phase 2 before
    phase 1 has been measured should produce the phase-2 charts without the
    baseline rather than fail.
    """
    if not profile.compare_with:
        return {}

    path = workspace.results_dir(profile.compare_with) / "metrics.csv"
    if not path.exists():
        print(
            f"  no baseline at {path} - the bracketing chart needs "
            f"`--profile {profile.compare_with}` to have been measured first",
            flush=True,
        )
        return {}

    values: dict[str, list[float]] = {}
    for row in csv_export.read_metrics_csv(path):
        raw = row.get("RDF_Coherence")
        if raw:
            values.setdefault(row["Experiment"], []).append(float(raw))
    return values


def _validate(experiments: list[Experiment], specs: dict[str, GeneratorSpec]) -> None:
    """Fail before starting a multi-hour sweep, not three hours into it."""
    problems: list[str] = []
    for experiment in experiments:
        spec = specs.get(experiment.generator)
        if spec is None:
            problems.append(
                f"{experiment.name}: unknown generator {experiment.generator!r} "
                f"(known: {', '.join(sorted(specs)) or 'none'})"
            )
            continue
        try:
            spec.render_args(experiment.params)
        except ConfigError as exc:
            problems.append(f"{experiment.name}: {exc}")
    if problems:
        raise ConfigError("invalid profile:\n  - " + "\n  - ".join(problems))


def _unique_specs(
    experiments: list[Experiment], specs: dict[str, GeneratorSpec]
) -> list[GeneratorSpec]:
    seen: dict[str, GeneratorSpec] = {}
    for experiment in experiments:
        spec = specs[experiment.generator]
        seen.setdefault(spec.name, spec)
    return list(seen.values())


def _banner(title: str, subtitle: str = "") -> None:
    print(f"\n{'=' * 78}\n{title}", flush=True)
    if subtitle:
        print(subtitle, flush=True)
    print("=" * 78, flush=True)


def _summary(result: PipelineResult, planned: int) -> None:
    _banner("summary")
    succeeded = len([o for o in result.outcomes if o.ok])
    if result.outcomes:
        print(f"generation : {succeeded}/{len(result.outcomes)} run(s) ok (planned {planned})")
    if result.metrics:
        good = len([m for m in result.metrics if m.ok])
        print(f"metrics    : {good}/{len(result.metrics)} run(s) measured")

    for outcome in result.failed_runs:
        print(f"  FAILED generate: {outcome.experiment} run_{outcome.run}: {outcome.error}")
    for metric in result.failed_metrics:
        print(f"  FAILED metrics : {metric.experiment} run_{metric.run}: {metric.error}")

    notes = [(m, n) for m in result.metrics for n in m.notes]
    if notes:
        print("\nnotes:")
        for metric, note in notes:
            print(f"  {metric.experiment} run_{metric.run}: {note}")

    mins, secs = divmod(int(result.elapsed_seconds), 60)
    print(f"\nelapsed    : {mins}m {secs}s")
    print(f"status     : {'OK' if result.ok else 'INCOMPLETE'}")
