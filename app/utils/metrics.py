# -*- coding: utf-8 -*-
"""
All aggregation and normalisation. No disk reads, no chart objects, no widgets —
pages and chart builders call these with already-loaded frames.

Two rules run through everything here:

* **Per-90, not absolute.** Five of the 25 matches went to extra time, so a raw
  count from one of them is not comparable with a 90-minute match. Absolute
  totals are only ever shown when they are the point (goals scored, matches won).
* **A gap is never a zero.** ``NaN`` propagates. If World Cup 2026 has no carry
  data, a carries mean over a selection including WC 2026 covers only the matches
  that have it, and ``coverage()`` reports how many that was so the page can say so.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from . import config as C

#: Metrics where a larger number is the better outcome. Used to colour delta
#: chips; anything absent is treated as directional-only (neutral framing).
HIGHER_IS_BETTER = {
    "goals", "goals_per90", "shots", "shots_per90", "shots_on_target",
    "shots_on_target_per90", "xg", "xg_per90", "xg_per_shot", "pass_pct",
    "passes_completed_per90", "progressive_passes_per90", "key_passes_per90",
    "passes_into_final_third_per90", "passes_into_penalty_area_per90",
    "progressive_carries_per90", "shot_accuracy_pct", "win_pct",
    "points_per_match", "possession_pct_proxy",
}

#: Display names and units, so a metric is labelled the same way on every page.
METRIC_META = {
    "possession_pct_proxy": ("Possession (proxy)", "%", 1),
    "passes_attempted_per90": ("Passes attempted", "/90", 0),
    "passes_completed_per90": ("Passes completed", "/90", 0),
    "pass_pct": ("Pass completion", "%", 1),
    "progressive_passes_per90": ("Progressive passes", "/90", 1),
    "key_passes_per90": ("Key passes", "/90", 1),
    "crosses_per90": ("Crosses", "/90", 1),
    "passes_into_final_third_per90": ("Passes into final third", "/90", 1),
    "passes_into_penalty_area_per90": ("Passes into the box", "/90", 1),
    "shots_per90": ("Shots", "/90", 1),
    "shots_on_target_per90": ("Shots on target", "/90", 1),
    "goals_per90": ("Goals", "/90", 2),
    "xg_per90": ("Expected goals", "/90", 2),
    "xg_per_shot": ("xG per shot", "", 3),
    "shot_accuracy_pct": ("Shot accuracy", "%", 1),
    "carries_per90": ("Ball carries", "/90", 0),
    "progressive_carries_per90": ("Progressive carries", "/90", 1),
    "tackles_per90": ("Tackles", "/90", 1),
    "interceptions_per90": ("Interceptions", "/90", 1),
    "clearances_per90": ("Clearances", "/90", 1),
    "blocks_per90": ("Blocks", "/90", 1),
    "recoveries_per90": ("Ball recoveries", "/90", 1),
    "pressures_per90": ("Pressures", "/90", 1),
    "fouls_committed_per90": ("Fouls committed", "/90", 1),
}

#: Metric families that only exist in the StatsBomb-covered matches.
STATSBOMB_ONLY = {"carries", "carries_per90", "progressive_carries",
                  "progressive_carries_per90", "pressures", "pressures_per90"}


def label_of(metric: str) -> str:
    return METRIC_META.get(metric, (metric.replace("_", " ").capitalize(), "", 1))[0]


def unit_of(metric: str) -> str:
    return METRIC_META.get(metric, ("", "", 1))[1]


def decimals_of(metric: str) -> int:
    return METRIC_META.get(metric, ("", "", 1))[2]


def higher_is_better(metric: str) -> bool:
    return metric in HIGHER_IS_BETTER


# --------------------------------------------------------------------------- #
# Change between two values
# --------------------------------------------------------------------------- #

def pct_change(old, new) -> Optional[float]:
    """Percentage change, or ``None`` when it isn't defined."""
    if old is None or new is None or pd.isna(old) or pd.isna(new) or old == 0:
        return None
    return (new - old) / abs(old) * 100.0


def coverage(series: pd.Series) -> tuple:
    """``(n_present, n_total)`` — how much of a selection a metric actually covers."""
    return int(series.notna().sum()), int(len(series))


def coverage_note(series: pd.Series, what: str = "matches") -> str:
    """A sentence naming the gap, or empty when the metric is fully covered."""
    present, total = coverage(series)
    if present == total or total == 0:
        return ""
    return (f"Covers {present} of {total} {what} — the rest carry no value for this "
            f"metric in the source, and are excluded rather than counted as zero.")


# --------------------------------------------------------------------------- #
# Spain team-level aggregation
# --------------------------------------------------------------------------- #

def spain_rows(team_stats: pd.DataFrame) -> pd.DataFrame:
    return team_stats[team_stats["is_spain"]].copy()


def opponent_rows(team_stats: pd.DataFrame) -> pd.DataFrame:
    return team_stats[~team_stats["is_spain"]].copy()


def aggregate(df: pd.DataFrame, by: str, metrics: Sequence[str],
              how: str = "mean") -> pd.DataFrame:
    """Group ``df`` by one column and reduce ``metrics``.

    ``mean`` over already-per-90 columns is the right reduction: each match
    contributes equally regardless of whether it ran 90 or 120 minutes.
    ``NaN`` inputs are skipped, never zero-filled.
    """
    cols = [m for m in metrics if m in df.columns]
    if not cols or df.empty:
        return pd.DataFrame(columns=[by] + list(metrics))
    grouped = df.groupby(by, observed=True)[cols].agg(how)
    return grouped.reset_index()


def era_profile(team_stats: pd.DataFrame, metrics: Sequence[str]) -> pd.DataFrame:
    """One row per era, with the per-match mean of each metric."""
    spain = spain_rows(team_stats)
    out = aggregate(spain, "era", metrics)
    out["era"] = pd.Categorical(out["era"], categories=C.ERAS, ordered=True)
    return out.sort_values("era")


def tournament_profile(team_stats: pd.DataFrame,
                       metrics: Sequence[str]) -> pd.DataFrame:
    """One row per tournament, chronological, tagged with its era."""
    spain = spain_rows(team_stats)
    out = aggregate(spain, "tournament", metrics)
    out["tournament"] = pd.Categorical(out["tournament"], categories=C.TOURNAMENTS,
                                       ordered=True)
    out = out.sort_values("tournament")
    out["era"] = out["tournament"].map(C.TOURNAMENT_ERA)
    out["label"] = out["tournament"].map(C.TOURNAMENT_LABEL)
    return out


def era_comparison(team_stats: pd.DataFrame,
                   metrics: Sequence[str]) -> pd.DataFrame:
    """Tidy era-vs-era table: one row per metric, with the change between them.

    This is the table behind the era comparison chart *and* its table view, so
    the chart and the numbers can never drift apart.
    """
    spain = spain_rows(team_stats)
    rows = []
    for metric in metrics:
        if metric not in spain.columns:
            continue
        enrique = spain.loc[spain["era"] == C.ERAS[0], metric]
        fuente = spain.loc[spain["era"] == C.ERAS[1], metric]
        a, b = enrique.mean(), fuente.mean()
        present_a, total_a = coverage(enrique)
        present_b, total_b = coverage(fuente)
        rows.append({
            "metric": metric,
            "label": label_of(metric),
            "unit": unit_of(metric),
            "decimals": decimals_of(metric),
            C.ERAS[0]: a,
            C.ERAS[1]: b,
            "change_pct": pct_change(a, b),
            "higher_is_better": higher_is_better(metric),
            "matches_enrique": f"{present_a}/{total_a}",
            "matches_fuente": f"{present_b}/{total_b}",
            "partial": present_a < total_a or present_b < total_b,
        })
    return pd.DataFrame(rows)


def match_timeline(team_stats: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Spain's per-match values for one metric, in date order, tagged by era.

    ``metric`` is only appended when it is not already one of the context
    columns — selecting it twice would return a frame with two identically
    named columns, which cannot be rendered as a table.
    """
    spain = spain_rows(team_stats).sort_values("date")
    cols = ["match_id", "date", "tournament", "era", "opponent", "round",
            "match_result", "match_spain_score", "match_opp_score"]
    cols = [c for c in cols if c in spain.columns]
    if metric in spain.columns and metric not in cols:
        cols = cols + [metric]
    out = spain[cols].copy()
    out["n"] = range(1, len(out) + 1)
    return out


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #

def record(matches: pd.DataFrame) -> dict:
    """W/D/L, goals and points for a set of matches."""
    if matches.empty:
        return {"matches": 0, "W": 0, "D": 0, "L": 0, "gf": 0, "ga": 0,
                "gd": 0, "win_pct": np.nan, "ppm": np.nan}
    counts = matches["result"].value_counts()
    wins, draws, losses = (int(counts.get(k, 0)) for k in "WDL")
    gf, ga = int(matches["spain_score"].sum()), int(matches["opp_score"].sum())
    return {
        "matches": len(matches), "W": wins, "D": draws, "L": losses,
        "gf": gf, "ga": ga, "gd": gf - ga,
        "win_pct": wins / len(matches) * 100,
        "ppm": (wins * 3 + draws) / len(matches),
    }


def record_by_era(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for era in C.ERAS:
        subset = matches[matches["era"] == era]
        if subset.empty:
            continue
        rows.append({"era": era, **record(subset)})
    return pd.DataFrame(rows)


def record_by_tournament(matches: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code in C.TOURNAMENTS:
        subset = matches[matches["tournament"] == code]
        if subset.empty:
            continue
        rows.append({"tournament": code, "label": C.TOURNAMENT_LABEL[code],
                     "era": C.TOURNAMENT_ERA[code], **record(subset)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Event-level aggregation
# --------------------------------------------------------------------------- #

def per90_from_events(events: pd.DataFrame, matches: pd.DataFrame,
                      by: str = "era") -> pd.DataFrame:
    """Turn an event count into a per-90 rate over the minutes actually played.

    Minutes come from ``matches`` (120 for an extra-time match, 90 otherwise),
    counted only over the matches present in ``events`` — so filtering to a
    subset of matches rescales the denominator with it.
    """
    if events.empty:
        return pd.DataFrame(columns=[by, "events", "matches", "minutes", "per90"])
    minutes = matches.copy()
    minutes["minutes"] = np.where(minutes["extra_time"], 120.0, 90.0)
    minutes = minutes[minutes["match_id"].isin(events["match_id"].unique())]
    denom = minutes.groupby(by, observed=True).agg(
        matches=("match_id", "nunique"), minutes=("minutes", "sum"))
    counts = events.groupby(by, observed=True).size().rename("events")
    out = denom.join(counts, how="left").fillna({"events": 0}).reset_index()
    out["per90"] = out["events"] / out["minutes"] * 90.0
    return out


def shot_summary(shots: pd.DataFrame) -> dict:
    """Headline shot numbers on the documented counting basis.

    ``counts_as_shot`` excludes penalty-shootout kicks and own goals, matching
    how ``team_stats.csv`` counts — so a figure derived here always agrees with
    the pre-aggregated table.
    """
    countable = shots[shots["counts_as_shot"]] if "counts_as_shot" in shots else shots
    n = len(countable)
    on_target = int(countable["is_on_target"].sum()) if "is_on_target" in countable else 0
    xg = countable["xg_combined"].sum(min_count=1)
    goals = int(shots["counts_as_goal"].sum()) if "counts_as_goal" in shots else 0
    official = countable["xg_quality"].eq("official").sum() if "xg_quality" in countable else 0
    return {
        "shots": n,
        "on_target": on_target,
        "goals": goals,
        "xg": xg,
        "xg_per_shot": xg / n if n else np.nan,
        "accuracy_pct": on_target / n * 100 if n else np.nan,
        "goals_minus_xg": goals - xg if pd.notna(xg) else np.nan,
        "pct_official_xg": official / n * 100 if n else np.nan,
    }


def pass_summary(passes: pd.DataFrame) -> dict:
    n = len(passes)
    if not n:
        return {"passes": 0, "completed": 0, "pass_pct": np.nan,
                "progressive": 0, "into_final_third": 0, "into_box": 0,
                "key_passes": 0, "crosses": 0, "forward_pct": np.nan}
    return {
        "passes": n,
        "completed": int(passes["is_complete"].sum()),
        "pass_pct": passes["is_complete"].mean() * 100,
        "progressive": int(passes["is_progressive"].sum()),
        "into_final_third": int(passes["into_final_third"].sum()),
        "into_box": int(passes["into_penalty_area"].sum()),
        "key_passes": int(passes["is_key_pass"].sum()),
        "crosses": int(passes["is_cross"].sum()),
        "forward_pct": passes["is_forward"].mean() * 100
        if "is_forward" in passes else np.nan,
    }


def zone_grid(events: pd.DataFrame, nx: int = 6, ny: int = 4,
              normalize: bool = True) -> pd.DataFrame:
    """Bin events into a pitch grid on the common 0-100 coordinates.

    ``normalize`` turns counts into a share of the total, which is what makes
    two eras with different event volumes comparable on the same colour scale.
    """
    if events.empty:
        return pd.DataFrame()
    x_bins = np.linspace(0, 100, nx + 1)
    y_bins = np.linspace(0, 100, ny + 1)
    grid = events.assign(
        xb=pd.cut(events["normalized_x"], x_bins, include_lowest=True, labels=False),
        yb=pd.cut(events["normalized_y"], y_bins, include_lowest=True, labels=False),
    )
    counts = (grid.groupby(["yb", "xb"], observed=True).size()
              .rename("events").reset_index())
    counts = counts.dropna()
    if normalize and counts["events"].sum():
        counts["share"] = counts["events"] / counts["events"].sum() * 100
    else:
        counts["share"] = np.nan
    counts["x_from"] = counts["xb"].astype(int) * (100 / nx)
    counts["x_to"] = (counts["xb"].astype(int) + 1) * (100 / nx)
    counts["y_from"] = counts["yb"].astype(int) * (100 / ny)
    counts["y_to"] = (counts["yb"].astype(int) + 1) * (100 / ny)
    return counts


def passing_network(passes: pd.DataFrame, min_passes: int = 3,
                    max_players: int = 11) -> tuple:
    """Average positions and pass volumes between players.

    Built from completed open-play passes with a known recipient. The recipient
    column only exists in the StatsBomb source, so this returns empty frames for
    a World Cup 2026 selection — the caller is expected to say so rather than
    render a blank pitch.
    """
    empty = (pd.DataFrame(), pd.DataFrame())
    if passes.empty or "recipient" not in passes.columns:
        return empty
    valid = passes[passes["is_complete"] & passes["recipient"].notna()
                   & passes["player_canonical"].notna()]
    if "is_open_play" in valid.columns:
        valid = valid[valid["is_open_play"]]
    if valid.empty:
        return empty

    # A recipient's canonical name isn't stored, so map it from the passer
    # column, where both spellings of every player appear.
    name_map = (passes.dropna(subset=["player", "player_canonical"])
                .drop_duplicates("player").set_index("player")["player_canonical"])
    valid = valid.assign(
        recipient_canonical=valid["recipient"].map(name_map).fillna(valid["recipient"]))

    nodes = (valid.groupby("player_canonical", observed=True)
             .agg(x=("normalized_x", "mean"), y=("normalized_y", "mean"),
                  passes=("player_canonical", "size")).reset_index()
             .rename(columns={"player_canonical": "player"}))
    nodes = nodes.sort_values("passes", ascending=False).head(max_players)
    keep = set(nodes["player"])

    edges = (valid[valid["player_canonical"].isin(keep)
                   & valid["recipient_canonical"].isin(keep)]
             .groupby(["player_canonical", "recipient_canonical"], observed=True)
             .size().rename("passes").reset_index()
             .rename(columns={"player_canonical": "passer",
                              "recipient_canonical": "receiver"}))
    edges = edges[edges["passes"] >= min_passes]
    pos = nodes.set_index("player")[["x", "y"]]
    if not edges.empty:
        edges = edges.join(pos, on="passer").join(pos, on="receiver",
                                                  rsuffix="_end")
        edges = edges.rename(columns={"x": "x_start", "y": "y_start",
                                      "x_end": "x_end", "y_end": "y_end"})
    return nodes, edges


# --------------------------------------------------------------------------- #
# Player-level
# --------------------------------------------------------------------------- #

def player_era_split(player_stats: pd.DataFrame, player: str,
                     metrics: Sequence[str]) -> pd.DataFrame:
    """One player's per-90 numbers under each manager.

    Aggregated from the player's own minutes (total events ÷ total minutes),
    not as a mean of per-match rates — a 12-minute cameo would otherwise weigh
    the same as a full match.
    """
    rows = player_stats[player_stats["player_canonical"] == player]
    if rows.empty:
        return pd.DataFrame()
    out = []
    for era in C.ERAS:
        subset = rows[rows["era"] == era]
        if subset.empty:
            continue
        minutes = subset["minutes_played"].sum(min_count=1)
        entry = {"era": era, "matches": len(subset), "minutes": minutes}
        for metric in metrics:
            base = metric.replace("_per90", "")
            if base not in subset.columns:
                entry[metric] = np.nan
                continue
            total = subset[base].sum(min_count=1)
            entry[metric] = (total / minutes * 90.0
                             if pd.notna(minutes) and minutes and pd.notna(total)
                             else np.nan)
            entry[f"{base}_total"] = total
        out.append(entry)
    return pd.DataFrame(out)


def squad_turnover(player_stats: pd.DataFrame) -> pd.DataFrame:
    """Which players each era used, and how the two squads overlap."""
    spain = player_stats[player_stats["is_spain"]]
    by_era = {era: set(spain.loc[spain["era"] == era, "player_canonical"].dropna())
              for era in C.ERAS}
    both = by_era[C.ERAS[0]] & by_era[C.ERAS[1]]
    return pd.DataFrame([
        {"group": "Used by Luis Enrique only",
         "players": len(by_era[C.ERAS[0]] - both)},
        {"group": "Used by both managers", "players": len(both)},
        {"group": "Used by Luis de la Fuente only",
         "players": len(by_era[C.ERAS[1]] - both)},
    ])
