# -*- coding: utf-8 -*-
"""
The layout shared by pages 2 and 3.

The architecture calls page 3 "same as page 2, mirrored", so the two pages are
one renderer parameterised by era rather than two copies of the same layout.
Each page supplies its own framing copy — the structure is identical, what the
numbers mean is not.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import charts_mplsoccer as cm
from . import charts_plotly as cp
from . import config as C
from . import data_loader as dl
from . import filters as flt
from . import metrics as M
from . import ui

KPI_METRICS = ["possession_pct_proxy", "passes_attempted_per90", "pass_pct",
               "progressive_passes_per90", "passes_into_final_third_per90",
               "shots_per90", "shots_on_target_per90", "xg_per90", "xg_per_shot",
               "goals_per90", "carries_per90", "progressive_carries_per90",
               "tackles_per90", "interceptions_per90", "clearances_per90",
               "recoveries_per90"]

TRENDABLE = ["passes_attempted_per90", "possession_pct_proxy", "pass_pct",
             "progressive_passes_per90", "passes_into_final_third_per90",
             "shots_per90", "shots_on_target_per90", "xg_per90", "goals_per90",
             "tackles_per90", "clearances_per90"]


def render(era: str, *, page_no: int, lede: str, character: str,
           key_prefix: str) -> None:
    """Render one manager's page.

    ``lede`` is the page's opening paragraph; ``character`` is the short reading
    of that era's style shown beside the tournament split.
    """
    sel = flt.render_sidebar(lock_era=era)
    color = C.era_color(era)
    other = C.ERAS[0] if era == C.ERAS[1] else C.ERAS[1]

    tournaments = [t for t in C.TOURNAMENTS if C.TOURNAMENT_ERA[t] == era]
    ui.page_header(f"Page {page_no} · {era}",
                   f"{era}: " + " and ".join(C.tournament_label(t)
                                             for t in tournaments),
                   lede)

    matches = sel.matches
    if matches.empty:
        ui.empty_state("No matches in the current selection.",
                       "Widen the tournament, opponent or round filters.")
        return

    team_stats = sel.team_stats
    spain = M.spain_rows(team_stats)
    all_team_stats = dl.load_team_stats()

    # ---- headline, with the other era as the reference point ----------- #
    comparison = M.era_comparison(all_team_stats, KPI_METRICS).set_index("metric")
    record = M.record(matches)

    def card(metric: str, sub: str = "", **kwargs) -> dict:
        row = comparison.loc[metric] if metric in comparison.index else None
        change = None
        if row is not None and pd.notna(row["change_pct"]):
            # The stored change always runs Enrique → De la Fuente; invert it
            # when this page is the earlier era so "vs the other manager" is
            # read from this page's own point of view.
            change = (row["change_pct"] if era == C.ERAS[1]
                      else M.pct_change(row[C.ERAS[1]], row[C.ERAS[0]]))
        return dict(
            label=M.label_of(metric),
            value=spain[metric].mean() if metric in spain.columns else None,
            unit=M.unit_of(metric), decimals=M.decimals_of(metric),
            accent=color, sub=sub, delta_pct=change,
            higher_is_better=M.higher_is_better(metric),
            delta_suffix=f" vs {C.ERA_SHORT[other]}", **kwargs)

    ui.section("This tenure in numbers",
               f"{sel.describe()}. Each change is measured against "
               f"{other}'s matches over the whole dataset, not against the "
               "current selection.", accent=color)

    ui.kpi_row([
        dict(label="Record", value=f"{record['W']}–{record['D']}–{record['L']}",
             accent=color,
             sub=f"{record['matches']} matches · {record['gf']} scored, "
                 f"{record['ga']} conceded · {record['win_pct']:.0f}% wins"),
        card("possession_pct_proxy", "Proxy figure — see the Possession page"),
        card("passes_attempted_per90", "Pass volume per 90 minutes"),
        card("pass_pct", "Completion rate"),
    ], per_row=4)
    st.markdown("")
    ui.kpi_row([
        card("progressive_passes_per90", "Passes cutting ≥25% off the distance "
             "to goal"),
        card("passes_into_final_third_per90", "Completed entries into the final "
             "third"),
        card("shots_per90", "Attempts per 90"),
        card("xg_per_shot", "Average quality of each attempt"),
    ], per_row=4)

    # ---- tournament split ---------------------------------------------- #
    ui.section("The two tournaments", character, accent=color)

    profile = M.tournament_profile(team_stats, KPI_METRICS)
    tournament_record = M.record_by_tournament(matches)

    cols = st.columns(max(len(tournament_record), 1), gap="medium")
    for col, row in zip(cols, tournament_record.itertuples()):
        stats = profile[profile["tournament"] == row.tournament]
        with col:
            passes = (stats["passes_attempted_per90"].iloc[0]
                      if not stats.empty else float("nan"))
            shots = stats["shots_per90"].iloc[0] if not stats.empty else float("nan")
            ui.kpi(row.label, f"{row.W}–{row.D}–{row.L}", accent=color,
                   sub=f"{row.matches} matches · {row.gf}–{row.ga} on aggregate"
                       f"<br>{passes:,.0f} passes/90 · {shots:,.1f} shots/90")

    st.markdown("")
    metric = st.selectbox("Metric to trace across this tenure", TRENDABLE,
                          format_func=M.label_of, key=f"{key_prefix}_metric")
    timeline = M.match_timeline(team_stats, metric)
    st.plotly_chart(
        cp.match_trend(timeline, metric, label=M.label_of(metric),
                       unit=M.unit_of(metric), decimals=M.decimals_of(metric),
                       title=f"{M.label_of(metric)} — every match in order",
                       subtitle="Dashed line is this tenure's mean"),
        use_container_width=True, config={"displayModeBar": False})

    display = timeline[["date", "tournament", "opponent", "round", "match_result",
                        metric]].copy()
    display["date"] = pd.to_datetime(display["date"]).dt.strftime("%d %b %Y")
    display.columns = ["Date", "Tournament", "Opponent", "Round", "Result",
                       M.label_of(metric) + M.unit_of(metric)]
    ui.table_view(display.round(2))

    # ---- shot maps ------------------------------------------------------ #
    ui.section("Where the shots came from",
               "Attacking half only. Marker area is the shot's xG; a filled "
               "marker is a goal. Own goals and penalty-shootout kicks are "
               "excluded, matching how the aggregate tables count shots.",
               accent=color)

    shots = sel.events("shots", spain_only=True)
    if "WC2026" in sel.tournaments:
        ui.notice(C.NOTE_XG_PROXY, kind="caution", label="Mixed xG provenance")

    st.pyplot(cm.shot_maps_by_group(
        shots, "tournament", tournaments, labels=C.TOURNAMENT_LABEL,
        era_of=C.TOURNAMENT_ERA, figsize=(11.5, 5.4)), width="stretch")

    summary = []
    for code in tournaments:
        subset = shots[shots["tournament"] == code]
        if subset.empty:
            continue
        stats = M.shot_summary(subset)
        summary.append({"Tournament": C.tournament_label(code),
                        "Shots": stats["shots"], "On target": stats["on_target"],
                        "Goals": stats["goals"],
                        "xG": round(stats["xg"], 2) if pd.notna(stats["xg"]) else None,
                        "xG per shot": round(stats["xg_per_shot"], 3)
                        if pd.notna(stats["xg_per_shot"]) else None,
                        "Official xG %": round(stats["pct_official_xg"], 0)})
    ui.table_view(pd.DataFrame(summary), "Show the shot totals")

    # ---- territory ------------------------------------------------------ #
    ui.section("Where the ball was played",
               "Pass origins as a share of this tenure's own passes, so the map "
               "shows distribution rather than volume.", accent=color)

    passes = sel.events("passes", spain_only=True)
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.pyplot(cm.event_heatmap(
            passes, era=era, title="Pass origins",
            note=f"{len(passes):,} passes across {len(matches)} matches",
            figsize=(7.6, 5.0)), width="stretch")
    with right:
        thirds = (passes.groupby("pitch_third", observed=True).size()
                  .rename("passes").reset_index())
        if not thirds.empty:
            thirds["share"] = thirds["passes"] / thirds["passes"].sum() * 100
            st.plotly_chart(
                cp.horizontal_ranking(
                    thirds.sort_values("share", ascending=False),
                    label_col="pitch_third", value_col="share", unit="%",
                    decimals=1, title="Share of passes by pitch third",
                    subtitle="Where this tenure started its passes",
                    height=260),
                use_container_width=True, config={"displayModeBar": False})
            ui.table_view(thirds.round(1), "Show pitch-third counts")

    # ---- passing network ------------------------------------------------ #
    ui.section("How the ball travelled between players", accent=color)

    network_matches = matches[matches["source_short"] == "StatsBomb"] \
        if "source_short" in matches.columns else matches
    if network_matches.empty:
        ui.notice(
            "A passing network needs the pass recipient, which only the StatsBomb "
            "source records. None of the selected matches come from it, so no "
            "network can be drawn — this is a source limitation, not an empty "
            "result.", kind="gap")
    else:
        labels = dict(zip(network_matches["match_id"], network_matches["label"]))
        match_id = st.selectbox(
            "Match", network_matches["match_id"].tolist(),
            format_func=lambda mid: labels.get(mid, mid),
            key=f"{key_prefix}_network_match")
        match_passes = passes[passes["match_id"] == match_id]
        nodes, edges = M.passing_network(match_passes, min_passes=3)
        row = network_matches[network_matches["match_id"] == match_id].iloc[0]
        left, right = st.columns([1.5, 1], gap="large")
        with left:
            st.pyplot(cm.passing_network(
                nodes, edges, era=era,
                title=f"Spain vs {row['opponent']} — {C.tournament_label(row['tournament'])}",
                note="Node size is the player's pass volume; line width the "
                     "passes between that pair (3 or more shown)",
                figsize=(7.6, 5.2)), width="stretch")
        with right:
            if not nodes.empty:
                st.plotly_chart(
                    cp.horizontal_ranking(
                        nodes.sort_values("passes", ascending=False),
                        label_col="player", value_col="passes", decimals=0,
                        title="Passes played", subtitle="Completed open-play "
                                                        "passes in this match",
                        height=330),
                    use_container_width=True, config={"displayModeBar": False})
                if not edges.empty:
                    top = edges.nlargest(8, "passes")[["passer", "receiver",
                                                       "passes"]]
                    top.columns = ["From", "To", "Passes"]
                    ui.table_view(top, "Show the strongest passing connections")

    ui.footer()
