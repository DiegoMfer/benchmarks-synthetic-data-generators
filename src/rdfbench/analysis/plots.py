"""Charts for the measured benchmark results.

Replaces ``metrics_histogram.ipynb`` with code that runs as part of the pipeline,
so the figures can never drift from the CSV beside them. The chart *forms* are
carried over from that notebook, because they encode the experimental design:

**Grouped bars, HIGH vs LOW per generator.** The benchmark asks whether each
generator actually responds to its coherence configuration. That question lives
in the *pair*, so the two configurations must sit side by side under one
generator label. Plotting the 16 experiments as independent bars would destroy
the comparison the benchmark exists to make.

**Error bars over runs.** Ten runs per configuration; mean +/- standard
deviation. PyGraft in particular varies enough between runs that a bare mean
would misrepresent it.

**A broken y-axis for throughput.** Throughput spans two orders of magnitude
across generators, so a linear axis flattens everything below the leader into
invisible stubs. The break here is computed from the data rather than hardcoded.

**A sensitivity chart.** ``|delta coherence|`` per generator, signed by colour:
this is the summary figure, and it is the one that shows which generators
control coherence at all and which move the wrong way.

Colour: the notebook used steelblue/coral, which fails the accessibility checks
(steelblue falls below the chroma floor and reads grey; coral falls below 3:1
against the surface). The blue/orange pair here is visually equivalent and
passes every check, including CVD separation. The diverging red/blue of the
sensitivity chart is kept exactly as it was -- it already passes.

These are print figures for a paper: light mode only, static, no hover layer.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable, Sequence

from ..metrics.compute import RunMetrics

# -- palette (validated: CVD dE 24.7, all slots >= 3:1 on this surface) ------
HIGH_COLOUR = "#2a78d6"  # blue
LOW_COLOUR = "#eb6834"  # orange
POSITIVE = "#1976d2"  # delta in the expected direction (HIGH > LOW)
NEGATIVE = "#d32f2f"  # delta inverted -- the generator moved the wrong way

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e3e2df"

FIG_W, FIG_H = 7.5, 5.0
TITLE_SIZE, LABEL_SIZE, TICK_SIZE, LEGEND_SIZE = 12, 10, 9, 9

HIGH, LOW, SINGLE = "HIGH", "LOW", "SINGLE"

#: Third slot for generators that expose no coherence configuration at all.
SINGLE_COLOUR = "#1baf7a"  # aqua, validated against the blue/orange pair

#: Reference-side bars keep their configuration colour and gain a hatch, so the
#: two facts stay on separate channels: hue says which configuration, texture
#: says whether the generator is part of the controlled comparison. Collapsing
#: both into one grey slot would hide that WatDiv, though it cannot be given the
#: shared schema, does respond to a structural parameter.
REFERENCE_HATCH = "///"

#: Gap, in bar-slot widths, inserted between the compared generators and the
#: reference block so the split is visible before any label is read.
REFERENCE_GAP = 0.75

#: (source, metric key, filename stem, y-axis label, title, value format)
GROUPED_CHARTS = (
    ("perf", "Throughput_Measured", "throughput_by_generator", "throughput (triples/s)",
     "Throughput by generator", "{:,.0f}"),
    ("rdf", "RDF_Coherence", "coherence_by_generator", "RDF coherence",
     "RDF coherence by generator", "{:.3f}"),
    ("perf", "Duration_Seconds", "execution_time_by_generator", "execution time (s)",
     "Execution time by generator", "{:.2f}"),
)


def render_all(
    metrics: Iterable[RunMetrics],
    out_dir: Path,
    baseline: dict[str, list[float]] | None = None,
) -> list[Path]:
    """Render every standard chart. Returns the paths written.

    *baseline* carries another profile's coherence, keyed by experiment name. It
    is supplied only for E3 phase 2, where the comparison a chart has to make
    spans two profiles.
    """
    metrics = [m for m in metrics if m.ok]
    if not metrics:
        return []

    try:
        import matplotlib
    except ImportError:
        print("  matplotlib not installed - skipping charts", flush=True)
        return []

    matplotlib.use("Agg")
    out_dir.mkdir(parents=True, exist_ok=True)

    # A profile that sweeps a numeric parameter gets response curves; grouped
    # bars over twenty fill values would carry no comparison. Detection is from
    # the recorded parameters, so no profile has to declare its kind.
    # E3 phase 2: the question is whether each source generator's coherence
    # falls inside the range rudof reaches from shapes extracted out of that
    # generator's own output. That is a triplet, so it precedes the generic
    # paired-bar path.
    written: list[Path] = []
    if baseline and _bracket_groups(metrics, baseline):
        chart = _bracketing_chart(metrics, baseline, out_dir / "coherence_bracketing.pdf")
        if chart:
            written.append(chart)

    # A sweep profile can carry both: the curves show *how* coherence responds,
    # the bracketing chart whether the source's own value lies in the range that
    # response covers. They answer different questions from the same runs.
    if _sweep_axis(metrics) is not None:
        return written + _sweep_charts(metrics, out_dir)
    if written:
        return written

    # A profile in which *every* experiment reports conformance, and which pairs
    # no configurations, is asking the conformance question: one measurement per
    # input schema. Requiring `all` keeps this chart out of profiles where rudof
    # reports conformance but the generators beside it cannot. Requiring the
    # absence of HIGH/LOW pairs keeps it out of an all-rudof profile that varies
    # a configuration across schemas -- there the question is the reachable span,
    # and the paired bars answer it.
    if metrics and all(m.conformance for m in metrics) and not _has_pairs(metrics):
        chart = _conformance_chart(metrics, out_dir / "schema_conformance.pdf")
        return [chart] if chart else []

    # The FHIR case study asks a domain question the generic bars cannot put:
    # coverage of a specification against conformance to it. It is a comparison
    # between *tools*, so it needs at least two of them -- an all-rudof profile
    # that happens to include a FHIR schema is asking about schemas, not about
    # who covers the specification better.
    if len({m.generator for m in metrics if m.domain}) >= 2:
        chart = _fhir_tradeoff_chart(metrics, out_dir / "fhir_coverage_vs_conformance.pdf")
        if chart:
            written.append(chart)

    paired = _has_pairs(metrics)

    for source, key, stem, ylabel, title, fmt in GROUPED_CHARTS:
        path = out_dir / f"{stem}.pdf"
        rendered = (
            _grouped_chart(metrics, source, key, ylabel, title, path)
            if paired
            else _single_series_chart(metrics, source, key, ylabel, title, fmt, path)
        )
        if rendered:
            written.append(rendered)

    return written


# ---------------------------------------------------------------------------
# Experiment naming
# ---------------------------------------------------------------------------


#: Experiment-name suffix -> configuration level. Both spellings are accepted:
#: the profiles use ``_high``/``_low``, the older published charts used
#: ``_high_coherence``. Longest suffixes first so ``_high_coherence`` is matched
#: before ``_high`` would strip only part of it.
LEVEL_SUFFIXES = (
    ("_high_coherence", HIGH),
    ("_low_coherence", LOW),
    ("_high", HIGH),
    ("_low", LOW),
)

#: Marks a generator that cannot be given the shared schema and is therefore
#: drawn apart from the controlled comparison rather than inside it.
REFERENCE_PREFIX = "ref_"


def _split(experiment: str) -> tuple[str, str]:
    """Split ``gaia_high`` into ``("gaia", "HIGH")``.

    Configuration level and comparison side are **independent**, which is what a
    single ``REFERENCE`` level got wrong: WatDiv cannot be given the LUBM schema,
    so it belongs on the reference side, but it does expose a structural
    parameter and so still has a HIGH and a LOW bar. Encoding "which side" as a
    level forced such a generator into one grey bar and discarded a result.

    Side comes from the ``ref_`` prefix (:func:`_is_reference`); level from the
    suffix:

    ``HIGH`` / ``LOW``
        The two ends of a generator's own coherence configuration.

    ``SINGLE``
        A generator exposing no such parameter, so it gets one bar. That is a
        result, not missing data -- RDFGraphGen reads the same SHACL shapes as
        rudof and offers nothing to turn.
    """
    name = experiment[len(REFERENCE_PREFIX):] if _is_reference(experiment) else experiment
    for suffix, level in LEVEL_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)], level
    return name, SINGLE


def _is_reference(experiment: str) -> bool:
    """True when the experiment sits outside the controlled comparison."""
    return experiment.startswith(REFERENCE_PREFIX)


def _has_pairs(metrics: Sequence[RunMetrics]) -> bool:
    """True when at least one generator has both a HIGH and a LOW experiment."""
    seen: dict[str, set[str]] = {}
    for metric in metrics:
        base, level = _split(metric.experiment)
        if level:
            seen.setdefault(base, set()).add(level)
    return any(levels == {HIGH, LOW} for levels in seen.values())


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _value(metric: RunMetrics, source: str, key: str) -> float | None:
    raw = (metric.rdf if source == "rdf" else metric.perf).get(key)
    return None if raw is None else float(raw)


def _stats(values: Sequence[float]) -> tuple[float, float]:
    """Mean and sample standard deviation; std is 0 for a single run."""
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


LEVELS = (HIGH, LOW, SINGLE)


def _grouped_series(
    metrics: Sequence[RunMetrics], source: str, key: str
) -> tuple[list[str], dict[str, list[float]], dict[str, list[float]], int]:
    """Return ``(bases, {level: means}, {level: stds}, n_compared)``.

    Compared generators come first, alphabetically, then reference ones.
    ``n_compared`` is where that boundary falls, so the caller can draw the
    split. Sorting references to the end is the point: LUBM and BSBM would
    otherwise land in the middle of the comparison and read as members of it.
    """
    buckets: dict[tuple[str, str], list[float]] = {}
    sides: dict[str, bool] = {}
    for metric in metrics:
        base, level = _split(metric.experiment)
        value = _value(metric, source, key)
        if value is None:
            continue
        buckets.setdefault((base, level), []).append(value)
        # A base is a reference if any of its experiments says so; they always
        # agree in practice, and disagreeing would be a profile bug.
        sides[base] = sides.get(base, False) or _is_reference(metric.experiment)

    compared = sorted(b for b in sides if not sides[b])
    references = sorted(b for b in sides if sides[b])
    bases = compared + references

    means: dict[str, list[float]] = {level: [] for level in LEVELS}
    stds: dict[str, list[float]] = {level: [] for level in LEVELS}

    for base in bases:
        for level in LEVELS:
            values = buckets.get((base, level))
            mean, std = _stats(values) if values else (0.0, 0.0)
            means[level].append(mean)
            stds[level].append(std)

    return bases, means, stds, len(compared)


# ---------------------------------------------------------------------------
# Broken axis
# ---------------------------------------------------------------------------


#: A broken axis only helps when the data is genuinely bimodal. These thresholds
#: encode that: a wide gap, and a top cluster tight enough that the upper panel
#: is readable once it is isolated.
BREAK_MIN_GAP = 4.0
BREAK_MAX_TOP_SPAN = 6.0
#: Above this overall dynamic range a linear axis is useless regardless.
LOG_MIN_RANGE = 50.0


def _scale_for(values: Sequence[float]) -> tuple[str, tuple | None]:
    """Choose the y-scale from the data. Returns ``(kind, break_limits)``.

    Three outcomes, in order of preference:

    ``("linear", None)``
        The default. Bars from a zero baseline, length proportional to value.

    ``("break", (bottom_top, top_bottom, top_max))``
        The data splits into two tight clusters with a wide gap between them --
        which is what the published benchmark's throughput actually looks like
        (a 9.9x gap, top cluster spanning only 2.9x). Isolating the clusters
        keeps both readable, and the diagonal marks make the discontinuity
        explicit.

    ``("log", None)``
        The values are spread continuously across orders of magnitude, so no
        single break helps -- cutting one gap still leaves the upper panel
        spanning too much. Bars are replaced by a dot plot in this case: bar
        length on a log axis is not proportional to value, whereas a dot only
        claims a position, which is exactly what a log axis can honestly give.
    """
    positive = sorted({v for v in values if v > 0})
    if len(positive) < 3:
        return "linear", None

    dynamic_range = positive[-1] / positive[0]
    if dynamic_range < LOG_MIN_RANGE:
        return "linear", None

    best_ratio, best_index = 0.0, -1
    for i in range(len(positive) - 1):
        ratio = positive[i + 1] / positive[i]
        if ratio > best_ratio:
            best_ratio, best_index = ratio, i

    if best_ratio >= BREAK_MIN_GAP:
        top = positive[best_index + 1 :]
        bottom = positive[: best_index + 1]
        top_span = top[-1] / top[0]
        if len(top) >= 2 and len(bottom) >= 2 and top_span <= BREAK_MAX_TOP_SPAN:
            return "break", (bottom[-1] * 1.35, top[0] * 0.9, top[-1] * 1.12)

    return "log", None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _style(ax) -> None:
    """Recessive axes: horizontal grid only, no box."""
    ax.set_facecolor(SURFACE)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=TICK_SIZE)


def _legend_above(ax, ncol: int = 2) -> None:
    """Put the legend between title and plot.

    An in-plot legend has no safe corner here: coherence bars routinely reach
    1.0 in the top-right, which is exactly where a legend wants to sit. Above
    the axes it can never collide with a mark.
    """
    ax.legend(
        fontsize=LEGEND_SIZE, loc="lower right", bbox_to_anchor=(1.0, 1.005),
        frameon=False, labelcolor=TEXT_SECONDARY, ncol=ncol,
        handlelength=1.6, handleheight=1.2, columnspacing=1.6,
    )


def _thousands(ax) -> None:
    from matplotlib.ticker import FuncFormatter

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))


def _grouped_chart(
    metrics: Sequence[RunMetrics],
    source: str,
    key: str,
    ylabel: str,
    title: str,
    path: Path,
) -> Path | None:
    import matplotlib.pyplot as plt
    import numpy as np

    bases, means, stds, n_compared = _grouped_series(metrics, source, key)
    if not bases:
        return None

    all_values = means[HIGH] + means[LOW] + means[SINGLE]
    # Only draw a series that actually has data, so a profile without any
    # single-configuration generator looks exactly as it did before.
    active = [(lvl, col, lab) for lvl, col, lab in (
        (HIGH, HIGH_COLOUR, "HIGH coherence config"),
        (LOW, LOW_COLOUR, "LOW coherence config"),
        (SINGLE, SINGLE_COLOUR, "single configuration (no coherence axis)"),
    ) if any(means[lvl])]
    # Which series each generator actually has, in drawing order -- used to
    # centre the bars of that generator on its own tick.
    present = [
        [lvl for lvl, _, _ in active if means[lvl][i] or stds[lvl][i]]
        for i in range(len(bases))
    ]
    scale, brk = _scale_for(all_values)
    width = 0.35
    # Push the reference block to the right of a visible gap. The comparison and
    # the anchor are different claims, and a reader should see that before
    # reading a single label.
    has_reference = 0 < n_compared < len(bases)
    x = np.arange(len(bases), dtype=float)
    if has_reference:
        x[n_compared:] += REFERENCE_GAP

    runs = _run_count(metrics)
    full_title = f"{title} (HIGH vs LOW config) - mean +/- std over {runs} run(s)"
    if scale == "log":
        ylabel = f"{ylabel}, log scale"
    value_fmt = "{:,.0f}" if max(all_values) >= 1000 else "{:.3f}"

    def draw(ax):
        if scale == "log":
            # Bars on a log axis, matching the notebook's chart form. Bar length
            # is not proportional to value on a log scale, so the axis is
            # labelled accordingly and the reading is the tick position.
            floor = min(v for v in all_values if v > 0) / 3
            group_max = max((len(levels) for levels in present), default=1)
            slot = width * 2 / max(group_max, 2)
            labelled: set[str] = set()
            for level, colour, label in active:
                for xi, base_levels in enumerate(present):
                    if level not in base_levels:
                        continue
                    k = base_levels.index(level)
                    offset = (k - (len(base_levels) - 1) / 2) * slot
                    value = means[level][xi]
                    if value <= 0:
                        continue
                    ax.bar(
                        x[xi] + offset, value - floor, slot * 0.9, bottom=floor,
                        yerr=stds[level][xi], capsize=4, color=colour,
                        hatch=REFERENCE_HATCH if xi >= n_compared else None,
                        edgecolor=SURFACE if xi >= n_compared else None,
                        linewidth=0,
                        label=label if level not in labelled else None,
                        error_kw={"linewidth": 1.2, "ecolor": TEXT_SECONDARY},
                    )
                    labelled.add(level)
            ax.set_yscale("log")
            ax.set_ylim(floor, max(all_values) * 1.6)
        else:
            # Bars are centred per generator, not per series: a generator with a
            # single configuration gets one bar on its tick rather than one
            # parked in the third slot, which would read as misaligned with its
            # label. Legend entries are attached to the first bar of each series.
            # Slot width comes from the widest *group*, not the number of
            # series on the chart: with a reference series present, dividing by
            # the global count would thin every bar to make room for a slot most
            # generators never fill.
            group_max = max((len(levels) for levels in present), default=1)
            slot = width * 2 / max(group_max, 2)
            labelled: set[str] = set()
            span = max(all_values) or 1.0
            # Where a generator's two bars are nearly equal -- which is itself a
            # result, the tool not responding to its configuration -- their value
            # labels overlap. Lift the second of such a pair so both stay legible
            # instead of shrinking the type or dropping one.
            crowded = [
                len(base_levels) > 1
                and max(means[lv][i] for lv in base_levels)
                - min(means[lv][i] for lv in base_levels) < span * 0.06
                for i, base_levels in enumerate(present)
            ]
            for level, colour, label in active:
                for xi, base_levels in enumerate(present):
                    if level not in base_levels:
                        continue
                    k = base_levels.index(level)
                    offset = (k - (len(base_levels) - 1) / 2) * slot
                    value, err = means[level][xi], stds[level][xi]
                    ax.bar(
                        x[xi] + offset, value, slot * 0.9,
                        yerr=err, capsize=4, color=colour,
                        hatch=REFERENCE_HATCH if xi >= n_compared else None,
                        edgecolor=SURFACE if xi >= n_compared else None,
                        linewidth=0,
                        label=label if level not in labelled else None,
                        error_kw={"linewidth": 1.2, "ecolor": TEXT_SECONDARY},
                    )
                    labelled.add(level)
                    # The aqua slot sits below 3:1 against this surface, which
                    # obliges a visible value rather than colour alone. Labelling
                    # every bar is cheap here -- there are at most a dozen -- and
                    # it also lets the figure be read without the CSV.
                    lift = span * 0.025
                    if crowded[xi] and k == len(base_levels) - 1:
                        lift += span * 0.055
                    ax.text(
                        x[xi] + offset, value + err + lift,
                        value_fmt.format(value), ha="center", va="bottom",
                        fontsize=7.5, color=TEXT_SECONDARY, clip_on=True,
                    )
            ax.set_ylim(0, span * 1.18)
        _style(ax)
        if scale != "log" and max(all_values) >= 10_000:
            _thousands(ax)

    def mark_reference(ax, annotate: bool) -> None:
        """Rule and caption separating the comparison from the anchor."""
        if not has_reference:
            return
        boundary = (x[n_compared - 1] + x[n_compared]) / 2
        ax.axvline(boundary, color=TEXT_SECONDARY, linewidth=0.9,
                   alpha=0.45, zorder=0)
        if annotate:
            ax.text(
                boundary + 0.12, ax.get_ylim()[1] * 0.985,
                "reference\nnot compared", ha="left", va="top",
                fontsize=7.5, color=TEXT_SECONDARY, linespacing=1.25,
            )

    # Four legend entries on one row are wider than the plot itself, and
    # `bbox_inches="tight"` then pads the figure out to the legend rather than
    # the axes -- which reads as a large empty margin. Wrap instead.
    # The hatch is a second encoding channel and needs its own key, so it gets a
    # proxy handle rather than being left for the reader to infer from the rule.
    def add_hatch_key(ax) -> None:
        if not has_reference:
            return
        from matplotlib.patches import Patch

        handles, labels = ax.get_legend_handles_labels()
        handles.append(Patch(facecolor=SURFACE, edgecolor=TEXT_SECONDARY,
                             hatch=REFERENCE_HATCH))
        labels.append("hatched: cannot take the shared schema")
        ax.legend(
            handles, labels,
            fontsize=LEGEND_SIZE, loc="lower right", bbox_to_anchor=(1.0, 1.005),
            frameon=False, labelcolor=TEXT_SECONDARY, ncol=legend_cols,
            handlelength=1.6, handleheight=1.2, columnspacing=1.6,
        )

    entries = len(active) + (1 if has_reference else 0)
    legend_cols = 2 if entries >= 4 else entries
    title_pad = 26 + 14 * (-(-entries // legend_cols) - 1)

    if scale != "break":
        fig, ax = plt.subplots(figsize=(FIG_W + 0.8 if has_reference else FIG_W, FIG_H),
                               facecolor=SURFACE)
        draw(ax)
        mark_reference(ax, annotate=True)
        ax.set_xticks(x)
        ax.set_xticklabels(bases, rotation=45, ha="right", fontsize=TICK_SIZE)
        ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
        ax.set_title(full_title, fontsize=TITLE_SIZE, color=TEXT_PRIMARY, pad=title_pad)
        _legend_above(ax, ncol=legend_cols)
        add_hatch_key(ax)
        axes_bottom = ax
    else:
        bottom_top, top_bottom, top_max = brk
        fig, (ax_top, ax_bot) = plt.subplots(
            2, 1, sharex=True, figsize=(FIG_W, FIG_H), facecolor=SURFACE,
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
        )
        draw(ax_top)
        draw(ax_bot)
        ax_top.set_ylim(top_bottom, top_max)
        ax_bot.set_ylim(0, bottom_top)
        # Caption only on the upper panel; the rule belongs on both so the split
        # runs the full height of the figure.
        mark_reference(ax_top, annotate=True)
        mark_reference(ax_bot, annotate=False)

        ax_top.spines["bottom"].set_visible(False)
        ax_bot.spines["top"].set_visible(False)
        ax_top.tick_params(axis="x", bottom=False)
        plt.setp(ax_top.get_xticklabels(), visible=False)

        # Diagonal marks so the discontinuity cannot be mistaken for real scale.
        d = 0.015
        kw = dict(transform=ax_top.transAxes, color=TEXT_SECONDARY, clip_on=False, linewidth=1)
        ax_top.plot((-d, +d), (-d, +d), **kw)
        ax_top.plot((1 - d, 1 + d), (-d, +d), **kw)
        kw.update(transform=ax_bot.transAxes)
        ax_bot.plot((-d, +d), (1 - d, 1 + d), **kw)
        ax_bot.plot((1 - d, 1 + d), (1 - d, 1 + d), **kw)

        ax_bot.set_xticks(x)
        ax_bot.set_xticklabels(bases, rotation=45, ha="right", fontsize=TICK_SIZE)
        ax_top.set_ylabel(ylabel, fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
        ax_top.yaxis.set_label_coords(-0.11, 0.3)
        ax_top.set_title(full_title, fontsize=TITLE_SIZE, color=TEXT_PRIMARY, pad=title_pad)
        _legend_above(ax_top, ncol=legend_cols)
        add_hatch_key(ax_top)
        axes_bottom = ax_bot

    axes_bottom.set_xlabel("")
    fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


def _single_series_chart(
    metrics: Sequence[RunMetrics],
    source: str,
    key: str,
    ylabel: str,
    title: str,
    fmt: str,
    path: Path,
) -> Path | None:
    """Fallback for profiles without a HIGH/LOW design, e.g. the FHIR use case."""
    import matplotlib.pyplot as plt
    import numpy as np

    buckets: dict[str, list[float]] = {}
    for metric in metrics:
        value = _value(metric, source, key)
        if value is not None:
            buckets.setdefault(metric.experiment, []).append(value)
    if not buckets:
        return None

    names = sorted(buckets)
    stats = [_stats(buckets[n]) for n in names]
    means = [s[0] for s in stats]
    stds = [s[1] for s in stats]
    x = np.arange(len(names))

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=SURFACE)
    # A handful of categories on a full-width axis turns 0.5-wide bars into
    # slabs; thin marks read better and the axis carries the scale either way.
    bar_width = 0.5 if len(names) > 4 else 0.30
    ax.bar(x, means, bar_width, yerr=stds, capsize=4, color=HIGH_COLOUR,
           error_kw={"linewidth": 1.2, "ecolor": TEXT_SECONDARY})
    ax.set_xlim(-0.6, len(names) - 0.4)
    _style(ax)
    if max(means) >= 10_000:
        _thousands(ax)

    span = max(means) or 1.0
    for xi, mean, std in zip(x, means, stds):
        ax.text(xi, mean + std + span * 0.02, fmt.format(mean), ha="center",
                fontsize=8, color=TEXT_SECONDARY)
    ax.set_ylim(0, span * 1.18)

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=TICK_SIZE)
    ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
    ax.set_title(f"{title} - mean +/- std over {_run_count(metrics)} run(s)",
                 fontsize=TITLE_SIZE, color=TEXT_PRIMARY)

    fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


def _sensitivity_chart(metrics: Sequence[RunMetrics], path: Path) -> Path | None:
    """|delta coherence| per generator, signed by colour.

    The summary figure: it answers "does configuring this generator for high
    coherence actually raise its coherence?". Bars are the absolute difference
    so magnitudes are comparable at a glance, while the colour and the signed
    annotation preserve direction -- a red bar is a generator whose HIGH config
    produced *less* coherent data than its LOW config.

    The difference is computed per run and then averaged, not as a difference of
    averages, so the standard deviation reflects run-to-run variation in the
    effect itself.
    """
    import matplotlib.pyplot as plt

    by_run: dict[tuple[str, int], dict[str, float]] = {}
    for metric in metrics:
        base, level = _split(metric.experiment)
        value = metric.rdf.get("RDF_Coherence")
        if level and value is not None:
            by_run.setdefault((base, metric.run), {})[level] = float(value)

    diffs: dict[str, list[float]] = {}
    for (base, _run), levels in by_run.items():
        if HIGH in levels and LOW in levels:
            diffs.setdefault(base, []).append(levels[HIGH] - levels[LOW])
    if not diffs:
        return None

    rows = []
    for base, values in diffs.items():
        mean, std = _stats(values)
        rows.append((base, mean, std))
    rows.sort(key=lambda r: abs(r[1]))

    names = [r[0] for r in rows]
    signed = [r[1] for r in rows]
    magnitude = [abs(r[1]) for r in rows]
    errors = [r[2] for r in rows]
    colours = [NEGATIVE if m < 0 else POSITIVE for m in signed]

    height = max(3.0, 0.5 * len(rows) + 1.6)
    fig, ax = plt.subplots(figsize=(9, height), facecolor=SURFACE)
    ax.barh(range(len(rows)), magnitude, xerr=errors, capsize=4, color=colours,
            edgecolor=SURFACE, height=0.6,
            error_kw={"linewidth": 1.2, "ecolor": TEXT_SECONDARY})

    # Signed annotation carries the direction that the absolute bar length drops.
    span = max(m + e for m, e in zip(magnitude, errors)) or 1.0
    for i, (mean, std) in enumerate(zip(signed, errors)):
        ax.text(abs(mean) + std + span * 0.02, i, f"{mean:+.4f} +/- {std:.4f}",
                va="center", ha="left", fontsize=8.5, fontweight="bold",
                color=colours[i])

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(names, fontsize=TICK_SIZE, color=TEXT_PRIMARY)
    ax.set_xlabel(
        f"|delta coherence|  (HIGH - LOW)  mean +/- std over {_run_count(metrics)} run(s)",
        fontsize=LABEL_SIZE, color=TEXT_SECONDARY,
    )
    ax.set_title("Coherence sensitivity to configuration, per generator",
                 fontsize=TITLE_SIZE + 2, color=TEXT_PRIMARY)
    ax.set_xlim(0, span * 1.45)

    ax.set_facecolor(SURFACE)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=TICK_SIZE, length=0)

    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Patch(facecolor=POSITIVE, label="HIGH more coherent (as intended)"),
            Patch(facecolor=NEGATIVE, label="inverted: HIGH less coherent"),
        ],
        fontsize=LEGEND_SIZE, loc="lower right", frameon=False,
        labelcolor=TEXT_SECONDARY,
    )

    fig.tight_layout()
    fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


def _run_count(metrics: Sequence[RunMetrics]) -> int:
    return max((m.run for m in metrics), default=1)


# ---------------------------------------------------------------------------
# Bracketing (E3 phase 2)
# ---------------------------------------------------------------------------

#: Colour for the source generator's own dataset in the bracketing chart. It is
#: not a rudof configuration, so it must not reuse the HIGH/LOW pair.
SOURCE_COLOUR = "#52514e"

#: ``rudof_bsbm_high`` (the two-point round-trip profile) and
#: ``rudof_bsbm_high_fill_030`` (the sweep) both reduce to the base ``bsbm_high``.
BRACKET_PATTERN = re.compile(r"^rudof_(?P<name>.+?)(?:_fill_\d+|_(?:high|low))$")


def _bracket_groups(
    metrics: Sequence[RunMetrics], baseline: dict[str, list[float]]
) -> dict[str, dict[str, list[float]]]:
    """Group runs into ``{name: {"source": [...], "rudof": [...]}}``.

    The band is taken as the **observed minimum and maximum** across every rudof
    run for a schema, not from the endpoint configurations. That matters because
    coherence is not monotone in property fill -- it is U-shaped, and PyGraft's
    curve descends -- so reading the band off the two extreme fill values would
    understate it for some schemas and invert it for others.

    A group is kept only when a source is present too: the claim being plotted is
    a containment, and there is nothing to contain without it.
    """
    groups: dict[str, list[float]] = {}
    for metric in metrics:
        match = BRACKET_PATTERN.match(metric.experiment)
        value = metric.rdf.get("RDF_Coherence")
        if not match or value is None:
            continue
        groups.setdefault(match["name"], []).append(float(value))

    complete: dict[str, dict[str, list[float]]] = {}
    for name, values in groups.items():
        source = baseline.get(f"src_{name}") or baseline.get(name)
        if source and len(values) >= 2:
            complete[name] = {"source": list(source), "rudof": values}
    return complete


def _bracket_layout(names: Sequence[str]) -> tuple[list[tuple[str, str, float]], dict[str, float]]:
    """Position each (generator, config) slot, grouped by generator.

    Returns the slots as ``(generator, level, x)`` plus the centre of each
    generator's group. Grouping is the point: ``bsbm_high`` and ``bsbm_low`` are
    two configurations of one tool, and drawn as unrelated columns they read as
    two different tools.
    """
    by_gen: dict[str, list[str]] = {}
    for name in names:
        for suffix in ("_high", "_low"):
            if name.endswith(suffix):
                by_gen.setdefault(name[: -len(suffix)], []).append(suffix[1:])
                break
        else:
            by_gen.setdefault(name, []).append("")

    slots: list[tuple[str, str, float]] = []
    centres: dict[str, float] = {}
    pos = 0.0
    for gen in sorted(by_gen):
        levels = sorted(by_gen[gen], key=lambda lv: {"high": 0, "low": 1}.get(lv, 0))
        first = pos
        for level in levels:
            slots.append((gen, level, pos))
            pos += 1.0
        centres[gen] = (first + pos - 1.0) / 2
        pos += 0.55  # gap between generators
    return slots, centres


def _bracketing_chart(
    metrics: Sequence[RunMetrics], baseline: dict[str, list[float]], path: Path
) -> Path | None:
    """Does each source's own coherence fall inside the band rudof reaches from its shapes?

    Grouped by source generator, with that generator's own HIGH and LOW
    configurations side by side inside the group. Each slot pairs the dataset the
    generator produced with the interval rudof spanned when driven by shapes mined
    from *that* dataset.

    Two readings, and the grouping is what makes the second one possible:

    * vertically within a slot -- does the bar's top lie inside the band?
    * horizontally within a group -- did the generator's own configuration move
      its output, and did that movement survive into the band?

    The band is the observed minimum and maximum across every rudof run for that
    schema, not the endpoint fills: coherence is not monotone in property fill, so
    endpoints understate the range for some schemas and invert it for others.
    """
    import matplotlib.pyplot as plt

    groups = _bracket_groups(metrics, baseline)
    if not groups:
        return None

    slots, centres = _bracket_layout(sorted(groups))
    width = 0.34

    fig, ax = plt.subplots(
        figsize=(max(FIG_W, 1.05 * len(slots) + 3.4), FIG_H + 0.4), facecolor=SURFACE
    )

    for i, (gen, level, x) in enumerate(slots):
        key = f"{gen}_{level}" if level else gen
        source_mean, source_std = _stats(groups[key]["source"])
        band = groups[key]["rudof"]
        lo, hi = min(band), max(band)
        inside = lo <= source_mean <= hi

        ax.bar(
            x - width / 2, source_mean, width * 0.9, yerr=source_std, capsize=3,
            color=SOURCE_COLOUR, error_kw={"linewidth": 1.1, "ecolor": TEXT_SECONDARY},
            label="source generator's own output" if i == 0 else None, zorder=2,
        )
        bx = x + width / 2
        ax.plot([bx, bx], [lo, hi], color=HIGH_COLOUR, linewidth=8, alpha=0.28,
                solid_capstyle="butt", zorder=1,
                label="rudof's band, from shapes mined from that output" if i == 0 else None)
        for edge in (lo, hi):
            ax.plot([bx - width * 0.45, bx + width * 0.45], [edge, edge],
                    color=HIGH_COLOUR, linewidth=2, zorder=3)

        ax.text(x - width / 2, source_mean + source_std + 0.015, f"{source_mean:.2f}",
                ha="center", va="bottom", fontsize=7, color=TEXT_SECONDARY)
        ax.text(bx + width * 0.5, hi, f"{hi:.2f}", va="center", ha="left",
                fontsize=6.5, color=TEXT_SECONDARY)
        ax.text(bx + width * 0.5, lo, f"{lo:.2f}", va="center", ha="left",
                fontsize=6.5, color=TEXT_SECONDARY)
        ax.text(x, 1.045, "in" if inside else "out", ha="center", fontsize=7.5,
                fontweight="bold", color=POSITIVE if inside else NEGATIVE)
        if level:
            ax.text(x, -0.045, level, ha="center", va="top", fontsize=7.5,
                    color=TEXT_SECONDARY, transform=ax.get_xaxis_transform())

    _style(ax)
    # Generator names sit below the per-configuration labels, so a group reads as
    # one tool with two settings rather than as two tools.
    ax.set_xticks(list(centres.values()))
    ax.set_xticklabels(list(centres), fontsize=TICK_SIZE)
    ax.tick_params(axis="x", pad=18)
    ax.set_xlim(-0.9, max(x for _, _, x in slots) + 0.9)
    ax.set_ylabel("RDF coherence", fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
    ax.set_ylim(0, 1.12)
    ax.set_title(
        "Does a generator's own structuredness survive extraction into ShEx?"
        f"\nband = min..max over rudof's property-fill sweep  ·  "
        f"{_run_count(metrics)} run(s) per point",
        fontsize=TITLE_SIZE, color=TEXT_PRIMARY, pad=38,
    )
    _legend_above(ax, ncol=2)

    fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# FHIR case study (E5)
# ---------------------------------------------------------------------------

#: (column, panel title, value format, lower-is-better)
FHIR_PANELS = (
    ("FHIR_R4_Coverage_Pct", "R4 resource-type coverage (%)", "{:.1f}%", False),
    ("FHIR_Missing_ResourceType_Pct", "Missing resourceType (%)", "{:.0f}%", True),
    ("FHIR_Malformed_Primitives", "Malformed primitives", "{:,.0f}", True),
)


def _fhir_tradeoff_chart(metrics: Sequence[RunMetrics], path: Path) -> Path | None:
    """Specification coverage beside conformance to that specification.

    These three numbers are the case study. The first is what a schema-driven
    generator buys -- every resource type in the standard, from the published
    schema and no domain code. The other two are what it costs, and they run the
    other way, so each panel states its own direction rather than leaving a
    reader to assume that taller is better.

    Three panels rather than one axis: a percentage and a raw count share no
    scale, and forcing them together would be the dual-axis mistake in another
    form.
    """
    import matplotlib.pyplot as plt
    import numpy as np

    names = sorted({m.experiment for m in metrics if m.domain})
    if len(names) < 2:
        return None

    colours = _colour_map(names)
    fig, axes = plt.subplots(
        1, len(FHIR_PANELS), figsize=(3.05 * len(FHIR_PANELS), 4.0), facecolor=SURFACE
    )

    for ax, (column, title, fmt, lower_better) in zip(np.atleast_1d(axes), FHIR_PANELS):
        values, errs = [], []
        for name in names:
            samples = [
                float(m.domain[column]) for m in metrics
                if m.experiment == name and m.domain.get(column) is not None
            ]
            mean, std = _stats(samples) if samples else (0.0, 0.0)
            values.append(mean)
            errs.append(std)

        x = np.arange(len(names))
        ax.bar(x, values, 0.55, yerr=errs if any(errs) else None, capsize=3,
               color=[colours[n] for n in names],
               error_kw={"linewidth": 1.1, "ecolor": TEXT_SECONDARY})
        _style(ax)
        top = max(values) or 1.0
        for xi, (v, e) in enumerate(zip(values, errs)):
            ax.text(xi, v + e + top * 0.03, fmt.format(v), ha="center", va="bottom",
                    fontsize=8, color=TEXT_SECONDARY)
        ax.set_ylim(0, top * 1.24)
        ax.set_xticks(x)
        ax.set_xticklabels([])
        ax.set_title(f"{title}\n{'lower is better' if lower_better else 'higher is better'}",
                     fontsize=9.5, color=TEXT_PRIMARY, pad=6)

    from matplotlib.patches import Patch

    fig.legend(handles=[Patch(facecolor=colours[n], label=n) for n in names],
               loc="lower center", ncol=len(names), frameon=False,
               fontsize=LEGEND_SIZE, labelcolor=TEXT_SECONDARY, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(
        "Coverage of the FHIR R4 specification, against conformance to it"
        f"  \u00b7  {_run_count(metrics)} run(s)",
        fontsize=TITLE_SIZE, color=TEXT_PRIMARY, y=0.99,
    )
    fig.tight_layout(rect=[0, 0.08, 1, 0.92])
    fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


def _conformance_chart(metrics: Sequence[RunMetrics], path: Path) -> Path | None:
    """Schema constraints kept vs lost in translation, one bar per input schema.

    A stacked bar rather than two grouped ones, because the two parts are shares
    of one whole -- the constraints in the source schema -- and stacking states
    that directly: every bar is the same length, and the orange segment is
    exactly what the intermediate representation could not express.

    Triple validity is annotated rather than plotted. It is a different quantity
    (a property of the output, not of the translation) and in practice sits at
    or near 100%, so as a bar it would be a row of full-length blocks carrying
    no information. Printed as a number it still supports the claim.
    """
    import matplotlib.pyplot as plt

    rows: list[tuple[str, float, float, int, int]] = []
    for name in sorted({m.experiment for m in metrics}):
        runs = [m for m in metrics if m.experiment == name]
        loss = [float(m.conformance["Shape_Translation_Loss_Pct"]) for m in runs
                if m.conformance.get("Shape_Translation_Loss_Pct") is not None]
        validity = [float(m.conformance["Triple_Validity_Pct"]) for m in runs
                    if m.conformance.get("Triple_Validity_Pct") is not None]
        if not loss:
            continue
        first = runs[0].conformance
        rows.append((
            _conformance_label(name),
            _stats(loss)[0],
            _stats(validity)[0] if validity else float("nan"),
            int(first.get("Schema_Constraints") or 0),
            int(first.get("Constraints_Represented") or 0),
        ))
    if not rows:
        return None

    labels = [r[0] for r in rows]
    losses = [r[1] for r in rows]
    kept = [100.0 - loss for loss in losses]
    y = list(range(len(rows)))

    height = max(2.6, 0.62 * len(rows) + 1.9)
    fig, ax = plt.subplots(figsize=(9, height), facecolor=SURFACE)

    ax.barh(y, kept, height=0.55, color=HIGH_COLOUR, edgecolor=SURFACE,
            label="represented in the unified IR")
    ax.barh(y, losses, height=0.55, left=kept, color=LOW_COLOUR, edgecolor=SURFACE,
            label="lost in translation")

    for i, (_label, loss, validity, total, represented) in enumerate(rows):
        ax.text(kept[i] / 2, i, f"{represented}/{total} constraints", va="center",
                ha="center", fontsize=8.5, color=SURFACE, fontweight="bold")
        ax.text(101.5, i, f"loss {loss:.1f}%" + (
            f"   validity {validity:.1f}%" if validity == validity else ""
        ), va="center", ha="left", fontsize=8.5, color=TEXT_SECONDARY)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=TICK_SIZE, color=TEXT_PRIMARY)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of the source schema's constraints (%)",
                  fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
    ax.set_title(f"Schema translation loss and triple validity, per input schema"
                 f" - {_run_count(metrics)} run(s)",
                 fontsize=TITLE_SIZE, color=TEXT_PRIMARY, pad=26)

    ax.set_facecolor(SURFACE)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=TICK_SIZE, length=0)
    _legend_above(ax, ncol=2)

    fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    return path


def _conformance_label(experiment: str) -> str:
    """``conformance_lubm_shex`` -> ``lubm / shex``."""
    stem = experiment[len("conformance_"):] if experiment.startswith("conformance_") else experiment
    parts = stem.split("_", 1)
    return " / ".join(parts) if len(parts) == 2 else stem


# ---------------------------------------------------------------------------
# Parameter sweeps
# ---------------------------------------------------------------------------


def _sweep_axis(metrics: Sequence[RunMetrics]) -> str | None:
    """Find the single numeric parameter that is being swept, if any.

    A sweep is detected from the recorded parameters rather than from a naming
    convention: a parameter qualifies when some generator takes at least three
    distinct numeric values for it. Returning ``None`` means this profile is not
    a sweep and no line chart is drawn.
    """
    by_gen: dict[str, dict[str, set]] = {}
    for m in metrics:
        for key, value in m.params.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                by_gen.setdefault(m.generator, {}).setdefault(key, set()).add(float(value))

    candidates = {
        key for params in by_gen.values() for key, values in params.items() if len(values) >= 3
    }
    if len(candidates) != 1:
        return None
    return candidates.pop()


def _sweep_charts(metrics: Sequence[RunMetrics], out_dir: Path) -> list[Path]:
    """Plot each metric against the swept parameter, one line per generator.

    A sweep answers a different question from the paired bars: not "does this
    tool respond to its configuration" but "what range can it reach, and how
    smoothly". A line is the right mark because the x-axis is continuous and the
    reading of interest is the shape of the curve between the measured points.
    """
    axis = _sweep_axis(metrics)
    if axis is None:
        return []

    import matplotlib.pyplot as plt

    written: list[Path] = []
    # One figure. Type coverage is the unweighted variant of coherence and moves
    # with it, so a second panel would restate the same result.
    for key, title, ylabel, fmt in (
        ("RDF_Coherence", "Coherence as a function of property fill", "RDF coherence", "{:.3f}"),
    ):
        series: dict[str, dict[float, list[float]]] = {}
        for m in metrics:
            x = m.params.get(axis)
            y = m.rdf.get(key)
            if x is None or y is None:
                continue
            # Key on the experiment family, not the generator: rudof runs the
            # sweep twice, once per schema language, and their agreement is the
            # result the figure exists to show. Keying on `generator` would
            # merge them into a single line and hide it.
            series.setdefault(_sweep_series(m, axis), {}).setdefault(float(x), []).append(float(y))
        if not series:
            continue

        # Composite encoding: hue identifies the *source* the schema came from,
        # line style its configuration. With a high/low schema per source there
        # are more series than the eight-slot categorical palette allows, and
        # cycling hues past eight produces pairs no colourblind reader can
        # separate. Splitting identity across two channels keeps the hue count at
        # the number of sources and makes the high/low pairing readable as a
        # pairing rather than as two unrelated lines.
        colours = _colour_map({_split(n)[0] for n in series})
        labels = _sweep_labels(metrics, series, axis)
        legend_title = _sweep_legend_title(metrics)
        # A wide legend in few rows beats a tall one: rows push the title up.
        ncol = 3 if len(series) <= 6 else 4
        rows = -(-len(series) // ncol)
        fig_w = FIG_W + (1.6 if len(series) > 6 else 0.0)
        fig, ax = plt.subplots(figsize=(fig_w, FIG_H), facecolor=SURFACE)

        # Solid for the maximal/only configuration, dashed for the low one -- so a
        # dashed line lying on a solid one also remains visible when a pair
        # coincides exactly, which is what E1 needs.
        styles = {HIGH: "-", SINGLE: "-", LOW: "--"}
        ends: list[tuple[float, str, str]] = []
        for name in sorted(series):
            base, level = _split(name)
            points = sorted(series[name].items())
            xs = [x for x, _ in points]
            ys = [_stats(v)[0] for _, v in points]
            errs = [_stats(v)[1] for _, v in points]
            ax.errorbar(
                xs, ys, yerr=errs if any(errs) else None,
                marker="o" if level != LOW else "s", markersize=5,
                linewidth=2, capsize=3,
                linestyle=styles.get(level, "-"),
                color=colours[base], ecolor=TEXT_SECONDARY, elinewidth=1,
                label=labels[name],
            )
            ends.append((ys[-1], labels[name], colours[base]))

        # Direct labels at the line ends, pushed apart so converging curves do
        # not stack their labels on top of each other. Past a handful of series
        # they collide no matter how they are nudged, so identity falls to the
        # legend alone -- a label per line would be chaos, not redundancy.
        ends.sort()
        if len(series) > 5:
            ends = []
        min_gap, last = 0.035, -1.0
        for y, name, colour in ends:
            y_label = max(y, last + min_gap)
            last = y_label
            ax.annotate(
                name, (max(xs), y), textcoords="offset points",
                xytext=(8, (y_label - y) * 260), va="center",
                fontsize=8, color=colour,
            )

        _style(ax)
        ax.set_xlabel(axis.replace("_", " "), fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
        ax.set_ylabel(ylabel, fontsize=LABEL_SIZE, color=TEXT_SECONDARY)
        # The constant belongs in the title, not the legend: as a legend title it
        # collides with this one, and it is the first thing a reader must know.
        subtitle = f"{legend_title}  ·  {_run_count(metrics)} run(s) per point" if legend_title \
            else f"{_run_count(metrics)} run(s) per point"
        ax.set_title(f"{title}\n{subtitle}",
                     fontsize=TITLE_SIZE, color=TEXT_PRIMARY, pad=22 + 13 * rows)
        ax.set_ylim(0, 1.05)
        # Headroom on the right so the direct labels are not clipped.
        xs_all = sorted({float(m.params[axis]) for m in metrics if m.params.get(axis) is not None})
        ax.set_xlim(min(xs_all) - 0.05, max(xs_all) + (max(xs_all) - min(xs_all)) * 0.22)
        _legend_above(ax, ncol=ncol)

        path = out_dir / f"sweep_{key.lower()}.pdf"
        fig.savefig(path, format="pdf", bbox_inches="tight", facecolor=SURFACE)
        plt.close(fig)
        written.append(path)

    return written


def _sweep_series(metric: RunMetrics, axis: str) -> str:
    """Series name for a swept run: the experiment name minus the swept value."""
    stripped = re.sub(r"_(fill|sweep)?_?\d+$", "", metric.experiment)
    return stripped or metric.generator


def _sweep_labels(
    metrics: Sequence[RunMetrics], series: Iterable[str], axis: str
) -> dict[str, str]:
    """Series labels that say what the series *is*.

    Dropping the shared ``rudof_`` prefix leaves labels like ``bsbm`` and
    ``watdiv`` -- which are the names of real generators elsewhere in this same
    benchmark, so the figure reads as a comparison of generators when every run
    in it is rudof. That is the most damaging thing a label can do here, so the
    provenance of each schema is spelled out instead: ``-derived`` marks one
    mined by sheXer from that generator's output, and the legend title names the
    tool that is held constant.
    """
    stripped = _drop_common_prefix(series)
    schema_of: dict[str, str] = {}
    for metric in metrics:
        name = _sweep_series(metric, axis)
        schema = metric.params.get("schema")
        if isinstance(schema, str):
            schema_of.setdefault(name, schema)

    out: dict[str, str] = {}
    for name, short in stripped.items():
        schema = schema_of.get(name, "")
        if "extracted/" in schema:
            out[name] = f"{short}-derived"
        elif schema:
            out[name] = f"{short} (authored)"
        else:
            out[name] = short
    return out


def _sweep_legend_title(metrics: Sequence[RunMetrics]) -> str | None:
    """Name the constant, so the varying thing cannot be mistaken for it."""
    generators = {m.generator for m in metrics}
    if len(generators) != 1:
        return None
    return f"one line per input schema; generator is {generators.pop()} throughout"


def _drop_common_prefix(names: Iterable[str]) -> dict[str, str]:
    """Map each series name to itself minus the prefix every series shares.

    A sweep holds the generator fixed and varies one thing, so that fixed part
    appears in every label and carries no information -- ``rudof_lubm`` and
    ``rudof_bsbm`` become ``lubm`` and ``bsbm``, and the legend then names the
    variable rather than the constant. Only whole underscore-separated segments
    are removed, so a shared prefix that is not a segment boundary is left alone.
    """
    names = sorted(set(names))
    if len(names) < 2:
        return {n: n for n in names}

    segments = [n.split("_") for n in names]
    shared = 0
    for parts in zip(*segments):
        if len(set(parts)) != 1:
            break
        shared += 1
    # Never strip everything: a series must keep at least one segment.
    shared = min(shared, min(len(s) for s in segments) - 1)
    if shared <= 0:
        return {n: n for n in names}
    return {n: "_".join(n.split("_")[shared:]) for n in names}


def _colour_map(names: Iterable[str]) -> dict[str, str]:
    """Stable generator -> hue assignment, sorted so it is reproducible."""
    ordered = sorted(set(names))
    if len(ordered) > len(CATEGORICAL):
        raise ValueError(
            f"{len(ordered)} generators exceeds the {len(CATEGORICAL)}-slot categorical palette"
        )
    return {name: CATEGORICAL[i] for i, name in enumerate(ordered)}


CATEGORICAL = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
)
