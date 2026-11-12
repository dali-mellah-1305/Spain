# -*- coding: utf-8 -*-
"""Page 4 — Passing: volume, completion, progression, networks."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from utils import charts_mplsoccer as cm
from utils import charts_plotly as cp
from utils import config as C
from utils import data_loader as dl
from utils import filters, metrics as M, ui

ui.page_setup("Passing", icon="🎯")
sel = filters.render_sidebar()

ui.page_header(
    "Page 4 · Passing",
    "The same share of the ball, far fewer touches",
    "Pass volume is where the two eras separate most clearly: 823 attempted "
    "passes per 90 under Luis Enrique against 633 under Luis de la Fuente, a 23% "
    "drop, while the possession proxy moves by less than two points. Completion "
    "holds near 88% in both. This page looks at what changed underneath that.")

team_stats = sel.team_stats
spain_team = M.spain_rows(team_stats)
passes = sel.events("passes", spain_only=True)

if passes.empty:
    ui.empty_state("No passes in the current selection.",
                   "Widen the filters in the sidebar.")
    st.stop()

# --------------------------------------------------------------------------- #
# Volume and completion
# --------------------------------------------------------------------------- #

PASS_METRICS = ["passes_attempted_per90", "passes_completed_per90", "pass_pct",
                "progressive_passes_per90", "key_passes_per90", "crosses_per90",
                "passes_into_final_third_per90", "passes_into_penalty_area_per90"]

comparison = M.era_comparison(team_stats, PASS_METRICS)
by_metric = comparison.set_index("metric")
summary = M.pass_summary(passes)
both = sel.both_eras


def card(metric: str, sub: str = "") -> dict:
    row = by_metric.loc[metric] if metric in by_metric.index else None
    era = sel.single_era or C.ERAS[1]
    return dict(label=M.label_of(metric),
                value=row[era] if row is not None else None,
                unit=M.unit_of(metric), decimals=M.decimals_of(metric),
                accent=C.era_color(era), sub=sub,
                delta_pct=(row["change_pct"] if (row is not None and both) else None),
                higher_is_better=M.higher_is_better(metric))


ui.section("Passing profile", sel.describe())
ui.kpi_row([
    dict(label="Passes in selection", value=summary["passes"], decimals=0,
         accent=C.BRAND,
         sub=f"{summary['completed']:,} completed · "
             f"{summary['pass_pct']:.1f}% completion · "
             f"{summary['forward_pct']:.0f}% played forward"),
    card("passes_attempted_per90", "Attempts per 90 minutes"),
    card("pass_pct", "Completion barely moves between eras"),
    card("progressive_passes_per90", "Passes cutting ≥25% off the distance to goal"),
], per_row=4)
st.markdown("")
ui.kpi_row([
    card("passes_into_final_third_per90", "Completed entries, started outside it"),
    card("passes_into_penalty_area_per90", "Completed entries into the box"),
    card("key_passes_per90", "Passes that directly led to a shot"),
    card("crosses_per90", "Passes flagged as crosses"),
], per_row=4)

st.markdown("")
if both:
    ui.notice(
        "Read the volume drop and the progression drop together. Attempted passes "
        "fall 23%, and passes into the final third fall further — 30%. But "
        "<strong>progressive passes fall only 9%</strong>, so progression did not "
        "shrink in proportion to volume: a larger share of the passes Spain does "
        "play now carry the ball forward.", kind="note",
        label="What the numbers say together")

# --------------------------------------------------------------------------- #
# Comparison chart
# --------------------------------------------------------------------------- #

if both:
    ui.era_legend()
    tab_bars, tab_change, tab_trend = st.tabs(
        ["Side by side", "Size of the change", "Match by match"])
    with tab_bars:
        st.plotly_chart(cp.era_comparison_bars(comparison),
                        use_container_width=True,
                        config={"displayModeBar": False})
    with tab_change:
        st.plotly_chart(
            cp.change_lollipop(comparison,
                               subtitle="Green favours the later era for that "
                                        "metric; the sign carries the direction"),
            use_container_width=True, config={"displayModeBar": False})
    with tab_trend:
        metric = st.selectbox("Metric", PASS_METRICS, format_func=M.label_of,
                              key="pass_trend_metric")
        st.plotly_chart(
            cp.match_trend(M.match_timeline(team_stats, metric), metric,
                           label=M.label_of(metric), unit=M.unit_of(metric),
                           decimals=M.decimals_of(metric)),
            use_container_width=True, config={"displayModeBar": False})

    display = comparison[["label", C.ERAS[0], C.ERAS[1], "change_pct"]].copy()
    display.columns = ["Metric", "Luis Enrique", "Luis de la Fuente", "Change %"]
    ui.table_view(display.round(2))

# --------------------------------------------------------------------------- #
# Where the passes start
# --------------------------------------------------------------------------- #

ui.section("Where the passes start",
           "Each panel is a share of that era's own passes, so two eras with very "
           "different pass volumes are comparable cell by cell.")

if both:
    st.pyplot(cm.heatmap_pair(
        passes[passes["era"] == C.ERAS[0]], passes[passes["era"] == C.ERAS[1]],
        left_title=C.ERAS[0], right_title=C.ERAS[1],
        left_era=C.ERAS[0], right_era=C.ERAS[1],
        note="Luis Enrique's passes concentrate through the central channel in "
             "Spain's own half; Luis de la Fuente's spread wider and further "
             "upfield."), width="stretch")
else:
    era = sel.single_era
    st.pyplot(cm.event_heatmap(passes, era=era, title=f"{era} — pass origins",
                               note=f"{len(passes):,} passes"),
              width="stretch")

thirds = (passes.groupby(["era", "pitch_third"], observed=True).size()
          .rename("passes").reset_index())
if not thirds.empty and both:
    st.plotly_chart(
        cp.stacked_share(thirds, category="pitch_third", value="passes",
                         group="era",
                         title="Share of passes by the third they start in",
                         subtitle="Normalised within each era, so the bars "
                                  "compare distribution rather than volume",
                         height=230),
        use_container_width=True, config={"displayModeBar": False})
    pivot = thirds.pivot_table(index="era", columns="pitch_third", values="passes",
                               observed=True).reset_index()
    ui.table_view(pivot, "Show pass counts by pitch third")

# --------------------------------------------------------------------------- #
# Progression
# --------------------------------------------------------------------------- #

ui.section("Progressive passes — where progression is attempted from",
           "Passes that cut at least 25% off the distance to goal. Both panels "
           "are shares of that era's own progressive passes.")

progressive = passes[passes["is_progressive"]]
if both and not progressive.empty:
    st.pyplot(cm.progression_comparison(
        progressive[progressive["era"] == C.ERAS[0]],
        progressive[progressive["era"] == C.ERAS[1]],
        left_title=f"{C.ERAS[0]} — {len(progressive[progressive['era'] == C.ERAS[0]]):,} progressive passes",
        right_title=f"{C.ERAS[1]} — {len(progressive[progressive['era'] == C.ERAS[1]]):,} progressive passes"),
        width="stretch")
elif not progressive.empty:
    st.pyplot(cm.event_heatmap(progressive, era=sel.single_era,
                               title="Progressive pass origins"),
              width="stretch")

left, right = st.columns(2, gap="medium")
with left:
    rates = (passes.groupby("era", observed=True)
             .agg(passes=("is_progressive", "size"),
                  progressive=("is_progressive", "sum")).reset_index())
    rates["share"] = rates["progressive"] / rates["passes"] * 100
    if not rates.empty:
        st.plotly_chart(
            cp.horizontal_ranking(
                rates, label_col="era", value_col="share", color_col="era",
                unit="%", decimals=1,
                title="Progressive share of all passes",
                subtitle="What proportion of passes carried the ball forward",
                height=200),
            use_container_width=True, config={"displayModeBar": False})
        ui.table_view(rates.round(1), "Show progressive-pass counts")
with right:
    types = (passes.groupby(["era", "pass_type"], observed=True).size()
             .rename("passes").reset_index())
    top_types = types.groupby("pass_type", observed=True)["passes"].sum().nlargest(5).index
    types = types[types["pass_type"].isin(top_types)]
    if not types.empty and both:
        st.plotly_chart(
            cp.stacked_share(types, category="pass_type", value="passes",
                             group="era", title="Pass types",
                             subtitle="Five most common types, as a share of "
                                      "each era's passes", height=200),
            use_container_width=True, config={"displayModeBar": False})

# --------------------------------------------------------------------------- #
# Networks
# --------------------------------------------------------------------------- #

ui.section("Passing networks",
           "Average positions with pass volume between each pair. This needs the "
           "pass recipient, which only the StatsBomb source logs — so it is "
           "available for the 17 EURO 2020 / WC 2022 / EURO 2024 matches and not "
           "for the 8 World Cup 2026 matches.")

sb_matches = sel.matches[sel.matches["source_short"] == "StatsBomb"]
if sb_matches.empty:
    ui.notice(
        "None of the selected matches come from the StatsBomb source, so no "
        "passing network can be built. The World Cup 2026 event files log no "
        "pass receiver — a source limitation, not an empty result.", kind="gap")
else:
    compare_networks = st.toggle(
        "Compare two matches side by side", value=len(sb_matches) > 1,
        key="pass_net_compare",
        help="The comparison the project's own findings rest on: a deep central "
             "triangle under Enrique against a direct right-flank outlet under "
             "De la Fuente.")
    labels = dict(zip(sb_matches["match_id"], sb_matches["label"]))
    options = sb_matches["match_id"].tolist()

    def draw_network(match_id: str, column) -> None:
        row = sb_matches[sb_matches["match_id"] == match_id].iloc[0]
        match_passes = passes[passes["match_id"] == match_id]
        nodes, edges = M.passing_network(match_passes, min_passes=3)
        with column:
            st.pyplot(cm.passing_network(
                nodes, edges, era=row["era"],
                title=f"Spain vs {row['opponent']}",
                note=f"{C.tournament_label(row['tournament'])} {row['round']} · "
                     f"{row['scoreline']} · connections of 3+ passes",
                figsize=(7.2, 5.0)), width="stretch")
            if not edges.empty:
                top = edges.nlargest(6, "passes")[["passer", "receiver", "passes"]]
                top.columns = ["From", "To", "Passes"]
                ui.table_view(top, f"Strongest connections — {row['opponent']}")

    if compare_networks and len(options) > 1:
        default_a = options[0]
        default_b = options[-1]
        col_a, col_b = st.columns(2, gap="large")
        draw_network(default_a, col_a)
        draw_network(default_b, col_b)
    else:
        single = options[-1]
        draw_network(single, st.container())

# --------------------------------------------------------------------------- #
# Pass arrows
# --------------------------------------------------------------------------- #

ui.section("Pass map",
           "Individual passes as arrows. Above a few hundred the pitch fills "
           "solid, so a large selection is sampled evenly and the caption says "
           "by how much — the heatmaps above are the better view at scale.")

all_matches = dl.load_matches().sort_values("date").reset_index(drop=True)
featured_match_ids = ["EURO2024_M7", "EURO2020_M6", "WC2022_M4", "WC2026_M8"]
featured_matches = all_matches[all_matches["match_id"].isin(featured_match_ids)]
match_labels = dict(zip(featured_matches["match_id"], featured_matches["label"]))
match_order = [match_id for match_id in featured_match_ids if match_id in match_labels]

filter_col, chart_col = st.columns([1, 3], gap="large")
with filter_col:
    st.markdown("**Matches**")
    selected_match_ids = [
        match_id for match_id in match_order
        if st.checkbox(match_labels[match_id], value=True,
                       key=f"pass_map_match_{match_id}")
    ]
    subset_choice = st.radio(
        "Show", ["All passes", "Progressive only", "Into the final third",
                 "Into the box", "Key passes", "Crosses"], key="pass_map_subset")
    show_incomplete = st.checkbox("Include incomplete passes", value=True,
                                  key="pass_map_incomplete")

with chart_col:
    if not selected_match_ids:
        ui.empty_state("Select at least one match.",
                       "Choose a Spain match from the list to show its pass map.")
    for map_match in selected_match_ids:
        map_passes = passes[passes["match_id"] == map_match]
        map_row = all_matches[all_matches["match_id"] == map_match].iloc[0]
        subset = {
            "All passes": map_passes,
            "Progressive only": map_passes[map_passes["is_progressive"]],
            "Into the final third": map_passes[map_passes["into_final_third"]],
            "Into the box": map_passes[map_passes["into_penalty_area"]],
            "Key passes": map_passes[map_passes["is_key_pass"]],
            "Crosses": map_passes[map_passes["is_cross"]],
        }[subset_choice]
        st.pyplot(cm.pass_map(
            subset, era=map_row["era"],
            title=f"Spain vs {map_row['opponent']} — {subset_choice.lower()}",
            note=f"{C.tournament_label(map_row['tournament'])} {map_row['round']} · "
                 f"{map_row['scoreline']}",
            show_incomplete=show_incomplete, figsize=(8.4, 5.4)),
            width="stretch")

        passers = (map_passes.groupby("player_canonical", observed=True)
                   .agg(passes=("is_complete", "size"),
                        completed=("is_complete", "sum"),
                        progressive=("is_progressive", "sum"),
                        into_final_third=("into_final_third", "sum"),
                        key_passes=("is_key_pass", "sum")).reset_index())
        if not passers.empty:
            passers["pass %"] = (passers["completed"] / passers["passes"] * 100).round(1)
            passers = passers.sort_values("passes", ascending=False)
            passers.columns = ["Player", "Passes", "Completed", "Progressive",
                               "Into final third", "Key passes", "Pass %"]
            ui.table_view(passers, f"Show every passer — Spain vs {map_row['opponent']}")

ui.footer()
