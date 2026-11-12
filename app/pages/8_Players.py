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
        radar = M.player_radar(spain_stats, player)
        if radar.empty:
            ui.notice(f"No radar for {player}: the dataset has no goalkeeping "
                      "events, and outfield percentiles would not describe a "
                      "goalkeeper.", kind="gap")
        else:
            kind = st.radio("Chart type", ["Radar", "Pizza"], horizontal=True,
                            key="pl_radar_kind")
            st.plotly_chart(
                cp.player_radar(
                    radar, kind=kind.lower(),
                    title=f"{player} — Luis Enrique vs Luis de la Fuente",
                    subtitle="Percentile among Spain outfield players in this "
                             "dataset (per 90, 180+ minutes under one manager)"),
                key=f"pl_radar_chart_{kind}",
                use_container_width=True, config={"displayModeBar": False})
            missing = [C.ERA_SHORT[e] for e in C.ERAS
                       if e not in set(radar["era"])]
            if missing:
                ui.notice(f"{player} played under 90 minutes under "
                          f"{' and '.join(missing)} — too few for per-90 rates, "
                          "so that side is not drawn.", kind="gap")
            st.caption("xG, progressive carries and tackles use the StatsBomb "
                       "matches only — World Cup 2026 does not log them.")
            shown = radar[["era", "label", "value", "percentile"]].round(2)
            shown.columns = ["Manager", "Metric", "Per 90 (or %)", "Percentile"]
            ui.table_view(shown, f"Show {player}'s radar numbers")

ui.footer()
