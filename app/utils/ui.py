# -*- coding: utf-8 -*-
"""
Presentation layer: the stylesheet, plus the small set of components every page
is assembled from (page header, section rule, KPI card, delta chip, provenance
badge, coverage notice, table view).

Pages call these instead of writing their own markup, so spacing, type scale and
colour stay identical across every page. Nothing here loads data or computes a
metric — components take values already computed by ``metrics.py``.
"""
from __future__ import annotations

import html
from typing import Optional, Sequence

import pandas as pd
import streamlit as st

from . import config as C

# --------------------------------------------------------------------------- #
# Stylesheet
# --------------------------------------------------------------------------- #

_CSS = f"""
<style>
  :root {{
    --surface: {C.SURFACE};
    --page: {C.PAGE};
    --ink: {C.INK};
    --ink-2: {C.INK_2};
    --muted: {C.INK_MUTED};
    --grid: {C.GRID};
    --axis: {C.AXIS};
    --border: {C.BORDER};
    --brand: {C.BRAND};
    --gold: {C.BRAND_GOLD};
    --enrique: {C.ERA_COLORS['Luis Enrique']};
    --fuente: {C.ERA_COLORS['Luis de la Fuente']};
    --good: {C.DELTA_UP_TEXT};
    --crit: {C.CRITICAL};
  }}

  html, body, button, input, select, textarea,
  [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
  [data-testid="stHeader"] {{
    font-family: {C.FONT};
  }}

  /* Streamlit's icons are font ligatures. A font-family rule broad enough to
     catch them (an attribute match on their emotion class, say) renders the
     ligature's own name — "keyboard_arrow_right" — as literal text on top of
     the label it sits beside. Font-family inherits, so the rule above reaches
     everything through the two containers, and the icon font is put back here
     explicitly rather than relying on specificity. */
  span[data-testid="stIconMaterial"], [class*="material-symbols"] {{
    font-family: "Material Symbols Rounded", "Material Icons" !important;
  }}
  .stApp {{ background: var(--page); }}
  .block-container {{ padding-top: 2.1rem; padding-bottom: 4rem; max-width: 1400px; }}

  /* Streamlit's own furniture we don't need */
  #MainMenu, footer, header [data-testid="stStatusWidget"] {{ visibility: hidden; }}

  /* ---------------- page header ---------------- */
  .pg-head {{
    display: flex; align-items: flex-start; gap: 1rem;
    padding: 0 0 1.15rem 0; margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--grid);
  }}
  .pg-head .bar {{
    width: 4px; align-self: stretch; min-height: 3.1rem; border-radius: 2px;
    background: linear-gradient(180deg, var(--brand) 0%, var(--gold) 100%);
    flex: 0 0 4px;
  }}
  .pg-head .eyebrow {{
    font-size: .705rem; font-weight: 650; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted); margin-bottom: .3rem;
  }}
  .pg-head h1 {{
    font-size: 1.82rem; font-weight: 680; letter-spacing: -.021em;
    color: var(--ink); margin: 0 0 .34rem 0; line-height: 1.16;
  }}
  .pg-head p {{
    font-size: .935rem; color: var(--ink-2); margin: 0; max-width: 78ch;
    line-height: 1.5;
  }}

  /* ---------------- section rule ---------------- */
  .sec {{ margin: 2.3rem 0 1.05rem 0; }}
  .sec h2 {{
    font-size: 1.055rem; font-weight: 660; letter-spacing: -.008em;
    color: var(--ink); margin: 0; display: flex; align-items: center; gap: .6rem;
  }}
  .sec h2::before {{
    content: ""; width: 14px; height: 2px; border-radius: 1px;
    background: var(--accent, var(--brand)); flex: 0 0 14px;
  }}
  .sec p {{
    font-size: .875rem; color: var(--ink-2); margin: .42rem 0 0 1.2rem;
    max-width: 84ch; line-height: 1.5;
  }}

  /* ---------------- KPI card ---------------- */
  .kpi {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 11px; padding: 1rem 1.1rem 1.05rem 1.1rem;
    height: 100%; position: relative; overflow: hidden;
  }}
  .kpi::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--accent, var(--axis));
  }}
  .kpi .lab {{
    font-size: .695rem; font-weight: 640; letter-spacing: .085em;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: .52rem; display: block; line-height: 1.35;
  }}
  .kpi .val {{
    font-size: 1.94rem; font-weight: 640; letter-spacing: -.031em;
    color: var(--ink); line-height: 1.02; display: block;
  }}
  .kpi .val .unit {{
    font-size: .92rem; font-weight: 550; color: var(--ink-2);
    letter-spacing: 0; margin-left: .13rem;
  }}
  .kpi .sub {{
    font-size: .775rem; color: var(--ink-2); margin-top: .5rem;
    line-height: 1.42; display: block;
  }}

  /* ---------------- delta chip ---------------- */
  .chip {{
    display: inline-flex; align-items: center; gap: .26rem;
    font-size: .765rem; font-weight: 620; border-radius: 6px;
    padding: .13rem .42rem; margin-top: .52rem;
    font-variant-numeric: tabular-nums;
  }}
  /* Tint strengths are raised for the dark surface: an .10 alpha wash that
     reads as a chip on white disappears on near-black. */
  .chip.up   {{ color: var(--good); background: rgba(12,163,12,.16); }}
  .chip.down {{ color: var(--crit); background: rgba(208,59,59,.18); }}
  .chip.flat {{ color: var(--ink-2); background: rgba(255,255,255,.07); }}
  .chip .arw {{ font-size: .72rem; line-height: 1; }}

  /* ---------------- badges ---------------- */
  .badge {{
    display: inline-flex; align-items: center; gap: .3rem;
    font-size: .705rem; font-weight: 620; letter-spacing: .012em;
    border-radius: 5px; padding: .17rem .46rem; margin: 0 .3rem .3rem 0;
    border: 1px solid var(--border); color: var(--ink-2); background: var(--surface);
    white-space: nowrap;
  }}
  .badge .dot {{
    width: 7px; height: 7px; border-radius: 50%; flex: 0 0 7px;
    background: var(--dot, var(--muted));
  }}
  /* On dark the badge text takes a light step of its own hue, not a dark one —
     #0d366b on near-black is unreadable. */
  .badge.official  {{ color: #9ec5f4; background: rgba(57,135,229,.16);
                      border-color: rgba(57,135,229,.34); }}
  .badge.estimated {{ color: #f7bda2; background: rgba(217,89,38,.18);
                      border-color: rgba(217,89,38,.36); }}

  /* ---------------- notice ---------------- */
  .notice {{
    background: var(--surface); border: 1px solid var(--border);
    border-left: 3px solid var(--nc, var(--gold));
    border-radius: 8px; padding: .72rem .9rem;
    font-size: .845rem; color: var(--ink-2); line-height: 1.53;
    margin: .3rem 0 1rem 0;
  }}
  .notice strong {{ color: var(--ink); font-weight: 640; }}
  .notice .nt {{
    font-size: .69rem; font-weight: 660; letter-spacing: .085em;
    text-transform: uppercase; color: var(--muted);
    display: block; margin-bottom: .22rem;
  }}

  /* ---------------- era legend ---------------- */
  .legend {{ display: flex; gap: 1.1rem; flex-wrap: wrap; margin: .1rem 0 .85rem 0; }}
  .legend .it {{
    display: inline-flex; align-items: center; gap: .4rem;
    font-size: .8rem; font-weight: 570; color: var(--ink-2);
  }}
  .legend .sw {{ width: 12px; height: 12px; border-radius: 3px; flex: 0 0 12px; }}

  /* ---------------- match result pills ---------------- */
  .form {{ display: flex; gap: .26rem; flex-wrap: wrap; align-items: center; }}
  .form .r {{
    width: 1.42rem; height: 1.42rem; border-radius: 5px;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: .715rem; font-weight: 700; color: #fff;
  }}
  .form .r.W {{ background: {C.GOOD}; }}
  .form .r.D {{ background: {C.INK_MUTED}; }}
  .form .r.L {{ background: {C.CRITICAL}; }}

  /* ---------------- sidebar ---------------- */
  [data-testid="stSidebar"] {{
    background: var(--surface); border-right: 1px solid var(--grid);
    min-width: 308px;   /* wide enough that "Luis de la Fuente" is not truncated */
  }}
  [data-testid="stSidebar"] [data-baseweb="tag"] {{
    max-width: 100%;    /* let a multiselect pill show its whole label */
  }}
  [data-testid="stSidebar"] .block-container {{ padding-top: 1.4rem; }}
  .sb-head {{
    font-size: .695rem; font-weight: 660; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted);
    margin: 1.15rem 0 .1rem 0; padding-top: .8rem;
    border-top: 1px solid var(--grid);
  }}
  .sb-head.first {{ border-top: none; padding-top: 0; margin-top: .2rem; }}
  .sb-brand {{
    display: flex; align-items: center; gap: .6rem; margin-bottom: 1.1rem;
  }}
  .sb-brand .flag {{
    width: 30px; height: 21px; border-radius: 3px; flex: 0 0 30px;
    background: linear-gradient(180deg, var(--brand) 0 26%, var(--gold) 26% 74%,
                                var(--brand) 74% 100%);
  }}
  .sb-brand .t {{ font-size: .93rem; font-weight: 670; color: var(--ink);
                  line-height: 1.2; }}
  .sb-brand .s {{ font-size: .7rem; color: var(--muted); }}
  .sb-count {{
    font-size: .78rem; color: var(--ink-2); background: var(--page);
    border: 1px solid var(--border); border-radius: 7px;
    padding: .5rem .62rem; margin-top: .9rem; line-height: 1.48;
  }}
  .sb-count b {{ color: var(--ink); font-variant-numeric: tabular-nums; }}

  /* ---------------- tabs & expanders ---------------- */
  .stTabs [data-baseweb="tab-list"] {{
    gap: .1rem; border-bottom: 1px solid var(--grid);
  }}
  .stTabs [data-baseweb="tab"] {{
    height: 2.45rem; padding: 0 .95rem; font-size: .87rem; font-weight: 580;
    color: var(--ink-2);
  }}
  .stTabs [aria-selected="true"] {{ color: var(--ink); font-weight: 650; }}
  [data-testid="stExpander"] {{
    border: 1px solid var(--border); border-radius: 9px; background: var(--surface);
  }}
  [data-testid="stExpander"] summary {{ font-size: .825rem; font-weight: 580; }}

  /* dataframes */
  [data-testid="stDataFrame"] {{ border-radius: 8px; }}
  .stPlotlyChart, [data-testid="stImage"] {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 11px; padding: .32rem;
  }}
  [data-testid="stImage"] img {{ border-radius: 9px; }}

  .foot {{
    margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--grid);
    font-size: .765rem; color: var(--muted); line-height: 1.55;
  }}
</style>
"""


def configure_app() -> None:
    """``st.set_page_config``. Called once, by the entry point only.

    Page config has to be the first Streamlit call in a run, and the entry
    point's ``st.navigation`` comes before any page body — so the entry point
    owns this and the pages own their stylesheet.
    """
    st.set_page_config(page_title=C.APP_TITLE, page_icon="⚽", layout="wide",
                       initial_sidebar_state="expanded")


def page_setup(page_title: str = "", icon: str = "⚽") -> None:
    """Inject the stylesheet. First call in every page body.

    ``page_title`` and ``icon`` are accepted and ignored here: the browser tab
    title and the sidebar label come from the entry point's ``st.Page``
    declarations, which keeps one name per page instead of two that can drift.
    """
    st.markdown(_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #

def page_header(eyebrow: str, title: str, lede: str) -> None:
    st.markdown(
        f'<div class="pg-head"><div class="bar"></div><div>'
        f'<div class="eyebrow">{html.escape(eyebrow)}</div>'
        f"<h1>{html.escape(title)}</h1><p>{lede}</p></div></div>",
        unsafe_allow_html=True)


def section(title: str, note: str = "", accent: Optional[str] = None) -> None:
    style = f' style="--accent:{accent}"' if accent else ""
    body = f"<p>{note}</p>" if note else ""
    st.markdown(f'<div class="sec"{style}><h2>{html.escape(title)}</h2>{body}</div>',
                unsafe_allow_html=True)


def _fmt(value, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, str):
        return value
    if decimals == 0:
        return f"{value:,.0f}"
    return f"{value:,.{decimals}f}"


def delta_chip(pct: Optional[float], *, higher_is_better: bool = True,
               suffix: str = " vs Enrique", delta_unit: str = "%") -> str:
    """Signed change as an arrow + number + unit.

    Direction is carried by the arrow and the sign, not by the colour alone —
    colour only reinforces whether the movement is favourable, which is a
    judgement the caller makes with ``higher_is_better``.

    ``delta_unit`` exists because a relative change in a metric that is itself a
    percentage reads badly: a win rate going 40% → 93% is "+133%" relatively but
    "+53 points" plainly, and the second is what a reader means. Callers pass
    ``delta_unit=" pts"`` with an already-differenced value for those.
    """
    if pct is None or pd.isna(pct):
        return ""
    if abs(pct) < 0.05:
        return (f'<span class="chip flat"><span class="arw">→</span>'
                f"no change{suffix}</span>")
    up = pct > 0
    good = up if higher_is_better else not up
    cls = "up" if good else "down"
    arrow = "▲" if up else "▼"
    return (f'<span class="chip {cls}"><span class="arw">{arrow}</span>'
            f"{abs(pct):,.1f}{delta_unit}{suffix}</span>")


def kpi(label: str, value, *, unit: str = "", decimals: int = 1,
        sub: str = "", accent: Optional[str] = None,
        delta_pct: Optional[float] = None, higher_is_better: bool = True,
        delta_suffix: str = " vs Enrique", delta_unit: str = "%") -> None:
    """One metric card. ``value`` of ``None``/NaN renders as an em dash."""
    unit_html = f'<span class="unit">{html.escape(unit)}</span>' if unit else ""
    chip = delta_chip(delta_pct, higher_is_better=higher_is_better,
                      suffix=delta_suffix,
                      delta_unit=delta_unit) if delta_pct is not None else ""
    sub_html = f'<span class="sub">{sub}</span>' if sub else ""
    style = f' style="--accent:{accent}"' if accent else ""
    st.markdown(
        f'<div class="kpi"{style}><span class="lab">{html.escape(label)}</span>'
        f'<span class="val">{_fmt(value, decimals)}{unit_html}</span>'
        f"{chip}{sub_html}</div>",
        unsafe_allow_html=True)


def kpi_row(cards: Sequence[dict], per_row: int = 4) -> None:
    """Lay KPI cards out in equal columns, wrapping to new rows."""
    for start in range(0, len(cards), per_row):
        chunk = cards[start:start + per_row]
        cols = st.columns(len(chunk), gap="small")
        for col, card in zip(cols, chunk):
            with col:
                kpi(**card)


def notice(body: str, *, kind: str = "note", label: Optional[str] = None) -> None:
    """A provenance / limitation callout. ``kind``: note | caution | gap."""
    colors = {"note": C.SERIES[0], "caution": C.BRAND_GOLD, "gap": C.INK_MUTED}
    labels = {"note": "Note", "caution": "Read with care", "gap": "Known gap"}
    st.markdown(
        f'<div class="notice" style="--nc:{colors.get(kind, C.BRAND_GOLD)}">'
        f'<span class="nt">{html.escape(label or labels.get(kind, "Note"))}</span>'
        f"{body}</div>",
        unsafe_allow_html=True)


def xg_badge(quality: str) -> str:
    """``official`` / ``estimated`` pill for xG provenance."""
    q = (quality or "").lower()
    if q.startswith("official"):
        return ('<span class="badge official"><span class="dot" '
                f'style="--dot:{C.SERIES[0]}"></span>official xG (StatsBomb)</span>')
    if q.startswith("estimated"):
        return ('<span class="badge estimated"><span class="dot" '
                f'style="--dot:{C.SERIES[1]}"></span>estimated xG (proxy model)</span>')
    return f'<span class="badge">{html.escape(quality)}</span>'


def badges(items: Sequence[str]) -> None:
    st.markdown("".join(items), unsafe_allow_html=True)


def era_legend(eras: Sequence[str] = tuple(C.ERAS)) -> None:
    """Explicit legend so era identity is never carried by colour alone."""
    items = "".join(
        f'<span class="it"><span class="sw" style="background:{C.era_color(e)}">'
        f"</span>{html.escape(e)}</span>" for e in eras)
    st.markdown(f'<div class="legend">{items}</div>', unsafe_allow_html=True)


def form_string(results: Sequence[str]) -> None:
    """W/D/L pills — letter plus colour, so the letter alone is readable."""
    pills = "".join(f'<span class="r {html.escape(str(r))}">{html.escape(str(r))}</span>'
                    for r in results)
    st.markdown(f'<div class="form">{pills}</div>', unsafe_allow_html=True)


def table_view(df: pd.DataFrame, label: str = "Show the numbers behind this chart",
               **kwargs) -> None:
    """Every chart ships its own table view.

    Two reasons this is not optional: it is the accessible fallback for readers
    who cannot separate the marks by colour, and three of the palette's series
    colours sit below 3:1 against this surface, which obliges a text route to
    the same values.
    """
    if df is None or df.empty:
        return
    with st.expander(label):
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)


def empty_state(message: str, hint: str = "") -> None:
    st.markdown(
        f'<div class="notice" style="--nc:{C.INK_MUTED}">'
        f'<span class="nt">Nothing to show</span>{html.escape(message)}'
        + (f"<br><span style='color:{C.INK_MUTED}'>{html.escape(hint)}</span>"
           if hint else "")
        + "</div>",
        unsafe_allow_html=True)


def footer(sources: str = "") -> None:
    # The data-source line that used to close every page now lives in the
    # root README (§1); only a page-specific note is rendered here.
    if sources:
        st.markdown(f'<div class="foot">{sources}</div>',
                    unsafe_allow_html=True)
