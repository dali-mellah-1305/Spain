# -*- coding: utf-8 -*-
"""
Application core for the Spain's-Evolution dashboard.

Five modules do the work described in the architecture diagram, plus one
presentation module:

===========================  =================================================
``config``                   Paths, labels, design tokens, provenance wording.
``data_loader``              The only module that reads from disk. All cached.
``filters``                  The only module that renders the sidebar, and the
                             only one that writes the selection to session state.
``metrics``                  Per-90 normalisation, era comparison, aggregation.
``charts_mplsoccer``         Static pitch visuals on the common 0-100 pitch.
``charts_plotly``            Interactive KPI trends, distributions, scatters.
``ui``                       Stylesheet and the components pages are built from.
===========================  =================================================

Pages hold layout only: they call these modules and place the results. No page
reads a CSV, computes a metric, or builds a figure of its own.
"""
