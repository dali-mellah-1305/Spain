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
    """Render the shared sidebar and return the resolved selection.

    ``lock_era`` is used by the two manager pages, which are *about* one era:
    they pin it and hide the era control rather than letting a page contradict
    its own title. Everything else stays live.
    """
    matches = dl.load_matches()
    team_stats = dl.load_team_stats()
    facts = dl.dataset_facts()

    st.sidebar.markdown(
        '<div class="sb-brand"><div class="flag"></div><div>'
        f'<div class="t">{C.APP_TITLE}</div>'
        '<div class="s">Spain · 2021–2026</div></div></div>',
        unsafe_allow_html=True)

    if not dl.is_cleaned():
        st.sidebar.warning(
            "Reading the **raw** dataset. Run `python src/clean_data.py` to build "
            "`data/clean/` — several charts depend on columns only the cleaned "
            "output has.", icon="⚠️")

    # ---- era ----
    if lock_era:
        eras = [lock_era]
        st.sidebar.markdown(
            f'<div class="sb-head first">Era</div>'
            f'<div class="sb-count" style="border-left:3px solid '
            f'{C.era_color(lock_era)}">Pinned to <b>{lock_era}</b> on this page.'
            f"</div>",
            unsafe_allow_html=True)
    else:
        _head("Era", first=True)
        eras = _multi(
            "eras", "Manager", C.ERAS, allow_empty=False, order=C.ERAS,
            label_visibility="collapsed",
            help="Both selected is the comparison the dashboard is built around.")
        if not eras:
            eras = list(C.ERAS)
            st.sidebar.caption("No era selected — showing both.")

    # ---- tournament, constrained by era ----
    available_tournaments = [t for t in C.TOURNAMENTS
                             if C.TOURNAMENT_ERA[t] in eras and t in facts["tournaments"]]
    _head("Tournament")
    tournaments = _multi("tournaments", "Tournament", available_tournaments,
                         allow_empty=False, order=C.TOURNAMENTS,
                         format_func=C.tournament_label,
                         label_visibility="collapsed")
    if not tournaments:
        tournaments = available_tournaments
        st.sidebar.caption("No tournament selected — showing all in range.")

    # ---- opponent & round, constrained by the above ----
    scope = matches[matches["era"].isin(eras) & matches["tournament"].isin(tournaments)]

    _head("Opponent")
    opponent_options = sorted(scope["opponent"].dropna().unique().tolist())
    opponents = _multi("opponents", "Opponent", opponent_options, fallback=[],
                       label_visibility="collapsed",
                       placeholder="All opponents")

    _head("Round")
    round_options = [r for r in C.ROUND_ORDER if r in set(scope["round"].dropna())]
    rounds = _multi("rounds", "Round", round_options, fallback=[],
                    label_visibility="collapsed", placeholder="All rounds")

    # ---- resolve the match set ----
    selected = scope
    if opponents:
        selected = selected[selected["opponent"].isin(opponents)]
    if rounds:
        selected = selected[selected["round"].isin(rounds)]
    if selected.empty:
        st.sidebar.error("That combination matches no games — opponent and round "
                         "filters ignored.", icon="🚫")
        selected = scope
        opponents, rounds = [], []

    selected = selected.sort_values("date")

    # ---- optional per-page controls ----
    player = st.session_state.get(_KEYS["player"])
    if show_player:
        _head("Player")
        squad = dl.spain_players(min_minutes=1)
        squad = squad[squad["player_canonical"].notna()]
        names = squad["player_canonical"].tolist()
        if names:
            player = _single("player", "Player", names, default=names[0],
                             label_visibility="collapsed",
                             help="Spain squad members, most minutes first.")

    # ---- summary of what is selected ----
    by_era = selected["era"].value_counts()
    st.sidebar.markdown(
        '<div class="sb-count">'
        f'<b>{len(selected)}</b> of {facts["n_matches"]} matches selected<br>'
        f'{int(by_era.get(C.ERAS[0], 0))} Enrique · '
        f'{int(by_era.get(C.ERAS[1], 0))} De la Fuente<br>'
        f'<span style="color:{C.INK_MUTED}">'
        f'{selected["date"].min():%b %Y} – {selected["date"].max():%b %Y}</span>'
        "</div>",
        unsafe_allow_html=True)

    if st.sidebar.button("Reset all filters", width="stretch"):
        # Clears both the persistent selections and the widget keys derived from
        # them, so the controls come back to their defaults rather than
        # redisplaying a widget value the selection no longer holds.
        for key in [k for k in st.session_state if str(k).startswith("flt_")]:
            st.session_state.pop(key, None)
        st.rerun()

    st.sidebar.markdown(
        f'<div class="sb-head">Data</div><div class="sb-count">'
        f'Reading <code>{dl.data_dir().name}/</code>'
        + ("<br>✔ cleaned &amp; validated" if dl.is_cleaned() else "<br>⚠ raw")
        + "</div>",
        unsafe_allow_html=True)

    selection = Selection(
        eras=list(eras), tournaments=list(tournaments), opponents=list(opponents),
        rounds=list(rounds), player=player, per90=True, matches=selected,
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
