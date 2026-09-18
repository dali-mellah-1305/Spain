# -*- coding: utf-8 -*-
"""Page 2 — Luis Enrique: EURO 2020 and the 2022 World Cup."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import config as C
from utils import era_page, ui

ui.page_setup("Luis Enrique", icon="🔵")

era_page.render(
    C.ERAS[0], page_no=2, key_prefix="le",
    lede="Ten matches across two tournaments, and the highest pass volume in the "
         "dataset by a wide margin — 823 attempted passes per 90. Both campaigns "
         "ended in a shootout: a semi-final against Italy at EURO 2020, a round "
         "of 16 against Morocco in 2022. Four wins in ten.",
    character="EURO 2020 and the 2022 World Cup are not the same team. The 2022 "
              "side passed even more (912 per 90 against 764) and shot far less "
              "(11.3 per 90 against 16.6) — the clearest case in this dataset of "
              "possession without penetration, and the campaign that ended "
              "goalless against Morocco.")
