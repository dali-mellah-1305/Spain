# -*- coding: utf-8 -*-
"""Page 1 — Overview: the era comparison in full."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from utils import charts_plotly as cp
from utils import config as C
from utils import data_loader as dl
from utils import filters, metrics as M, ui

ui.page_setup("Overview", icon="📊")
sel = filters.render_sidebar()

ui.page_header(
    "Page 1 · Overview",
    "The comparison, end to end",
    "Every headline metric under both managers, the size of each change, and the "
    "results that came with it. Per-90 throughout, normalised for the five "
    "matches that went to extra time.")

matches = sel.matches
team_stats = sel.team_stats
spain = M.spain_rows(team_stats)

if spain.empty:
    ui.empty_state("No matches in the current selection.",
                   "Widen the filters in the sidebar.")
    st.stop()

# --------------------------------------------------------------------------- #
# Headline KPIs
# --------------------------------------------------------------------------- #

HEADLINE = ["possession_pct_proxy", "passes_attempted_per90", "pass_pct",
            "progressive_passes_per90", "passes_into_final_third_per90",
            "shots_per90", "shots_on_target_per90", "xg_per90", "xg_per_shot",
            "goals_per90", "tackles_per90", "interceptions_per90",
            "clearances_per90", "recoveries_per90"]

comparison = M.era_comparison(team_stats, HEADLINE)
by_metric = comparison.set_index("metric")
both = sel.both_eras


def card(metric: str, *, label=None, decimals=None, sub="",
         higher_is_better=None) -> dict:
    """A KPI card for one metric — the later era's value, change beside it."""
    row = by_metric.loc[metric] if metric in by_metric.index else None
    era = sel.single_era or C.ERAS[1]
    value = row[era] if row is not None else None
    return dict(
        label=label or M.label_of(metric),
        value=value,
        unit=M.unit_of(metric),
        decimals=decimals if decimals is not None else M.decimals_of(metric),
        accent=C.era_color(era), sub=sub,
        delta_pct=(row["change_pct"] if (row is not None and both) else None),
        higher_is_better=(higher_is_better if higher_is_better is not None
                          else M.higher_is_better(metric)),
    )


record = M.record(matches)
ui.section("Headline" + (" — Luis de la Fuente, against Luis Enrique" if both
                         else f" — {sel.single_era}"),
           sel.describe())

ui.kpi_row([
    dict(label="Record", value=f"{record['W']}–{record['D']}–{record['L']}",
         accent=C.BRAND,
         sub=f"{record['matches']} matches · {record['win_pct']:.0f}% wins · "
             f"{record['ppm']:.2f} points per match"),
    card("possession_pct_proxy", sub="A proxy, not the broadcast stat — see the "
         "Possession page", higher_is_better=True),
    card("passes_attempted_per90", decimals=0,
         sub="Fewer touches for the same share of the ball",
         higher_is_better=False),
    card("pass_pct", sub="Completion barely moves — the change is volume, not "
         "accuracy"),
], per_row=4)
st.markdown("")
ui.kpi_row([
    card("shots_per90", sub="More attempts per match"),
    card("shots_on_target_per90", sub="The largest favourable move in the dataset"),
    card("xg_per90", sub="Chances created, model-estimated for World Cup 2026"),
    card("xg_per_shot", sub="Average quality of each attempt — the counterweight"),
], per_row=4)

st.markdown("")
if both:
    ui.notice(C.NOTE_SAMPLE, kind="caution", label="Before reading the changes")

# --------------------------------------------------------------------------- #
# Era comparison
# --------------------------------------------------------------------------- #

if both:
    ui.section("Metric by metric",
               "Per-90 means over each era's matches. These metrics run from 823 "
               "passes per 90 down to 0.098 xG per shot, so each row is scaled to "
               "its own larger value rather than to a shared axis that would "
               "flatten everything but the pass rows — and every bar is labelled "
               "with its real number.")
    ui.era_legend()

    tab_bars, tab_change = st.tabs(["Side by side", "Size of the change"])
    with tab_bars:
        st.plotly_chart(
            cp.era_comparison_bars(comparison, height=760),
            use_container_width=True, config={"displayModeBar": False})
    with tab_change:
        st.plotly_chart(
            cp.change_lollipop(
                comparison,
                subtitle="Green is a favourable move for that metric, red "
                         "unfavourable; the arrow and sign carry the direction."),
            use_container_width=True, config={"displayModeBar": False})

    display = comparison[["label", C.ERAS[0], C.ERAS[1], "change_pct", "unit",
                          "matches_enrique", "matches_fuente"]].copy()
    display.columns = ["Metric", "Luis Enrique", "Luis de la Fuente",
                       "Change %", "Unit", "Enrique matches", "Fuente matches"]
    ui.table_view(display.round(3), "Show the numbers behind these charts")
else:
    ui.notice(
        f"Only <strong>{sel.single_era}</strong> is selected, so there is nothing "
        "to compare against. Select both eras in the sidebar to see the "
        "side-by-side comparison.", kind="note")

# --------------------------------------------------------------------------- #
# Chronology
# --------------------------------------------------------------------------- #

ui.section("Match by match",
           "One metric across the selection in date order. Each era's mean is "
           "laid in behind as a dashed line, and the line breaks where the "
           "manager changed rather than sloping through it.")

TRENDABLE = ["passes_attempted_per90", "possession_pct_proxy", "pass_pct",
             "progressive_passes_per90", "passes_into_final_third_per90",
             "shots_per90", "shots_on_target_per90", "xg_per90", "goals_per90",
             "tackles_per90", "interceptions_per90", "clearances_per90"]

metric = st.selectbox("Metric", TRENDABLE, index=0, format_func=M.label_of,
                      key="ov_trend_metric")
timeline = M.match_timeline(team_stats, metric)
st.plotly_chart(
    cp.match_trend(timeline, metric, label=M.label_of(metric),
                   unit=M.unit_of(metric), decimals=M.decimals_of(metric)),
    use_container_width=True, config={"displayModeBar": False})

left, right = st.columns(2, gap="medium")
with left:
    st.plotly_chart(
        cp.era_distribution(spain, metric, label=M.label_of(metric),
                            unit=M.unit_of(metric),
                            decimals=M.decimals_of(metric),
                            title="Spread across matches",
                            subtitle="Every match drawn as its own point — with "
                                     "10 and 15 observations the spread matters "
                                     "as much as the mean"),
        use_container_width=True, config={"displayModeBar": False})
with right:
    profile = M.tournament_profile(team_stats, TRENDABLE)
    st.plotly_chart(
        cp.tournament_trend(profile, metric, label=M.label_of(metric),
                            unit=M.unit_of(metric),
                            decimals=M.decimals_of(metric),
                            title="By tournament",
                            subtitle="Tournaments sit on the axis; colour is the "
                                     "era, as everywhere in this app"),
        use_container_width=True, config={"displayModeBar": False})

note = M.coverage_note(spain[metric], "selected matches")
if note:
    ui.notice(note, kind="gap", label="Partial coverage")

# --------------------------------------------------------------------------- #
# Results table
# --------------------------------------------------------------------------- #

ui.section("Every match in the selection")

table = matches[["date", "tournament", "round", "opponent", "scoreline",
                 "result", "extra_time", "penalty_score", "venue_city"]].copy()
table["date"] = pd.to_datetime(table["date"]).dt.strftime("%d %b %Y")
table["tournament"] = table["tournament"].map(C.TOURNAMENT_LABEL)
table.columns = ["Date", "Tournament", "Round", "Opponent", "Spain – Opp",
                 "Result", "Extra time", "Penalties", "City"]
st.dataframe(table, width="stretch", hide_index=True, height=420)

ui.footer()
