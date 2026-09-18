# -*- coding: utf-8 -*-
"""Page 8 — Players: who bridged the eras, and how their role changed."""
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

ui.page_setup("Players", icon="👤")
sel = filters.render_sidebar(show_player=True)

ui.page_header(
    "Page 8 · Players",
    "Fourteen players bridge both eras",
    "The squad is the confound in every other page: 14 players appear under both "
    "managers, 14 only under Luis Enrique and 18 only under Luis de la Fuente. "
    "For the players who span the change, per-90 numbers under each manager show "
    "how an individual's role moved — which is the closest this dataset comes to "
    "separating the system from the personnel.")

players = dl.load_players()
player_stats = dl.load_player_stats()
spain_players = players[players["is_spain"]].copy()
spain_stats = player_stats[player_stats["is_spain"]].copy()

if spain_players.empty:
    ui.empty_state("No Spain players in the dataset.")
    st.stop()

# --------------------------------------------------------------------------- #
# Squad turnover
# --------------------------------------------------------------------------- #

turnover = M.squad_turnover(player_stats)
bridging = spain_players[spain_players["bridges_eras"]]

ui.section("Squad continuity")
ui.kpi_row([
    dict(label="Spain players in the dataset", value=len(spain_players),
         decimals=0, accent=C.BRAND,
         sub=f"Across all 25 matches, unified to one canonical name per player"),
    dict(label="Used by both managers", value=len(bridging), decimals=0,
         accent=C.SERIES[2],
         sub="The players whose own numbers can be compared across the change"),
    dict(label="Luis Enrique only",
         value=int(turnover.loc[turnover["group"].str.contains("Enrique only"),
                                "players"].iloc[0]) if not turnover.empty else None,
         decimals=0, accent=C.era_color(C.ERAS[0]),
         sub="Busquets, Jordi Alba, Thiago and the rest of the earlier squad"),
    dict(label="Luis de la Fuente only",
         value=int(turnover.loc[turnover["group"].str.contains("Fuente only"),
                                "players"].iloc[0]) if not turnover.empty else None,
         decimals=0, accent=C.era_color(C.ERAS[1]),
         sub="Yamal, Cucurella, Le Normand and the newer intake"),
], per_row=4)

st.markdown("")
ui.notice(
    "This is why every style difference on the other pages is described as "
    "something that happened, not something the manager caused: more than half "
    "the squad changed at the same time as the manager did, including the arrival "
    "of a generational wide forward. The two cannot be separated with 25 matches.",
    kind="caution", label="The confound, stated plainly")

# --------------------------------------------------------------------------- #
# One player across the change
# --------------------------------------------------------------------------- #

ui.section("One player, both managers",
           "Per-90 figures aggregated from the player's own minutes — total "
           "events divided by total minutes, not an average of per-match rates, "
           "so a short substitute appearance does not weigh the same as a full "
           "match.")

bridging_names = bridging.sort_values("minutes_played_total", ascending=False)[
    "player_canonical"].dropna().tolist()

if not bridging_names:
    ui.notice("No player in this dataset appears under both managers.", kind="gap")
else:
    default = sel.player if sel.player in bridging_names else bridging_names[0]
    player = st.selectbox(
        "Player", bridging_names, index=bridging_names.index(default),
        key="pl_bridge_player",
        help="Only players who appeared under both managers — the comparison "
             "needs both halves.")

    PLAYER_METRICS = ["passes_attempted_per90", "passes_completed_per90",
                      "progressive_passes_per90", "key_passes_per90",
                      "crosses_per90", "shots_per90", "goals_per90",
                      "carries_per90", "progressive_carries_per90",
                      "tackles_per90", "interceptions_per90", "recoveries_per90"]
    split = M.player_era_split(spain_stats, player, PLAYER_METRICS)

    if len(split) < 2:
        ui.notice(f"{player} has usable minutes under only one manager in this "
                  "dataset.", kind="gap")
    else:
        row = spain_players[spain_players["player_canonical"] == player].iloc[0]
        cards = [dict(label="Career in this dataset",
                      value=f"{int(row['matches_played'])} matches", accent=C.BRAND,
                      sub=f"{row['minutes_played_total']:,.0f} minutes · "
                          f"{row['tournaments'].replace(',', ', ')}")]
        for entry in split.itertuples():
            cards.append(dict(
                label=entry.era, value=entry.minutes, unit=" min", decimals=0,
                accent=C.era_color(entry.era),
                sub=f"{entry.matches} matches under this manager"))
        ui.kpi_row(cards, per_row=3)

        st.markdown("")
        ui.era_legend([e for e in C.ERAS if e in set(split["era"])])
        st.plotly_chart(
            cp.player_era_bars(
                split, PLAYER_METRICS, [M.label_of(m) for m in PLAYER_METRICS],
                title=f"{player} — per-90 role change",
                subtitle="Indexed to this player's own Luis Enrique level, so "
                         "metrics on very different scales share one axis"),
            use_container_width=True, config={"displayModeBar": False})

        # Built metric-per-row rather than by transposing the frame: a
        # transpose mixes ints, floats and strings into one object column,
        # which the table renderer cannot serialise.
        by_era = split.set_index("era")
        rows = []
        for metric in PLAYER_METRICS:
            if metric not in split.columns:
                continue
            old = by_era[metric].get(C.ERAS[0])
            new = by_era[metric].get(C.ERAS[1])
            change = M.pct_change(old, new)
            rows.append({
                "Metric": M.label_of(metric) + M.unit_of(metric),
                C.ERAS[0]: round(old, 2) if pd.notna(old) else None,
                C.ERAS[1]: round(new, 2) if pd.notna(new) else None,
                "Change %": round(change, 1) if change is not None else None,
            })
        ui.table_view(pd.DataFrame(rows),
                      f"Show {player}'s raw per-90 numbers")

        carry_cols = [c for c in ("carries_per90", "progressive_carries_per90")
                      if c in split.columns]
        if carry_cols and split[carry_cols].isna().any().any():
            ui.notice(
                "Carry figures are blank for this player's World Cup 2026 "
                "appearances — the source logs no carry events, so those minutes "
                "are excluded from the carry rates rather than counted as zero.",
                kind="gap", label="Partial coverage")

# --------------------------------------------------------------------------- #
# The squad, mapped
# --------------------------------------------------------------------------- #

ui.section("The squad, mapped",
           "Each dot is a player's career total in this dataset; size is minutes "
           "played. Colour marks which manager(s) used them — three categories, "
           "which is the limit at which a scatter's colours stay separable.")

AXES = {
    "passes_attempted_per90": "Passes per 90",
    "progressive_passes_per90": "Progressive passes per 90",
    "key_passes_per90": "Key passes per 90",
    "shots_per90": "Shots per 90",
    "goals_per90": "Goals per 90",
    "xg_total_per90": "xG per 90",
    "tackles_per90": "Tackles per 90",
    "interceptions_per90": "Interceptions per 90",
    "recoveries_per90": "Ball recoveries per 90",
    "carries_per90": "Carries per 90 (StatsBomb matches only)",
    "progressive_carries_per90": "Progressive carries per 90 (StatsBomb only)",
}
available = {k: v for k, v in AXES.items() if k in spain_players.columns}

controls = st.columns([1, 1, 1], gap="medium")
with controls[0]:
    x_metric = st.selectbox("X axis", list(available), index=0,
                            format_func=lambda k: available[k], key="pl_x")
with controls[1]:
    y_keys = list(available)
    y_metric = st.selectbox("Y axis", y_keys,
                            index=min(1, len(y_keys) - 1),
                            format_func=lambda k: available[k], key="pl_y")
with controls[2]:
    min_minutes = st.slider("Minimum minutes played", 0, 1200, 270, step=90,
                            key="pl_minutes",
                            help="Per-90 rates from very few minutes are noise; "
                                 "270 is roughly three full matches.")

scatter_data = spain_players[
    spain_players["minutes_played_total"].fillna(0) >= min_minutes]

if scatter_data.empty:
    ui.empty_state("No player clears that minutes threshold.",
                   "Lower the slider.")
else:
    st.plotly_chart(
        cp.player_scatter(scatter_data, x_metric, y_metric,
                          x_label=available[x_metric], y_label=available[y_metric],
                          size="minutes_played_total",
                          title=f"{available[y_metric]} against {available[x_metric]}",
                          subtitle=f"{len(scatter_data)} Spain players with "
                                   f"{min_minutes}+ minutes · bubble size is "
                                   "minutes played"),
        use_container_width=True, config={"displayModeBar": False})

    if x_metric == y_metric:
        st.caption("Both axes show the same metric, so every point sits on the "
                   "diagonal — pick two different metrics to compare them.")

    # The two axis columns are de-duplicated: the selectors are independent, so
    # the same metric can be chosen for both, and taking it twice would build a
    # frame with two identically-named columns that cannot be rendered.
    axis_columns = [x_metric] if x_metric == y_metric else [x_metric, y_metric]
    base_columns = ["player_canonical", "matches_played", "minutes_played_total",
                    "tournaments", "eras"]
    display = scatter_data[base_columns + axis_columns].copy()
    display.columns = (["Player", "Matches", "Minutes", "Tournaments", "Eras"]
                       + [available[c] for c in axis_columns])
    ui.table_view(display.round(2).sort_values("Minutes", ascending=False),
                  "Show every player in this view")

# --------------------------------------------------------------------------- #
# Rankings
# --------------------------------------------------------------------------- #

ui.section("Rankings")

RANKABLE = {
    "minutes_played_total": ("Minutes played", 0),
    "goals": ("Goals", 0),
    "shots": ("Shots", 0),
    "xg_total": ("xG", 2),
    "key_passes": ("Key passes", 0),
    "progressive_passes": ("Progressive passes", 0),
    "passes_completed": ("Passes completed", 0),
    "progressive_carries": ("Progressive carries", 0),
    "tackles": ("Tackles", 0),
    "interceptions": ("Interceptions", 0),
    "recoveries": ("Ball recoveries", 0),
}
available_ranks = {k: v for k, v in RANKABLE.items() if k in spain_players.columns}

left, right = st.columns([1, 1], gap="large")
with left:
    rank_metric = st.selectbox("Rank by", list(available_ranks),
                               format_func=lambda k: available_ranks[k][0],
                               key="pl_rank")
with right:
    top_n = st.slider("Show top", 5, 25, 12, key="pl_topn")

ranked = spain_players.dropna(subset=[rank_metric]).nlargest(top_n, rank_metric)
if ranked.empty:
    ui.empty_state(f"No player has a value for {available_ranks[rank_metric][0]}.")
else:
    label, decimals = available_ranks[rank_metric]
    ranked = ranked.assign(era_group=ranked["eras"].map(
        lambda e: "Both" if "," in str(e) else e))
    st.plotly_chart(
        cp.horizontal_ranking(
            ranked, label_col="player_canonical", value_col=rank_metric,
            color_col="era_group", decimals=decimals,
            title=f"{label} — top {len(ranked)}",
            subtitle="Career totals across this dataset. Bar colour is the era "
                     "the player belongs to; a player who spans both is shown "
                     "in the third colour."),
        use_container_width=True, config={"displayModeBar": False})
    # `minutes_played_total` is itself rankable, so the ranked metric may already
    # be one of the context columns — appending it again would duplicate a name.
    context = {"player_canonical": "Player", "matches_played": "Matches",
               "minutes_played_total": "Minutes", "eras": "Eras"}
    columns = list(context)
    if rank_metric not in context:
        columns.append(rank_metric)
    display = ranked[columns].copy()
    display.columns = [context.get(c, label) for c in columns]
    ui.table_view(display.round(2))

note = M.coverage_note(spain_players[rank_metric], "Spain players")
if note:
    ui.notice(note, kind="gap", label="Partial coverage")

ui.footer()
