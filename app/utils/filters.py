# -*- coding: utf-8 -*-
"""
The sidebar. This is the only module that renders it, and the only one that
writes the active selection into ``st.session_state``.

Every page calls :func:`render_sidebar` once at the top and gets back a
:class:`Selection`. Because the selection lives in session state rather than in
each page's own widgets, choosing "Luis de la Fuente + WC 2026" on the Overview
page is still in force after navigating to Possession — Streamlit's multipage
navigation does not reset session state.

Filters are additive and ordered coarse → fine: era narrows the tournament
options, tournament narrows the opponent and match options, and so on. A filter
that would produce an empty selection is refused and reported rather than
silently applied, so a page never has to render a blank chart.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import pandas as pd
import streamlit as st

from . import config as C
from . import data_loader as dl
from . import ui

_KEYS = {
    "eras": "flt_eras",
    "tournaments": "flt_tournaments",
    "opponents": "flt_opponents",
    "rounds": "flt_rounds",
    "player": "flt_player",
    "per90": "flt_per90",
}


@dataclass
class Selection:
    """The active filter state, plus the frames it resolves to."""

    eras: list = field(default_factory=lambda: list(C.ERAS))
    tournaments: list = field(default_factory=lambda: list(C.TOURNAMENTS))
    opponents: list = field(default_factory=list)
    rounds: list = field(default_factory=list)
    player: Optional[str] = None
    per90: bool = True
    matches: pd.DataFrame = field(default_factory=pd.DataFrame)
    team_stats: pd.DataFrame = field(default_factory=pd.DataFrame)

    # -- convenience ------------------------------------------------------- #
    @property
    def match_ids(self) -> list:
        return self.matches["match_id"].tolist()

    @property
    def tournament_tuple(self) -> tuple:
        """Hashable form for the cached loaders."""
        return tuple(self.tournaments)

    @property
    def is_full_dataset(self) -> bool:
        return len(self.matches) == dl.dataset_facts()["n_matches"]

    @property
    def both_eras(self) -> bool:
        return len(set(self.eras)) == 2

    @property
    def single_era(self) -> Optional[str]:
        return self.eras[0] if len(set(self.eras)) == 1 else None

    @property
    def has_carry_data(self) -> bool:
        """Whether any selected match logs ball carries."""
        return ("has_carries" in self.matches.columns
                and bool(self.matches["has_carries"].any()))

    @property
    def n_carry_matches(self) -> int:
        if "has_carries" not in self.matches.columns:
            return 0
        return int(self.matches["has_carries"].sum())

    def events(self, kind: str, spain_only: bool = True) -> pd.DataFrame:
        """One event family, filtered to the selected matches."""
        kind = kind.lower()
        loader = {
            "passes": dl.load_passes, "shots": dl.load_shots,
            "carries": dl.load_carries,
            "defensive actions": dl.load_defensive_actions,
            "defensive_actions": dl.load_defensive_actions,
        }[kind]
        events = loader(self.tournament_tuple, spain_only)
        return events[events["match_id"].isin(self.match_ids)]

    def describe(self) -> str:
        """One line naming the active selection, for a chart subtitle."""
        if self.is_full_dataset:
            return "All 25 matches"
        bits = []
        if len(set(self.eras)) == 1:
            bits.append(self.eras[0])
        if len(self.tournaments) < len(C.TOURNAMENTS):
            bits.append(", ".join(C.tournament_label(t) for t in self.tournaments))
        if self.opponents:
            bits.append("vs " + ", ".join(self.opponents))
        if self.rounds:
            bits.append(", ".join(self.rounds))
        head = " · ".join(bits) if bits else "All matches"
        return f"{head} — {len(self.matches)} match{'es' if len(self.matches) != 1 else ''}"


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #

def _widget_key(state_key: str, options: Sequence) -> str:
    """A widget key that changes when the option set does.

    The filters are nested — narrowing the era shrinks the tournament options —
    and a widget holding a value that is no longer on offer is a bug waiting to
    happen. Folding the option set into the key means a changed option list
    produces a fresh widget, seeded from the reconciled selection below.
    """
    return f"{state_key}__w{abs(hash(tuple(options))) % 1_000_000}"


def _reconcile(stored, options: Sequence, fallback: Optional[list],
               allow_empty: bool) -> list:
    """The selection to show, given what was stored and what is on offer."""
    default = list(options if fallback is None else fallback)
    if stored is None:
        return default
    kept = [v for v in stored if v in options]
    if kept:
        return kept
    if not allow_empty:
        # Era and tournament have no meaningful empty state — the whole
        # dashboard is a comparison of eras, so "none" is read as "all". Showing
        # that in the control beats an empty box above a page of both eras' data.
        return list(options)
    return [] if stored == [] else default


def _multi(key: str, label: str, options: Sequence, *,
           fallback: Optional[list] = None, allow_empty: bool = True,
           order: Optional[Sequence] = None, **kwargs) -> list:
    """A sidebar multiselect whose selection survives a page switch.

    The persistent value lives in a plain session-state entry and is passed to
    the widget as its ``default``; the widget owns a *separate* key. Two
    problems make that indirection necessary, and neither is avoidable:

    * ``st.navigation`` resets widget state when it switches pages, so a widget
      that owned the persistent value renders empty on the first run of the next
      page — the filters would appear cleared every time you changed page, while
      the page below them still showed the old selection.
    * Writing the persistent value into the *widget's own* key while also
      passing ``default`` is what raises Streamlit's "created with a default
      value but also had its value set via the Session State API" warning.

    A separate mirror key sidesteps both: nothing ever assigns to the widget's
    key, and the mirror is ordinary state that page switches leave alone.
    """
    state_key = _KEYS[key]
    stored = st.session_state.get(state_key) or []
    current = _reconcile(st.session_state.get(state_key), options, fallback,
                         allow_empty)
    value = st.sidebar.multiselect(
        label, list(options), default=current,
        key=_widget_key(state_key, options), **kwargs)
    # Choices that are not on offer right now are kept, not discarded: the two
    # manager pages pin an era, which takes the other era's tournaments off the
    # list, and a visit there should not quietly drop them from a selection the
    # user made elsewhere. What is on offer is whatever the widget returns.
    off_offer = [v for v in stored if v not in options]
    persisted = list(value) + off_offer
    if order:
        rank = {v: i for i, v in enumerate(order)}
        persisted.sort(key=lambda v: rank.get(v, len(rank)))
    st.session_state[state_key] = persisted
    return list(value)


def _single(key: str, label: str, options: Sequence, *, default=None,
            widget: str = "selectbox", **kwargs):
    """A sidebar selectbox or radio, persisted the same way as :func:`_multi`."""
    if not options:
        return None
    state_key = _KEYS[key]
    stored = st.session_state.get(state_key)
    if stored in options:
        current = stored
    elif default in options:
        current = default
    else:
        current = options[0]
    render = st.sidebar.radio if widget == "radio" else st.sidebar.selectbox
    value = render(label, list(options), index=list(options).index(current),
                   key=_widget_key(state_key, options), **kwargs)
    st.session_state[state_key] = value
    return value


def _head(text: str, first: bool = False) -> None:
    st.sidebar.markdown(
        f'<div class="sb-head{" first" if first else ""}">{text}</div>',
        unsafe_allow_html=True)


def render_sidebar(*, show_player: bool = False,
                   lock_era: Optional[str] = None) -> Selection:
    """Return a valid selection without rendering the sidebar controls.

    When a page is pinned to one manager era, the selection must remain scoped to
    that era. The sidebar is intentionally hidden, but the underlying selection
    still has to reflect the correct timeframe and tournament set.
    """
    matches = dl.load_matches().sort_values("date").reset_index(drop=True)
    team_stats = dl.load_team_stats()

    if lock_era is not None:
        selected = matches[matches["era"] == lock_era].reset_index(drop=True)
        tournaments = [t for t in C.TOURNAMENTS if C.TOURNAMENT_ERA[t] == lock_era]
        eras = [lock_era]
    else:
        selected = matches
        tournaments = list(C.TOURNAMENTS)
        eras = list(C.ERAS)

    selection = Selection(
        eras=list(eras),
        tournaments=list(tournaments),
        opponents=[],
        rounds=[],
        player=None,
        per90=True,
        matches=selected,
        team_stats=team_stats[team_stats["match_id"].isin(selected["match_id"])],
    )
    st.session_state["selection"] = selection
    return selection


def coverage_notices(sel: Selection, *, carries: bool = False,
                     xg: bool = False, possession: bool = False) -> None:
    """Render the provenance notices a page needs, only when they apply."""
    if possession:
        ui.notice(C.NOTE_POSSESSION, kind="caution",
                  label="Possession is a proxy")
    if xg and "WC2026" in sel.tournaments:
        ui.notice(C.NOTE_XG_PROXY, kind="caution", label="Mixed xG provenance")
    if carries:
        n, total = sel.n_carry_matches, len(sel.matches)
        if n < total:
            ui.notice(
                f"{C.NOTE_CARRIES}<br><strong>In this selection: {n} of {total} "
                "matches have carry data.</strong>", kind="gap",
                label="Partial coverage")
