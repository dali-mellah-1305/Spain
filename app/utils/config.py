# -*- coding: utf-8 -*-
"""
Single source of truth for paths, labels and design tokens.

Colour policy (this is the whole rule, and it is deliberately narrow)
---------------------------------------------------------------------
**Hue always means era.** Luis Enrique is blue, Luis de la Fuente is orange —
in every chart, on every page. Tournaments never get their own hue: a tournament
is a *position in time*, so it lives on the x-axis and takes its era's colour.
That keeps the app down to one two-colour categorical scale, which clears the
colour-vision separation gates on the all-pairs test (ΔE 24.7 CVD / 33.6 normal)
rather than only the adjacent-pairs one.

Where a chart genuinely needs more series (comparing several players), it draws
from ``SERIES`` in fixed slot order — never cycled, never re-assigned when a
filter changes the series count — and is capped at ``MAX_SERIES``.

The app renders on a **dark surface**. Every value below is the dark-mode step
of the same palette, not a light value dimmed — the hues were re-stepped for the
dark band and validated as a set against this app's own surface (``SURFACE``).
Both the era pair and the segment palette clear every gate there, and on dark
all of them also reach 3:1 against the surface, which light mode could not
manage for three of the segment hues.
"""
from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
ROOT = APP_DIR.parent

#: Where to look for data, best first. ``data/clean/`` is what
#: ``src/clean_data.py`` writes and is the only directory the app is designed
#: against; the others are fallbacks so the app still starts on a fresh
#: checkout that has not run the cleaner yet (it then shows a warning).
DATA_DIR_CANDIDATES = [ROOT / "data" / "clean", ROOT / "data" / "final", ROOT / "Data"]

APP_TITLE = "Spain's Evolution"
APP_SUBTITLE = "Luis Enrique → Luis de la Fuente · 25 matches, four tournaments"

ERAS = ["Luis Enrique", "Luis de la Fuente"]
ERA_SHORT = {"Luis Enrique": "Enrique", "Luis de la Fuente": "De la Fuente"}
TOURNAMENTS = ["EURO2020", "WC2022", "EURO2024", "WC2026"]
TOURNAMENT_LABEL = {
    "EURO2020": "EURO 2020",
    "WC2022": "World Cup 2022",
    "EURO2024": "EURO 2024",
    "WC2026": "World Cup 2026",
}
TOURNAMENT_ERA = {
    "EURO2020": "Luis Enrique", "WC2022": "Luis Enrique",
    "EURO2024": "Luis de la Fuente", "WC2026": "Luis de la Fuente",
}
ROUND_ORDER = ["Group Stage", "Round of 32", "Round of 16", "Quarter-finals",
               "Semi-finals", "Final"]

# --------------------------------------------------------------------------- #
# Design tokens
# --------------------------------------------------------------------------- #

# Chrome & ink — dark mode
SURFACE = "#1a1a19"        # card / chart surface
PAGE = "#0d0d0d"           # page plane behind the cards
INK = "#ffffff"            # primary text
INK_2 = "#c3c2b7"          # secondary text
INK_MUTED = "#898781"      # axis labels, captions (the one mode-invariant step)
GRID = "#2c2c2a"           # hairline gridline
AXIS = "#383835"           # baseline / axis line
BORDER = "rgba(255,255,255,0.10)"

# Brand accent — chrome only. Never used as a series colour, so it can never be
# mistaken for data. Spain red is lightened slightly for the dark surface, where
# #c60b1e sits under 3:1 and reads as muddy rather than as an accent.
BRAND = "#e2213a"          # Spain red, stepped for dark
BRAND_GOLD = "#f2b705"

# Era identity — the only categorical scale in the app
ERA_COLORS = {"Luis Enrique": "#3987e5", "Luis de la Fuente": "#d95926"}
ERA_FILL = {"Luis Enrique": "rgba(57,135,229,0.20)",
            "Luis de la Fuente": "rgba(217,89,38,0.20)"}

#: Fixed categorical slot order, for the few charts that need >2 series.
#: The same eight hues as the light palette, stepped for the dark surface.
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500",
          "#d55181", "#008300", "#9085e9", "#e66767"]
MAX_SERIES = 6

#: Palette for the *segments* of a composition chart — pitch thirds, entry
#: channels, pass types, shot outcomes. It deliberately starts at slot 3,
#: skipping the two era hues: on a bar grouped by era, a blue segment meaning
#: "right flank" would collide head-on with blue meaning "Luis Enrique"
#: everywhere else in the app. Slots 3-8 are consecutive in the validated
#: order, so every adjacent pair still clears the colour-vision gates
#: (worst adjacent ΔE 8.4 CVD / 19.3 normal on this surface, and all six reach
#: 3:1 against it — which the light-mode steps could not manage for three).
SEGMENT_SERIES = SERIES[2:]

# Status — reserved, always shipped with a label or arrow, never colour alone.
# These four steps are fixed, never themed: all clear 3:1 on the dark surface.
GOOD = "#0ca30c"
WARNING = "#fab219"
CRITICAL = "#d03b3b"
DELTA_UP_TEXT = "#0ca30c"   # the dark-mode success text step

#: Single-hue sequential ramp for magnitude (heatmaps, density).
#: On a dark surface the direction reverses: the step nearest zero recedes
#: *toward* the surface, so the ramp runs dark → bright rather than light → dark.
SEQUENTIAL_BLUE = ["#1a1a19", "#0d366b", "#184f95", "#256abf",
                   "#3987e5", "#6da7ec", "#9ec5f4"]
#: Second sequential context, when a blue and an orange heatmap sit side by side.
SEQUENTIAL_ORANGE = ["#1a1a19", "#5c2410", "#8a3612", "#c14d20",
                     "#d95926", "#f2926a", "#f7bda2"]

FONT = ('system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", '
        "Arial, sans-serif")

#: Pitch rendering, matched to the card surface so a pitch reads as part of the
#: card. On dark the markings are a step *lighter* than the surface rather than
#: darker — the same recessive relationship, inverted.
PITCH_BG = SURFACE
PITCH_LINE = "#4a4a46"


def era_color(era: str) -> str:
    """Era hue, falling back to slot 1 for an unexpected label."""
    return ERA_COLORS.get(era, SERIES[0])


def sequential_for(era: str) -> list:
    """The one-hue ramp belonging to an era, for density plots."""
    return SEQUENTIAL_ORANGE if era == "Luis de la Fuente" else SEQUENTIAL_BLUE


def tournament_label(code: str) -> str:
    return TOURNAMENT_LABEL.get(code, code)


# --------------------------------------------------------------------------- #
# Provenance notices — the app surfaces the dataset's limits, it does not hide
# them. Text lives here so the same wording appears on every page that needs it.
#
# These are rendered inside `ui.notice`, which emits raw HTML: Markdown is not
# processed there, so emphasis is written as <strong>, not as asterisks.
# --------------------------------------------------------------------------- #

NOTE_POSSESSION = (
    "Possession here is a <strong>proxy, not the broadcast statistic</strong> — "
    "and the two sources compute it differently: share of possession chains for "
    "the 17 StatsBomb matches, share of on-ball touches for the 8 WC 2026 "
    "matches. Read cross-tournament possession as directional, not exact."
)
NOTE_XG_PROXY = (
    "World Cup 2026 has no official xG. Those shots use a distance/angle "
    "logistic model (5-fold CV log-loss 0.28, correlation 0.86 with real "
    "StatsBomb xG). <strong>Estimated</strong> and <strong>official</strong> "
    "values are distinguished everywhere they appear — they are never blended "
    "silently."
)
NOTE_CARRIES = (
    "Ball carries exist for the 17 StatsBomb matches only — Opta's taxonomy, "
    "which backs World Cup 2026, has no discrete carry event. The 8 WC 2026 "
    "matches are <strong>absent from carry figures, not zero</strong>."
)
NOTE_SAMPLE = (
    "10 matches against 15 is a small, unequal sample. Every difference below "
    "is directional evidence about two periods, not a demonstrated effect of "
    "the change in manager — squad, opponents and competition depth all moved "
    "at the same time."
)
