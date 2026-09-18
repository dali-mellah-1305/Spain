# Streamlit app — spec, and what was built against it

This file was written as the **spec** for the dashboard in
`07_streamlit_architecture.png`, before any code existed. The app is now built.

**The living documentation is [`app/README.md`](app/README.md)** — module layout,
filter behaviour, charting rules, caching, and deployment. This file is kept as
the record of what was specified and where the implementation diverged, so the
diagram and the code can still be read against each other.

## Built as specified

- **Three layers**, `data/ → app/utils/ → app/pages/`, with the data directory
  read-only and nothing in `app/` writing to it.
- **The five core modules**, each keeping exactly the responsibility the diagram
  gave it: `data_loader.py` is the only module that calls `pd.read_csv` and every
  loader is `@st.cache_data`-wrapped; `filters.py` is the only module that renders
  the sidebar and the only one that writes the selection to `st.session_state`;
  `metrics.py` does per-90 normalisation, era comparison and aggregation with no
  I/O and no figures; `charts_mplsoccer.py` and `charts_plotly.py` build the
  static pitch visuals and the interactive figures.
- **Pages 1–8**, numbered in `app/pages/`, with the page-to-table mapping from
  §5 of the spec. Page 9 was built too, then removed — see departure 4.
- **Filters shared across pages** via session state, so "Luis de la Fuente + WC
  2026" chosen on page 1 is still in force on page 6.
- **Pages hold layout only** — no page reads a CSV, computes a metric, or builds
  a figure of its own.
- **Caching as specified**: only the loaders are cached, keyed by their
  arguments; nothing in `metrics.py` or the chart modules is.
- **The constraints in §8 surfaced rather than hidden** — coordinate systems,
  the possession proxy, estimated versus official xG, and partial carry
  coverage. (The fifth, the missing possession-chain table, was surfaced on the
  Match Explorer and left the app with it; it remains documented in
  `README.md` §5.)

## Four departures, and why

1. **Data lives in `data/clean/`, not `data/final/`.** The spec assumed a
   `data/final/` built by `src/`; the collected tables were in `Data/`. They
   needed a cleaning pass before the app could read them (seven concrete defects,
   two source vocabularies, and several columns the charts require — see
   `README.md` §7), so `src/clean_data.py` writes `data/clean/` and
   `data_loader.py` resolves `data/clean/` → `data/final/` → `Data/`, warning in
   the sidebar when it is not reading the cleaned output.

2. **`streamlit_app.py` is a router; the landing content is in `home.py`.** The
   spec assumed filename-based page discovery ("filename prefix number = menu
   order, no router to write by hand"). That does order the pages, but it also
   derives every sidebar label from the filename — which makes the entry point
   read as "streamlit app" in the navigation. `st.navigation` is Streamlit's own
   API for naming and ordering pages, so the entry point declares the pages and
   the sidebar shows the labels a visitor should see. The numbered files in
   `pages/` still fix the order. The spec allowed the entry
   point to mirror page 1 *or* redirect to it; it does neither — it orients (what
   the data is, what it cannot answer, how clean it is) instead of duplicating
   the Overview.

3. **Three modules beyond the five.** `config.py` holds paths, labels, design
   tokens and the provenance wording reused across pages; `ui.py` holds the
   stylesheet and the components every page is assembled from; `era_page.py`
   holds the layout pages 2 and 3 share, which the spec itself describes as
   mirrors of one another ("Same as page 2, mirrored"). Without the third, that
   layout would exist twice.

4. **Page 9, Match Explorer, was removed.** It was built as specified — a
   match-level drill into passes, shots, carries and defensive actions, driven
   by match and event-type selectors in the sidebar — and then taken out at the
   project owner's request. The sidebar controls, loader and chart builder that
   only it used went with it. Single-match views remain where they answer a
   page's own question: the passing networks and pass map on pages 2–4.

## Also delivered, beyond the spec

The spec's own parent README listed player-level analysis and
final-third/penalty-area entry maps as outstanding. Both are in the app — page 8
traces the 14 players who appear under both managers, and page 7 maps entries
into the final third and the penalty area.

Possession-sequence chains remain out of scope: they need a `possessions.csv`
that the WC2026 source cannot support like-for-like (`README.md` §5).
