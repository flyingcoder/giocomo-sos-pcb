#!/usr/bin/env python3
"""Bakes static fixtures for the Netlify build's Simulation tab.

Run this by hand whenever giacomo_circuit.py's default parameters or
ANALYSES schema change (requires PySpice + a system ngspice install --
see simulation/README.md). It is NOT run by the Netlify build itself,
which has no native ngspice binary available; the JSON/PNG files this
writes under webapp/static/sim-data/ are committed to git like the
existing simulation/output/*.png plots, and scripts/build_static_site.py
just copies them into dist/.

Usage:
    python3 simulation/webapp/build_fixtures.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import giacomo_circuit  # noqa: E402
import schematic_graph  # noqa: E402
import scoring  # noqa: E402

from app import (  # noqa: E402
    ANALYSES,
    OVERLAY_BUILDERS,
    RUN_FUNCS,
    TRANSIENT_ANALYSES,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO_ROOT, "webapp", "static", "sim-data")
PLOTS_DIR = os.path.join(OUT_DIR, "plots")
RESULTS_DIR = os.path.join(OUT_DIR, "results")


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    _write_json(os.path.join(OUT_DIR, "schematic.json"), schematic_graph.get_graph())
    _write_json(os.path.join(OUT_DIR, "analyses.json"), ANALYSES)

    results = {}
    for analysis in ANALYSES:
        name = analysis["name"]
        run_func = RUN_FUNCS[name]
        kwargs = {"plot_to_bytes": True} if name in TRANSIENT_ANALYSES else {}
        print(f"Running {name}...")
        result = run_func(**kwargs)
        results[name] = result

        subsystem = schematic_graph.subsystem_for_analysis(name)
        raw_overlay = OVERLAY_BUILDERS[name](result["summary"])
        overlay = {f"{subsystem}__{net}": value for net, value in raw_overlay.items()}

        plot_url = None
        plot_bytes = result.get("plot_bytes")
        if plot_bytes:
            plot_filename = f"{name}.png"
            with open(os.path.join(PLOTS_DIR, plot_filename), "wb") as f:
                f.write(plot_bytes)
            plot_url = f"plots/{plot_filename}"

        _write_json(os.path.join(RESULTS_DIR, f"{name}.json"), {
            "summary": result["summary"],
            "plot_url": plot_url,
            "overlay": overlay,
        })

    print("Computing board health score...")
    score = scoring.compute_board_score(results)
    _write_json(os.path.join(OUT_DIR, "score.json"), score)

    print(f"Wrote fixtures to {OUT_DIR}")


if __name__ == "__main__":
    main()
