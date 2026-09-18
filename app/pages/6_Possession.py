# -*- coding: utf-8 -*-
"""Page 6 — Possession: the proxy, its limits, and what it bought."""
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

ui.page_setup("Possession", icon="⏱️")
sel = filters.render_sidebar()

ui.page_header(
    "Page 6 · Possession",
    "The same ball, held differently",
    "Possession is the metric that barely moves — 54.2% to 55.6% — while almost "
    "everything about how Spain uses it does. That makes this page as much about "
    "what the number cannot tell you as about what it can.")

# The caveat comes before the first figure, not after it.
ui.notice(C.NOTE_POSSESSION, kind="caution", label="This is not the broadcast stat")

team_stats = sel.team_stats
spain = M.spain_rows(team_stats)

if spain.empty:
    ui.empty_state("No matches in the current selection.",
                   "Widen the filters in the sidebar.")
    st.stop()

methods = sorted(spain["possession_proxy_method"].dropna().unique())
if len(methods) > 1:
    ui.notice(
        "This selection mixes <strong>both</strong> proxy definitions — "
        + ", ".join(f"<code>{m}</code>" for m in methods) +
        ". Differences between tournaments here are partly a difference of "
        "measurement, not only of play. Filter to a single data source if you "
        "need a like-for-like comparison.", kind="gap",
        label="Two definitions in one view")

both = sel.both_eras

# --------------------------------------------------------------------------- #
# Headline
# --------------------------------------------------------------------------- #

POSS_METRICS = ["possession_pct_proxy", "passes_attempted_per90", "pass_pct",
                "progressive_passes_per90", "shots_per90", "xg_per90",
                "recoveries_per90"]
comparison = M.era_comparison(team_stats, POSS_METRICS)
by_metric = comparison.set_index("metric")


def card(metric: str, sub: str = "") -> dict:
    row = by_metric.loc[metric] if metric in by_metric.index else None
    era = sel.single_era or C.ERAS[1]
    return dict(label=M.label_of(metric),
                value=row[era] if row is not None else None,
                unit=M.unit_of(metric), decimals=M.decimals_of(metric),
                accent=C.era_color(era), sub=sub,
                delta_pct=(row["change_pct"] if (row is not None and both) else None),
                higher_is_better=M.higher_is_better(metric))


def passes_per_point(rows: pd.DataFrame):
    """Passes per 90 for each point of possession share."""
    if rows.empty:
        return None
    possession = rows["possession_pct_proxy"].mean()
    if not possession:
        return None
    return rows["passes_attempted_per90"].mean() / possession


enrique = spain[spain["era"] == C.ERAS[0]]
fuente = spain[spain["era"] == C.ERAS[1]]
ratio_a, ratio_b = passes_per_point(enrique), passes_per_point(fuente)
shown_era = sel.single_era or C.ERAS[1]

ui.section("Possession profile", sel.describe())
ui.kpi_row([
    card("possession_pct_proxy", "Proxy share of the ball"),
    card("passes_attempted_per90", "Touches used to hold that share"),
    # Same era basis as the cards beside it, not a figure pooled over both.
    dict(label="Passes per 1% of possession",
         value=passes_per_point(spain[spain["era"] == shown_era]),
         decimals=1, accent=C.era_color(shown_era),
         sub="How many passes each point of possession costs — the ratio that "
             "actually separates the two eras",
         delta_pct=(M.pct_change(ratio_a, ratio_b) if both else None),
         higher_is_better=False),
    card("shots_per90", "What the possession produced"),
], per_row=4)

st.markdown("")
if both and ratio_a and ratio_b:
    ui.notice(
        f"Under Luis Enrique each point of possession came with "
        f"<strong>{ratio_a:.1f} passes</strong>; under Luis de la Fuente, "
        f"<strong>{ratio_b:.1f}</strong>. Same share of the ball, roughly "
        f"{abs(1 - ratio_b / ratio_a) * 100:.0f}% fewer passes to hold it — which "
        "is the change the raw possession figure hides completely.", kind="note",
        label="The ratio, not the share")

# --------------------------------------------------------------------------- #
# Distribution and chronology
# --------------------------------------------------------------------------- #

ui.section("Possession match by match",
           "Every match as its own point. With 10 and 15 observations, the "
           "spread is as informative as the mean — and it is wide in both eras.")

left, right = st.columns([1.4, 1], gap="large")
with left:
    st.plotly_chart(
        cp.match_trend(M.match_timeline(team_stats, "possession_pct_proxy"),
                       "possession_pct_proxy", label="Possession (proxy)",
                       unit="%", decimals=1,
                       title="Possession share across the selection"),
        use_container_width=True, config={"displayModeBar": False})
with right:
    st.plotly_chart(
        cp.era_distribution(spain, "possession_pct_proxy",
                            label="Possession (proxy)", unit="%", decimals=1,
                            title="Spread by era"),
        use_container_width=True, config={"displayModeBar": False})

display = spain[["date", "tournament", "opponent", "possession_pct_proxy",
                 "possession_proxy_method", "passes_attempted", "pass_pct",
                 "shots"]].copy()
display["date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")
display.columns = ["Date", "Tournament", "Opponent", "Possession % (proxy)",
                   "Proxy method", "Passes", "Pass %", "Shots"]
ui.table_view(display.round(1), "Show possession per match, with its proxy method")

# --------------------------------------------------------------------------- #
# Did possession buy anything?
# --------------------------------------------------------------------------- #

ui.section("Did more of the ball buy more of anything?",
           "One point per match: possession share against the metric on the "
           "y-axis. A flat cloud means possession and the outcome move "
           "independently — which is broadly what this dataset shows.")

outcome = st.selectbox(
    "Compare possession against",
    ["shots_per90", "xg_per90", "goals_per90", "passes_into_final_third_per90",
     "progressive_passes_per90", "shots_on_target_per90"],
    format_func=M.label_of, key="poss_outcome")

st.plotly_chart(
    cp.possession_vs_metric(spain, outcome, label=M.label_of(outcome),
                            unit=M.unit_of(outcome),
                            title=f"Possession against {M.label_of(outcome).lower()}",
                            subtitle="Each point is one match"),
    use_container_width=True, config={"displayModeBar": False})

correlations = []
for era in C.ERAS:
    subset = spain[spain["era"] == era].dropna(
        subset=["possession_pct_proxy", outcome])
    if len(subset) > 2:
        correlations.append({
            "Era": era, "Matches": len(subset),
            "Correlation with possession":
                round(subset["possession_pct_proxy"].corr(subset[outcome]), 3)})
if correlations:
    ui.table_view(pd.DataFrame(correlations),
                  "Show the correlation (and remember the sample size)")
    ui.notice(
        "A correlation over 10 or 15 matches is not a finding — it is a hint that "
        "would need many more matches to stand up. It is shown because leaving it "
        "out invites the eye to read a trend into the scatter that the numbers do "
        "not support.", kind="caution", label="On these correlations")

# --------------------------------------------------------------------------- #
# Territory
# --------------------------------------------------------------------------- #

ui.section("Where possession happened",
           "Possession share says nothing about location. These are all on-ball "
           "events — passes, carries and defensive actions together — as a share "
           "of each era's own events.")

passes = sel.events("passes", spain_only=True)
defensive = sel.events("defensive actions", spain_only=True)
columns = ["match_id", "era", "normalized_x", "normalized_y"]
touches = pd.concat(
    [frame[columns] for frame in (passes, defensive) if not frame.empty],
    ignore_index=True) if not passes.empty or not defensive.empty else pd.DataFrame()

if touches.empty:
    ui.empty_state("No on-ball events in this selection.")
elif both:
    st.pyplot(cm.heatmap_pair(
        touches[touches["era"] == C.ERAS[0]], touches[touches["era"] == C.ERAS[1]],
        left_title=C.ERAS[0], right_title=C.ERAS[1],
        left_era=C.ERAS[0], right_era=C.ERAS[1],
        note="Carries are excluded here so the two panels cover the same event "
             "families — the World Cup 2026 source logs no carry events."),
        width="stretch")
    ui.notice(C.NOTE_CARRIES, kind="gap", label="Why carries are left out")
else:
    st.pyplot(cm.event_heatmap(touches, era=sel.single_era,
                               title=f"{sel.single_era} — on-ball events",
                               note=f"{len(touches):,} events"),
              width="stretch")

zones = M.zone_grid(touches, nx=6, ny=3) if not touches.empty else pd.DataFrame()
if not zones.empty:
    display = zones[["x_from", "x_to", "y_from", "y_to", "events", "share"]].round(1)
    display.columns = ["x from", "x to", "y from", "y to", "Events", "Share %"]
    ui.table_view(display, "Show the zone grid behind the heatmap")

ui.footer()
