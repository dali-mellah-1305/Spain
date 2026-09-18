# -*- coding: utf-8 -*-
"""
Pitch visuals (matplotlib + mplsoccer). Static images, returned as figures for
``st.pyplot``.

Coordinates
-----------
Every function here takes the **common 0-100 pitch** — ``normalized_x`` /
``normalized_y``, and ``normalized_end_x`` / ``normalized_end_y`` — never the raw
``x``/``y``, which are in each row's own native system (StatsBomb 120×80, Opta
100×100) and cannot be overlaid. This is what lets one chart mix the StatsBomb
tournaments with World Cup 2026.

Those normalised values are square (0-100 on both axes), which is not the shape
of a football pitch: plotted directly, the pitch comes out as tall as it is wide
and every distance is read wrongly. So :func:`_sx` / :func:`_sy` map them onto a
105 × 68 m pitch before drawing. The mapping is linear per axis and the
normalisation was too, so relative positions are preserved exactly while the
geometry becomes the real thing.

Direction was checked rather than assumed: in both sources the attacking team
already moves left→right in every period (Spain's shots average x ≈ 84-90 across
periods 1-4 in both), so no half-time flip is applied. See
``data/clean/data_quality_report.md``.
"""
from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch, VerticalPitch

from . import config as C

#: Real pitch dimensions in metres. The normalised 0-100 coordinates are mapped
#: onto these so a pitch looks like a pitch and distances read correctly.
PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0

_TITLE_KW = dict(fontsize=12.5, fontweight="600", color=C.INK, family="sans-serif")
_NOTE_KW = dict(fontsize=9.5, color=C.INK_MUTED, family="sans-serif")

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "figure.facecolor": C.SURFACE,
    "axes.facecolor": C.SURFACE,
    "savefig.facecolor": C.SURFACE,
})


def _sx(values) -> np.ndarray:
    """0-100 normalised length → metres along the pitch."""
    return np.asarray(values, dtype=float) / 100.0 * PITCH_LENGTH


def _sy(values) -> np.ndarray:
    """0-100 normalised width → metres across the pitch."""
    return np.asarray(values, dtype=float) / 100.0 * PITCH_WIDTH


def _cmap(era: str) -> LinearSegmentedColormap:
    """One-hue ramp for the era, light (near zero) to dark."""
    return LinearSegmentedColormap.from_list(f"era_{era}", C.sequential_for(era))


def _pitch(vertical: bool = False, half: bool = False):
    # line_zorder=2 keeps the pitch markings visible *above* a heatmap (drawn at
    # zorder 1) while staying below the marks themselves (zorder 3+).
    kwargs = dict(pitch_type="custom", pitch_length=PITCH_LENGTH,
                  pitch_width=PITCH_WIDTH, pitch_color=C.SURFACE,
                  line_color=C.PITCH_LINE, linewidth=1.1, line_zorder=2,
                  goal_type="box", spot_scale=0.005, pad_top=2)
    if vertical:
        return VerticalPitch(half=half, **kwargs)
    return Pitch(**kwargs)


def _annotate(ax, title: str, note: str = "", color: Optional[str] = None) -> None:
    if title:
        ax.set_title(title, loc="left", pad=9,
                     **{**_TITLE_KW, **({"color": color} if color else {})})
    if note:
        ax.text(0, -0.035, note, transform=ax.transAxes, ha="left", va="top",
                **_NOTE_KW)


def _direction_arrow(pitch, ax, label: bool = True) -> None:
    """A single 'this way is forward' cue, below the pitch."""
    y = -PITCH_WIDTH * 0.065
    pitch.arrows(PITCH_LENGTH * 0.40, y, PITCH_LENGTH * 0.60, y, ax=ax,
                 color=C.INK_MUTED, width=1.1, headwidth=5, headlength=5,
                 zorder=2, clip_on=False)
    if label:
        ax.text(PITCH_LENGTH / 2, -PITCH_WIDTH * 0.115, "attacking direction",
                ha="center", va="top", clip_on=False, **_NOTE_KW)


def _no_data(message: str, figsize=(6, 4)) -> plt.Figure:
    """A labelled empty pitch — an explanation, not a blank rectangle."""
    pitch = _pitch()
    fig, ax = pitch.draw(figsize=figsize)
    ax.text(PITCH_LENGTH / 2, PITCH_WIDTH / 2, message, ha="center", va="center",
            fontsize=10.5, color=C.INK_MUTED, family="sans-serif",
            linespacing=1.5)
    fig.patch.set_facecolor(C.SURFACE)
    return fig


# --------------------------------------------------------------------------- #
# Shot maps
# --------------------------------------------------------------------------- #

def shot_map(shots: pd.DataFrame, *, era: Optional[str] = None, title: str = "",
             note: str = "", figsize=(7.2, 5.6),
             mark_provenance: bool = True) -> plt.Figure:
    """Attacking-half shot map, marker area ∝ xG.

    When the selection mixes official and model-estimated xG, estimated shots
    are drawn with a dashed outline and named in the legend — the two are never
    blended into one undifferentiated cloud, because their reliability differs.
    """
    if shots.empty:
        return _no_data("No shots in this selection.", figsize)

    countable = shots[shots["counts_as_shot"]] if "counts_as_shot" in shots else shots
    if countable.empty:
        return _no_data("No countable shots here — the only shot events in\n"
                        "this selection are own goals or shootout kicks.", figsize)

    pitch = _pitch(vertical=True, half=True)
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(C.SURFACE)

    color = C.era_color(era) if era else C.SERIES[0]
    xg = countable["xg_combined"].fillna(0.05)
    sizes = 60 + xg * 1600
    x, y = _sx(countable["normalized_x"]), _sy(countable["normalized_y"])

    estimated = (countable["xg_quality"].eq("estimated").to_numpy()
                 if "xg_quality" in countable
                 else np.zeros(len(countable), dtype=bool))
    goals = (countable["is_goal"].to_numpy() if "is_goal" in countable
             else np.zeros(len(countable), dtype=bool))

    groups = [
        (~goals & ~estimated, dict(facecolor="none", edgecolor=color, linewidth=1.4,
                                   alpha=0.85), "Shot · official xG"),
        (~goals & estimated, dict(facecolor="none", edgecolor=color, linewidth=1.3,
                                  alpha=0.8, linestyle=(0, (2, 1.6))),
         "Shot · estimated xG"),
        (goals & ~estimated, dict(facecolor=color, edgecolor=C.SURFACE, linewidth=2,
                                  alpha=0.95), "Goal · official xG"),
        (goals & estimated, dict(facecolor=color, edgecolor=C.SURFACE, linewidth=2,
                                 alpha=0.95, hatch="///"), "Goal · estimated xG"),
    ]
    drawn = []
    for mask, style, label in groups:
        if not mask.any():
            continue
        handle = pitch.scatter(x[mask], y[mask], s=sizes.to_numpy()[mask], ax=ax,
                               zorder=3, **style)
        if mark_provenance or "estimated" not in label:
            drawn.append((handle, f"{label} · {int(mask.sum())}"))

    if drawn:
        legend = ax.legend([h for h, _ in drawn], [t for _, t in drawn],
                           loc="upper center", bbox_to_anchor=(0.5, -0.02),
                           ncol=2, frameon=False, fontsize=8.6,
                           labelcolor=C.INK_2, handletextpad=0.5,
                           columnspacing=1.3, scatterpoints=1)
        for handle in legend.legend_handles:
            try:
                handle.set_sizes([46])
            except Exception:
                pass

    _annotate(ax, title, note, color=color)
    return fig


def shot_maps_by_group(shots: pd.DataFrame, group_col: str, groups: list, *,
                       labels: Optional[dict] = None,
                       era_of: Optional[dict] = None,
                       figsize=(13.5, 5.2)) -> plt.Figure:
    """Small multiples — one attacking-half shot map per tournament or era.

    Small multiples rather than one pitch with four colours: the marks overlap
    heavily in the same central zone, and four hues on top of each other would
    be unreadable regardless of how well the palette separates.
    """
    present = [g for g in groups if g in set(shots[group_col].dropna())]
    if not present:
        return _no_data("No shots in this selection.", (8, 4))

    pitch = _pitch(vertical=True, half=True)
    fig, axes = pitch.draw(nrows=1, ncols=len(present), figsize=figsize)
    axes = np.atleast_1d(axes).ravel()
    fig.patch.set_facecolor(C.SURFACE)

    for ax, group in zip(axes, present):
        subset = shots[shots[group_col] == group]
        if "counts_as_shot" in subset:
            subset = subset[subset["counts_as_shot"]]
        era = (era_of or {}).get(group, group)
        color = C.era_color(era) if era in C.ERA_COLORS else C.SERIES[0]
        if not subset.empty:
            sizes = 46 + subset["xg_combined"].fillna(0.05) * 1350
            goals = (subset["is_goal"].to_numpy() if "is_goal" in subset
                     else np.zeros(len(subset), dtype=bool))
            x, y = _sx(subset["normalized_x"]), _sy(subset["normalized_y"])
            pitch.scatter(x[~goals], y[~goals], s=sizes.to_numpy()[~goals],
                          facecolor="none", edgecolor=color, linewidth=1.3,
                          alpha=0.8, ax=ax, zorder=3)
            pitch.scatter(x[goals], y[goals], s=sizes.to_numpy()[goals],
                          facecolor=color, edgecolor=C.SURFACE, linewidth=1.8,
                          alpha=0.95, ax=ax, zorder=4)
            total_xg = subset["xg_combined"].sum(min_count=1)
            note = (f"{len(subset)} shots · {int(goals.sum())} goals · "
                    f"{total_xg:.1f} xG" if pd.notna(total_xg)
                    else f"{len(subset)} shots · {int(goals.sum())} goals")
        else:
            note = "no shots"
        ax.set_title((labels or {}).get(group, str(group)), loc="left", pad=8,
                     fontsize=11.5, fontweight="600", color=color,
                     family="sans-serif")
        ax.text(0, -0.03, note, transform=ax.transAxes, ha="left", va="top",
                **_NOTE_KW)
    fig.subplots_adjust(wspace=0.08)
    return fig


# --------------------------------------------------------------------------- #
# Heatmaps
# --------------------------------------------------------------------------- #

def event_heatmap(events: pd.DataFrame, *, era: str, title: str = "",
                  note: str = "", bins=(12, 8), figsize=(7.4, 5.0),
                  show_colorbar: bool = True) -> plt.Figure:
    """Event density, as a share of this selection's own events.

    Normalising to a share is what makes two eras comparable: Luis Enrique's
    matches contain far more passes in absolute terms, so a raw-count heatmap
    would be brighter everywhere and say nothing about where play happened.
    """
    if events.empty:
        return _no_data("No events in this selection.", figsize)

    pitch = _pitch()
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(C.SURFACE)

    stats = pitch.bin_statistic(_sx(events["normalized_x"]),
                                _sy(events["normalized_y"]),
                                statistic="count", bins=bins)
    total = stats["statistic"].sum()
    if total:
        stats["statistic"] = stats["statistic"] / total * 100
    mesh = pitch.heatmap(stats, ax=ax, cmap=_cmap(era), edgecolors=C.SURFACE,
                         linewidth=1.2, zorder=1)

    if show_colorbar:
        cbar = fig.colorbar(mesh, ax=ax, shrink=0.72, pad=0.015, aspect=20)
        cbar.set_label("% of this selection's events", fontsize=9,
                       color=C.INK_MUTED)
        cbar.ax.tick_params(labelsize=8.5, colors=C.INK_MUTED, length=0)
        cbar.outline.set_visible(False)

    _direction_arrow(pitch, ax)
    _annotate(ax, title, note, color=C.era_color(era))
    return fig


def heatmap_pair(left: pd.DataFrame, right: pd.DataFrame, *,
                 left_title: str, right_title: str, left_era: str, right_era: str,
                 note: str = "", bins=(12, 8), figsize=(13.5, 4.8)) -> plt.Figure:
    """Two heatmaps side by side, each on its own era's hue ramp.

    Both are shares of their own selection, and both run 0→the same maximum
    taken across the pair, so a cell's darkness means the same thing on each.
    """
    pitch = _pitch()
    fig, axes = pitch.draw(nrows=1, ncols=2, figsize=figsize)
    axes = np.atleast_1d(axes).ravel()
    fig.patch.set_facecolor(C.SURFACE)

    stats = []
    for events in (left, right):
        if events.empty:
            stats.append(None)
            continue
        stat = pitch.bin_statistic(_sx(events["normalized_x"]),
                                   _sy(events["normalized_y"]),
                                   statistic="count", bins=bins)
        total = stat["statistic"].sum()
        if total:
            stat["statistic"] = stat["statistic"] / total * 100
        stats.append(stat)

    vmax = max((s["statistic"].max() for s in stats if s is not None), default=1)

    for ax, stat, title, era, events in zip(
            axes, stats, (left_title, right_title), (left_era, right_era),
            (left, right)):
        if stat is None:
            ax.text(PITCH_LENGTH / 2, PITCH_WIDTH / 2,
                    "No events for this era\nin the current selection",
                    ha="center", va="center", fontsize=10, color=C.INK_MUTED,
                    family="sans-serif", linespacing=1.5)
        else:
            pitch.heatmap(stat, ax=ax, cmap=_cmap(era), vmin=0, vmax=vmax,
                          edgecolors=C.SURFACE, linewidth=1.2, zorder=1)
        ax.set_title(title, loc="left", pad=8, fontsize=11.5, fontweight="600",
                     color=C.era_color(era), family="sans-serif")
        ax.text(0, -0.03, f"{len(events):,} events" if not events.empty else "—",
                transform=ax.transAxes, ha="left", va="top", **_NOTE_KW)
        _direction_arrow(pitch, ax, label=False)

    if note:
        fig.text(0.008, 0.012, note, ha="left", va="bottom", **_NOTE_KW)
    fig.subplots_adjust(wspace=0.07)
    return fig


# --------------------------------------------------------------------------- #
# Pass maps & networks
# --------------------------------------------------------------------------- #

def pass_map(passes: pd.DataFrame, *, era: str, title: str = "", note: str = "",
             max_arrows: int = 500, figsize=(7.4, 5.2),
             show_incomplete: bool = True) -> plt.Figure:
    """Pass arrows, start to end, on the common pitch.

    Capped at ``max_arrows`` by an even sample across the selection — beyond
    roughly 500 arrows the pitch turns into a solid block and the heatmap is the
    honest view instead. The cap is stated in the caption rather than applied
    silently.
    """
    if passes.empty:
        return _no_data("No passes in this selection.", figsize)

    pitch = _pitch()
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(C.SURFACE)

    sample = passes
    sampled = False
    if len(passes) > max_arrows:
        sample = passes.iloc[:: max(1, len(passes) // max_arrows)].head(max_arrows)
        sampled = True

    color = C.era_color(era)
    complete = sample[sample["is_complete"]] if "is_complete" in sample else sample
    incomplete = (sample[~sample["is_complete"]] if "is_complete" in sample
                  else sample.iloc[:0])

    if show_incomplete and not incomplete.empty:
        pitch.lines(_sx(incomplete["normalized_x"]), _sy(incomplete["normalized_y"]),
                    _sx(incomplete["normalized_end_x"]),
                    _sy(incomplete["normalized_end_y"]),
                    lw=1.1, color=C.INK_MUTED, alpha=0.3, ax=ax, zorder=2,
                    label=f"Incomplete · {len(incomplete)}")
    if not complete.empty:
        pitch.arrows(_sx(complete["normalized_x"]), _sy(complete["normalized_y"]),
                     _sx(complete["normalized_end_x"]),
                     _sy(complete["normalized_end_y"]),
                     width=1.5, headwidth=4.2, headlength=4.2, color=color,
                     alpha=0.55, ax=ax, zorder=3,
                     label=f"Complete · {len(complete)}")

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2,
              frameon=False, fontsize=8.8, labelcolor=C.INK_2)

    caption = note
    if sampled:
        caption = ((note + " · ") if note else "") + \
            f"showing an even sample of {len(sample)} of {len(passes):,} passes"
    _annotate(ax, title, caption, color=color)
    return fig


def passing_network(nodes: pd.DataFrame, edges: pd.DataFrame, *, era: str,
                    title: str = "", note: str = "",
                    figsize=(7.4, 5.2)) -> plt.Figure:
    """Average positions, with line width ∝ passes between each pair.

    Node area is the player's pass volume, line width the volume between the
    pair. Both channels encode volume, so nothing here puts two different
    quantities into one visual dimension.
    """
    if nodes.empty:
        return _no_data("No passing network available for this selection.\n\n"
                        "A network needs the pass recipient, which only the\n"
                        "StatsBomb source records — the World Cup 2026 events\n"
                        "log no receiver.", figsize)

    pitch = _pitch()
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(C.SURFACE)
    color = C.era_color(era)

    if not edges.empty:
        widths = edges["passes"] / edges["passes"].max() * 5.2 + 0.5
        alphas = (edges["passes"] / edges["passes"].max() * 0.5 + 0.14).clip(0, 0.7)
        for (_, edge), width, alpha in zip(edges.iterrows(), widths, alphas):
            pitch.lines(_sx(edge["x_start"]), _sy(edge["y_start"]),
                        _sx(edge["x_end"]), _sy(edge["y_end"]),
                        lw=width, color=color, alpha=alpha, ax=ax, zorder=2)

    sizes = nodes["passes"] / nodes["passes"].max() * 850 + 170
    pitch.scatter(_sx(nodes["x"]), _sy(nodes["y"]), s=sizes, color=color,
                  edgecolors=C.SURFACE, linewidth=2.4, alpha=0.95, ax=ax, zorder=4)
    for (_, node), size in zip(nodes.iterrows(), sizes):
        offset = 2.6 + size / 460
        ax.text(_sx(node["x"]), _sy(node["y"]) - offset, node["player"],
                ha="center", va="top", fontsize=8.6, color=C.INK,
                family="sans-serif", zorder=5,
                bbox=dict(boxstyle="round,pad=0.2", facecolor=C.SURFACE,
                          edgecolor="none", alpha=0.84))

    _direction_arrow(pitch, ax)
    _annotate(ax, title, note, color=color)
    return fig


# --------------------------------------------------------------------------- #
# Final third & progression
# --------------------------------------------------------------------------- #

def entry_map(passes: pd.DataFrame, *, era: str, zone: str = "final_third",
              title: str = "", note: str = "", figsize=(7.4, 5.2)) -> plt.Figure:
    """Where the ball enters the final third or the box, drawn as end points.

    End points rather than full arrows: the question is *where* entries land,
    and an arrow from every origin would bury that under lines.
    """
    column = "into_penalty_area" if zone == "penalty_area" else "into_final_third"
    if passes.empty or column not in passes.columns:
        return _no_data("No entry passes in this selection.", figsize)
    entries = passes[passes[column] & passes["is_complete"]]
    if entries.empty:
        zone_name = "penalty area" if zone == "penalty_area" else "final third"
        return _no_data(f"No completed passes into the {zone_name}\n"
                        "in this selection.", figsize)

    pitch = _pitch()
    fig, ax = pitch.draw(figsize=figsize)
    fig.patch.set_facecolor(C.SURFACE)
    color = C.era_color(era)

    if zone != "penalty_area":
        boundary = PITCH_LENGTH * 2 / 3
        ax.axvline(boundary, color=C.AXIS, linestyle=(0, (4, 3)), linewidth=1.2,
                   zorder=2)
        ax.text(boundary + 1.0, PITCH_WIDTH - 1.2, "final third", fontsize=9,
                color=C.INK_MUTED, va="top", family="sans-serif")

    pitch.lines(_sx(entries["normalized_x"]), _sy(entries["normalized_y"]),
                _sx(entries["normalized_end_x"]), _sy(entries["normalized_end_y"]),
                lw=1.1, color=color, alpha=0.2, ax=ax, zorder=2, comet=True)
    pitch.scatter(_sx(entries["normalized_end_x"]), _sy(entries["normalized_end_y"]),
                  s=32, color=color, edgecolors=C.SURFACE, linewidth=1, alpha=0.8,
                  ax=ax, zorder=3)

    _annotate(ax, title, note or f"{len(entries):,} completed entries", color=color)
    return fig


def progression_comparison(left: pd.DataFrame, right: pd.DataFrame, *,
                           left_title: str, right_title: str,
                           figsize=(13.5, 4.8)) -> plt.Figure:
    """Progressive-action origins for two eras, side by side."""
    return heatmap_pair(left, right, left_title=left_title, right_title=right_title,
                        left_era=C.ERAS[0], right_era=C.ERAS[1], bins=(10, 6),
                        note="Each panel is a share of that era's own progressive "
                             "actions, so the two are comparable despite different "
                             "volumes.",
                        figsize=figsize)
