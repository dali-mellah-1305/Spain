# -*- coding: utf-8 -*-
"""
Interactive charts. Every figure here is built from a tidy frame the caller
already has, so the same frame can be handed to ``ui.table_view`` and the chart
and the table can never disagree.

House rules applied to all of them
----------------------------------
* **One y-axis, ever.** Two measures on different scales become two charts or an
  indexed view — never a second axis, which lets the author choose the crossing
  point and therefore the conclusion.
* **Hue = era** (see ``config``). A filter that drops a series never repaints
  the survivors, because each trace's colour comes from its era, not its order.
* **A legend whenever two or more series are drawn**, plus direct labels on bars
  and on the last point of a line — so identity never rests on colour alone.
* **Recessive chrome**: hairline horizontal gridlines only, no vertical grid, no
  chart border (the card supplies it), axis lines in the muted ink.
* Bars carry rounded ends and a 2px surface gap; markers are at least 8px.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import config as C

_HOVER = dict(bgcolor=C.SURFACE, bordercolor=C.GRID,
              font=dict(family=C.FONT, size=12, color=C.INK))


def _finish(fig: go.Figure, *, title: str = "", subtitle: str = "",
            height: int = 380, showlegend: bool = False,
            xgrid: bool = False, ygrid: bool = True,
            hovermode: str = "closest") -> go.Figure:
    # Title and subtitle are drawn as paper-space annotations rather than with
    # `layout.title`. Plotly's own title anchors against the figure container,
    # and on a short figure with a two-line title it places the first line above
    # the top edge, where it is clipped — `automargin` does not rescue it.
    # Annotations anchored to the plot area are positioned predictably, so the
    # band above the plot is laid out explicitly here: legend nearest the plot,
    # then the subtitle, then the title.
    legend_band = 24 if showlegend else 0
    subtitle_band = 18 if (title and subtitle) else 0
    title_band = 23 if title else 0
    top = 12 + legend_band + subtitle_band + title_band

    if title and subtitle:
        fig.add_annotation(
            x=0, y=1, xref="paper", yref="paper", xanchor="left",
            yanchor="bottom", yshift=legend_band + 2, showarrow=False,
            text=subtitle, align="left",
            font=dict(family=C.FONT, size=12, color=C.INK_MUTED))
    if title:
        fig.add_annotation(
            x=0, y=1, xref="paper", yref="paper", xanchor="left",
            yanchor="bottom", yshift=legend_band + subtitle_band + 3,
            showarrow=False, text=f"<b>{title}</b>", align="left",
            font=dict(family=C.FONT, size=15, color=C.INK))

    fig.update_layout(
        paper_bgcolor=C.SURFACE, plot_bgcolor=C.SURFACE,
        font=dict(family=C.FONT, size=12, color=C.INK_2),
        margin=dict(l=8, r=18, t=top, b=10),
        height=height + top, hovermode=hovermode, hoverlabel=_HOVER,
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1, yref="paper",
                    xanchor="right", x=1, font=dict(size=11.5),
                    bgcolor="rgba(0,0,0,0)", itemclick="toggleothers"),
        dragmode=False,
    )
    fig.update_xaxes(showgrid=xgrid, gridcolor=C.GRID, gridwidth=1,
                     zeroline=False, linecolor=C.AXIS, showline=True, ticks="",
                     tickfont=dict(size=11.5, color=C.INK_MUTED),
                     title_font=dict(size=11.5, color=C.INK_MUTED))
    fig.update_yaxes(showgrid=ygrid, gridcolor=C.GRID, gridwidth=1,
                     zeroline=False, showline=False, ticks="",
                     tickfont=dict(size=11.5, color=C.INK_MUTED),
                     title_font=dict(size=11.5, color=C.INK_MUTED))
    return fig


def _fmt(value, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.{decimals}f}"


def _label_ink(fill: str) -> str:
    """Text colour for a label sitting *on* a filled mark.

    Picked from the fill's own luminance rather than fixed to white: the dark
    palette's yellow and magenta steps are light enough that white text on them
    lands near 3:1, while its green and violet steps need white. Choosing per
    segment keeps every in-bar percentage readable.
    """
    hex_value = fill.lstrip("#")
    if len(hex_value) != 6:
        return "#ffffff"
    channels = []
    for offset in (0, 2, 4):
        value = int(hex_value[offset:offset + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045
                        else ((value + 0.055) / 1.055) ** 2.4)
    luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    # Contrast of white against this fill, versus near-black against it.
    return "#ffffff" if (1.05 / (luminance + 0.05)) >= ((luminance + 0.05) / 0.05) \
        else "#0b0b0b"


# --------------------------------------------------------------------------- #
# Era comparison — the dashboard's signature chart
# --------------------------------------------------------------------------- #

def era_comparison_bars(comparison: pd.DataFrame, *, title: str = "",
                        subtitle: str = "", height: Optional[int] = None
                        ) -> go.Figure:
    """Paired horizontal bars, one metric per row, **each row on its own scale**.

    The metrics here run from 823 passes per 90 down to 0.098 xG per shot. On a
    single shared axis the pass rows would be the only visible bars and every
    other row would collapse to a sliver — a chart that hides thirteen of its
    fourteen findings. So each row is scaled to the larger of its own two
    values: bar *length within a row* is the ratio between the eras, the real
    magnitudes are written on the bars, and the axis carries no ticks because
    comparing a length in one row to a length in another would mean nothing.

    Horizontal because metric names are words, not codes: they read straight
    across on a y-axis instead of being angled under a vertical one.
    """
    if comparison.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)

    df = comparison.iloc[::-1].reset_index(drop=True)  # first metric on top
    labels = df["label"].tolist()

    # Per-row denominator. A row where both eras are zero or unknown scales to
    # 1 so it renders as an empty row rather than dividing by zero.
    row_max = (df[list(C.ERAS)].abs().max(axis=1).replace(0, np.nan)
               .fillna(1.0))

    fig = go.Figure()
    for era in C.ERAS:
        values = df[era]
        scaled = (values / row_max * 100).fillna(0)
        text = [f"{_fmt(v, int(d))}{u}" for v, d, u in
                zip(values, df["decimals"], df["unit"])]
        matches_col = f"matches_{'enrique' if era == C.ERAS[0] else 'fuente'}"
        fig.add_trace(go.Bar(
            y=labels, x=scaled, orientation="h", name=era,
            marker=dict(color=C.era_color(era),
                        line=dict(color=C.SURFACE, width=2)),
            text=text, textposition="outside",
            textfont=dict(size=11, color=C.INK_2, family=C.FONT),
            cliponaxis=False,
            customdata=np.stack([values, df["unit"], df[matches_col]], -1),
            hovertemplate=(f"<b>{era}</b><br>%{{y}}: "
                           "<b>%{customdata[0]:,.3f}%{customdata[1]}</b>"
                           "<br><span style='color:#898781'>%{customdata[2]} matches"
                           "</span><extra></extra>"),
        ))

    fig.update_layout(barmode="group", bargap=0.34, bargroupgap=0.08,
                      uniformtext=dict(mode="hide", minsize=9))
    # Headroom on the right for the value labels of a row at full scale.
    fig.update_xaxes(showticklabels=False, showline=False, showgrid=False,
                     range=[0, 132])
    fig.update_yaxes(tickfont=dict(size=12, color=C.INK))
    fig = _finish(fig, title=title, subtitle=subtitle,
                  height=height or max(260, 46 * len(labels) + 80),
                  showlegend=True, ygrid=False, xgrid=False)
    # The scaling rule travels with the chart, not with the page copy — without
    # it a reader could compare a bar in one row against a bar in another.
    fig.add_annotation(
        x=0, y=0, xref="paper", yref="paper", xanchor="left", yanchor="top",
        yshift=-12, showarrow=False,
        text="Each row is scaled to its own larger value — bar length compares "
             "the two eras within a row, not across rows. Real values are "
             "printed on the bars.",
        font=dict(size=10.5, color=C.INK_MUTED, family=C.FONT))
    margin = fig.layout.margin
    fig.update_layout(margin=dict(l=margin.l, r=margin.r, t=margin.t, b=34),
                      height=fig.layout.height + 24)
    return fig


def change_lollipop(comparison: pd.DataFrame, *, title: str = "",
                    subtitle: str = "") -> go.Figure:
    """Percentage change per metric, signed, as a stem and a dot.

    The dot sits at the value, the stem ties it to the zero line, and the sign
    is written on the label — so the direction survives in greyscale. Colour
    reinforces whether the movement is favourable, which is a separate judgement
    from its direction and is why ``higher_is_better`` is carried in the frame.
    """
    df = comparison.dropna(subset=["change_pct"]).copy()
    if df.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    df = df.sort_values("change_pct")
    favourable = np.where(df["higher_is_better"], df["change_pct"] > 0,
                          df["change_pct"] < 0)
    colors = [C.GOOD if f else C.CRITICAL for f in favourable]

    fig = go.Figure()
    for label, value, color in zip(df["label"], df["change_pct"], colors):
        fig.add_shape(type="line", x0=0, x1=value, y0=label, y1=label,
                      line=dict(color=color, width=2), layer="below")
    fig.add_trace(go.Scatter(
        x=df["change_pct"], y=df["label"], mode="markers+text",
        marker=dict(size=13, color=colors, line=dict(color=C.SURFACE, width=2)),
        text=[f"{v:+.1f}%" for v in df["change_pct"]],
        textposition=["middle left" if v < 0 else "middle right"
                      for v in df["change_pct"]],
        textfont=dict(size=11, color=C.INK_2, family=C.FONT),
        hovertemplate="<b>%{y}</b><br>%{x:+.1f}% under De la Fuente<extra></extra>",
        showlegend=False, cliponaxis=False,
    ))
    fig.add_vline(x=0, line=dict(color=C.AXIS, width=1.5))
    span = max(abs(df["change_pct"].min()), abs(df["change_pct"].max())) * 1.38
    fig.update_xaxes(range=[-span, span], ticksuffix="%", showline=False)
    fig.update_yaxes(tickfont=dict(size=12, color=C.INK))
    return _finish(fig, title=title, subtitle=subtitle,
                   height=max(250, 36 * len(df) + 90), ygrid=False, xgrid=True)


# --------------------------------------------------------------------------- #
# Trends over time
# --------------------------------------------------------------------------- #

def match_trend(timeline: pd.DataFrame, metric: str, *, label: str,
                unit: str = "", decimals: int = 1, title: str = "",
                subtitle: str = "", show_era_means: bool = True) -> go.Figure:
    """One metric across the 25 matches in date order.

    The line is drawn per era so the handover shows as a break rather than a
    continuous slope through a change of manager, and each era's mean is laid in
    behind as a dashed reference.
    """
    if timeline.empty or metric not in timeline.columns:
        return _finish(go.Figure(), title=title, subtitle=subtitle)

    df = timeline.dropna(subset=[metric]).copy()
    fig = go.Figure()

    if show_era_means:
        for era in C.ERAS:
            subset = df[df["era"] == era]
            if subset.empty:
                continue
            mean = subset[metric].mean()
            fig.add_trace(go.Scatter(
                x=[subset["n"].min() - 0.4, subset["n"].max() + 0.4],
                y=[mean, mean], mode="lines", showlegend=False,
                line=dict(color=C.era_color(era), width=1.5, dash="dot"),
                opacity=0.55, hoverinfo="skip",
            ))
            fig.add_annotation(
                x=subset["n"].max() + 0.4, y=mean, text=f" mean {_fmt(mean, decimals)}",
                showarrow=False, xanchor="left", yanchor="middle",
                font=dict(size=10.5, color=C.era_color(era), family=C.FONT))

    for era in C.ERAS:
        subset = df[df["era"] == era]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["n"], y=subset[metric], mode="lines+markers", name=era,
            line=dict(color=C.era_color(era), width=2, shape="linear"),
            marker=dict(size=8, color=C.era_color(era),
                        line=dict(color=C.SURFACE, width=2)),
            customdata=np.stack([
                subset["opponent"], subset["tournament"].astype(str),
                subset["round"].astype(str), subset["match_result"],
                subset["match_spain_score"], subset["match_opp_score"]], -1),
            hovertemplate=(
                f"<b>%{{customdata[0]}}</b> · %{{customdata[1]}} %{{customdata[2]}}"
                f"<br>Spain %{{customdata[4]}}–%{{customdata[5]}} (%{{customdata[3]}})"
                f"<br>{label}: <b>%{{y:,.{decimals}f}}{unit}</b><extra></extra>"),
        ))

    # Mark the handover between managers.
    boundary = df[df["era"] == C.ERAS[1]]["n"].min()
    if pd.notna(boundary) and df[df["era"] == C.ERAS[0]].shape[0]:
        fig.add_vline(x=boundary - 0.5, line=dict(color=C.AXIS, width=1, dash="dash"))
        fig.add_annotation(x=boundary - 0.5, y=1, yref="paper", yshift=-4,
                           text="new manager", showarrow=False, xanchor="center",
                           yanchor="top",
                           font=dict(size=10, color=C.INK_MUTED, family=C.FONT))

    fig.update_xaxes(title="Match, in chronological order", tickmode="linear", dtick=2)
    fig.update_yaxes(title=f"{label}{unit}", rangemode="tozero")
    return _finish(fig, title=title, subtitle=subtitle, height=400, showlegend=True,
                   hovermode="closest")


def tournament_trend(profile: pd.DataFrame, metric: str, *, label: str,
                     unit: str = "", decimals: int = 1, title: str = "",
                     subtitle: str = "") -> go.Figure:
    """One metric across the four tournaments, era carried by the marker colour.

    Tournaments are positions in time, so they sit on the x-axis and the only
    colour in play is the era's — which is what makes the two-hue scale hold
    across the whole app.
    """
    if profile.empty or metric not in profile.columns:
        return _finish(go.Figure(), title=title, subtitle=subtitle)

    df = profile.dropna(subset=[metric]).copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["label"], y=df[metric], mode="lines", showlegend=False,
        line=dict(color=C.AXIS, width=2), hoverinfo="skip"))
    for era in C.ERAS:
        subset = df[df["era"] == era]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["label"], y=subset[metric], mode="markers+text", name=era,
            marker=dict(size=15, color=C.era_color(era),
                        line=dict(color=C.SURFACE, width=2.5)),
            text=[_fmt(v, decimals) for v in subset[metric]],
            textposition="top center",
            textfont=dict(size=11.5, color=C.INK, family=C.FONT),
            hovertemplate=(f"<b>%{{x}}</b><br>{label}: "
                           f"<b>%{{y:,.{decimals}f}}{unit}</b><extra></extra>"),
            cliponaxis=False,
        ))
    fig.update_yaxes(title=f"{label}{unit}", rangemode="tozero")
    return _finish(fig, title=title, subtitle=subtitle, height=330, showlegend=True)


# --------------------------------------------------------------------------- #
# Distributions
# --------------------------------------------------------------------------- #

def era_distribution(spain: pd.DataFrame, metric: str, *, label: str,
                     unit: str = "", decimals: int = 1, title: str = "",
                     subtitle: str = "") -> go.Figure:
    """Per-match spread of one metric under each manager.

    Every match is drawn as its own point beside the box, because with 10 and 15
    observations a box on its own hides how thin the evidence is.
    """
    if spain.empty or metric not in spain.columns:
        return _finish(go.Figure(), title=title, subtitle=subtitle)

    fig = go.Figure()
    for era in C.ERAS:
        subset = spain[(spain["era"] == era) & spain[metric].notna()]
        if subset.empty:
            continue
        fig.add_trace(go.Box(
            y=subset[metric], name=C.ERA_SHORT.get(era, era),
            marker=dict(color=C.era_color(era), size=8,
                        line=dict(color=C.SURFACE, width=1.5)),
            line=dict(color=C.era_color(era), width=2),
            fillcolor=C.ERA_FILL[era], boxpoints="all", jitter=0.42,
            pointpos=0, width=0.5, hoveron="points",
            customdata=np.stack([subset["opponent"],
                                 subset["tournament"].astype(str)], -1),
            hovertemplate=(f"<b>%{{customdata[0]}}</b> · %{{customdata[1]}}"
                           f"<br>{label}: <b>%{{y:,.{decimals}f}}{unit}</b>"
                           "<extra></extra>"),
            showlegend=False,
        ))
    fig.update_yaxes(title=f"{label}{unit}", rangemode="tozero")
    fig.update_xaxes(showline=False, tickfont=dict(size=12, color=C.INK))
    return _finish(fig, title=title, subtitle=subtitle, height=360)


def stacked_share(df: pd.DataFrame, *, category: str, value: str, group: str,
                  title: str = "", subtitle: str = "", height: int = 260,
                  colors: Optional[dict] = None) -> go.Figure:
    """Composition bars, normalised to 100% within each group.

    The groups are the eras (named on the y-axis) and the segments are the
    categories, so segments draw from ``SEGMENT_SERIES`` — which skips the two
    era hues, because a blue segment meaning "right flank" sitting inside a bar
    labelled "Luis Enrique" would fight the one colour rule this app has.

    Segments get a 2px surface gap so adjacent fills read as separate pieces
    rather than one continuous band, and each carries its own percentage label.
    """
    if df.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    pivot = df.pivot_table(index=group, columns=category, values=value,
                           aggfunc="sum", observed=True).fillna(0)
    shares = pivot.div(pivot.sum(axis=1), axis=0) * 100
    palette = C.SEGMENT_SERIES
    fig = go.Figure()
    for i, col in enumerate(shares.columns):
        color = (colors or {}).get(col, palette[i % len(palette)])
        fig.add_trace(go.Bar(
            y=shares.index.astype(str), x=shares[col], orientation="h", name=str(col),
            marker=dict(color=color, line=dict(color=C.SURFACE, width=2)),
            text=[f"{v:.0f}%" if v >= 7 else "" for v in shares[col]],
            textposition="inside", insidetextanchor="middle",
            textfont=dict(size=11, color=_label_ink(color), family=C.FONT),
            customdata=pivot[col],
            hovertemplate=(f"<b>{col}</b><br>%{{x:.1f}}% of passes"
                           "<br>%{customdata:,.0f} events<extra></extra>"),
        ))
    fig.update_layout(barmode="stack", bargap=0.42)
    fig.update_xaxes(range=[0, 100], ticksuffix="%", showline=False)
    fig.update_yaxes(tickfont=dict(size=12, color=C.INK))
    return _finish(fig, title=title, subtitle=subtitle, height=height,
                   showlegend=True, ygrid=False, xgrid=True)


# --------------------------------------------------------------------------- #
# Shooting
# --------------------------------------------------------------------------- #

def xg_vs_goals(timeline: pd.DataFrame, *, title: str = "",
                subtitle: str = "") -> go.Figure:
    """Cumulative goals against cumulative xG, per era.

    Both series are goals, so they share one axis honestly. The gap between the
    pair is the story: finishing above or below the chances created.
    """
    if timeline.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    df = timeline.sort_values("date").copy()
    fig = go.Figure()
    for era in C.ERAS:
        subset = df[df["era"] == era].copy()
        if subset.empty:
            continue
        subset["cum_goals"] = subset["goals"].cumsum()
        subset["cum_xg"] = subset["xg"].cumsum()
        color = C.era_color(era)
        fig.add_trace(go.Scatter(
            x=subset["n"], y=subset["cum_xg"], mode="lines",
            name=f"{C.ERA_SHORT[era]} — xG", line=dict(color=color, width=2, dash="dot"),
            hovertemplate="Cumulative xG: <b>%{y:.2f}</b><extra></extra>"))
        fig.add_trace(go.Scatter(
            x=subset["n"], y=subset["cum_goals"], mode="lines",
            name=f"{C.ERA_SHORT[era]} — goals", line=dict(color=color, width=2.6),
            fill="tonexty", fillcolor=C.ERA_FILL[era],
            hovertemplate="Cumulative goals: <b>%{y:.0f}</b><extra></extra>"))
    fig.update_xaxes(title="Match, in chronological order")
    fig.update_yaxes(title="Cumulative goals / xG")
    return _finish(fig, title=title, subtitle=subtitle, height=380, showlegend=True,
                   hovermode="x unified")


def xg_histogram(shots: pd.DataFrame, *, title: str = "",
                 subtitle: str = "") -> go.Figure:
    """Distribution of shot quality, split by era.

    Overlaid rather than stacked, at partial opacity, because the question is
    where each era's shots sit on the quality scale — not what they sum to.
    """
    if shots.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    fig = go.Figure()
    for era in C.ERAS:
        subset = shots[(shots["era"] == era) & shots["xg_combined"].notna()]
        if subset.empty:
            continue
        fig.add_trace(go.Histogram(
            x=subset["xg_combined"], name=era, nbinsx=26,
            marker=dict(color=C.era_color(era), line=dict(color=C.SURFACE, width=1.5)),
            opacity=0.72, histnorm="percent",
            hovertemplate=("<b>" + era + "</b><br>xG %{x}<br>"
                           "%{y:.1f}% of that era's shots<extra></extra>"),
        ))
    fig.update_layout(barmode="overlay", bargap=0.06)
    fig.update_xaxes(title="xG of the shot (chance quality)")
    fig.update_yaxes(title="Share of the era's shots", ticksuffix="%")
    return _finish(fig, title=title, subtitle=subtitle, height=340, showlegend=True)


# --------------------------------------------------------------------------- #
# Players
# --------------------------------------------------------------------------- #

def player_era_bars(split: pd.DataFrame, metrics: Sequence[str],
                    labels: Sequence[str], *, title: str = "",
                    subtitle: str = "") -> go.Figure:
    """One player's per-90 profile under each manager, metric by metric.

    Each metric is indexed to the player's Enrique-era value so metrics on very
    different scales (passes/90 near 60, goals/90 near 0.3) can share one axis
    without a second scale.
    """
    if split.empty or len(split) < 2:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    base = split[split["era"] == C.ERAS[0]].iloc[0]
    later = split[split["era"] == C.ERAS[1]].iloc[0]

    rows = []
    for metric, label in zip(metrics, labels):
        old, new = base.get(metric), later.get(metric)
        if pd.isna(old) or pd.isna(new) or old == 0:
            continue
        rows.append({"label": label, "old": old, "new": new,
                     "indexed": new / old * 100})
    if not rows:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    df = pd.DataFrame(rows).iloc[::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["label"], x=df["indexed"] - 100, orientation="h",
        base=100, name=C.ERAS[1],
        marker=dict(color=[C.era_color(C.ERAS[1])] * len(df),
                    line=dict(color=C.SURFACE, width=2)),
        text=[f"{v:+.0f}%" for v in df["indexed"] - 100],
        textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=C.INK_2, family=C.FONT),
        customdata=np.stack([df["old"], df["new"]], -1),
        hovertemplate=("<b>%{y}</b><br>Enrique: %{customdata[0]:.2f} per 90"
                       "<br>De la Fuente: %{customdata[1]:.2f} per 90"
                       "<extra></extra>"),
    ))
    fig.add_vline(x=100, line=dict(color=C.era_color(C.ERAS[0]), width=2))
    # Inside the plot area, not above it: an annotation in the top margin
    # competes with the title for the same band and one of them gets clipped.
    fig.add_annotation(x=100, y=1, yref="paper", yshift=-4,
                       text=f"{C.ERAS[0]} baseline = 100", showarrow=False,
                       xanchor="center", yanchor="top",
                       font=dict(size=10.5, color=C.era_color(C.ERAS[0]),
                                 family=C.FONT))
    fig.update_xaxes(title="Indexed to the player's Luis Enrique per-90 level")
    fig.update_yaxes(tickfont=dict(size=12, color=C.INK))
    return _finish(fig, title=title, subtitle=subtitle,
                   height=max(240, 42 * len(df) + 110), ygrid=False, xgrid=True)


def player_radar(radar: pd.DataFrame, *, kind: str = "radar", title: str = "",
                 subtitle: str = "") -> go.Figure:
    """One player under both managers, as a radar or a pizza chart.

    ``radar`` is the tidy frame from ``metrics.player_radar``: one row per era
    and axis, with the raw per-90 ``value`` and its ``percentile`` (the radius).
    """
    if radar.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    labels = list(dict.fromkeys(radar["label"]))
    step = 360 / len(labels)
    centre = {label: i * step for i, label in enumerate(labels)}
    eras = [e for e in C.ERAS if e in set(radar["era"])]

    fig = go.Figure()
    for i, era in enumerate(eras):
        df = radar[(radar["era"] == era) & radar["percentile"].notna()]
        if df.empty:
            continue
        custom = np.stack([df["label"], df["value"].map(lambda v: _fmt(v, 2))], -1)
        hover = (f"<b>%{{customdata[0]}}</b><br>{era}<br>Percentile: %{{r:.0f}}"
                 "<br>Value: %{customdata[1]}<extra></extra>")
        theta = df["label"].map(centre)
        if kind == "pizza":
            shift = (i - (len(eras) - 1) / 2) * step * 0.44
            fig.add_trace(go.Barpolar(
                r=df["percentile"], theta=theta + shift, width=step * 0.42,
                name=era, customdata=custom, hovertemplate=hover,
                marker=dict(color=C.era_color(era),
                            line=dict(color=C.SURFACE, width=2))))
        else:
            closed = lambda s: list(s) + [s.iloc[0]]  # noqa: E731
            fig.add_trace(go.Scatterpolar(
                r=closed(df["percentile"]), theta=closed(theta), name=era,
                mode="lines+markers", fill="toself",
                fillcolor=C.ERA_FILL.get(era), customdata=closed(pd.Series(
                    list(custom))), hovertemplate=hover,
                line=dict(color=C.era_color(era), width=2),
                marker=dict(size=8, color=C.era_color(era))))

    fig.update_layout(polar=dict(
        bgcolor=C.SURFACE,
        radialaxis=dict(range=[0, 100], tickvals=[25, 50, 75, 100], angle=90,
                        tickangle=90, gridcolor=C.GRID, linecolor=C.GRID,
                        tickfont=dict(size=10, color=C.INK_MUTED)),
        angularaxis=dict(direction="clockwise", rotation=90, thetaunit="degrees",
                         tickvals=list(centre.values()), ticktext=labels,
                         gridcolor=C.GRID, linecolor=C.AXIS,
                         tickfont=dict(size=12, color=C.INK))))
    fig = _finish(fig, title=title, subtitle=subtitle, height=520,
                  showlegend=True)
    fig.update_layout(margin=dict(l=90, r=90, b=40,
                                  t=fig.layout.margin.t + 30))
    return fig


def player_scatter(players: pd.DataFrame, x: str, y: str, *, x_label: str,
                   y_label: str, size: Optional[str] = None,
                   title: str = "", subtitle: str = "",
                   highlight: Sequence[str] = ()) -> go.Figure:
    """Squad scatter, coloured by which era(s) a player appeared in.

    Three categories only — Enrique only, both, De la Fuente only — which is
    inside the three-series cap that the palette clears on the all-pairs test
    that scatter plots require.
    """
    if players.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    df = players.dropna(subset=[x, y]).copy()
    if df.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)

    def group_of(eras: str) -> str:
        if "," in str(eras):
            return "Both managers"
        return f"{eras} only"

    df["group"] = df["eras"].map(group_of)
    group_colors = {
        f"{C.ERAS[0]} only": C.era_color(C.ERAS[0]),
        "Both managers": C.SERIES[2],
        f"{C.ERAS[1]} only": C.era_color(C.ERAS[1]),
    }
    sizes = (df[size].fillna(0) if size and size in df.columns
             else pd.Series(1, index=df.index))
    scale = 30 / max(sizes.max(), 1)

    fig = go.Figure()
    for group, color in group_colors.items():
        subset = df[df["group"] == group]
        if subset.empty:
            continue
        subset_sizes = (subset[size].fillna(0) * scale + 9 if size in subset.columns
                        else pd.Series(11, index=subset.index))
        fig.add_trace(go.Scatter(
            x=subset[x], y=subset[y], mode="markers", name=group,
            marker=dict(size=subset_sizes, color=color, opacity=0.82,
                        line=dict(color=C.SURFACE, width=2)),
            customdata=np.stack([subset["player_canonical"],
                                 subset["matches_played"],
                                 subset["minutes_played_total"]], -1),
            hovertemplate=(f"<b>%{{customdata[0]}}</b><br>{x_label}: %{{x:,.2f}}"
                           f"<br>{y_label}: %{{y:,.2f}}"
                           "<br><span style='color:#898781'>%{customdata[1]} matches, "
                           "%{customdata[2]:,.0f} min</span><extra></extra>"),
        ))

    # Name only the handful worth naming; a label on every point is noise.
    named = df[df["player_canonical"].isin(highlight)] if len(highlight) else \
        df.nlargest(min(6, len(df)), y)
    if not named.empty:
        fig.add_trace(go.Scatter(
            x=named[x], y=named[y], mode="text", text=named["player_canonical"],
            textposition="top center", showlegend=False, hoverinfo="skip",
            textfont=dict(size=11, color=C.INK, family=C.FONT), cliponaxis=False))

    fig.update_xaxes(title=x_label, showgrid=True, gridcolor=C.GRID)
    fig.update_yaxes(title=y_label)
    return _finish(fig, title=title, subtitle=subtitle, height=470, showlegend=True)


def horizontal_ranking(df: pd.DataFrame, *, label_col: str, value_col: str,
                       color_col: Optional[str] = None, unit: str = "",
                       decimals: int = 1, title: str = "", subtitle: str = "",
                       height: Optional[int] = None) -> go.Figure:
    """A ranked bar list — top scorers, most-used players, and the like."""
    if df.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    data = df.iloc[::-1]
    if color_col and color_col in data.columns:
        colors = [C.era_color(v) if v in C.ERA_COLORS else C.SERIES[2]
                  for v in data[color_col]]
    else:
        colors = [C.SERIES[0]] * len(data)
    fig = go.Figure(go.Bar(
        y=data[label_col], x=data[value_col], orientation="h",
        marker=dict(color=colors, line=dict(color=C.SURFACE, width=2)),
        text=[f"{v:,.{decimals}f}{unit}" for v in data[value_col]],
        textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=C.INK_2, family=C.FONT),
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:,.{decimals}f}}{unit}<extra></extra>",
    ))
    fig.update_xaxes(showticklabels=False, showline=False)
    fig.update_yaxes(tickfont=dict(size=12, color=C.INK))
    return _finish(fig, title=title, subtitle=subtitle,
                   height=height or max(240, 30 * len(data) + 90),
                   ygrid=False, xgrid=True)


# --------------------------------------------------------------------------- #
# Possession & territory
# --------------------------------------------------------------------------- #

def possession_vs_metric(spain: pd.DataFrame, metric: str, *, label: str,
                         unit: str = "", title: str = "",
                         subtitle: str = "") -> go.Figure:
    """Possession share against another metric, one point per match.

    Answers whether more of the ball actually bought more of the thing — which
    for this dataset it largely does not, and the scatter shows that plainly.
    """
    if spain.empty or metric not in spain.columns:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    df = spain.dropna(subset=["possession_pct_proxy", metric])
    fig = go.Figure()
    for era in C.ERAS:
        subset = df[df["era"] == era]
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["possession_pct_proxy"], y=subset[metric], mode="markers",
            name=era,
            marker=dict(size=13, color=C.era_color(era), opacity=0.85,
                        line=dict(color=C.SURFACE, width=2)),
            customdata=np.stack([subset["opponent"],
                                 subset["tournament"].astype(str)], -1),
            hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}"
                           "<br>Possession proxy: %{x:.1f}%"
                           f"<br>{label}: <b>%{{y:,.2f}}{unit}</b><extra></extra>"),
        ))
    fig.update_xaxes(title="Possession share (proxy, %)", showgrid=True,
                     gridcolor=C.GRID, ticksuffix="%")
    fig.update_yaxes(title=f"{label}{unit}", rangemode="tozero")
    return _finish(fig, title=title, subtitle=subtitle, height=420, showlegend=True)


def zone_heatmap(grid: pd.DataFrame, *, era: str, value: str = "share",
                 title: str = "", subtitle: str = "",
                 height: int = 300) -> go.Figure:
    """Pitch zones as a single-hue heatmap — light means near zero.

    Values are shares of the era's own events, so two eras with different event
    volumes are comparable cell by cell on the same scale.
    """
    if grid.empty:
        return _finish(go.Figure(), title=title, subtitle=subtitle)
    matrix = grid.pivot_table(index="yb", columns="xb", values=value,
                              aggfunc="sum").fillna(0)
    ramp = C.sequential_for(era)
    colorscale = [[i / (len(ramp) - 1), c] for i, c in enumerate(ramp)]
    fig = go.Figure(go.Heatmap(
        z=matrix.values, colorscale=colorscale, xgap=2, ygap=2,
        colorbar=dict(title=dict(text="% of events", font=dict(size=10.5)),
                      thickness=10, len=0.8, tickfont=dict(size=10),
                      outlinewidth=0),
        hovertemplate="%{z:.1f}% of this era's events<extra></extra>",
    ))
    fig.update_xaxes(showticklabels=False, showline=False, showgrid=False,
                     title="← own goal · attacking direction · opponent goal →")
    fig.update_yaxes(showticklabels=False, showgrid=False, autorange="reversed")
    return _finish(fig, title=title, subtitle=subtitle, height=height, ygrid=False)
