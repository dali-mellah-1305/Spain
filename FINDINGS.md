# Spain's Evolution — EDA Findings (Luis Enrique vs Luis de la Fuente)

Based on `data/final/eda_team_summary_by_era.csv`, `eda_team_summary_by_tournament.csv`, and the visualizations in `visualizations/`. All per-90 figures are Spain's own numbers, normalized for extra-time matches. Luis Enrique = EURO2020 + WC2022 (10 matches). Luis de la Fuente = EURO2024 + WC2026 (15 matches).

**A note on statistical power**: 10 vs 15 matches is a small, unequal sample. Treat every number below as directional evidence, not a definitive verdict — and see the methodological caveat in finding 4.

---

### 1. Spain passes far less under de la Fuente, at almost the same possession share

- **Evidence**: 822.9 passes/90 (Luis Enrique) → 632.9 passes/90 (Luis de la Fuente), **-23.1%**. Possession proxy barely moves: 54.2% → 55.6% (+2.6%).
- **Checked against a data-artifact explanation**: this isn't a StatsBomb-vs-Opta source quirk — EURO2024 (StatsBomb, same source as the Luis Enrique matches) shows the same lower pass volume (597.5/90) as WC2026 (Opta, 663.8/90). The drop shows up within a single, consistent data source.
- **Visualization**: `01_era_comparison_bars.png`, `04_era_touch_heatmap.png`.
- **Interpretation**: Spain holds a similar share of the ball under both managers, but moves it with noticeably fewer touches under de la Fuente — consistent with a shift away from Luis Enrique's dense, patient circulation toward something more direct.

### 2. Fewer passes into the final third, but more shots and much better shot accuracy

- **Evidence**: passes into the final third fall 63.7 → 45.0 per 90 (**-29.5%**), yet shots rise 14.5 → 16.6 per 90 (**+14.9%**) and shots on target jump 5.4 → 8.1 per 90 (**+51.4%**).
- **Visualization**: `03_shot_maps_by_tournament.png`, `05_progressive_pass_heatmap.png`.
- **Interpretation**: Spain builds through the final third less often via short combination play, but converts the attacks it does mount into shots — and on-target shots specifically — more reliably. Progressive carries rose (+20.9%) while progressive passes fell (-9.2%), pointing at more individual ball-carrying progression (Yamal, Nico Williams-type wing play) replacing some of the old intricate short-passing progression.

### 3. More shots, but each one worth less: average shot quality (xG/shot) declined

- **Evidence**: xG/90 falls 1.78 → 1.62 (-9.0%) despite the rise in shot volume. xG per shot: 0.123 (Luis Enrique) vs 0.097 (Luis de la Fuente).
- **Visualization**: `03_shot_maps_by_tournament.png` (compare shot marker sizes/spread across tournaments).
- **Interpretation**: the extra shot volume under de la Fuente comes with lower average shot quality per attempt — more shots from less advantageous positions, not necessarily better chance creation. This tempers finding 2: shots and shots-on-target both rose, but that isn't the same as generating better chances on average.

### 4. Results improved sharply even as underlying shot-quality metrics did not

- **Evidence**: Luis Enrique: 4W–3D–3L across 10 matches (40% win rate). Luis de la Fuente: 14W–1D–0L across 15 matches (93% win rate) — including a EURO 2024 and a World Cup 2026 title.
- **Methodological caveat (important)**: per the project's own ground rules, this is **not** evidence that the tactical shift *caused* the better results. Two eras with different opponents, different squad talent (a generational wave including Yamal, Nico Williams, Pedri's peak years), and different levels of competition depth cannot be separated from "the manager" using this data alone. Treat the style change (findings 1–3) and the results change (finding 4) as two things that happened in the same period, not a demonstrated cause-and-effect.

### 5. Territorial shift: from central buildup to wide, higher-up play

- **Evidence**: `04_era_touch_heatmap.png` shows Luis Enrique's touches concentrated through the central channel in Spain's own half and midfield; Luis de la Fuente's touches spread further right and further upfield.
- **Visualization**: `06_passing_network_comparison.png` — the Luis de la Fuente network (Spain vs Croatia, EURO2024) shows a direct long-range passing connection from right-back straight to the right winger (Carvajal → Yamal) that has no equivalent in the Luis Enrique network (Spain vs Sweden, EURO2020), where the ball moves through the deep central triangle (Laporte–Koke–Busquets–Llorente) before reaching wide areas.
- **Interpretation**: a visible territorial and structural shift toward using the right flank as a direct outlet, consistent with the emergence of a genuine wide 1v1 threat (Yamal) that Luis Enrique's squads didn't have in the same way.

### 6. Defensive activity fell, clearances rose

- **Evidence**: tackles/90 -17.1%, interceptions/90 -20.9%, recoveries/90 -7.8%, but clearances/90 **+45.2%**.
- **Interpretation**: read cautiously (small sample) — could reflect facing more sustained direct pressure at times, a deeper defensive block in some matches, or simply variance across 10 vs 15 matches. Worth revisiting once more matches (post-WC2026) are available, and alongside opponent-strength context this dataset doesn't yet encode.

---

## What this EDA does not yet answer

- Player-by-player evolution (e.g., Rodri's or Pedri's individual role change) — `players.csv` supports this but it hasn't been analyzed here yet.
- Possession-sequence-level detail (buildup → progression → final third → shot chains) — needs the possession-chain table flagged as a gap in the main README.
- Any opponent-strength adjustment — a weak-Saudi-Arabia performance and a France semi-final are both just "one match" in these averages.
