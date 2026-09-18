# -*- coding: utf-8 -*-
"""
The only module in the app that reads from disk.

Every loader is wrapped in ``@st.cache_data`` and keyed by its arguments, so
switching a filter that doesn't change *which* file is needed reuses the parsed
frame instead of re-reading a 12 MB CSV. Nothing here writes to the data
directory — the app is read-only over ``data/clean/``.

Loaders that take a ``tournaments`` argument accept a tuple (hashable, so it can
be a cache key) and filter after reading the full file once; the full read stays
cached under its own key, so the per-filter call is a cheap mask on cached data
rather than another parse.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import pandas as pd
import streamlit as st

from . import config as C

_DATE_COLS = {"date"}
_BOOL_COLS = {
    "is_spain", "extra_time", "penalties", "went_to_penalties", "is_cross",
    "is_through_ball", "is_key_pass", "is_progressive", "into_final_third",
    "into_penalty_area", "is_own_goal", "is_shootout", "is_goal", "is_on_target",
    "is_penalty", "has_xg", "counts_as_shot", "counts_as_goal", "is_complete",
    "is_set_piece", "is_open_play", "is_forward", "is_successful", "bridges_eras",
    "has_carries", "has_pressures", "has_official_xg", "has_positions",
}


# --------------------------------------------------------------------------- #
# Where the data is
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False)
def resolve_data_dir() -> tuple:
    """Find the data directory. Returns ``(path, is_cleaned)``.

    Prefers ``data/clean/`` (what ``src/clean_data.py`` writes). The raw
    ``Data/`` directory is a fallback so the app still starts before the cleaner
    has been run — pages then show a banner, because the derived columns the
    charts rely on only exist in the cleaned output.
    """
    for candidate in C.DATA_DIR_CANDIDATES:
        if (candidate / "matches.csv").exists():
            return str(candidate), candidate.name == "clean"
    raise FileNotFoundError(
        "No dataset found. Looked for matches.csv in: "
        + ", ".join(str(p) for p in C.DATA_DIR_CANDIDATES)
        + ". Run `python src/clean_data.py` from the repo root first."
    )


def data_dir() -> Path:
    return Path(resolve_data_dir()[0])


def is_cleaned() -> bool:
    return bool(resolve_data_dir()[1])


@st.cache_data(show_spinner=False)
def quality_report() -> Optional[dict]:
    """The cleaning pipeline's JSON report, if it was run."""
    path = data_dir() / "data_quality_report.json"
    if not path.exists():
        return None
    import json
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Generic reader
# --------------------------------------------------------------------------- #

def _read(name: str, usecols: Optional[Sequence[str]] = None) -> pd.DataFrame:
    path = data_dir() / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing — run `python src/clean_data.py`.")
    df = pd.read_csv(path, low_memory=False,
                     usecols=list(usecols) if usecols else None)
    for col in df.columns:
        if col in _DATE_COLS:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif col in _BOOL_COLS and df[col].dtype != bool:
            df[col] = (df[col].astype("string").str.lower()
                       .map({"true": True, "false": False, "1": True, "0": False})
                       .fillna(False).astype(bool))
    if "tournament" in df.columns:
        df["tournament"] = pd.Categorical(df["tournament"], categories=C.TOURNAMENTS,
                                          ordered=True)
    if "era" in df.columns:
        df["era"] = pd.Categorical(df["era"], categories=C.ERAS, ordered=True)
    if "round" in df.columns:
        df["round"] = pd.Categorical(df["round"], categories=C.ROUND_ORDER,
                                      ordered=True)
    return df


# --------------------------------------------------------------------------- #
# Small tables — always loaded whole
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False)
def load_matches() -> pd.DataFrame:
    return _read("matches").sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_team_stats() -> pd.DataFrame:
    return _read("team_stats")


@st.cache_data(show_spinner=False)
def load_player_stats() -> pd.DataFrame:
    return _read("player_stats")


@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame:
    return _read("players")


@st.cache_data(show_spinner=False)
def load_era_summary() -> pd.DataFrame:
    return _read("eda_team_summary_by_era")


@st.cache_data(show_spinner=False)
def load_tournament_summary() -> pd.DataFrame:
    return _read("eda_team_summary_by_tournament").sort_values("tournament")


# --------------------------------------------------------------------------- #
# Event tables — large, so the whole-file read is cached once and the
# per-tournament views are masks over that cached frame
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner="Loading pass events…")
def _all_passes() -> pd.DataFrame:
    return _read("passes")


@st.cache_data(show_spinner=False)
def _all_shots() -> pd.DataFrame:
    return _read("shots")


@st.cache_data(show_spinner="Loading carry events…")
def _all_carries() -> pd.DataFrame:
    return _read("carries")


@st.cache_data(show_spinner="Loading defensive events…")
def _all_defensive_actions() -> pd.DataFrame:
    return _read("defensive_actions")


def _subset(df: pd.DataFrame, tournaments: Optional[tuple],
            spain_only: bool) -> pd.DataFrame:
    if spain_only and "is_spain" in df.columns:
        df = df[df["is_spain"]]
    if tournaments and "tournament" in df.columns:
        df = df[df["tournament"].isin(list(tournaments))]
    return df


@st.cache_data(show_spinner=False)
def load_passes(tournaments: Optional[tuple] = None,
                spain_only: bool = False) -> pd.DataFrame:
    return _subset(_all_passes(), tournaments, spain_only)


@st.cache_data(show_spinner=False)
def load_shots(tournaments: Optional[tuple] = None,
               spain_only: bool = False) -> pd.DataFrame:
    return _subset(_all_shots(), tournaments, spain_only)


@st.cache_data(show_spinner=False)
def load_carries(tournaments: Optional[tuple] = None,
                 spain_only: bool = False) -> pd.DataFrame:
    return _subset(_all_carries(), tournaments, spain_only)


@st.cache_data(show_spinner=False)
def load_defensive_actions(tournaments: Optional[tuple] = None,
                           spain_only: bool = False) -> pd.DataFrame:
    return _subset(_all_defensive_actions(), tournaments, spain_only)


# --------------------------------------------------------------------------- #
# Dataset-wide facts, used by the sidebar
# --------------------------------------------------------------------------- #

@st.cache_data(show_spinner=False)
def dataset_facts() -> dict:
    matches = load_matches()
    return {
        "n_matches": len(matches),
        "n_by_era": matches["era"].value_counts().reindex(C.ERAS).to_dict(),
        "date_min": matches["date"].min(),
        "date_max": matches["date"].max(),
        "opponents": sorted(matches["opponent"].dropna().unique().tolist()),
        "tournaments": [t for t in C.TOURNAMENTS
                        if t in set(matches["tournament"].dropna())],
        "carry_matches": int(matches["has_carries"].sum())
        if "has_carries" in matches.columns else 0,
    }


@st.cache_data(show_spinner=False)
def spain_players(min_minutes: int = 0) -> pd.DataFrame:
    """Spain squad members, most-used first — the player selector's options."""
    players = load_players()
    spain = players[players["is_spain"]].copy()
    if min_minutes:
        spain = spain[spain["minutes_played_total"].fillna(0) >= min_minutes]
    return spain.sort_values("minutes_played_total", ascending=False)
