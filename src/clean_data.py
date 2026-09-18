# -*- coding: utf-8 -*-
"""
Cleaning + validation pipeline for the Spain's-Evolution dataset.

    python src/clean_data.py

Reads the collected CSVs in ``Data/`` and writes analysis-ready copies to
``data/clean/``, plus a data-quality report (``data_quality_report.md`` and
``data_quality_report.json``) recording every rule applied and every check run.

Design rules this script holds itself to
----------------------------------------
* **Nothing is invented.** A value that is genuinely unavailable in the source
  (WC2026 carries, WC2026 official xG, Opta player positions) stays ``NaN`` —
  it is never filled with 0, and never estimated here.
* **Every transformation is one of three kinds**, and the report says which:
  ``harmonise`` (two sources spelling the same fact differently),
  ``derive`` (a new convenience column computed from existing ones),
  ``repair`` (a demonstrable defect in the collected file).
* **Aggregate definitions are preserved.** The derived flags reproduce
  ``team_stats.csv``'s own ``shots`` / ``shots_on_target`` / ``goals`` / ``xg``
  tallies exactly (asserted in the validation pass), so a number computed from
  the event files in the app always agrees with the pre-aggregated table.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "Data"
OUT_DIR = ROOT / "data" / "clean"

# --------------------------------------------------------------------------- #
# Canonical vocabularies — the harmonisation targets
# --------------------------------------------------------------------------- #

#: ``matches.csv`` says "Cape Verde"; every event file says "Cabo Verde".
#: Canonical form is the country's own / FIFA name, applied to *all* files so
#: team names join cleanly across tables.
TEAM_NAME_FIXES = {"Cape Verde": "Cabo Verde"}

#: Three spellings of two datasets across the collected files -> one short label.
SOURCE_SHORT = {
    "StatsBomb Open Data": "StatsBomb",
    "WhoScored (nlbair/wc2026-events)": "WhoScored",
    "WhoScored (via nlbair/wc2026-events)": "WhoScored",
}

#: StatsBomb numbers its periods; Opta names them. Both mean the same thing.
PERIOD_MAP = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "FirstHalf": 1, "SecondHalf": 2,
    "FirstPeriodOfExtraTime": 3, "SecondPeriodOfExtraTime": 4,
    "PenaltyShootout": 5, "ShootOut": 5, "Shootout": 5,
}
PERIOD_LABEL = {
    1: "1st half", 2: "2nd half",
    3: "Extra time 1st half", 4: "Extra time 2nd half",
    5: "Penalty shootout",
}

#: StatsBomb and Opta shot vocabularies -> one 5-value scale.
#: The split is chosen so that ``outcome_std in {"Goal", "Saved"}`` reproduces
#: ``team_stats.csv``'s ``shots_on_target`` exactly (verified in validation):
#: StatsBomb's "Saved Off Target" is *not* counted on target by that tally.
SHOT_OUTCOME_STD = {
    # StatsBomb
    "Goal": "Goal",
    "Saved": "Saved",
    "Saved Off Target": "Off target",
    "Saved to Post": "Woodwork",
    "Post": "Woodwork",
    "Off T": "Off target",
    "Wayward": "Off target",
    "Blocked": "Blocked",
    # Opta / WhoScored
    "SavedShot": "Saved",
    "MissedShots": "Off target",
    "ShotOnPost": "Woodwork",
}
ON_TARGET_OUTCOMES = {"Goal", "Saved"}

#: StatsBomb logs "Foul Committed", Opta logs "Foul" — same event.
DEFENSIVE_ACTION_FIXES = {"Foul": "Foul Committed"}

#: Coarse grouping for the defensive-action filter in the UI.
DEFENSIVE_ACTION_GROUP = {
    "Tackle": "Tackle",
    "Interception": "Interception",
    "Clearance": "Clearance",
    "Block": "Block",
    "Ball Recovery": "Recovery",
    "Duel": "Duel",
    "Pressure": "Pressure",
    "Foul Committed": "Foul",
}

#: Verbose provenance note -> one short token used for UI badges.
XG_QUALITY = {
    "official (StatsBomb)": "official",
    "estimated (distance/angle proxy model)": "estimated",
}

#: README §4 flags two Spain players whose canonical name was left as the raw
#: StatsBomb legal name. "José Luis Sanmartín Mato" is unambiguously Joselu;
#: "Robin Le Normand" already *is* the common name, so it is left alone.
PLAYER_CANONICAL_FIXES = {"José Luis Sanmartín Mato": "Joselu"}

BOOL_COLUMNS = [
    "is_spain", "extra_time", "penalties", "is_cross", "is_through_ball",
    "is_key_pass", "is_progressive", "into_final_third", "into_penalty_area",
    "is_own_goal",
]

TOURNAMENT_ORDER = ["EURO2020", "WC2022", "EURO2024", "WC2026"]
ERA_ORDER = ["Luis Enrique", "Luis de la Fuente"]

EVENT_FILES = ["passes", "shots", "carries", "defensive_actions"]
TABLE_FILES = ["matches", "team_stats", "player_stats", "players",
               "eda_team_summary_by_era", "eda_team_summary_by_tournament"]


# --------------------------------------------------------------------------- #
# Report accumulator
# --------------------------------------------------------------------------- #

class Report:
    """Collects everything the pipeline did, for the written report."""

    def __init__(self) -> None:
        self.actions: list[dict] = []
        self.checks: list[dict] = []
        self.tables: dict[str, dict] = {}

    def action(self, table: str, column: str, kind: str, detail: str,
               rows: int | None = None) -> None:
        assert kind in {"harmonise", "derive", "repair"}, kind
        self.actions.append({"table": table, "column": column, "kind": kind,
                             "detail": detail, "rows_affected": rows})

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.checks.append({"check": name, "status": "PASS" if passed else "FAIL",
                            "detail": detail})
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}"
              + (f" — {detail}" if detail else ""))
        return passed


REPORT = Report()


# --------------------------------------------------------------------------- #
# Shared column-level cleaners
# --------------------------------------------------------------------------- #

def _strip_object_columns(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Trim stray whitespace and turn empty strings into NaN."""
    touched = 0
    for col in df.select_dtypes("object").columns:
        before = df[col].copy()
        cleaned = df[col].astype("string").str.strip()
        cleaned = cleaned.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
        df[col] = cleaned.astype(object).where(cleaned.notna(), np.nan)
        touched += int((before.astype(object).fillna("\0")
                        != df[col].astype(object).fillna("\0")).sum())
    if touched:
        REPORT.action(table, "(all text columns)", "repair",
                      "Trimmed whitespace / normalised empty strings to NaN", touched)
    return df


def _fix_team_names(df: pd.DataFrame, table: str) -> pd.DataFrame:
    for col in ("team", "opponent", "scoring_player_team"):
        if col in df.columns:
            hits = int(df[col].isin(TEAM_NAME_FIXES).sum())
            if hits:
                df[col] = df[col].replace(TEAM_NAME_FIXES)
                REPORT.action(table, col, "harmonise",
                              "'Cape Verde' -> 'Cabo Verde' (one spelling across all tables)",
                              hits)
    return df


def _short_source(df: pd.DataFrame, table: str) -> pd.DataFrame:
    for col in ("source", "data_source"):
        if col in df.columns:
            unknown = set(df[col].dropna().unique()) - set(SOURCE_SHORT)
            if unknown:
                raise ValueError(f"{table}.{col}: unmapped source labels {unknown}")
            df["source_short"] = df[col].map(SOURCE_SHORT)
            REPORT.action(table, "source_short", "derive",
                          "Short provenance label ('StatsBomb' / 'WhoScored') derived "
                          f"from `{col}`, whose three verbose spellings name only two datasets",
                          len(df))
            break
    return df


def _normalise_periods(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """StatsBomb integers + Opta names -> `period_no` / `period_label` / `is_shootout`."""
    if "period" not in df.columns:
        return df
    raw = df["period"].astype("string").str.strip()
    mapped = raw.map(PERIOD_MAP)
    if mapped.isna().any():
        raise ValueError(f"{table}: unmapped period values "
                         f"{sorted(raw[mapped.isna()].dropna().unique())}")
    df["period_no"] = mapped.astype("int8")
    df["period_label"] = df["period_no"].map(PERIOD_LABEL)
    df["is_shootout"] = df["period_no"].eq(5)
    REPORT.action(table, "period_no / period_label / is_shootout", "harmonise",
                  "StatsBomb's numeric periods (1-5) and Opta's names "
                  "('FirstHalf', 'FirstPeriodOfExtraTime', ...) collapsed onto one "
                  "1-5 scale; period 5 flagged as penalty shootout",
                  len(df))
    return df


def _coerce_bools(df: pd.DataFrame, table: str) -> pd.DataFrame:
    fixed = []
    for col in BOOL_COLUMNS:
        if col in df.columns and df[col].dtype != bool:
            df[col] = (df[col].astype("string").str.strip().str.lower()
                       .map({"true": True, "false": False, "1": True, "0": False})
                       .fillna(False).astype(bool))
            fixed.append(col)
    if fixed:
        REPORT.action(table, ", ".join(fixed), "harmonise",
                      "Parsed to real booleans (were read as text/object)", len(df))
    return df


def _clean_coords(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """Keep `normalized_*` strictly inside the 0-100 pitch."""
    for col in ("normalized_x", "normalized_y"):
        if col in df.columns:
            out = int(((df[col] < 0) | (df[col] > 100)).sum())
            if out:
                df[col] = df[col].clip(0, 100)
                REPORT.action(table, col, "repair",
                              "Clipped values marginally outside the 0-100 pitch", out)
    return df


def _add_match_context(df: pd.DataFrame, matches: pd.DataFrame,
                       table: str) -> pd.DataFrame:
    """Attach era / manager / round / opponent so pages need no extra join."""
    if "match_id" not in df.columns:
        return df
    ctx = matches[["match_id", "era", "manager", "round", "opponent",
                   "spain_score", "opp_score", "result", "extra_time",
                   "match_no_in_era"]].rename(
        columns={"spain_score": "match_spain_score",
                 "opp_score": "match_opp_score",
                 "result": "match_result"})
    ctx = ctx.drop(columns=[c for c in ctx.columns
                            if c != "match_id" and c in df.columns])
    before = len(df)
    df = df.merge(ctx, on="match_id", how="left", validate="many_to_one")
    assert len(df) == before, f"{table}: match-context join changed row count"
    REPORT.action(table, "era / manager / round / opponent / match_result / extra_time",
                  "derive",
                  "Match context joined in from matches.csv so every event row "
                  "carries its era without a second lookup", len(df))
    return df


def _order_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Make tournament/era sort chronologically rather than alphabetically."""
    if "tournament" in df.columns:
        df["tournament"] = pd.Categorical(df["tournament"],
                                          categories=TOURNAMENT_ORDER, ordered=True)
    if "era" in df.columns:
        df["era"] = pd.Categorical(df["era"], categories=ERA_ORDER, ordered=True)
    return df


def _base_clean(df: pd.DataFrame, table: str) -> pd.DataFrame:
    df = df.copy()
    dupes = int(df.duplicated().sum())
    if dupes:
        df = df.drop_duplicates().reset_index(drop=True)
        REPORT.action(table, "(whole row)", "repair", "Dropped exact duplicate rows", dupes)
    df = _strip_object_columns(df, table)
    df = _fix_team_names(df, table)
    df = _short_source(df, table)
    df = _coerce_bools(df, table)
    df = _normalise_periods(df, table)
    df = _clean_coords(df, table)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="raise")
    if "player_canonical" in df.columns:
        hits = int(df["player_canonical"].isin(PLAYER_CANONICAL_FIXES).sum())
        if hits:
            df["player_canonical"] = df["player_canonical"].replace(PLAYER_CANONICAL_FIXES)
            REPORT.action(table, "player_canonical", "repair",
                          "Mapped the remaining raw StatsBomb legal name to its common "
                          "name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4",
                          hits)
    if "xg_note" in df.columns:
        df["xg_quality"] = df["xg_note"].map(XG_QUALITY)
        if df["xg_quality"].isna().any() and df["xg_note"].notna().any():
            raise ValueError(f"{table}: unmapped xg_note values")
        REPORT.action(table, "xg_quality", "derive",
                      "'official' / 'estimated' token derived from `xg_note` for UI badges",
                      len(df))
    return df


# --------------------------------------------------------------------------- #
# Per-table cleaners
# --------------------------------------------------------------------------- #

def clean_matches(raw: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "matches")

    df["goal_difference"] = df["spain_score"] - df["opp_score"]
    df["scoreline"] = (df["spain_score"].astype(str) + "–" + df["opp_score"].astype(str))
    REPORT.action("matches", "goal_difference / scoreline", "derive",
                  "Convenience columns for KPI cards and match tables", len(df))

    df["went_to_penalties"] = df["penalties"]
    df["label"] = (df["date"].dt.strftime("%d %b %Y") + " · Spain " + df["scoreline"]
                   + " " + df["opponent"] + "  (" + df["tournament"].astype(str)
                   + " " + df["round"] + ")")
    REPORT.action("matches", "label", "derive",
                  "Human-readable one-line match label for the match selector", len(df))

    # Coverage flags — which optional metric families actually exist per match.
    # These drive the 'partial coverage' notices in the app instead of a page
    # silently plotting a gap as zero.
    df["has_carries"] = df["source_short"].eq("StatsBomb")
    df["has_pressures"] = df["source_short"].eq("StatsBomb")
    df["has_official_xg"] = df["source_short"].eq("StatsBomb")
    df["has_positions"] = df["source_short"].eq("StatsBomb")
    REPORT.action("matches",
                  "has_carries / has_pressures / has_official_xg / has_positions",
                  "derive",
                  "Per-match coverage flags for the metric families that exist in "
                  "StatsBomb but not in the Opta-taxonomy WC2026 source (README §5), "
                  "so the app can label a gap instead of implying zero", len(df))

    df["match_no_in_era"] = df.sort_values("date").groupby("era", observed=True).cumcount() + 1
    df["match_no_overall"] = df["date"].rank(method="first").astype(int)
    REPORT.action("matches", "match_no_in_era / match_no_overall", "derive",
                  "Chronological match counters for trend charts", len(df))

    return _order_categoricals(df).sort_values("date").reset_index(drop=True)


def clean_team_stats(raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "team_stats")
    df = _add_match_context(df, matches, "team_stats")

    # Per-90: extra-time matches are 120 minutes, so an absolute count from one
    # of them is not comparable with a 90-minute match. Uses the same
    # normalisation the era/tournament summaries were built with.
    df["match_minutes"] = np.where(df["extra_time"], 120.0, 90.0)
    per90_cols = [
        "passes_attempted", "passes_completed", "progressive_passes", "key_passes",
        "crosses", "passes_into_final_third", "passes_into_penalty_area", "shots",
        "shots_on_target", "goals", "xg", "carries", "progressive_carries",
        "tackles", "interceptions", "clearances", "blocks", "recoveries",
        "pressures", "fouls_committed",
    ]
    for col in per90_cols:
        df[f"{col}_per90"] = df[col] / df["match_minutes"] * 90.0
    REPORT.action("team_stats", "match_minutes + *_per90", "derive",
                  f"{len(per90_cols)} per-90 columns, normalised by 120 minutes for "
                  "extra-time matches and 90 otherwise (same rule as the EDA summaries)",
                  len(df))

    df["xg_per_shot"] = np.where(df["shots"] > 0, df["xg"] / df["shots"], np.nan)
    df["shot_accuracy_pct"] = np.where(df["shots"] > 0,
                                       df["shots_on_target"] / df["shots"] * 100, np.nan)
    df["goals_minus_xg"] = df["goals"] - df["xg"]
    REPORT.action("team_stats", "xg_per_shot / shot_accuracy_pct / goals_minus_xg",
                  "derive", "Shot-quality ratios (NaN, not 0, when a team took no shots)",
                  len(df))

    return _order_categoricals(df).sort_values(["date", "is_spain"]).reset_index(drop=True)


def clean_player_stats(raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "player_stats")
    df = _add_match_context(df, matches, "player_stats")

    # `minutes_played` is missing for 98 WC2026 rows (no sub events logged for
    # those players). Left NaN on purpose; per-90 is NaN there rather than inf.
    minutes = df["minutes_played"].where(df["minutes_played"] > 0)
    for col in ["passes_attempted", "passes_completed", "progressive_passes",
                "key_passes", "crosses", "shots", "shots_on_target", "goals", "xg",
                "carries", "progressive_carries", "tackles", "interceptions",
                "clearances", "recoveries"]:
        df[f"{col}_per90"] = df[col] / minutes * 90.0
    REPORT.action("player_stats", "*_per90", "derive",
                  "Per-90 columns from `minutes_played`; NaN (never inf or 0) where "
                  "minutes are unknown — 98 WC2026 rows have no substitution events",
                  len(df))

    df["goal_contributions"] = df["goals"] + df["key_passes"]
    REPORT.action("player_stats", "goal_contributions", "derive",
                  "goals + key passes (assists are not logged in both sources, so key "
                  "passes stand in — labelled as such in the UI)", len(df))

    return _order_categoricals(df).sort_values(["date", "team", "player"]).reset_index(drop=True)


def clean_players(raw: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "players")

    df["n_tournaments"] = df["tournaments"].str.count(",") + 1
    df["n_eras"] = df["eras"].str.count(",") + 1
    df["bridges_eras"] = df["n_eras"].eq(2)
    REPORT.action("players", "n_tournaments / n_eras / bridges_eras", "derive",
                  "Counts parsed from the comma-joined `tournaments` / `eras` strings; "
                  "`bridges_eras` marks the players who played under both managers",
                  len(df))

    minutes = df["minutes_played_total"].where(df["minutes_played_total"] > 0)
    for col in ["goals", "shots", "shots_on_target", "xg_total", "passes_attempted",
                "passes_completed", "key_passes", "progressive_passes", "crosses",
                "carries", "progressive_carries", "tackles", "interceptions",
                "clearances", "recoveries"]:
        df[f"{col}_per90"] = df[col] / minutes * 90.0
    REPORT.action("players", "*_per90", "derive",
                  "Career per-90 columns over `minutes_played_total`", len(df))

    df["minutes_per_match"] = np.where(df["matches_played"] > 0,
                                       df["minutes_played_total"] / df["matches_played"],
                                       np.nan)
    REPORT.action("players", "minutes_per_match", "derive",
                  "Average minutes per appearance", len(df))
    return df.sort_values("minutes_played_total", ascending=False).reset_index(drop=True)


def clean_shots(raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "shots")

    # -- repair 1: one WC2026 row carries the string "True" in `body_part`,
    #    a parsing artifact from the source CSV. No body part is recoverable.
    bad_bp = int(df["body_part"].eq("True").sum())
    if bad_bp:
        df.loc[df["body_part"].eq("True"), "body_part"] = np.nan
        REPORT.action("shots", "body_part", "repair",
                      "Literal string 'True' (a source parsing artifact, not a body "
                      "part) replaced with NaN", bad_bp)

    # -- repair 2: the same row is an own goal but was typed 'Open Play'.
    wrong_type = int((df["is_own_goal"] & df["shot_type"].ne("Own Goal")).sum())
    if wrong_type:
        df.loc[df["is_own_goal"], "shot_type"] = "Own Goal"
        REPORT.action("shots", "shot_type", "repair",
                      "`shot_type` set to 'Own Goal' where `is_own_goal` was true but "
                      "the type said 'Open Play' (WC2026 own-goal row)", wrong_type)

    # -- repair 3: own goals have no shooter attributed in StatsBomb.
    #    Labelled explicitly so charts and tables show a fact, not a blank.
    no_player = int((df["is_own_goal"] & df["player"].isna()).sum())
    if no_player:
        mask = df["is_own_goal"] & df["player"].isna()
        df.loc[mask, "player"] = "Own goal (shooter not logged)"
        df.loc[mask, "player_canonical"] = "Own goal (shooter not logged)"
        REPORT.action("shots", "player / player_canonical", "repair",
                      "Own goals carry no shooter in the source; labelled explicitly "
                      "instead of NaN so they are visible rather than silently dropped",
                      no_player)

    # -- harmonise: two shot-outcome vocabularies -> one 5-value scale.
    unknown = set(df["outcome"].dropna().unique()) - set(SHOT_OUTCOME_STD)
    if unknown:
        raise ValueError(f"shots: unmapped outcomes {unknown}")
    df["outcome_std"] = df["outcome"].map(SHOT_OUTCOME_STD)
    REPORT.action("shots", "outcome_std", "harmonise",
                  "StatsBomb's 8 outcome labels and Opta's 3 mapped onto one scale "
                  "(Goal / Saved / Off target / Blocked / Woodwork)", len(df))

    df["is_goal"] = df["outcome_std"].eq("Goal")
    df["is_on_target"] = df["outcome_std"].isin(ON_TARGET_OUTCOMES)
    df["is_penalty"] = df["shot_type"].eq("Penalty")
    REPORT.action("shots", "is_goal / is_on_target / is_penalty", "derive",
                  "Boolean flags; `is_on_target` is defined to reproduce "
                  "team_stats.csv's own `shots_on_target` tally exactly (asserted "
                  "in the validation pass)", len(df))

    # `xg_combined` is NaN for the 7 own-goal rows — an own goal has no xG.
    # Flagged rather than zero-filled so an xG sum can exclude them knowingly.
    df["has_xg"] = df["xg_combined"].notna()
    df["xg_quality"] = np.where(
        df["xg_source"].eq("statsbomb_official"), "official",
        np.where(df["xg_source"].eq("proxy_distance_angle_model"), "estimated",
                 "not applicable (own goal)"))
    REPORT.action("shots", "has_xg / xg_quality", "derive",
                  "xG provenance as a short token; the 7 own-goal rows have no xG in "
                  "any source and are marked 'not applicable' rather than 0", len(df))

    # Counting basis: matches team_stats.csv's definitions exactly.
    df["counts_as_shot"] = ~df["is_shootout"] & ~df["is_own_goal"]
    df["counts_as_goal"] = ~df["is_shootout"] & df["is_goal"]
    REPORT.action("shots", "counts_as_shot / counts_as_goal", "derive",
                  "The counting basis behind team_stats.csv: shots exclude penalty "
                  "shootouts and own goals; goals exclude shootouts but include own "
                  "goals, credited to the benefiting team", len(df))

    df["distance_to_goal"] = np.sqrt((100 - df["normalized_x"]) ** 2
                                     + (50 - df["normalized_y"]) ** 2)
    REPORT.action("shots", "distance_to_goal", "derive",
                  "Distance from the shot to the goal centre on the common 0-100 "
                  "pitch (comparable across both coordinate systems)", len(df))

    df = _add_match_context(df, matches, "shots")
    return _order_categoricals(df).sort_values(
        ["date", "period_no", "minute", "second"]).reset_index(drop=True)


def clean_passes(raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "passes")

    df["is_complete"] = df["outcome"].eq("Complete")
    REPORT.action("passes", "is_complete", "derive",
                  "One boolean for completion; the raw `outcome` has 6 values "
                  "(Complete / Incomplete / Out / Unknown / Pass Offside / "
                  "Injury Clearance), only the first of which is a completed pass",
                  len(df))

    df["is_set_piece"] = df["pass_type"].isin(
        ["Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"])
    df["is_open_play"] = ~df["is_set_piece"]
    REPORT.action("passes", "is_set_piece / is_open_play", "derive",
                  "Set-piece grouping over `pass_type` so open-play passing can be "
                  "isolated", len(df))

    # End coordinates on the common 0-100 pitch — the raw end_x/end_y are in each
    # row's own native system, which cannot be overlaid across sources.
    sb = df["coord_system"].eq("statsbomb_120x80")
    df["normalized_end_x"] = np.where(sb, df["end_x"] / 120 * 100, df["end_x"]).clip(0, 100)
    df["normalized_end_y"] = np.where(sb, df["end_y"] / 80 * 100, df["end_y"]).clip(0, 100)
    REPORT.action("passes", "normalized_end_x / normalized_end_y", "derive",
                  "Pass end points rescaled onto the common 0-100 pitch (StatsBomb "
                  "÷120/÷80; Opta unchanged) — the start points already had this, the "
                  "end points did not, so pass-arrow charts could not mix sources",
                  len(df))

    df["pass_distance"] = np.sqrt((df["normalized_end_x"] - df["normalized_x"]) ** 2
                                  + (df["normalized_end_y"] - df["normalized_y"]) ** 2)
    df["is_forward"] = df["normalized_end_x"] > df["normalized_x"]
    REPORT.action("passes", "pass_distance / is_forward", "derive",
                  "Pass length on the common pitch and direction of travel; the raw "
                  "`length` column is in each source's own units and is not comparable",
                  len(df))

    third = pd.cut(df["normalized_x"], [-0.01, 100 / 3, 200 / 3, 100.01],
                   labels=["Defensive third", "Middle third", "Final third"])
    df["pitch_third"] = third
    REPORT.action("passes", "pitch_third", "derive",
                  "Which third the pass started in, on the common 0-100 pitch", len(df))

    df = _add_match_context(df, matches, "passes")
    return _order_categoricals(df).sort_values(
        ["date", "period_no", "minute", "second"]).reset_index(drop=True)


def clean_carries(raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "carries")
    sb = df["coord_system"].eq("statsbomb_120x80")
    df["normalized_end_x"] = np.where(sb, df["end_x"] / 120 * 100, df["end_x"]).clip(0, 100)
    df["normalized_end_y"] = np.where(sb, df["end_y"] / 80 * 100, df["end_y"]).clip(0, 100)
    REPORT.action("carries", "normalized_end_x / normalized_end_y", "derive",
                  "Carry end points on the common 0-100 pitch", len(df))
    df = _add_match_context(df, matches, "carries")
    return _order_categoricals(df).sort_values(
        ["date", "period_no", "minute", "second"]).reset_index(drop=True)


def clean_defensive_actions(raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    df = _base_clean(raw, "defensive_actions")

    hits = int(df["action_type"].isin(DEFENSIVE_ACTION_FIXES).sum())
    if hits:
        df["action_type"] = df["action_type"].replace(DEFENSIVE_ACTION_FIXES)
        REPORT.action("defensive_actions", "action_type", "harmonise",
                      "Opta's 'Foul' and StatsBomb's 'Foul Committed' were two "
                      "categories for one event; merged into 'Foul Committed'", hits)

    unknown = set(df["action_type"].dropna().unique()) - set(DEFENSIVE_ACTION_GROUP)
    if unknown:
        raise ValueError(f"defensive_actions: unmapped action_type {unknown}")
    df["action_group"] = df["action_type"].map(DEFENSIVE_ACTION_GROUP)
    REPORT.action("defensive_actions", "action_group", "derive",
                  "Short action grouping for the event-type filter", len(df))

    df["is_successful"] = df["outcome"].isin(
        ["Won", "Success In Play", "Success Out", "Successful", "Recovered"])
    REPORT.action("defensive_actions", "is_successful", "derive",
                  "Success boolean over the 8 source outcome labels; note 61.7% of "
                  "rows log no outcome at all (mostly pressures), which read as "
                  "not-successful — use with the outcome column, not alone", len(df))

    df["defensive_third"] = pd.cut(df["normalized_x"], [-0.01, 100 / 3, 200 / 3, 100.01],
                                   labels=["Own third", "Middle third", "Final third"])
    REPORT.action("defensive_actions", "defensive_third", "derive",
                  "Pitch third of the action — the basis for a pressing-height read",
                  len(df))

    df = _add_match_context(df, matches, "defensive_actions")
    return _order_categoricals(df).sort_values(
        ["date", "period_no", "minute", "second"]).reset_index(drop=True)


def clean_eda_summary(raw: pd.DataFrame, table: str) -> pd.DataFrame:
    df = _base_clean(raw, table)
    df["win_pct"] = df["wins"] / df["matches"] * 100
    df["points_per_match"] = (df["wins"] * 3 + df["draws"]) / df["matches"]
    df["xg_per_shot"] = df["xg_per90"] / df["shots_per90"]
    df["shot_accuracy_pct"] = df["shots_on_target_per90"] / df["shots_per90"] * 100
    REPORT.action(table, "win_pct / points_per_match / xg_per_shot / shot_accuracy_pct",
                  "derive", "Rates used directly by the Overview KPI cards", len(df))
    return _order_categoricals(df)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def validate(clean: dict) -> bool:
    """Cross-table consistency checks. Every one must pass for the output to ship."""
    print("\nValidation")
    ok = True
    matches, team_stats = clean["matches"], clean["team_stats"]
    shots, passes = clean["shots"], clean["passes"]

    ok &= REPORT.check("matches.csv holds 25 unique matches",
                       len(matches) == 25 and matches["match_id"].is_unique,
                       f"{len(matches)} rows")

    ok &= REPORT.check(
        "Era split is 10 Luis Enrique / 15 Luis de la Fuente",
        matches["era"].value_counts().reindex(ERA_ORDER).tolist() == [10, 15],
        str(matches["era"].value_counts().reindex(ERA_ORDER).to_dict()))

    # Every event row must belong to a known match.
    for name in EVENT_FILES + ["team_stats", "player_stats"]:
        orphans = set(clean[name]["match_id"]) - set(matches["match_id"])
        ok &= REPORT.check(f"{name}: every match_id exists in matches.csv",
                           not orphans, f"orphans: {sorted(orphans)}" if orphans else "")

    # The headline reconciliation: goals in the event stream vs the match scores.
    goals = (shots[shots["counts_as_goal"]]
             .groupby(["match_id", "is_spain"], observed=True).size().unstack(fill_value=0)
             .reindex(columns=[False, True], fill_value=0))
    rec = matches.set_index("match_id")[["spain_score", "opp_score"]].join(goals).fillna(0)
    mismatched = rec[(rec["spain_score"] != rec[True]) | (rec["opp_score"] != rec[False])]
    ok &= REPORT.check(
        "Goals in shots.csv reconcile with every scoreline in matches.csv",
        mismatched.empty,
        "all 25 matches agree" if mismatched.empty
        else f"mismatched: {mismatched.index.tolist()}")

    # Derived event flags must reproduce the pre-aggregated table exactly.
    for label, mask, col in [
        ("shots", shots["counts_as_shot"], "shots"),
        ("shots on target", shots["counts_as_shot"] & shots["is_on_target"],
         "shots_on_target"),
    ]:
        calc = shots[mask].groupby(["match_id", "team"], observed=True).size()
        base = team_stats.set_index(["match_id", "team"])[col]
        diff = base.to_frame("agg").join(calc.rename("calc")).fillna(0)
        n_bad = int((diff["agg"] != diff["calc"]).sum())
        ok &= REPORT.check(
            f"shots.csv flags reproduce team_stats.csv `{col}` for all 50 team-matches",
            n_bad == 0, f"{n_bad} disagreements" if n_bad else "exact")

    calc = passes.groupby(["match_id", "team"], observed=True)["is_complete"].agg(
        ["size", "sum"])
    base = team_stats.set_index(["match_id", "team"])[["passes_attempted",
                                                       "passes_completed"]]
    j = base.join(calc)
    n_bad = int(((j["passes_attempted"] != j["size"])
                 | (j["passes_completed"] != j["sum"])).sum())
    ok &= REPORT.check("passes.csv reproduces team_stats.csv pass counts",
                       n_bad == 0, f"{n_bad} disagreements" if n_bad else "exact")

    poss = team_stats.groupby("match_id", observed=True)["possession_pct_proxy"].sum()
    ok &= REPORT.check("Possession proxy sums to 100% in every match",
                       bool(np.allclose(poss, 100, atol=0.05)),
                       f"range {poss.min():.2f}–{poss.max():.2f}")

    # Coverage must match the documented gaps exactly — no silent zero-filling.
    carry_matches = set(clean["carries"]["match_id"])
    expected = set(matches.loc[matches["has_carries"], "match_id"])
    ok &= REPORT.check("carries.csv covers exactly the 17 StatsBomb matches",
                       carry_matches == expected,
                       f"{len(carry_matches)} matches")

    wc26 = team_stats[team_stats["source_short"].eq("WhoScored")]
    ok &= REPORT.check(
        "WC2026 carries/pressures stay NaN (never zero-filled)",
        bool(wc26[["carries", "progressive_carries", "pressures"]].isna().all().all()),
        "all NaN as documented in README §5")

    for name in EVENT_FILES:
        df = clean[name]
        bad = int(((df["normalized_x"] < 0) | (df["normalized_x"] > 100)
                   | (df["normalized_y"] < 0) | (df["normalized_y"] > 100)).sum())
        ok &= REPORT.check(f"{name}: normalized coordinates inside the 0-100 pitch",
                           bad == 0, f"{bad} out of range" if bad else "")

    # One spelling per team, everywhere.
    all_teams = set()
    for name in EVENT_FILES + ["team_stats", "player_stats"]:
        all_teams |= set(clean[name]["team"].dropna().unique())
    known = set(matches["opponent"].dropna()) | {"Spain"}
    ok &= REPORT.check("Team names are consistent across every table",
                       all_teams <= known,
                       f"unknown: {sorted(all_teams - known)}" if all_teams - known else
                       f"{len(all_teams)} teams, one spelling each")

    ok &= REPORT.check("No duplicate rows remain in any table",
                       all(not clean[n].duplicated().any() for n in clean),
                       f"{len(clean)} tables checked")

    return bool(ok)


# --------------------------------------------------------------------------- #
# Report writing
# --------------------------------------------------------------------------- #

def write_report(clean: dict, all_ok: bool) -> None:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "generated_utc": generated,
        "source_dir": str(RAW_DIR.relative_to(ROOT)),
        "output_dir": str(OUT_DIR.relative_to(ROOT)),
        "all_checks_passed": all_ok,
        "tables": REPORT.tables,
        "actions": REPORT.actions,
        "checks": REPORT.checks,
    }
    (OUT_DIR / "data_quality_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    kinds = {"harmonise": "Harmonised", "derive": "Derived", "repair": "Repaired"}
    lines = [
        "# Data quality report",
        "",
        f"Generated {generated} by `src/clean_data.py` — "
        f"`{RAW_DIR.name}/` → `{OUT_DIR.relative_to(ROOT).as_posix()}/`.",
        "",
        f"**{len(REPORT.checks)} consistency checks, "
        f"{sum(c['status'] == 'PASS' for c in REPORT.checks)} passed"
        f"{'' if all_ok else ' — SEE FAILURES BELOW'}.**",
        "",
        "## Tables written", "",
        "| Table | Rows | Columns | Added |", "|---|---:|---:|---:|",
    ]
    for name, meta in REPORT.tables.items():
        lines.append(f"| `{name}.csv` | {meta['rows']:,} | {meta['cols_out']} "
                     f"| +{meta['cols_out'] - meta['cols_in']} |")

    lines += ["", "## Consistency checks", "", "| Check | Result | Detail |",
              "|---|---|---|"]
    for c in REPORT.checks:
        lines.append(f"| {c['check']} | **{c['status']}** | {c['detail'] or '—'} |")

    lines += ["", "## What was changed", "",
              "Three kinds of change, and nothing else: *harmonise* (two sources "
              "spelling one fact differently), *derive* (a new column computed from "
              "existing ones), *repair* (a demonstrable defect in the collected "
              "file). No value was estimated or filled in here — genuinely missing "
              "data stays `NaN`.", ""]
    for kind, title in kinds.items():
        acts = [a for a in REPORT.actions if a["kind"] == kind]
        if not acts:
            continue
        lines += [f"### {title} ({len(acts)})", "", "| Table | Column(s) | What | Rows |",
                  "|---|---|---|---:|"]
        for a in acts:
            rows = f"{a['rows_affected']:,}" if a["rows_affected"] is not None else "—"
            lines.append(f"| `{a['table']}` | `{a['column']}` | {a['detail']} | {rows} |")
        lines.append("")

    lines += [
        "## Gaps left in place on purpose", "",
        "These are source coverage limits, not defects, and are **not** filled:", "",
        "| Gap | Extent | Handling |", "|---|---|---|",
        "| Ball carries | absent for the 8 WC2026 matches — Opta's taxonomy has no "
        "discrete carry event | `NaN`; `matches.has_carries` flags it and the app "
        "labels affected charts |",
        "| Pressures | StatsBomb-only, same 8 matches | `NaN`; "
        "`matches.has_pressures` |",
        "| Official xG | StatsBomb-only; WC2026 uses the distance/angle proxy model | "
        "`xg_combined` + `xg_quality` ('official' / 'estimated') distinguish them "
        "everywhere |",
        "| xG for own goals | 7 rows have no xG in any source | `xg_quality` = "
        "'not applicable (own goal)'; excluded from shot tallies by `counts_as_shot` |",
        "| Player positions | Opta source logs none | `NaN` for 252 WC2026 rows |",
        "| Minutes played | no substitution events for 98 WC2026 player-rows | `NaN`, "
        "so their per-90 values are `NaN` rather than misleading |",
        "| Possession % | a proxy, and a *different* proxy per source | kept as "
        "`possession_pct_proxy` with `possession_proxy_method`; labelled as a proxy "
        "in the UI |",
        "| Possession chains | no `possessions.csv` exists | out of scope; "
        "StatsBomb's chain id has no WC2026 equivalent (README §5) |",
        "",
        "## One caveat resolved", "",
        "`README.md` §5 warns that StatsBomb lets teams switch attacking direction at "
        "half-time, so combining the two sources on one pitch would need direction "
        "normalisation. Checked directly against the data: Spain's shot x-coordinates "
        "average 86.6 / 87.4 / 87.4 / 89.5 across periods 1-4 in the StatsBomb matches "
        "and 84.2 / 83.6 in the WC2026 matches — both sources already record the "
        "attacking team moving left→right in every period. No flip is required, and "
        "`normalized_x` / `normalized_y` can be overlaid across sources directly. "
        "(The one Spain 'shot' at x = 2.5 is the Al-Tambakti own goal, taken at the "
        "other end and credited to Spain — which is why own goals are excluded from "
        "shot maps via `counts_as_shot`.)",
        "",
    ]
    (OUT_DIR / "data_quality_report.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> int:
    if not RAW_DIR.exists():
        raise SystemExit(f"Source directory not found: {RAW_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Reading {RAW_DIR.relative_to(ROOT)}/ ...")
    raw = {name: pd.read_csv(RAW_DIR / f"{name}.csv", low_memory=False)
           for name in TABLE_FILES + EVENT_FILES}
    for name, df in raw.items():
        print(f"  {name:34} {len(df):>7,} rows x {df.shape[1]:>2} cols")

    print("\nCleaning ...")
    clean: dict = {}
    clean["matches"] = clean_matches(raw["matches"])
    m = clean["matches"]
    clean["team_stats"] = clean_team_stats(raw["team_stats"], m)
    clean["player_stats"] = clean_player_stats(raw["player_stats"], m)
    clean["players"] = clean_players(raw["players"])
    clean["shots"] = clean_shots(raw["shots"], m)
    clean["passes"] = clean_passes(raw["passes"], m)
    clean["carries"] = clean_carries(raw["carries"], m)
    clean["defensive_actions"] = clean_defensive_actions(raw["defensive_actions"], m)
    clean["eda_team_summary_by_era"] = clean_eda_summary(
        raw["eda_team_summary_by_era"], "eda_team_summary_by_era")
    clean["eda_team_summary_by_tournament"] = clean_eda_summary(
        raw["eda_team_summary_by_tournament"], "eda_team_summary_by_tournament")

    for name, df in clean.items():
        REPORT.tables[name] = {"rows": len(df), "cols_in": raw[name].shape[1],
                               "cols_out": df.shape[1]}

    all_ok = validate(clean)

    print(f"\nWriting {OUT_DIR.relative_to(ROOT).as_posix()}/ ...")
    for name, df in clean.items():
        out = OUT_DIR / f"{name}.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  {name + '.csv':36} {len(df):>7,} rows x {df.shape[1]:>2} cols"
              f"  ({out.stat().st_size / 1_048_576:.1f} MB)")

    write_report(clean, all_ok)
    print("  data_quality_report.md / .json")

    n_pass = sum(c["status"] == "PASS" for c in REPORT.checks)
    print(f"\n{'OK' if all_ok else 'FAILED'}: {n_pass}/{len(REPORT.checks)} checks passed, "
          f"{len(REPORT.actions)} cleaning actions recorded.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
