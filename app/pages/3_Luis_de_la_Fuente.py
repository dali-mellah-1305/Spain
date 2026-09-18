# -*- coding: utf-8 -*-
"""Page 3 — Luis de la Fuente: EURO 2024 and the 2026 World Cup."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import config as C
from utils import era_page, ui

ui.page_setup("Luis de la Fuente", icon="🟠")

era_page.render(
    C.ERAS[1], page_no=3, key_prefix="ldlf",
    lede="Fifteen matches, fourteen wins, one draw, no defeats — and two "
         "trophies. Pass volume falls 23% against the Enrique years while the "
         "share of possession barely moves, which is the single clearest "
         "stylistic change in this dataset: the same ball, far fewer touches.",
    character="EURO 2024 and the 2026 World Cup differ mainly in pass volume "
              "(598 per 90 against 664) while shot volume holds almost level "
              "(16.9 against 16.4). Note that the World Cup 2026 figures come "
              "from a different data source with model-estimated xG and no carry "
              "events — differences between these two tournaments are the ones "
              "to read most cautiously in the whole dashboard.")
