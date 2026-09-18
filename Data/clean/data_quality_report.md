# Data quality report

Generated 2026-09-18 17:14 UTC by `src/clean_data.py` — `Data/` → `data/clean/`.

**21 consistency checks, 21 passed.**

## Tables written

| Table | Rows | Columns | Added |
|---|---:|---:|---:|
| `matches.csv` | 25 | 30 | +11 |
| `team_stats.csv` | 50 | 65 | +35 |
| `player_stats.csv` | 796 | 57 | +27 |
| `players.csv` | 415 | 42 | +19 |
| `shots.csv` | 642 | 49 | +22 |
| `passes.csv` | 28,903 | 52 | +21 |
| `carries.csv` | 16,249 | 35 | +15 |
| `defensive_actions.csv` | 12,725 | 34 | +16 |
| `eda_team_summary_by_era.csv` | 2 | 31 | +4 |
| `eda_team_summary_by_tournament.csv` | 4 | 31 | +4 |

## Consistency checks

| Check | Result | Detail |
|---|---|---|
| matches.csv holds 25 unique matches | **PASS** | 25 rows |
| Era split is 10 Luis Enrique / 15 Luis de la Fuente | **PASS** | {'Luis Enrique': 10, 'Luis de la Fuente': 15} |
| passes: every match_id exists in matches.csv | **PASS** | — |
| shots: every match_id exists in matches.csv | **PASS** | — |
| carries: every match_id exists in matches.csv | **PASS** | — |
| defensive_actions: every match_id exists in matches.csv | **PASS** | — |
| team_stats: every match_id exists in matches.csv | **PASS** | — |
| player_stats: every match_id exists in matches.csv | **PASS** | — |
| Goals in shots.csv reconcile with every scoreline in matches.csv | **PASS** | all 25 matches agree |
| shots.csv flags reproduce team_stats.csv `shots` for all 50 team-matches | **PASS** | exact |
| shots.csv flags reproduce team_stats.csv `shots_on_target` for all 50 team-matches | **PASS** | exact |
| passes.csv reproduces team_stats.csv pass counts | **PASS** | exact |
| Possession proxy sums to 100% in every match | **PASS** | range 100.00–100.00 |
| carries.csv covers exactly the 17 StatsBomb matches | **PASS** | 17 matches |
| WC2026 carries/pressures stay NaN (never zero-filled) | **PASS** | all NaN as documented in README §5 |
| passes: normalized coordinates inside the 0-100 pitch | **PASS** | — |
| shots: normalized coordinates inside the 0-100 pitch | **PASS** | — |
| carries: normalized coordinates inside the 0-100 pitch | **PASS** | — |
| defensive_actions: normalized coordinates inside the 0-100 pitch | **PASS** | — |
| Team names are consistent across every table | **PASS** | 22 teams, one spelling each |
| No duplicate rows remain in any table | **PASS** | 10 tables checked |

## What was changed

Three kinds of change, and nothing else: *harmonise* (two sources spelling one fact differently), *derive* (a new column computed from existing ones), *repair* (a demonstrable defect in the collected file). No value was estimated or filled in here — genuinely missing data stays `NaN`.

### Harmonised (7)

| Table | Column(s) | What | Rows |
|---|---|---|---:|
| `matches` | `opponent` | 'Cape Verde' -> 'Cabo Verde' (one spelling across all tables) | 1 |
| `shots` | `period_no / period_label / is_shootout` | StatsBomb's numeric periods (1-5) and Opta's names ('FirstHalf', 'FirstPeriodOfExtraTime', ...) collapsed onto one 1-5 scale; period 5 flagged as penalty shootout | 642 |
| `shots` | `outcome_std` | StatsBomb's 8 outcome labels and Opta's 3 mapped onto one scale (Goal / Saved / Off target / Blocked / Woodwork) | 642 |
| `passes` | `period_no / period_label / is_shootout` | StatsBomb's numeric periods (1-5) and Opta's names ('FirstHalf', 'FirstPeriodOfExtraTime', ...) collapsed onto one 1-5 scale; period 5 flagged as penalty shootout | 28,903 |
| `carries` | `period_no / period_label / is_shootout` | StatsBomb's numeric periods (1-5) and Opta's names ('FirstHalf', 'FirstPeriodOfExtraTime', ...) collapsed onto one 1-5 scale; period 5 flagged as penalty shootout | 16,249 |
| `defensive_actions` | `period_no / period_label / is_shootout` | StatsBomb's numeric periods (1-5) and Opta's names ('FirstHalf', 'FirstPeriodOfExtraTime', ...) collapsed onto one 1-5 scale; period 5 flagged as penalty shootout | 12,725 |
| `defensive_actions` | `action_type` | Opta's 'Foul' and StatsBomb's 'Foul Committed' were two categories for one event; merged into 'Foul Committed' | 392 |

### Derived (41)

| Table | Column(s) | What | Rows |
|---|---|---|---:|
| `matches` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `data_source`, whose three verbose spellings name only two datasets | 25 |
| `matches` | `goal_difference / scoreline` | Convenience columns for KPI cards and match tables | 25 |
| `matches` | `label` | Human-readable one-line match label for the match selector | 25 |
| `matches` | `has_carries / has_pressures / has_official_xg / has_positions` | Per-match coverage flags for the metric families that exist in StatsBomb but not in the Opta-taxonomy WC2026 source (README §5), so the app can label a gap instead of implying zero | 25 |
| `matches` | `match_no_in_era / match_no_overall` | Chronological match counters for trend charts | 25 |
| `team_stats` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `source`, whose three verbose spellings name only two datasets | 50 |
| `team_stats` | `xg_quality` | 'official' / 'estimated' token derived from `xg_note` for UI badges | 50 |
| `team_stats` | `era / manager / round / opponent / match_result / extra_time` | Match context joined in from matches.csv so every event row carries its era without a second lookup | 50 |
| `team_stats` | `match_minutes + *_per90` | 20 per-90 columns, normalised by 120 minutes for extra-time matches and 90 otherwise (same rule as the EDA summaries) | 50 |
| `team_stats` | `xg_per_shot / shot_accuracy_pct / goals_minus_xg` | Shot-quality ratios (NaN, not 0, when a team took no shots) | 50 |
| `player_stats` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `source`, whose three verbose spellings name only two datasets | 796 |
| `player_stats` | `xg_quality` | 'official' / 'estimated' token derived from `xg_note` for UI badges | 796 |
| `player_stats` | `era / manager / round / opponent / match_result / extra_time` | Match context joined in from matches.csv so every event row carries its era without a second lookup | 796 |
| `player_stats` | `*_per90` | Per-90 columns from `minutes_played`; NaN (never inf or 0) where minutes are unknown — 98 WC2026 rows have no substitution events | 796 |
| `player_stats` | `goal_contributions` | goals + key passes (assists are not logged in both sources, so key passes stand in — labelled as such in the UI) | 796 |
| `players` | `n_tournaments / n_eras / bridges_eras` | Counts parsed from the comma-joined `tournaments` / `eras` strings; `bridges_eras` marks the players who played under both managers | 415 |
| `players` | `*_per90` | Career per-90 columns over `minutes_played_total` | 415 |
| `players` | `minutes_per_match` | Average minutes per appearance | 415 |
| `shots` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `source`, whose three verbose spellings name only two datasets | 642 |
| `shots` | `is_goal / is_on_target / is_penalty` | Boolean flags; `is_on_target` is defined to reproduce team_stats.csv's own `shots_on_target` tally exactly (asserted in the validation pass) | 642 |
| `shots` | `has_xg / xg_quality` | xG provenance as a short token; the 7 own-goal rows have no xG in any source and are marked 'not applicable' rather than 0 | 642 |
| `shots` | `counts_as_shot / counts_as_goal` | The counting basis behind team_stats.csv: shots exclude penalty shootouts and own goals; goals exclude shootouts but include own goals, credited to the benefiting team | 642 |
| `shots` | `distance_to_goal` | Distance from the shot to the goal centre on the common 0-100 pitch (comparable across both coordinate systems) | 642 |
| `shots` | `era / manager / round / opponent / match_result / extra_time` | Match context joined in from matches.csv so every event row carries its era without a second lookup | 642 |
| `passes` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `source`, whose three verbose spellings name only two datasets | 28,903 |
| `passes` | `is_complete` | One boolean for completion; the raw `outcome` has 6 values (Complete / Incomplete / Out / Unknown / Pass Offside / Injury Clearance), only the first of which is a completed pass | 28,903 |
| `passes` | `is_set_piece / is_open_play` | Set-piece grouping over `pass_type` so open-play passing can be isolated | 28,903 |
| `passes` | `normalized_end_x / normalized_end_y` | Pass end points rescaled onto the common 0-100 pitch (StatsBomb ÷120/÷80; Opta unchanged) — the start points already had this, the end points did not, so pass-arrow charts could not mix sources | 28,903 |
| `passes` | `pass_distance / is_forward` | Pass length on the common pitch and direction of travel; the raw `length` column is in each source's own units and is not comparable | 28,903 |
| `passes` | `pitch_third` | Which third the pass started in, on the common 0-100 pitch | 28,903 |
| `passes` | `era / manager / round / opponent / match_result / extra_time` | Match context joined in from matches.csv so every event row carries its era without a second lookup | 28,903 |
| `carries` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `source`, whose three verbose spellings name only two datasets | 16,249 |
| `carries` | `normalized_end_x / normalized_end_y` | Carry end points on the common 0-100 pitch | 16,249 |
| `carries` | `era / manager / round / opponent / match_result / extra_time` | Match context joined in from matches.csv so every event row carries its era without a second lookup | 16,249 |
| `defensive_actions` | `source_short` | Short provenance label ('StatsBomb' / 'WhoScored') derived from `source`, whose three verbose spellings name only two datasets | 12,725 |
| `defensive_actions` | `action_group` | Short action grouping for the event-type filter | 12,725 |
| `defensive_actions` | `is_successful` | Success boolean over the 8 source outcome labels; note 61.7% of rows log no outcome at all (mostly pressures), which read as not-successful — use with the outcome column, not alone | 12,725 |
| `defensive_actions` | `defensive_third` | Pitch third of the action — the basis for a pressing-height read | 12,725 |
| `defensive_actions` | `era / manager / round / opponent / match_result / extra_time` | Match context joined in from matches.csv so every event row carries its era without a second lookup | 12,725 |
| `eda_team_summary_by_era` | `win_pct / points_per_match / xg_per_shot / shot_accuracy_pct` | Rates used directly by the Overview KPI cards | 2 |
| `eda_team_summary_by_tournament` | `win_pct / points_per_match / xg_per_shot / shot_accuracy_pct` | Rates used directly by the Overview KPI cards | 4 |

### Repaired (9)

| Table | Column(s) | What | Rows |
|---|---|---|---:|
| `player_stats` | `player_canonical` | Mapped the remaining raw StatsBomb legal name to its common name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4 | 2 |
| `players` | `player_canonical` | Mapped the remaining raw StatsBomb legal name to its common name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4 | 1 |
| `shots` | `player_canonical` | Mapped the remaining raw StatsBomb legal name to its common name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4 | 3 |
| `shots` | `body_part` | Literal string 'True' (a source parsing artifact, not a body part) replaced with NaN | 1 |
| `shots` | `shot_type` | `shot_type` set to 'Own Goal' where `is_own_goal` was true but the type said 'Open Play' (WC2026 own-goal row) | 1 |
| `shots` | `player / player_canonical` | Own goals carry no shooter in the source; labelled explicitly instead of NaN so they are visible rather than silently dropped | 6 |
| `passes` | `player_canonical` | Mapped the remaining raw StatsBomb legal name to its common name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4 | 14 |
| `carries` | `player_canonical` | Mapped the remaining raw StatsBomb legal name to its common name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4 | 11 |
| `defensive_actions` | `player_canonical` | Mapped the remaining raw StatsBomb legal name to its common name ('José Luis Sanmartín Mato' -> 'Joselu'), per README §4 | 26 |

## Gaps left in place on purpose

These are source coverage limits, not defects, and are **not** filled:

| Gap | Extent | Handling |
|---|---|---|
| Ball carries | absent for the 8 WC2026 matches — Opta's taxonomy has no discrete carry event | `NaN`; `matches.has_carries` flags it and the app labels affected charts |
| Pressures | StatsBomb-only, same 8 matches | `NaN`; `matches.has_pressures` |
| Official xG | StatsBomb-only; WC2026 uses the distance/angle proxy model | `xg_combined` + `xg_quality` ('official' / 'estimated') distinguish them everywhere |
| xG for own goals | 7 rows have no xG in any source | `xg_quality` = 'not applicable (own goal)'; excluded from shot tallies by `counts_as_shot` |
| Player positions | Opta source logs none | `NaN` for 252 WC2026 rows |
| Minutes played | no substitution events for 98 WC2026 player-rows | `NaN`, so their per-90 values are `NaN` rather than misleading |
| Possession % | a proxy, and a *different* proxy per source | kept as `possession_pct_proxy` with `possession_proxy_method`; labelled as a proxy in the UI |
| Possession chains | no `possessions.csv` exists | out of scope; StatsBomb's chain id has no WC2026 equivalent (README §5) |

## One caveat resolved

`README.md` §5 warns that StatsBomb lets teams switch attacking direction at half-time, so combining the two sources on one pitch would need direction normalisation. Checked directly against the data: Spain's shot x-coordinates average 86.6 / 87.4 / 87.4 / 89.5 across periods 1-4 in the StatsBomb matches and 84.2 / 83.6 in the WC2026 matches — both sources already record the attacking team moving left→right in every period. No flip is required, and `normalized_x` / `normalized_y` can be overlaid across sources directly. (The one Spain 'shot' at x = 2.5 is the Al-Tambakti own goal, taken at the other end and credited to Spain — which is why own goals are excluded from shot maps via `counts_as_shot`.)
