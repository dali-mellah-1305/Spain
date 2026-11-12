# -*- coding: utf-8 -*-
"""Page 5 — Shooting: shot maps, xG, and the shot-quality question."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from utils import charts_mplsoccer as cm
from utils import charts_plotly as cp
from utils import config as C
from utils import filters, metrics as M, ui

ui.page_setup("Shooting", icon="🥅")
sel = filters.render_sidebar()

ui.page_header(
    "Page 5 · Shooting",
    "More shots, each one worth less",
    "Shots rise 15% and shots on target 51% between the two eras — but xG per "
    "shot falls from 0.123 to 0.097. Both things are true, and they pull in "
    "opposite directions: Spain now shoots more often from less promising "
    "positions. This page keeps official and model-estimated xG visibly apart "
    "throughout, because the second kind is not evidence of the same strength.")

team_stats = sel.team_stats
shots = sel.events("shots", spain_only=True)

if shots.empty:
    ui.empty_state("No shots in the current selection.",
                   "Widen the filters in the sidebar.")
    st.stop()

countable = shots[shots["counts_as_shot"]]
both = sel.both_eras

# --------------------------------------------------------------------------- #
# Provenance, stated before any xG number is read
# --------------------------------------------------------------------------- #

official = int(countable["xg_quality"].eq("official").sum())
estimated = int(countable["xg_quality"].eq("estimated").sum())
if estimated:
    ui.badges([ui.xg_badge("official"), ui.xg_badge("estimated")])
    ui.notice(
        f"{C.NOTE_XG_PROXY}<br><strong>In this selection: {official} shots carry "
        f"official xG, {estimated} carry an estimate.</strong>", kind="caution",
        label="Mixed xG provenance")

# --------------------------------------------------------------------------- #
# Headline
# --------------------------------------------------------------------------- #

SHOT_METRICS = ["shots_per90", "shots_on_target_per90", "goals_per90", "xg_per90",
                "xg_per_shot", "shot_accuracy_pct"]
comparison = M.era_comparison(team_stats, SHOT_METRICS)
by_metric = comparison.set_index("metric")
summary = M.shot_summary(shots)


def card(metric: str, sub: str = "") -> dict:
    row = by_metric.loc[metric] if metric in by_metric.index else None
    era = sel.single_era or C.ERAS[1]
    return dict(label=M.label_of(metric),
                value=row[era] if row is not None else None,
                unit=M.unit_of(metric), decimals=M.decimals_of(metric),
                accent=C.era_color(era), sub=sub,
                delta_pct=(row["change_pct"] if (row is not None and both) else None),
                higher_is_better=M.higher_is_better(metric))


ui.section("Shooting profile", sel.describe())
ui.kpi_row([
    dict(label="Shots in selection", value=summary["shots"], decimals=0,
         accent=C.BRAND,
         sub=f"{summary['on_target']} on target · {summary['goals']} goals · "
             f"{summary['accuracy_pct']:.0f}% accuracy"),
    card("shots_per90", "Attempts per 90 minutes"),
    card("shots_on_target_per90", "The largest favourable change in the dataset"),
    card("goals_per90", "Goals, including own goals credited to Spain"),
], per_row=4)
st.markdown("")
ui.kpi_row([
    card("xg_per90", "Chances created per 90"),
    card("xg_per_shot", "Average quality per attempt — the counterweight"),
    dict(label="Goals minus xG", value=summary["goals_minus_xg"], decimals=2,
         accent=C.era_color(sel.single_era or C.ERAS[1]),
         sub="Above zero means Spain scored more than the chance quality implied. "
             "With estimated xG in the mix, read this as directional."),
    dict(label="Shot accuracy", value=summary["accuracy_pct"], unit="%",
         decimals=1, accent=C.era_color(sel.single_era or C.ERAS[1]),
         sub="Share of countable shots on target — goals and saves, on the same "
             "definition the aggregate tables use"),
], per_row=4)

st.markdown("")
if both:
    ui.notice(
        "These two facts are the page. <strong>Volume and accuracy both rose; "
        "average chance quality fell.</strong> More shots on target is not the "
        "same as better chances — it is consistent with shooting more often from "
        "range and hitting the target more reliably when doing so.", kind="note",
        label="How to read this together")

# --------------------------------------------------------------------------- #
# Shot maps
# --------------------------------------------------------------------------- #

ui.section("Shot maps",
           "Attacking half only; marker area is the shot's xG and a filled marker "
           "is a goal. A dashed outline marks a shot whose xG is model-estimated "
           "rather than official. Own goals and penalty-shootout kicks are "
           "excluded, matching the aggregate tables.")

view = st.radio("Split by", ["Tournament", "Era"],
                horizontal=True, key="shot_map_view")

if view == "Tournament":
    st.pyplot(cm.shot_maps_by_group(
        shots, "tournament", [t for t in C.TOURNAMENTS if t in sel.tournaments],
        labels=C.TOURNAMENT_LABEL, era_of=C.TOURNAMENT_ERA),
        width="stretch")
else:
    st.pyplot(cm.shot_maps_by_group(
        shots, "era", [e for e in C.ERAS if e in sel.eras],
        labels={e: e for e in C.ERAS}, era_of={e: e for e in C.ERAS},
        figsize=(9.5, 5.6)), width="stretch")

group_summary = []
group_col = "tournament" if view == "Tournament" else "era"
for group in (C.TOURNAMENTS if group_col == "tournament" else C.ERAS):
    subset = countable[countable[group_col] == group]
    if subset.empty:
        continue
    stats = M.shot_summary(subset)
    group_summary.append({
        group_col.title(): C.tournament_label(group) if group_col == "tournament"
        else group,
        "Shots": stats["shots"], "On target": stats["on_target"],
        "Goals": stats["goals"],
        "xG": round(stats["xg"], 2) if pd.notna(stats["xg"]) else None,
        "xG per shot": round(stats["xg_per_shot"], 3)
        if pd.notna(stats["xg_per_shot"]) else None,
        "Accuracy %": round(stats["accuracy_pct"], 1),
    })
ui.table_view(pd.DataFrame(group_summary), "Show the shot totals")

# --------------------------------------------------------------------------- #
# xG against goals
# --------------------------------------------------------------------------- #

ui.section("Chances created against goals scored",
           "Both series are in goals, so they share one axis honestly. The gap "
           "between the pair is finishing above or below the chance quality.")

spain_team = M.spain_rows(team_stats).sort_values("date")
timeline = M.match_timeline(team_stats, "goals")
if "xg" in spain_team.columns and not timeline.empty:
    timeline = timeline.assign(goals=spain_team["goals"].values,
                               xg=spain_team["xg"].values)
    st.plotly_chart(cp.xg_vs_goals(timeline),
                    use_container_width=True, config={"displayModeBar": False})
    display = timeline[["date", "tournament", "opponent", "goals", "xg"]].copy()
    display["date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")
    display["goals − xg"] = (display["goals"] - display["xg"]).round(2)
    display.columns = ["Date", "Tournament", "Opponent", "Goals", "xG", "Goals − xG"]
    ui.table_view(display.round(2))

# --------------------------------------------------------------------------- #
# Shot distance, type, and the shooters
# --------------------------------------------------------------------------- #

ui.section("What kind of shots")

left, right = st.columns(2, gap="medium")
with left:
    if "distance_to_goal" in countable.columns:
        distance = (countable.groupby("era", observed=True)["distance_to_goal"]
                    .mean().reset_index())
        distance.columns = ["era", "distance"]
        st.plotly_chart(
            cp.horizontal_ranking(
                distance, label_col="era", value_col="distance", color_col="era",
                unit=" m", decimals=1,
                title="Average shot distance from goal",
                subtitle="On the common 0-100 pitch, scaled to metres",
                height=200),
            use_container_width=True, config={"displayModeBar": False})
        ui.table_view(distance.round(2), "Show shot distances")
with right:
    types = (countable.groupby(["era", "shot_type"], observed=True).size()
             .rename("shots").reset_index())
    if not types.empty and both:
        st.plotly_chart(
            cp.stacked_share(types, category="shot_type", value="shots",
                             group="era", title="Shot types",
                             subtitle="Open play, penalties and free kicks as a "
                                      "share of each era's shots", height=200),
            use_container_width=True, config={"displayModeBar": False})

outcomes = (countable.groupby(["era", "outcome_std"], observed=True).size()
            .rename("shots").reset_index())
if not outcomes.empty and both:
    st.plotly_chart(
        cp.stacked_share(outcomes, category="outcome_std", value="shots",
                         group="era", title="Shot outcomes",
                         subtitle="StatsBomb's and Opta's separate outcome "
                                  "vocabularies harmonised onto one five-value "
                                  "scale by the cleaning pass", height=230),
        use_container_width=True, config={"displayModeBar": False})
    pivot = outcomes.pivot_table(index="era", columns="outcome_std", values="shots",
                                 observed=True).reset_index()
    ui.table_view(pivot, "Show outcome counts")

ui.section("Who shot")

shooters = (countable[countable["player_canonical"].notna()]
            .groupby(["player_canonical", "era"], observed=True)
            .agg(shots=("is_goal", "size"), goals=("is_goal", "sum"),
                 on_target=("is_on_target", "sum"),
                 xg=("xg_combined", "sum")).reset_index())
if not shooters.empty:
    totals = (shooters.groupby("player_canonical", observed=True)
              .agg(shots=("shots", "sum"), goals=("goals", "sum"),
                   xg=("xg", "sum")).reset_index())
    totals["xg_per_shot"] = (totals["xg"] / totals["shots"]).round(3)
    top = totals.nlargest(12, "shots")
    st.plotly_chart(
        cp.horizontal_ranking(
            top.sort_values("shots", ascending=False),
            label_col="player_canonical", value_col="shots", decimals=0,
            title="Most shots in the selection",
            subtitle="Countable shots — own goals and shootout kicks excluded"),
        use_container_width=True, config={"displayModeBar": False})
    display = totals.sort_values("shots", ascending=False).round(3)
    display.columns = ["Player", "Shots", "Goals", "xG", "xG per shot"]
    ui.table_view(display, "Show every shooter")

ui.footer()
