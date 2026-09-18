# Data Dictionary

See `README.md` for sources, methodology, and limitations. Columns common to several files are described once at first appearance.

This describes the **collected** tables in `Data/`. `src/clean_data.py` writes `data/clean/` with the same rows plus the derived columns in §"Columns added by the cleaning pass" at the end of this file — that is what the dashboard reads.

## matches.csv
| Column | Description |
|---|---|
| match_id | Internal id, e.g. `EURO2024_M5` |
| date | Match date (YYYY-MM-DD) |
| competition | Full competition name |
| tournament | Short code: EURO2020 / WC2022 / EURO2024 / WC2026 |
| era | `Luis Enrique` or `Luis de la Fuente` |
| manager | Spain head coach for this match |
| round | Group Stage / Round of 32 / Round of 16 / Quarter-finals / Semi-finals / Final |
| spain_venue | home/away/neutral (all 25 are neutral — international tournament) |
| opponent | Opponent team name |
| spain_score, opp_score | Full-time score after extra time if played (excludes penalty shootout) |
| result | W/D/L from Spain's perspective, penalty shootout outcome decides W/L when applicable |
| extra_time | Whether the match went to extra time |
| penalties | Whether the match was decided on penalties |
| penalty_score | "Spain-Opponent" penalty shootout score, if applicable |
| venue_city | Host city |
| data_source | Which open dataset backs this match's event data |
| sb_match_id | StatsBomb match id (if applicable) |
| wc2026_file | Source CSV filename in nlbair/wc2026-events (if applicable) |

## team_stats.csv / player_stats.csv
| Column | Description |
|---|---|
| team | Team name |
| is_spain | Boolean |
| position | Player's starting position (StatsBomb matches only) |
| minutes_played | Approximate minutes played (see README §5) |
| possession_pct_proxy | See README §5 — NOT an official possession % |
| possession_proxy_method | `share_of_possession_chains` (StatsBomb) or `share_of_touches` (WC2026) |
| passes_attempted / passes_completed / pass_pct | Open-play + set-piece passes |
| progressive_passes | Completed passes cutting distance-to-goal by ≥25% |
| key_passes | Passes that directly led to a shot |
| crosses | Passes flagged as crosses |
| passes_into_final_third / passes_into_penalty_area | Completed passes ending in that zone, starting outside it |
| shots / shots_on_target / goals | Excludes penalty-shootout kicks (see README §4) |
| xg | Real StatsBomb xG where available, else the distance/angle proxy model's estimate (see README §5 and `shots.csv` below) |
| xg_note | `official (StatsBomb)` or `estimated (distance/angle proxy model)` |
| carries / progressive_carries | StatsBomb matches only; blank for WC2026 |
| tackles / interceptions / clearances / blocks / recoveries / pressures / fouls_committed | Defensive actions; `pressures` is StatsBomb-only (Opta has no direct equivalent) |
| source | Which dataset the row came from |

## players.csv
Aggregates `player_stats.csv` up to one row per `player_canonical` per team, across every match in the dataset. `tournaments` and `eras` list every tournament/era that player appears in — use this to spot players who bridge both managerial eras (Rodri, Pedri, Dani Olmo, Morata, etc.).

## passes.csv
| Column | Description |
|---|---|
| player / recipient | Passer and intended receiver (recipient is StatsBomb-only; WC2026 events don't log an explicit receiver) |
| x, y / end_x, end_y | Start/end location in the row's native `coord_system` |
| coord_system | `statsbomb_120x80` or `opta_100x100` — see README §5 before combining |
| outcome | Complete / Incomplete / Out / Unknown / etc. |
| pass_type | Regular Play / Corner / Free Kick / Kick Off / Throw-in, etc. |
| body_part, height, length, angle | Technique detail (height is StatsBomb-only) |
| is_cross / is_through_ball / is_key_pass / is_progressive | Boolean flags |
| into_final_third / into_penalty_area | Boolean: pass ends in that zone having started outside it |
| player_canonical / recipient_canonical | Unified player names — see README §4 (`recipient_canonical` is computed at chart-build time in `src/viz_04_passing_networks.py`, not stored as a base column) |
| normalized_x / normalized_y | x/y rescaled onto a common 0–100 pitch (StatsBomb ÷120,÷80 ×100; WC2026 unchanged) — use these, not raw x/y, when comparing/overlaying both sources |

## shots.csv
| Column | Description |
|---|---|
| x, y | Shot location, native coord system |
| end_x, end_y | StatsBomb: shot end location. WC2026: goal-mouth y/z (a different meaning — see `coord_system`) |
| outcome | Goal / Saved / Off T / Blocked / Post / SavedShot / MissedShots, etc. (StatsBomb and Opta use different vocab — kept as-is per source) |
| shot_type | Open Play / Penalty / Free Kick / Own Goal |
| xg | Real StatsBomb xG; blank for WC2026 non-penalty shots |
| xg_proxy | Distance/angle logistic-model estimate — populated for WC2026 shots and penalties missing official xG (see README §5) |
| xg_combined | `xg` if present, else `xg_proxy` — the column to use by default |
| xg_source | `statsbomb_official` or `proxy_distance_angle_model` |
| is_own_goal | Boolean |
| scoring_player_team | WC2026 own goals only: the scorer's actual team (see README §4) — `team` is always the *credited/beneficiary* team |
| period | StatsBomb: 1/2=halves, 3/4=extra time halves, 5=penalty shootout (excluded from team/player aggregate tallies but present here) |
| normalized_x / normalized_y | See `passes.csv` above |

## carries.csv
StatsBomb-covered matches only. `distance` in pitch units (yards, StatsBomb's 120x80 system). `is_progressive` uses the same threshold as passes.

## defensive_actions.csv
| Column | Description |
|---|---|
| action_type | Tackle / Interception / Clearance / Block / Ball Recovery / Duel / Pressure / Foul Committed (StatsBomb) or the Opta-taxonomy equivalents (WC2026) |
| outcome | Where available (e.g. Duel won/lost) |

---

# Columns added by the cleaning pass

`data/clean/*.csv` only. Written by `src/clean_data.py`; every one is listed with its rationale in `data/clean/data_quality_report.md`. Nothing here replaces a source column — the originals are all kept.

## Added to every table that has the input column

| Column | Description |
|---|---|
| source_short | `StatsBomb` or `WhoScored` — one label for the two datasets, which the collected files spell three different ways |
| period_no | Period as an integer 1–5, unifying StatsBomb's numbers with Opta's `FirstHalf` / `FirstPeriodOfExtraTime` / … names |
| period_label | `1st half` / `2nd half` / `Extra time 1st half` / `Extra time 2nd half` / `Penalty shootout` |
| is_shootout | `period_no == 5`. Shootout kicks are present in `shots.csv` but excluded from every shot/goal/xG tally |
| xg_quality | `official` / `estimated` (from `xg_note`), for UI badges |
| era, manager, round, opponent, extra_time, match_result, match_spain_score, match_opp_score, match_no_in_era | Match context joined from `matches.csv` onto every event and per-team/per-player row, so a frame carries its era without a second lookup |

## matches.csv

| Column | Description |
|---|---|
| goal_difference, scoreline | `spain_score − opp_score`; `"2–1"` |
| label | One-line human-readable match label, used by the match selector |
| has_carries / has_pressures / has_official_xg / has_positions | **Per-match coverage flags.** False for the 8 WC2026 matches. These are what let a consumer tell "absent in the source" from "zero" |
| match_no_in_era / match_no_overall | Chronological counters, for trend charts |

## team_stats.csv / player_stats.csv / players.csv

| Column | Description |
|---|---|
| match_minutes | 120 for an extra-time match, 90 otherwise — the per-90 denominator |
| *_per90 | Per-90 rate for each counting metric, on that denominator. `NaN` (never 0 or inf) where minutes are unknown — 98 WC2026 player-rows have no substitution event |
| xg_per_shot, shot_accuracy_pct, goals_minus_xg | Shot-quality ratios; `NaN`, not 0, when a team took no shots |
| goal_contributions | goals + key passes (assists are not logged in both sources, so key passes stand in — labelled as such in the UI) |
| n_tournaments / n_eras / bridges_eras | `players.csv` only: parsed from the comma-joined `tournaments` / `eras` strings. `bridges_eras` marks the 14 players who appear under both managers |
| minutes_per_match | `players.csv` only |

## shots.csv

| Column | Description |
|---|---|
| outcome_std | The 11 source outcome labels mapped onto 5: `Goal` / `Saved` / `Off target` / `Blocked` / `Woodwork` |
| is_goal / is_on_target / is_penalty | Booleans. `is_on_target` is defined so that it reproduces `team_stats.csv`'s own `shots_on_target` exactly — which means StatsBomb's `Saved Off Target` counts as **off** target |
| counts_as_shot / counts_as_goal | The counting basis `team_stats.csv` uses: shots exclude shootout kicks **and own goals**; goals exclude shootouts but **include** own goals, credited to the benefiting team |
| has_xg | False for the 7 own-goal rows, which have no xG in any source and are marked `xg_quality = "not applicable (own goal)"` rather than 0 |
| distance_to_goal | Distance to the goal centre on the common 0–100 pitch, comparable across both coordinate systems |

## passes.csv

| Column | Description |
|---|---|
| is_complete | `outcome == "Complete"`. The raw `outcome` has 6 values, only one of which is a completed pass |
| is_set_piece / is_open_play | Grouping over `pass_type` (Corner / Free Kick / Throw-in / Goal Kick / Kick Off) |
| normalized_end_x / normalized_end_y | **Pass end points on the common 0–100 pitch.** The start points already had this; the end points did not, so no pass-arrow chart could mix the two sources |
| pass_distance / is_forward | Length on the common pitch, and direction of travel. The raw `length` is in each source's own units and is not comparable across them |
| pitch_third | `Defensive third` / `Middle third` / `Final third`, by where the pass started |

## carries.csv

| Column | Description |
|---|---|
| normalized_end_x / normalized_end_y | Carry end points on the common 0–100 pitch |

## defensive_actions.csv

| Column | Description |
|---|---|
| action_type | Opta's `Foul` merged into StatsBomb's `Foul Committed` — they were two categories for one event |
| action_group | Short grouping: Tackle / Interception / Clearance / Block / Recovery / Duel / Pressure / Foul |
| is_successful | True for `Won` / `Success In Play` / `Success Out` / `Successful` / `Recovered`. **Use with `outcome`, not alone:** 61.7% of rows (mostly pressures) log no outcome at all and read as not-successful |
| defensive_third | `Own third` / `Middle third` / `Final third` — the basis for a pressing-height read |

## eda_team_summary_by_era.csv / _by_tournament.csv

| Column | Description |
|---|---|
| win_pct, points_per_match, xg_per_shot, shot_accuracy_pct | Rates used by the Overview KPI cards |
