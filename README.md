# Spain's Evolution: Luis Enrique → Luis de la Fuente

Event-level dataset + first-pass EDA covering every Spain men's national team match at **UEFA Euro 2020**, **FIFA World Cup 2022**, **UEFA Euro 2024**, and **FIFA World Cup 2026** — 25 matches in total.

**→ See [`FINDINGS.md`](FINDINGS.md) for the analysis** (6 evidence-backed findings on how Spain's style changed between eras) **and `visualizations/` for the charts** (era comparison bars, chronological trend, shot maps by tournament, touch/progressive-pass heatmaps by era, passing network comparison).

## Project status

Done: data collection (25 matches, event-level), an xG proxy model for the 8 matches missing official xG, team-level EDA (absolute + per-90, by tournament and by era), 6 core visualizations, a **cleaning + validation pass** (`src/clean_data.py` → `data/clean/`, see §7), and the **Streamlit dashboard** (`app/`, see §8) — which also covers the player-level analysis and the final-third/penalty-area entry maps that were previously outstanding.

Not yet done: possession-sequence chains (needs a `possessions.csv` that the WC2026 source cannot support like-for-like — see §5), and the 01–07 notebook sequence from the original project spec (this pass used plain scripts instead, listed in §6).

## 1. Data sources

| Source | Tournaments covered | Spain matches | What it provides | License / access |
|---|---|---|---|---|
| [StatsBomb Open Data](https://github.com/statsbomb/open-data) | EURO 2020, World Cup 2022, EURO 2024 | 17 | Full event stream (passes, shots w/ xG, carries, pressures, duels, etc.), pitch coords **0–120 x, 0–80 y** | Free, open (StatsBomb open-data license — non-commercial, attribution required) |
| [nlbair/wc2026-events](https://github.com/nlbair/wc2026-events) (WhoScored-sourced, community-curated) | World Cup 2026 | 8 | Full Opta-taxonomy event stream (passes, shots, defensive actions, qualifiers), pitch coords **0–100 x, 0–100 y** | Open GitHub repo; no official StatsBomb open data exists yet for WC2026 |
| FBref | (attempted) | — | Aggregate box-score stats | **Not used** — FBref rate-limited/blocked automated access during this collection (its own anti-scraping policy caps external requests). It also only exposes aggregate per-match stats, not event coordinates, so it could not have supplied the pass-map/shot-map/passing-network data the project needs anyway. |
| Wikipedia / ESPN / Goal.com / press reports | All 4 | — | Used only to confirm match dates, opponents, scorelines, venues, and manager-tenure boundaries for `matches.csv` — cross-checked against the goal events actually present in the StatsBomb/WhoScored data (see §4). | — |

**Source per match.** The dashboard's match table (Overview page) no longer shows a "Data source" column; the mapping is by tournament, with no exceptions:

| Tournament | Era | Spain matches | Data source |
|---|---|---|---|
| EURO 2020 | Luis Enrique | 6 | StatsBomb |
| World Cup 2022 | Luis Enrique | 4 | StatsBomb |
| EURO 2024 | Luis de la Fuente | 7 | StatsBomb |
| World Cup 2026 | Luis de la Fuente | 8 | WhoScored (nlbair/wc2026-events) |

**In short** (this line used to close every dashboard page): event data is StatsBomb Open Data (EURO 2020, World Cup 2022, EURO 2024) and nlbair/wc2026-events, WhoScored-sourced (World Cup 2026). Possession is a proxy; World Cup 2026 xG is model-estimated. See `data/clean/data_quality_report.md` for every cleaning rule and consistency check applied to the underlying tables.

No data was fabricated. Where a variable is not available from either source (see §3), it is left blank (`NaN`), not estimated.

## 2. Coverage

- **Luis Enrique era**: EURO 2020 (6 matches) + World Cup 2022 (4 matches) = 10 matches
- **Luis de la Fuente era**: EURO 2024 (7 matches) + World Cup 2026 (8 matches) = 15 matches
- All 25 matches have full event-level data (passes, shots, defensive actions). 17 of 25 (all StatsBomb-covered matches) additionally have ball-carry events and shot xG.

## 3. Files

The collected tables live in `Data/`. **`src/clean_data.py` reads them and writes analysis-ready copies to `data/clean/`** — same rows, harmonised vocabularies and extra derived columns, plus a quality report (§7). The dashboard reads `data/clean/`; anything computing from the raw tables should read §5 first.

- `matches.csv` — one row per match: date, competition, round, opponent, score, manager/era, venue, extra time/penalties, and which source+match id backs it.
- `team_stats.csv` — one row per team per match: possession proxy, passing, shooting, progression, and defensive aggregates (see §5 for the possession caveat).
- `player_stats.csv` — one row per player per match, same metric families as `team_stats.csv`.
- `players.csv` — one row per player (canonical name), aggregated across all matches/tournaments they appear in — this is the table to use for cross-era player comparison (Rodri, Pedri, etc.).
- `passes.csv` — event-level, every recorded pass: locations, outcome, type, body part, cross/through-ball/key-pass/progressive flags, final-third/box-entry flags.
- `shots.csv` — event-level, every shot (incl. own goals, and penalty-shootout kicks, flagged separately — see §5): location, outcome, body part, type, xG (StatsBomb matches only).
- `carries.csv` — event-level ball carries with progressive-carry flag. **StatsBomb-covered matches only** (17/25) — Opta's taxonomy (used for WC2026) does not log carries as discrete events.
- `defensive_actions.csv` — event-level tackles/interceptions/clearances/blocks/pressures/duels/recoveries.
- `eda_team_summary_by_tournament.csv` / `eda_team_summary_by_era.csv` — Spain's aggregated team stats (absolute + per-90), chronological by tournament and grouped by managerial era. Source data for `FINDINGS.md` and `visualizations/01`–`02`.

All of `passes.csv`/`shots.csv`/`carries.csv`/`defensive_actions.csv` also carry `normalized_x`/`normalized_y` (both sources rescaled to a common 0–100 pitch) for charts that compare eras directly.

## 4. Methodology notes & corrections made during collection

- Match results were first drafted from press/Wikipedia summaries, then **verified against the actual goal events in the source data** (StatsBomb / WhoScored). Two corrections came out of that check:
  - Spain 4–0 Saudi Arabia (WC2026 group stage) — a secondary source said 5–0; the event log confirms 4 goals (Yamal, Oyarzabal x2, Al-Tambakti own goal).
  - Spain 1–0 Argentina (WC2026 final, a.e.t.) — the WC2026 file's own `home_score`/`away_score` header columns are stale (`0–0`) in that file, but the event log itself contains exactly one goal (Ferran Torres, 105th minute), matching every press account. `matches.csv` uses the event-verified score.
- **Own goals**: StatsBomb's "Own Goal For" event already credits the *benefiting* team. Opta/WhoScored's own-goal events instead tag the *scoring player's own team* — this was re-mapped so `shots.csv`'s `team`/`is_spain` always reflects who the goal counts for; the scorer's actual team is kept in `scoring_player_team` for WC2026 rows.
- **Penalty shootouts**: StatsBomb tags shootout kicks as period 5. They remain in `shots.csv` (so shootout analysis is possible) but are **excluded** from `team_stats.csv`/`player_stats.csv` shot/goal/xG tallies, which reflect regulation + extra time only — matching `matches.csv`'s `spain_score`/`opp_score` columns. Shootout results live in `matches.csv`'s `penalty_score` column.
- **Player name unification**: StatsBomb uses full legal names (e.g. "Rodrigo Hernández Cascante"), the WC2026 source uses common names ("Rodri"). A manual mapping (`player_canonical` column) unifies ~40 Spain squad members across sources so a player's career can be tracked across all four tournaments. A handful of fringe/uncertain names were left unmapped rather than guessed.
- **Progressive pass/carry** definitions follow the common StatsBomb-community threshold (distance-to-goal reduced by ≥25%), applied identically to both sources after rescaling coordinates.

## 5. Known limitations — read before analyzing

- **Two different coordinate systems.** StatsBomb: 0–120 (x) × 0–80 (y). WC2026/Opta: 0–100 × 0–100. Both are kept in their **native units** (`coord_system` column tags each row) rather than silently rescaled. Use `normalized_x`/`normalized_y` for anything that mixes the two sources.
  - **Attacking direction: resolved.** This section previously warned that StatsBomb lets teams switch attacking direction at half-time, so combining the sources would need a direction-normalisation step. Checked directly against the data (and asserted by `src/clean_data.py`): Spain's shot x-coordinates average 86.6 / 87.4 / 87.4 / 89.5 across periods 1–4 in the StatsBomb matches and 84.2 / 83.6 in the WC2026 matches — **both sources already record the attacking team moving left→right in every period**, so no flip is required and `normalized_x`/`normalized_y` can be overlaid directly. (The one Spain "shot" at x = 2.5 is the Al-Tambakti own goal, taken at the other end and credited to Spain — which is why own goals are excluded from shot maps.)
  - The normalised values are square (0–100 on both axes), which is not the shape of a pitch: plotted as-is, the pitch comes out as tall as it is wide. Map them onto real proportions (105 × 68) before drawing, as `app/utils/charts_mplsoccer.py` does.
- **Possession % is a proxy, not the official broadcast stat**, and the two sources use *different* proxies (documented per-row in `possession_proxy_method`): StatsBomb matches use "share of possession chains"; WC2026 matches use "share of on-ball touches." Treat cross-tournament possession comparisons as directional, not exact.
- **xG**: real StatsBomb xG covers the 17 StatsBomb matches. For the 8 WC2026 matches (no official xG available), `shots.csv` adds an `xg_proxy` column from a simple logistic-regression model (distance + shot angle + header + set-piece flags) trained on the 449 non-penalty StatsBomb shots (5-fold CV log-loss 0.28; proxy probabilities correlate 0.86 with real StatsBomb xG on the training data). Penalties get a fixed 0.79 (standard penalty conversion rate) wherever no official xG exists. `xg_combined` = real xG where available, else the proxy; `xg_source` says which. `team_stats.csv`/`player_stats.csv`/`players.csv`'s `xg` column uses this combined value, tagged via `xg_note` as `official` or `estimated`. **Treat WC2026 xG figures as directional estimates, not ground truth.**
- **Carries only exist for the 17 StatsBomb matches** (see §3) — `carries.csv` has no WC2026 rows, and WC2026 rows in `player_stats.csv`/`players.csv` show `carries`/`progressive_carries` as blank, not zero.
- **Minutes played are approximate**, derived from starting-XI/substitution events (StatsBomb) or `SubstitutionOn`/`SubstitutionOff` events (WC2026); red-card send-offs and stoppage-time nuances are not separately reconciled.
- **No possession-sequence table** (`possessions.csv`) is included in this pass — StatsBomb's `possession` chain id would support one for the 17 StatsBomb matches, but Opta's taxonomy has no equivalent chain id for WC2026, so a like-for-like version across all 25 matches needs a bit more derivation work than this collection pass covered. `passes.csv`/`shots.csv` retain minute/second ordering so a chain table can still be built later.
- Two players in `player_stats.csv` retain their raw StatsBomb full name (`player_canonical` unmapped) where the corresponding common name used by the WC2026 source could not be confirmed with confidence. `src/clean_data.py` resolves one of them ("José Luis Sanmartín Mato" → "Joselu") and leaves "Robin Le Normand", which already *is* the common name, alone.

### Defects in the collected files, and where they are fixed

Found while building the cleaning pass. `src/clean_data.py` repairs all of these in `data/clean/`; they are still present in `Data/`.

| Defect | Extent |
|---|---|
| `matches.csv` spells the opponent "Cape Verde"; every event file says "Cabo Verde" | breaks a team-name join across tables |
| `period` mixes StatsBomb's integers (`1`–`5`) with Opta's names (`FirstHalf`, `FirstPeriodOfExtraTime`, …) | all four event files |
| `shots.outcome` uses two vocabularies (`Off T`/`Saved`/`Wayward`/`Post` vs `MissedShots`/`SavedShot`/`ShotOnPost`) | 11 labels for 5 distinct outcomes |
| `defensive_actions.action_type` has both `Foul` (Opta) and `Foul Committed` (StatsBomb) as separate categories | 885 rows split across two names for one event |
| `shots.body_part` holds the literal string `"True"` | 1 row (a parsing artifact; no body part is recoverable) |
| The same row is an own goal but typed `shot_type = "Open Play"` | 1 row |
| `source` / `data_source` spell the two datasets three different ways | across `matches.csv` and the event files |

## 6. Reproducing / extending this dataset

All source files are the original open-data JSON (StatsBomb) and CSV (WC2026) — no scraping of gated/paywalled sites was performed. The StatsBomb files are pulled directly from `raw.githubusercontent.com/statsbomb/open-data`; the WC2026 files from `raw.githubusercontent.com/nlbair/wc2026-events`, both saved under `data/raw/`. Re-running collection only requires re-downloading those same public files.

`src/` run order (each script reads/writes `data/final/*.csv`):
1. `build_matches.py` — writes `matches.csv`
2. `build_events.py` — parses `data/raw/` into `passes/shots/carries/defensive_actions/player_stats/team_stats.csv`
3. `apply_canonical_names.py` — adds unified `player_canonical` names
4. `build_players.py` — rolls up `players.csv`
5. `build_xg_proxy.py` — trains/applies the WC2026 xG proxy model → adds `xg_proxy`/`xg_combined`/`xg_source` to `shots.csv`
6. `update_xg_in_aggregates.py` — propagates combined xG into `team_stats.csv`/`player_stats.csv`/`players.csv`
7. `add_normalized_coords.py` — adds `normalized_x`/`normalized_y` (common 0–100 scale) to the event-level files
8. `build_eda.py` — writes `eda_team_summary_by_tournament.csv` / `eda_team_summary_by_era.csv`, prints the era comparison
9. `viz_01_eda_charts.py`, `viz_02_shot_maps.py`, `viz_03_heatmaps.py`, `viz_04_passing_networks.py` — write `visualizations/*.png` (uses `viz_common.py` for the shared color palette)
10. `clean_data.py` — reads `Data/*.csv`, writes `data/clean/*.csv` + the quality report (§7)

## 7. Cleaning & validation

```bash
python src/clean_data.py
```

Reads `Data/`, writes `data/clean/` plus `data_quality_report.md` and `.json`. Row counts are unchanged; columns grow (for example `shots.csv` 27 → 49) with harmonised vocabularies and derived conveniences.

Every change is one of exactly three kinds, and the report says which for each:

- **harmonise** — the two sources spelling one fact differently (periods, shot outcomes, foul types, team names, source labels).
- **derive** — a new column computed from existing ones (per-90 rates, `outcome_std`, `is_on_target`, `counts_as_shot`, normalised pass/carry *end* points, pitch thirds, per-match coverage flags, match context joined onto every event row).
- **repair** — a demonstrable defect in the collected file (the seven listed in §5).

**No value is estimated or filled.** Data that is genuinely absent — WC2026 carries and pressures, Opta player positions, minutes for players with no substitution event, xG for own goals — stays `NaN`, and `matches.csv` gains `has_carries` / `has_pressures` / `has_official_xg` / `has_positions` so a consumer can distinguish "absent" from "zero".

21 consistency checks run on every build and all must pass, including:

- goals in `shots.csv` reconcile with all 25 scorelines in `matches.csv`;
- the derived event flags reproduce `team_stats.csv`'s own `shots`, `shots_on_target`, `passes_attempted` and `passes_completed` for all 50 team-match rows exactly — so a number computed from the event files always agrees with the pre-aggregated table;
- the possession proxy sums to 100% in every match;
- `carries.csv` covers exactly the 17 StatsBomb matches, and WC2026 carries/pressures are still `NaN`;
- every `match_id` in every table exists in `matches.csv`, normalised coordinates stay inside the 0–100 pitch, and team names are spelled one way everywhere.

Reverse-engineering `team_stats.csv` to make the third check pass pinned down its counting basis, which was not written down anywhere: **shots** exclude penalty-shootout kicks *and* own goals; **goals** exclude shootouts but *include* own goals credited to the benefiting team; **shots on target** counts `Goal` and `Saved` but not StatsBomb's `Saved Off Target`. The cleaned `counts_as_shot` / `counts_as_goal` / `is_on_target` flags encode those rules.

## 8. The dashboard

```bash
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
```

Nine pages over `data/clean/` — an orientation page plus eight of the nine in the architecture diagram (Overview, the two manager pages, Passing, Shooting, Possession, Final Third, Players), with era/tournament/opponent/round/player filters shared across all of them. The diagram's ninth page, Match Explorer, was built and then removed. See [`app/README.md`](app/README.md) for the module layout, the charting rules, and where it departs from the diagram.

The dashboard surfaces this README's §5 rather than hiding it: possession is labelled a proxy before its first figure, estimated xG is drawn differently from official xG and never blended into it, and carry-based figures report how many of the selected matches actually have carry data.
