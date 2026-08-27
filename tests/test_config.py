"""Tests for generator specs and profiles.

The profile files that ship with the project are validated here too: a typo in
e2.yaml would otherwise only surface hours into a run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rdfbench.config import (
    ConfigError,
    GeneratorSpec,
    ParamSpec,
    Profile,
    Workspace,
)

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def workspace() -> Workspace:
    return Workspace(ROOT)


# -- parameter rendering --------------------------------------------------


def test_scalar_param_renders_flag_and_value():
    assert ParamSpec(flag="--products", type="int").render(100) == ["--products", "100"]


def test_true_bool_renders_only_its_flag():
    assert ParamSpec(flag="--materialization", type="bool").render(True) == [
        "--materialization"
    ]


def test_false_bool_renders_nothing_without_a_false_flag():
    assert ParamSpec(flag="--materialization", type="bool").render(False) == []


def test_false_bool_renders_its_false_flag_when_declared():
    spec = ParamSpec(flag="--forward-chaining", type="bool", false_flag="--no-forward-chaining")
    assert spec.render(False) == ["--no-forward-chaining"]


# -- generator specs ------------------------------------------------------


def test_unknown_param_is_rejected_rather_than_dropped():
    """A profile typo must fail, not silently generate with defaults."""
    spec = GeneratorSpec(
        name="bsbm",
        service="bsbm",
        data_files=("dataset.ttl",),
        rdf_format="turtle",
        params={"products": ParamSpec(flag="--products", type="int")},
    )
    with pytest.raises(ConfigError, match="prodcts"):
        spec.render_args({"prodcts": 100})


def test_every_shipped_generator_spec_loads(workspace):
    specs = workspace.load_generators()
    assert set(specs) == {
        "bsbm",
        "gaia",
        "linkgen",
        "lubm",
        "pygraft",
        "rdfgraphgen",
        "rudof",
        "synthea",
        "watdiv",
        "lemming",
    }
    for name, spec in specs.items():
        assert spec.name == name
        assert spec.data_files, f"{name} declares no data_files"
        assert spec.rdf_format


# -- profiles -------------------------------------------------------------


def test_experiment_selection_filters_and_preserves_order(workspace):
    profile = Profile.load(workspace.profile_path("e2"))
    selected = profile.select(["rudof_shex_low", "gaia_high"])
    assert [e.name for e in selected] == ["rudof_shex_low", "gaia_high"]


def test_selecting_an_unknown_experiment_is_rejected(workspace):
    profile = Profile.load(workspace.profile_path("e2"))
    with pytest.raises(ConfigError, match="nonexistent"):
        profile.select(["nonexistent"])


def test_unknown_profile_lists_the_available_ones(workspace):
    """A typo should name the alternatives, not just fail."""
    with pytest.raises(ConfigError, match="e2"):
        workspace.profile_path("does_not_exist")


ALL_PROFILES = [
    "e2", "e2_smoke",
    "e4", "e4_smoke",
    "e5", "e5_smoke",
]


@pytest.mark.parametrize("name", ALL_PROFILES)
def test_shipped_profiles_are_valid_against_the_generator_specs(workspace, name):
    """Catch a bad profile at test time instead of hours into a sweep."""
    profile = Profile.load(workspace.profile_path(name))
    specs = workspace.load_generators()

    for experiment in profile.experiments:
        assert experiment.generator in specs, (
            f"{name}/{experiment.name} names unknown generator {experiment.generator!r}"
        )
        # Raises ConfigError if any parameter is not declared by the generator.
        specs[experiment.generator].render_args(experiment.params)


@pytest.mark.parametrize("full", ["e2", "e4", "e5"])
def test_each_experiment_has_a_matching_smoke_profile(workspace, full):
    """A smoke profile must exercise exactly its full profile's configurations.

    The smoke variant exists to verify an experiment before it is run for real,
    which only works if the two define the same experiments and differ solely in
    their numbers.
    """
    a = {e.name for e in Profile.load(workspace.profile_path(full)).experiments}
    b = {e.name for e in Profile.load(workspace.profile_path(f"{full}_smoke")).experiments}
    assert a == b


@pytest.mark.parametrize("name,runs", [("e2", 10), ("e5", 10)])
def test_full_profiles_repeat_runs(workspace, name, runs):
    """Repeated runs are what make the reported spread meaningful."""
    profile = Profile.load(workspace.profile_path(name))
    assert profile.runs == runs
    assert profile.total_runs == runs * len(profile.experiments)


def test_malformed_profile_is_rejected(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("name: bad\nruns: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="experiments"):
        Profile.load(path)


# -- E2: the divider is what makes the comparison legitimate ---------------


#: How each compared generator receives the LUBM schema. A parameter name means
#: the profile supplies it and the value is checked; ``None`` means the path is
#: fixed inside that generator's entrypoint. Listing the second case explicitly
#: keeps it a stated exemption rather than a silent pass.
LUBM_INPUT = {
    "rudof": "schema",
    "rdfgraphgen": "shape",
    "linkgen": "ontology",
    "gaia": None,  # hardcoded: /schemas/lubm/univ-bench.owl
}


@pytest.mark.parametrize("name", ["e2", "e2_smoke"])
def test_e2_compared_generators_all_read_the_lubm_schema(workspace, name):
    """Left of the divider, the input must actually be shared.

    E2's only defensible claim is that generators fed the *same* schema differ
    because the tools differ. An experiment quietly reading something else would
    void it, so membership is asserted rather than left to review.
    """
    profile = Profile.load(workspace.profile_path(name))
    for experiment in profile.experiments:
        if experiment.name.startswith("ref_"):
            continue
        assert experiment.generator in LUBM_INPUT, (
            f"{experiment.name} uses {experiment.generator}, which is not known to "
            "read the shared schema; add it to LUBM_INPUT or move it behind ref_"
        )
        param = LUBM_INPUT[experiment.generator]
        if param is None:
            continue  # schema fixed in the entrypoint
        value = str(experiment.params.get(param, ""))
        assert "lubm" in value or "univ-bench" in value, (
            f"{experiment.name} is left of the divider but its {param} is {value!r}"
        )


@pytest.mark.parametrize("name", ["e2", "e2_smoke"])
def test_e2_reference_generators_take_no_shared_schema(workspace, name):
    """Right of the divider are exactly the tools that cannot be given one.

    Being fixed-schema, DSL-driven or data-driven is the entry criterion; a
    generator that *could* read the shared schema belongs in the comparison, and
    parking it on the reference side would understate the comparison's reach.
    """
    profile = Profile.load(workspace.profile_path(name))
    cannot_take_a_schema = {"lubm", "bsbm", "watdiv", "pygraft", "lemming"}
    refs = [e for e in profile.experiments if e.name.startswith("ref_")]
    assert refs, f"{name} defines no reference experiments"
    for experiment in refs:
        assert experiment.generator in cannot_take_a_schema, (
            f"{experiment.name} uses {experiment.generator}, which can read a schema"
        )
