# -*- coding: utf-8 -*-
"""
Entry point.

    streamlit run app/streamlit_app.py

This file is the router and nothing else: it sets the page config, declares the
nine pages, and runs whichever one is selected. Every page body lives in its own
file — ``home.py`` plus the eight numbered files in ``pages/``.

Why declare the pages instead of letting Streamlit discover ``pages/`` by
itself: filename-based discovery derives each sidebar label from the filename,
which makes the entry point read as "streamlit app" in the navigation and gives
"3_Luis_de_la_Fuente" back as "Luis de la Fuente" only by luck of the
underscores. ``st.navigation`` is Streamlit's own API for naming and ordering
pages, so the labels below are the labels a visitor sees, and the numbered
filenames still fix the order.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from utils import ui

ui.configure_app()

PAGES = [
    st.Page("home.py", title="Start here", icon="⚽", default=True,
            url_path="start"),
    st.Page("pages/1_Overview.py", title="Overview", icon="📊"),
    st.Page("pages/2_Luis_Enrique.py", title="Luis Enrique", icon="🔵"),
    st.Page("pages/3_Luis_de_la_Fuente.py", title="Luis de la Fuente", icon="🟠"),
    st.Page("pages/4_Passing.py", title="Passing", icon="🎯"),
    st.Page("pages/5_Shooting.py", title="Shooting", icon="🥅"),
    st.Page("pages/6_Possession.py", title="Possession", icon="⏱️"),
    st.Page("pages/7_Final_Third.py", title="Final third", icon="📐"),
    st.Page("pages/8_Players.py", title="Players", icon="👤"),
]

st.navigation(PAGES).run()
