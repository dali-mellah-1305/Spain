# Spain's Evolution — Streamlit dashboard

A nine-page dashboard over the cleaned event data in `data/clean/`, comparing how
Spain played under Luis Enrique (EURO 2020 + World Cup 2022, 10 matches) and
under Luis de la Fuente (EURO 2024 + World Cup 2026, 15 matches).

Implements the architecture in `visualizations/07_streamlit_architecture.png`.
The departures from that diagram are listed in §7.

## 1. Running it

```bash
# once, from the repo root — builds data/clean/ and its quality report
python src/clean_data.py

# then
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
```

`data_loader.py` resolves paths from `pathlib.Path(__file__)`, so the working
directory does not matter. It prefers `data/clean/`, falls back to `data/final/`
and then the raw `Data/`, and shows a sidebar warning when it is not reading the
cleaned output — several charts depend on columns only the cleaning pass adds.

Python 3.9 is supported. `mplsoccer` is capped below 1.5 in `requirements.txt`
because 1.5+ imports `dataclasses.KW_ONLY` and needs Python 3.10; drop the cap on
a newer interpreter.

## 2. Three layers

```
data/clean/*.csv  →  app/utils/ (cache + filters + metrics + charts)  →  pages
```

| Module | Responsibility |
|---|---|
| `utils/config.py` | Paths, labels, design tokens, and the provenance wording reused across pages. |
| `utils/data_loader.py` | **The only module that reads from disk.** Every loader is `@st.cache_data`-wrapped. |
| `utils/filters.py` | **The only module that renders the sidebar**, and the only one that writes the selection to session state. |
| `utils/metrics.py` | Per-90 normalisation, era comparison, aggregation, passing networks. No I/O, no figures. |
| `utils/charts_mplsoccer.py` | Static pitch visuals: shot maps, heatmaps, pass maps, networks, entry maps. |
| `utils/charts_plotly.py` | Interactive figures: comparison bars, trends, distributions, scatters. |
| `utils/ui.py` | The stylesheet and the components pages are assembled from (header, section, KPI card, delta chip, notice, table view). |
| `utils/era_page.py` | The layout shared by pages 2 and 3, which the architecture specifies as mirrors of one another. |

Pages hold **layout only**. No page reads a CSV, computes a metric, or builds a
figure of its own.

## 3. The pages

| | Page | What it answers |
|---|---|---|
| — | `home.py` | What this is, what the data can and cannot answer, how clean the tables are. |
| 1 | `pages/1_Overview.py` | Every headline metric under both managers, the size of each change, the record. |
| 2 | `pages/2_Luis_Enrique.py` | EURO 2020 + WC 2022 on their own terms. |
| 3 | `pages/3_Luis_de_la_Fuente.py` | EURO 2024 + WC 2026, same layout mirrored. |
| 4 | `pages/4_Passing.py` | Volume, completion, progression, pitch thirds, passing networks. |
| 5 | `pages/5_Shooting.py` | Shot maps, xG, shot quality — official and estimated xG kept apart. |
| 6 | `pages/6_Possession.py` | The proxy, its limits, and whether more of the ball bought anything. |
| 7 | `pages/7_Final_Third.py` | Entries into the final third and the box; pass-versus-carry progression. |
| 8 | `pages/8_Players.py` | Squad turnover, and the 14 players whose own role can be traced across the change. |

## 4. Filters and session state

`filters.render_sidebar()` returns a `Selection` — the resolved match set, the
matching `team_stats` rows, and an `events()` accessor that loads the right
cached event table and trims it to the selection. Pages never filter raw frames
themselves.

Filters are nested coarse → fine: era narrows the tournament options, tournament
narrows opponent and round. Two details are worth knowing:

* **Selections survive page switches.** Each control keeps its value in a plain
  session-state entry and receives it back as the widget's `default`; the widget
  owns a *separate* key. This indirection is necessary because `st.navigation`
  resets widget state when it changes page — a control that owned the persistent
  value would render empty on the first run of every new page, while the page
  below it still showed the old selection.
* **A temporarily unavailable choice is kept, not dropped.** Pages 2 and 3 pin an
  era, which takes the other era's tournaments off the list. Those selections are
  preserved and reappear when you leave, rather than being silently discarded.

An era or tournament selection that would be empty is read as "all" and written
back, so the control always shows what is actually in force.

## 5. Charting rules

The app renders on a **dark surface** (`#0d0d0d` page, `#1a1a19` cards). Every
colour is the dark-mode step of its hue, re-stepped for that band and validated
as a set against this surface — not a light value dimmed.

**Hue means era, everywhere.** Luis Enrique is blue `#3987e5`, Luis de la Fuente
is orange `#d95926`, in every chart on every page. Tournaments never get their
own hue — a tournament is a position in time, so it sits on the x-axis and takes
its era's colour. That keeps the app to a single two-colour categorical scale,
which clears the colour-vision separation gates on the all-pairs test (ΔE 26.8
CVD / 31.8 normal), not just the adjacent-pairs one. Spain red (`#e2213a`, a
lighter step than the flag's `#c60b1e`, which sits under 3:1 on this surface) is
chrome only and is never a series colour, so nothing in the interface can be
mistaken for data.

Two consequences of the dark surface worth noting: the sequential ramps run
**dark → bright** rather than light → dark, so the step nearest zero recedes
toward the surface; and in-bar percentage labels take their ink from each
segment's own luminance rather than being fixed to white, because the dark
palette's yellow and magenta steps are light enough that white on them lands
near 3:1.

The four theme values in `.streamlit/config.toml` must stay in step with the
tokens in `utils/config.py` — Streamlit paints its own widgets from the former,
the custom stylesheet paints everything else, and a mismatch shows as cards that
do not sit on their own background.

Composition charts (pitch thirds, entry channels, shot outcomes) draw their
segments from `SEGMENT_SERIES`, which skips the two era hues: a blue segment
meaning "right flank" inside a bar labelled "Luis Enrique" would fight the one
colour rule the app has.

Other rules held throughout: one y-axis, never two; a legend whenever two or more
series are drawn, plus direct labels; every chart ships a table view of the frame
it was built from (`ui.table_view`) as the accessible route to the same values.
On this surface every era and segment colour reaches 3:1, which the light-mode
steps could not manage for three of the segment hues.

Chart titles are drawn as paper-space annotations, not with `layout.title`:
Plotly anchors its own title against the figure container, and on a short figure
with a two-line title it places the first line above the top edge where it is
clipped — `automargin` does not rescue it. `_finish()` lays out the band above
the plot area explicitly instead (legend nearest the plot, then subtitle, then
title) and sizes the top margin from what that band actually contains.

The era comparison bars scale **each row to its own larger value**, because the
metrics run from 823 passes per 90 down to 0.098 xG per shot — on one shared axis
the pass rows would be the only visible bars. The rule is printed on the chart.

Pitch visuals always use `normalized_x` / `normalized_y` (a common 0-100 pitch),
never the raw `x`/`y`, which are in each source's own system. Those normalised
values are square, so they are mapped onto real 105 × 68 m proportions before
drawing — otherwise the pitch comes out as tall as it is wide and every distance
reads wrongly.

## 6. What the app refuses to do

The dataset's limits are surfaced, not hidden. Wording lives in `config.py` so it
is identical everywhere it appears.

- **No causal claim.** More than half the squad changed at the same time as the
  manager; 10 matches against 15 cannot separate them. Every difference is
  described as something that happened.
- **Possession is labelled a proxy** — and a *different* proxy per source. The
  Possession page says so before its first figure, and flags a selection that
  mixes both definitions.
- **Estimated xG is never blended into official xG.** World Cup 2026 shots carry
  a model estimate; they are drawn with a dashed outline, named in the legend,
  and counted separately in every table.
- **A gap is never shown as a zero.** Carries do not exist for the 8 World Cup
  2026 matches, so pages that use them report the coverage instead of implying
  zero, and `metrics.coverage_note()` names the shortfall.
- **A source limitation is explained, not left blank.** Passing networks need a
  pass recipient, which only StatsBomb logs, so a World Cup 2026 selection gets
  an explanation rather than an empty pitch.

## 7. Where this departs from the architecture diagram

1. **`streamlit_app.py` is a router, and the landing content lives in
   `home.py`.** The diagram assumes filename-based page discovery, which derives
   each sidebar label from the filename — that makes the entry point read as
   "streamlit app" in the navigation. `st.navigation` is Streamlit's own API for
   naming and ordering pages, so the labels in the sidebar are the ones a visitor
   should see. The numbered files in `pages/` still fix the order. The diagram
   allows the entry point to mirror page 1 *or* redirect; it instead orients —
   what the data is, what it cannot answer, how clean it is — rather than
   duplicating the Overview.
2. **Three modules beyond the five in the diagram**: `config.py` (tokens and
   shared wording), `ui.py` (stylesheet and components), and `era_page.py` (the
   layout pages 2 and 3 share, which the diagram itself describes as mirrors).
   The five specified modules keep exactly the responsibilities given to them.
3. **Page 9, Match Explorer, was removed.** The diagram's ninth page (one match,
   event by event, on the pitch) was built and then taken out at the project
   owner's request. With it went the sidebar's match and event-type selectors,
   `data_loader.load_match_events()` and `charts_mplsoccer.match_events()`, which
   nothing else used. Single-match views survive where they serve a page's own
   question: the passing networks and the pass map on pages 2–4 each take a
   match selector.

## 8. Caching

Only `data_loader.py` touches disk, and every loader is `@st.cache_data`-wrapped
and keyed by its arguments. The large event files are read once, whole, under
their own cache key; the per-tournament loaders are masks over that cached frame,
so changing a filter is a mask rather than another 12 MB CSV parse.

Nothing in `metrics.py` or the chart modules is cached: they work on
already-filtered frames where recomputation is cheap, and caching derived,
filter-shaped results bloats memory faster than it saves time.

## 9. Deploying

Streamlit Community Cloud: point it at this repo, set the app file to
`app/streamlit_app.py`, and it picks up `app/requirements.txt`. The data is
static, so no database or scheduled job is needed — but `data/clean/` must be
committed, or `src/clean_data.py` run as part of the build, since the app does
not generate it. `passes.csv` is the largest file at about 12 MB and is the
candidate for trimming unused columns if repo size becomes a problem.
