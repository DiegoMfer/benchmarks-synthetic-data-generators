"""Declarative configuration: generators and profiles are data, not code.

Two kinds of YAML feed the runner:

``generators/<name>/generator.yaml``
    A :class:`GeneratorSpec`. Declares the compose service, which files the
    generator produces, their RDF serialisation, and how each parameter maps to
    a command-line flag. This is the single source of truth for output
    discovery -- the old codebase hardcoded those filenames in two places 600
    lines apart, so renaming an output silently produced empty metrics.

``profiles/<name>.yaml``
    A :class:`Profile`. A named set of experiments plus repeat count. ``smoke``
    and ``paper`` share this schema and differ only in their numbers, so the
    fast configuration exercises exactly the same code path as the real one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml

#: Parameter types a generator may declare.
PARAM_TYPES = frozenset({"int", "float", "str", "bool"})


class ConfigError(ValueError):
    """Raised for malformed generator specs or profiles."""


@dataclass(frozen=True)
class ParamSpec:
    """How one experiment parameter becomes a container command-line argument."""

    flag: str
    type: str = "str"
    #: For ``bool`` params: the flag emitted when the value is ``False``. When
    #: ``None`` (the default) a false value emits nothing, i.e. store_true.
    false_flag: str | None = None

    def render(self, value: Any) -> list[str]:
        """Return the argv fragment for *value*, or ``[]`` if it contributes none."""
        if self.type == "bool":
            if bool(value):
                return [self.flag]
            return [self.false_flag] if self.false_flag else []
        return [self.flag, str(value)]


@dataclass(frozen=True)
class GeneratorSpec:
    name: str
    service: str
    data_files: tuple[str, ...]
    rdf_format: str
    params: dict[str, ParamSpec] = field(default_factory=dict)
    description: str = ""

    @classmethod
    def load(cls, path: Path) -> GeneratorSpec:
        raw = _load_yaml(path)
        for key in ("name", "service", "data_files", "rdf_format"):
            if key not in raw:
                raise ConfigError(f"{path}: missing required key {key!r}")

        params: dict[str, ParamSpec] = {}
        for pname, praw in (raw.get("params") or {}).items():
            if not isinstance(praw, dict) or "flag" not in praw:
                raise ConfigError(f"{path}: param {pname!r} needs a 'flag'")
            ptype = praw.get("type", "str")
            if ptype not in PARAM_TYPES:
                raise ConfigError(
                    f"{path}: param {pname!r} has type {ptype!r}, expected one of {sorted(PARAM_TYPES)}"
                )
            params[pname] = ParamSpec(
                flag=praw["flag"], type=ptype, false_flag=praw.get("false_flag")
            )

        return cls(
            name=raw["name"],
            service=raw["service"],
            data_files=tuple(raw["data_files"]),
            rdf_format=raw["rdf_format"],
            params=params,
            description=raw.get("description", ""),
        )

    def render_args(self, params: dict[str, Any]) -> list[str]:
        """Turn an experiment's parameters into container argv.

        Unknown parameters are an error rather than being silently dropped -- a
        typo in a profile should fail loudly, not produce a dataset generated
        with default settings.
        """
        unknown = set(params) - set(self.params)
        if unknown:
            raise ConfigError(
                f"generator {self.name!r} has no parameter(s): {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(self.params))}"
            )
        argv: list[str] = []
        for pname, value in params.items():
            argv.extend(self.params[pname].render(value))
        return argv


@dataclass(frozen=True)
class Experiment:
    """One named generator configuration, repeated ``runs`` times."""

    name: str
    generator: str
    params: dict[str, Any]
    runs: int
    description: str = ""


@dataclass(frozen=True)
class Profile:
    name: str
    runs: int
    timeout_seconds: int
    experiments: tuple[Experiment, ...]
    description: str = ""
    #: Another profile whose measured results this one is plotted against.
    #: E3 is the only user: its phase-2 chart needs each source generator's
    #: coherence beside the rudof pair derived from it, and those live in a
    #: different profile's CSV. Declared here rather than inferred so the
    #: pairing is visible in the profile that depends on it.
    compare_with: str | None = None

    @classmethod
    def load(cls, path: Path) -> Profile:
        raw = _load_yaml(path)
        if "experiments" not in raw:
            raise ConfigError(f"{path}: missing 'experiments'")

        default_runs = int(raw.get("runs", 1))
        experiments = []
        for ename, eraw in raw["experiments"].items():
            if not isinstance(eraw, dict) or "generator" not in eraw:
                raise ConfigError(f"{path}: experiment {ename!r} needs a 'generator'")
            experiments.append(
                Experiment(
                    name=ename,
                    generator=eraw["generator"],
                    params=dict(eraw.get("params") or {}),
                    runs=int(eraw.get("runs", default_runs)),
                    description=eraw.get("description", ""),
                )
            )

        if not experiments:
            raise ConfigError(f"{path}: profile defines no experiments")

        return cls(
            name=raw.get("name", path.stem),
            runs=default_runs,
            timeout_seconds=int(raw.get("timeout_seconds", 3600)),
            experiments=tuple(experiments),
            description=raw.get("description", ""),
            compare_with=raw.get("compare_with"),
        )

    def select(self, only: list[str] | None) -> list[Experiment]:
        """Return experiments filtered by name, preserving profile order."""
        if not only:
            return list(self.experiments)
        known = {e.name for e in self.experiments}
        unknown = set(only) - known
        if unknown:
            raise ConfigError(
                f"profile {self.name!r} has no experiment(s): {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(known))}"
            )
        return [e for e in self.experiments if e.name in set(only)]

    @property
    def total_runs(self) -> int:
        return sum(e.runs for e in self.experiments)


@dataclass(frozen=True)
class Workspace:
    """Filesystem layout. Everything generated lives under ``data/``."""

    root: Path

    @property
    def generators_dir(self) -> Path:
        return self.root / "generators"

    @property
    def profiles_dir(self) -> Path:
        return self.root / "profiles"

    @property
    def schemas_dir(self) -> Path:
        return self.root / "schemas"

    @property
    def compose_file(self) -> Path:
        return self.root / "docker-compose.yml"

    def runs_dir(self, profile: str) -> Path:
        return self.root / "data" / "runs" / profile

    def results_dir(self, profile: str) -> Path:
        return self.root / "data" / "results" / profile

    def run_dir(self, profile: str, experiment: str, run: int) -> Path:
        return self.runs_dir(profile) / experiment / f"run_{run}"

    def profile_path(self, name: str) -> Path:
        path = self.profiles_dir / f"{name}.yaml"
        if not path.exists():
            available = sorted(p.stem for p in self.profiles_dir.glob("*.yaml"))
            raise ConfigError(f"no profile {name!r}. Available: {', '.join(available) or '(none)'}")
        return path

    def load_generators(self) -> dict[str, GeneratorSpec]:
        """Discover every ``generators/*/generator.yaml``."""
        specs: dict[str, GeneratorSpec] = {}
        for spec_file in sorted(self.generators_dir.glob("*/generator.yaml")):
            spec = GeneratorSpec.load(spec_file)
            if spec.name in specs:
                raise ConfigError(f"duplicate generator name {spec.name!r} at {spec_file}")
            specs[spec.name] = spec
        return specs


def iter_planned_runs(
    experiments: list[Experiment],
) -> Iterator[tuple[Experiment, int]]:
    """Yield ``(experiment, run_number)`` pairs, run numbers starting at 1."""
    for experiment in experiments:
        for run in range(1, experiment.runs + 1):
            yield experiment, run


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"{path}: cannot read ({exc})") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML ({exc})") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: expected a YAML mapping at the top level")
    return raw
