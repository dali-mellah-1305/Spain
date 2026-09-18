# -*- coding: utf-8 -*-
"""Page 7 — Final Third: entries, box access, and pass-versus-carry progression."""
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

ui.page_setup("Final Third", icon="📐")
sel = filters.render_sidebar()

ui.page_header(
    "Page 7 · Final third",
    "Fewer entries, more carried in",
    "Passes into the final third fall 30% between the eras while shots rise — so "
    "Spain is reaching the final third less often by passing, and doing more once "
    "there. Progressive carries rose 21% as progressive passes fell 9%, which "
    "points at individual ball-carrying taking over some of the work the short "
    "passing used to do.")

passes = sel.events("passes", spain_only=True)
team_stats = sel.team_stats
both = sel.both_eras

if passes.empty:
    ui.empty_state("No passes in the current selection.",
                   "Widen the filters in the sidebar.")
    st.stop()

# --------------------------------------------------------------------------- #
# Entry volume
# --------------------------------------------------------------------------- #

ENTRY_METRICS = ["passes_into_final_third_per90", "passes_into_penalty_area_per90",
                 "progressive_passes_per90", "progressive_carries_per90",
                 "key_passes_per90", "crosses_per90", "shots_per90", "xg_per90"]
comparison = M.era_comparison(team_stats, ENTRY_METRICS)
by_metric = comparison.set_index("metric")


def card(metric: str, sub: str = "") -> dict:
    row = by_metric.loc[metric] if metric in by_metric.index else None
    era = sel.single_era or C.ERAS[1]
    value = row[era] if row is not None else None
    partial = bool(row["partial"]) if row is not None else False
    return dict(label=M.label_of(metric), value=value, unit=M.unit_of(metric),
                decimals=M.decimals_of(metric),
                accent=C.era_color(era),
                sub=sub + (" · partial coverage" if partial else ""),
                delta_pct=(row["change_pct"] if (row is not None and both) else None),
                higher_is_better=M.higher_is_better(metric))


entries = passes[passes["into_final_third"] & passes["is_complete"]]
box_entries = passes[passes["into_penalty_area"] & passes["is_complete"]]

ui.section("Getting there", sel.describe())
ui.kpi_row([
    dict(label="Final-third entries", value=len(entries), decimals=0,
         accent=C.BRAND,
         sub=f"Completed passes ending in the final third, having started "
             f"outside it · {len(box_entries):,} reached the box"),
    card("passes_into_final_third_per90", "Entries per 90"),
    card("passes_into_penalty_area_per90", "Box entries per 90"),
    card("key_passes_per90", "Passes that led directly to a shot"),
], per_row=4)
st.markdown("")
ui.kpi_row([
    card("progressive_passes_per90", "Passes cutting ≥25% off the distance to goal"),
    card("progressive_carries_per90", "Carries doing the same — StatsBomb matches only"),
    card("crosses_per90", "Crosses per 90"),
    card("shots_per90", "What the entries produced"),
], per_row=4)

filters.coverage_notices(sel, carries=True)

# --------------------------------------------------------------------------- #
# Where entries land
# --------------------------------------------------------------------------- #

ui.section("Where the ball enters",
           "Each dot is where a completed entry pass ended; the comet tail shows "
           "where it came from. This is about the landing zone, which an arrow "
           "from every origin would bury.")

zone = st.radio("Entry into", ["Final third", "Penalty area"], horizontal=True,
                key="ft_zone")
zone_key = "penalty_area" if zone == "Penalty area" else "final_third"

if both:
    left, right = st.columns(2, gap="large")
    for column, era in zip((left, right), C.ERAS):
        era_passes = passes[passes["era"] == era]
        with column:
            st.pyplot(cm.entry_map(
                era_passes, era=era, zone=zone_key, title=era,
                figsize=(7.0, 4.9)), width="stretch")
else:
    era = sel.single_era
    st.pyplot(cm.entry_map(passes, era=era, zone=zone_key,
                           title=f"{era} — {zone.lower()} entries"),
              width="stretch")

# Which flank, and how high up
target = entries if zone_key == "final_third" else box_entries
if not target.empty:
    flank = pd.cut(target["normalized_end_y"], [-0.01, 33.3, 66.7, 100.01],
                   labels=["Right flank", "Central", "Left flank"])
    flanks = (target.assign(flank=flank)
              .groupby(["era", "flank"], observed=True).size()
              .rename("entries").reset_index())
    if both and not flanks.empty:
        st.plotly_chart(
            cp.stacked_share(flanks, category="flank", value="entries",
                             group="era",
                             title=f"Which channel the {zone.lower()} entries used",
                             subtitle="Share of each era's own entries. Note the "
                                      "pitch y-axis runs 0 at one touchline to "
                                      "100 at the other.", height=230),
            use_container_width=True, config={"displayModeBar": False})
        pivot = flanks.pivot_table(index="era", columns="flank", values="entries",
                                   observed=True).reset_index()
        ui.table_view(pivot, "Show entry counts by channel")

# --------------------------------------------------------------------------- #
# Pass or carry?
# --------------------------------------------------------------------------- #

ui.section("Passed forward, or carried forward?",
           "The project's own reading of the era change is that individual "
           "ball-carrying replaced some of the short combination play. Carries "
           "exist for the 17 StatsBomb matches only, so this section covers those "
           "and says so rather than showing the 8 World Cup 2026 matches as zero.")

carries = sel.events("carries", spain_only=True)

if carries.empty:
    ui.notice(
        f"{C.NOTE_CARRIES}<br><strong>No selected match has carry data</strong>, "
        "so the pass-versus-carry comparison cannot be drawn for this selection. "
        "Include EURO 2020, the 2022 World Cup or EURO 2024 to see it.",
        kind="gap", label="No carry data in this selection")
else:
    carry_matches = set(carries["match_id"])
    comparable_passes = passes[passes["match_id"].isin(carry_matches)]

    rows = []
    for era in C.ERAS:
        era_carries = carries[carries["era"] == era]
        era_passes = comparable_passes[comparable_passes["era"] == era]
        if era_carries.empty and era_passes.empty:
            continue
        n_matches = len(set(era_carries["match_id"]) | set(era_passes["match_id"]))
        rows.append({
            "era": era, "matches": n_matches,
            "Progressive passes": int(era_passes["is_progressive"].sum()),
            "Progressive carries": int(era_carries["is_progressive"].sum()),
        })
    progression = pd.DataFrame(rows)

    if not progression.empty:
        tidy = progression.melt(id_vars=["era", "matches"],
                                value_vars=["Progressive passes",
                                            "Progressive carries"],
                                var_name="kind", value_name="events")
        tidy["per_match"] = tidy["events"] / tidy["matches"]

        left, right = st.columns([1, 1], gap="medium")
        with left:
            st.plotly_chart(
                cp.stacked_share(tidy, category="kind", value="events",
                                 group="era",
                                 title="Progression: passes against carries",
                                 subtitle="Share of each era's progressive "
                                          "actions, over matches with both "
                                          "kinds of data", height=230),
                use_container_width=True, config={"displayModeBar": False})
        with right:
            display = tidy[["era", "kind", "events", "per_match", "matches"]].round(1)
            display.columns = ["Era", "Type", "Events", "Per match", "Matches"]
            st.dataframe(display, width="stretch", hide_index=True)

        ui.notice(
            "Restricted to the matches that have both pass and carry data, so the "
            "two are counted over the same games. That is 17 of 25 matches at "
            "most — the 8 World Cup 2026 fixtures are absent from this comparison "
            "entirely.", kind="note", label="What this is counted over")

    progressive_carries = carries[carries["is_progressive"]]
    if both and not progressive_carries.empty:
        st.pyplot(cm.progression_comparison(
            progressive_carries[progressive_carries["era"] == C.ERAS[0]],
            progressive_carries[progressive_carries["era"] == C.ERAS[1]],
            left_title=f"{C.ERAS[0]} — progressive carries",
            right_title=f"{C.ERAS[1]} — progressive carries"),
            width="stretch")
    elif not progressive_carries.empty:
        st.pyplot(cm.event_heatmap(progressive_carries, era=sel.single_era,
                                   title="Progressive carry origins"),
                  width="stretch")

    carriers = (carries[carries["player_canonical"].notna()]
                .groupby("player_canonical", observed=True)
                .agg(carries=("is_progressive", "size"),
                     progressive=("is_progressive", "sum"),
                     distance=("distance", "mean")).reset_index())
    if not carriers.empty:
        top = carriers.nlargest(12, "progressive")
        st.plotly_chart(
            cp.horizontal_ranking(
                top.sort_values("progressive", ascending=False),
                label_col="player_canonical", value_col="progressive", decimals=0,
                title="Most progressive carries in the selection",
                subtitle="StatsBomb-covered matches only"),
            use_container_width=True, config={"displayModeBar": False})
        display = carriers.sort_values("progressive", ascending=False).round(2)
        display.columns = ["Player", "Carries", "Progressive carries",
                           "Mean distance"]
        ui.table_view(display, "Show every carrier")

# --------------------------------------------------------------------------- #
# Entry to shot
# --------------------------------------------------------------------------- #

ui.section("From entry to shot",
           "How many entries it took per shot. A lower number means Spain turned "
           "final-third access into attempts more directly.")

shots = sel.events("shots", spain_only=True)
countable = shots[shots["counts_as_shot"]] if not shots.empty else shots

rows = []
for era in C.ERAS:
    era_entries = entries[entries["era"] == era]
    era_box = box_entries[box_entries["era"] == era]
    era_shots = countable[countable["era"] == era] if not countable.empty else countable
    if era_entries.empty and (era_shots is None or era_shots.empty):
        continue
    n_shots = len(era_shots) if era_shots is not None else 0
    rows.append({
        "Era": era, "Final-third entries": len(era_entries),
        "Box entries": len(era_box), "Shots": n_shots,
        "Entries per shot": round(len(era_entries) / n_shots, 2) if n_shots else None,
        "Box entries per shot": round(len(era_box) / n_shots, 2) if n_shots else None,
    })
efficiency = pd.DataFrame(rows)
if not efficiency.empty:
    left, right = st.columns([1, 1.2], gap="medium")
    with left:
        plot = efficiency.dropna(subset=["Entries per shot"]).rename(
            columns={"Entries per shot": "value"})
        if not plot.empty:
            st.plotly_chart(
                cp.horizontal_ranking(
                    plot.assign(era=plot["Era"]), label_col="Era",
                    value_col="value", color_col="era", decimals=2,
                    title="Final-third entries per shot",
                    subtitle="Lower means access converted into attempts more "
                             "directly", height=200),
                use_container_width=True, config={"displayModeBar": False})
    with right:
        st.dataframe(efficiency, width="stretch", hide_index=True)

ui.footer()
