# -*- coding: utf-8 -*-
"""
The landing page — orientation, not analysis.

It frames the question, states what the data can and cannot answer, and shows
how clean the underlying tables are, then hands off to the eight analysis pages
rather than repeating them. Reached as the default page declared in
``streamlit_app.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from utils import config as C
from utils import data_loader as dl
from utils import filters, metrics as M, ui

ui.page_setup()

try:
    sel = filters.render_sidebar()
except FileNotFoundError as exc:
    st.error(str(exc), icon="🚫")
    st.stop()

matches = dl.load_matches()
team_stats = dl.load_team_stats()

ui.page_header(
    "Spain · 2021 – 2026",
    "How Spain changed between Luis Enrique and Luis de la Fuente",
    "Event-level data for all 25 matches Spain played at EURO 2020, the 2022 World "
    "Cup, EURO 2024 and the 2026 World Cup — every pass, shot, carry and defensive "
    "action — read as one question: what actually changed in how this team plays?")

# --------------------------------------------------------------------------- #
# The headline
# --------------------------------------------------------------------------- #

full_record = {era: M.record(matches[matches["era"] == era]) for era in C.ERAS}
headline = M.era_comparison(team_stats, [
    "passes_attempted_per90", "shots_per90", "xg_per_shot", "possession_pct_proxy"])
by_metric = headline.set_index("metric")


def change(metric: str):
    return by_metric.loc[metric, "change_pct"] if metric in by_metric.index else None


ui.kpi_row([
    dict(label="Matches in the dataset", value=len(matches), decimals=0,
         accent=C.BRAND, sub="10 under Enrique · 15 under De la Fuente, "
                              "every match event-level"),
    dict(label="Win rate", value=full_record[C.ERAS[1]]["win_pct"], unit="%",
         decimals=0, accent=C.era_color(C.ERAS[1]),
         sub=f"{full_record[C.ERAS[1]]['W']}W–{full_record[C.ERAS[1]]['D']}D–"
             f"{full_record[C.ERAS[1]]['L']}L under De la Fuente, against "
             f"{full_record[C.ERAS[0]]['win_pct']:.0f}% before",
         # A rate's change is shown in points, not as a relative percentage:
         # 40% → 93% is "+53 points", which is what the reader means.
         delta_pct=(full_record[C.ERAS[1]]["win_pct"]
                    - full_record[C.ERAS[0]]["win_pct"]),
         delta_unit=" pts", higher_is_better=True),
    dict(label="Passes per 90", value=by_metric.loc["passes_attempted_per90",
                                                    C.ERAS[1]], decimals=0,
         accent=C.era_color(C.ERAS[1]),
         sub="The clearest change in the whole dataset — the same share of the "
             "ball, moved with far fewer touches",
         delta_pct=change("passes_attempted_per90"), higher_is_better=False),
    dict(label="xG per shot", value=by_metric.loc["xg_per_shot", C.ERAS[1]],
         decimals=3, accent=C.era_color(C.ERAS[1]),
         sub="More shots, each one worth less — the counterweight to the "
             "improved results",
         delta_pct=change("xg_per_shot"), higher_is_better=True),
], per_row=4)

st.markdown("")
ui.notice(C.NOTE_SAMPLE, kind="caution", label="Read every number this way")

# --------------------------------------------------------------------------- #
# The two eras
# --------------------------------------------------------------------------- #

ui.section("The two tenures",
           "Chronological, one pill per match. The record is the part of this "
           "comparison that moved most — and the part the event data explains "
           "least.")

for era in C.ERAS:
    subset = matches[matches["era"] == era].sort_values("date")
    rec = full_record[era]
    color = C.era_color(era)
    left, right = st.columns([1, 2.1], gap="medium")
    with left:
        ui.kpi(era, f"{rec['W']}–{rec['D']}–{rec['L']}", accent=color,
               sub=f"{rec['matches']} matches · {rec['gf']} scored, "
                   f"{rec['ga']} conceded · {rec['ppm']:.2f} points per match")
    with right:
        st.markdown(
            f"<div style='font-size:.71rem;font-weight:640;letter-spacing:.085em;"
            f"text-transform:uppercase;color:{C.INK_MUTED};margin-bottom:.45rem'>"
            f"{', '.join(C.tournament_label(t) for t in C.TOURNAMENTS if C.TOURNAMENT_ERA[t] == era)}"
            "</div>", unsafe_allow_html=True)
        ui.form_string(subset["result"].tolist())
        st.markdown(
            f"<div style='font-size:.79rem;color:{C.INK_2};margin-top:.5rem;"
            "line-height:1.5'>"
            + " · ".join(f"{row.opponent} {row.spain_score}–{row.opp_score}"
                         for row in subset.itertuples())
            + "</div>", unsafe_allow_html=True)
    st.markdown("")

# --------------------------------------------------------------------------- #
# What the pages hold
# --------------------------------------------------------------------------- #

ui.section("Where to go next",
           "Filters in the sidebar — era, tournament, opponent, round — carry "
           "across every page, so a selection made here is still in force there.")

GUIDE = [
    ("1 · Overview", "The era comparison in full: every headline metric, the "
     "size of each change, and the match-by-match record."),
    ("2 · Luis Enrique", "EURO 2020 and the 2022 World Cup on their own terms — "
     "dense circulation, central buildup, 40% win rate."),
    ("3 · Luis de la Fuente", "EURO 2024 and the 2026 World Cup — fewer passes, "
     "wider play, two trophies."),
    ("4 · Passing", "Volume, completion, progression and the passing networks "
     "that show how the ball actually travelled."),
    ("5 · Shooting", "Shot maps, xG and the shot-quality question — with "
     "official and estimated xG kept visibly apart."),
    ("6 · Possession", "The proxy, what it does and does not say, and whether "
     "more of the ball bought anything."),
    ("7 · Final third", "Entries into the final third and the box, and the "
     "pass-versus-carry shift in how Spain progresses."),
    ("8 · Players", "Who bridged both eras and how their own role changed — "
     "Rodri, Pedri, Dani Olmo and the rest of the squad."),
]
# Four per row: eight pages then fill two rows exactly, with no ragged last row.
PER_ROW = 4
for start in range(0, len(GUIDE), PER_ROW):
    for col, (name, blurb) in zip(st.columns(PER_ROW, gap="medium"),
                                  GUIDE[start:start + PER_ROW]):
        with col:
            st.markdown(
                f'<div class="kpi" style="--accent:{C.BRAND}">'
                f'<span class="lab">{name}</span>'
                f'<span class="sub" style="margin-top:.1rem;font-size:.825rem">'
                f"{blurb}</span></div>", unsafe_allow_html=True)
    st.markdown("")

# --------------------------------------------------------------------------- #
# Data provenance & cleaning
# --------------------------------------------------------------------------- #

ui.section("The data underneath", accent=C.SERIES[2])

report = dl.quality_report()
left, right = st.columns([1.15, 1], gap="large")

with left:
    if report:
        passed = sum(c["status"] == "PASS" for c in report["checks"])
        total = len(report["checks"])
        kinds = {}
        for action in report["actions"]:
            kinds[action["kind"]] = kinds.get(action["kind"], 0) + 1
        st.markdown(
            f'<div class="kpi" style="--accent:{C.GOOD if passed == total else C.CRITICAL}">'
            f'<span class="lab">Cleaning &amp; validation</span>'
            f'<span class="val">{passed}<span class="unit">/ {total} checks pass'
            f'</span></span><span class="sub">'
            f'{kinds.get("harmonise", 0)} harmonisations across the two sources · '
            f'{kinds.get("derive", 0)} derived columns · '
            f'{kinds.get("repair", 0)} repairs to defects in the collected files.'
            "<br>Goals in the event stream reconcile with all 25 scorelines, and "
            "the derived event flags reproduce the pre-aggregated team totals "
            "exactly.</span></div>", unsafe_allow_html=True)
    else:
        ui.notice(
            "The cleaning pipeline has not been run, so this app is reading the "
            "raw collected files. Run <code>python src/clean_data.py</code> from "
            "the repo root to build <code>data/clean/</code>.", kind="caution")

    st.markdown("")
    ui.notice(
        "Two sources, one dataset. <strong>StatsBomb Open Data</strong> backs the "
        "17 matches at EURO 2020, the 2022 World Cup and EURO 2024. "
        "<strong>nlbair/wc2026-events</strong> (WhoScored-sourced) backs the 8 "
        "World Cup 2026 matches, in Opta's taxonomy. They differ in coordinate "
        "system, event vocabulary and coverage — the cleaning pass reconciles what "
        "can be reconciled and labels the rest.", kind="note",
        label="Where it comes from")

with right:
    st.markdown(
        f'<div class="kpi" style="--accent:{C.BRAND_GOLD}">'
        '<span class="lab">What this dashboard will not do</span>'
        '<span class="sub" style="margin-top:.2rem;font-size:.845rem">'
        "<strong>Claim the manager caused the results.</strong> Squad, opponents "
        "and competition depth all changed at the same time; 10 matches against 15 "
        "cannot separate them.<br><br>"
        "<strong>Present the possession proxy as the broadcast figure.</strong> It "
        "is a proxy, and a different one per source.<br><br>"
        "<strong>Blend estimated xG into official xG.</strong> World Cup 2026 has "
        "no official xG; those values come from a model and are marked as such "
        "wherever they appear.<br><br>"
        "<strong>Show a gap as a zero.</strong> Ball carries do not exist for the "
        "8 World Cup 2026 matches, and pages that use them say so."
        "</span></div>", unsafe_allow_html=True)

ui.footer()
