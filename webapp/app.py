#!/usr/bin/env python3
"""Unified read-only dashboard for the Giacomo PCB project.

Single place to browse everything produced about this EasyEDA export:
every analysis markdown doc (including the root-level accuracy feedback
and the simulation notes), the raw source JSON files, the four schematic
screenshots, the mermaid diagram page, and a live embed of the PySpice
circuit-simulation webapp.

All served content is looked up through fixed allowlist dicts below
(DOCS / DATA_FILES / IMAGES) keyed by short slug -- routes never take a
raw filesystem path from the client, so there's no path-traversal surface
even though this reads arbitrary project files.

Launch (from anywhere): `python3 webapp/app.py`, then open
http://127.0.0.1:5058. (5057 is already used by
simulation/webapp/app.py -- start that separately if you want the
Circuit Simulation tab to work; see simulation/README.md.)
"""

import json
from pathlib import Path

import markdown as md
from flask import Flask, abort, jsonify, render_template, send_file

ROOT = Path(__file__).resolve().parent.parent

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc"]

DOCS = {
    "overview": {
        "title": "Overview",
        "group": "Overview",
        "path": ROOT / "analysis" / "README.md",
    },
    "feedback": {
        "title": "Analysis Accuracy Feedback",
        "group": "Overview",
        "path": ROOT / "ANALYSIS_FEEDBACK.md",
    },
    "inventory": {
        "title": "01 · Folder Inventory",
        "group": "Analysis",
        "path": ROOT / "analysis" / "01-folder-inventory.md",
    },
    "project": {
        "title": "02 · Project Overview",
        "group": "Analysis",
        "path": ROOT / "analysis" / "02-project-overview.md",
    },
    "schematic": {
        "title": "03 · Schematic Analysis",
        "group": "Analysis",
        "path": ROOT / "analysis" / "03-schematic-analysis.md",
    },
    "bom": {
        "title": "04 · Bill of Materials",
        "group": "Analysis",
        "path": ROOT / "analysis" / "04-bom.md",
    },
    "pcb": {
        "title": "05 · PCB Layout Analysis",
        "group": "Analysis",
        "path": ROOT / "analysis" / "05-pcb-layout-analysis.md",
    },
    "images-doc": {
        "title": "06 · Image Contents",
        "group": "Analysis",
        "path": ROOT / "analysis" / "06-images.md",
    },
    "sim-readme": {
        "title": "Simulation Notes",
        "group": "Simulation",
        "path": ROOT / "simulation" / "README.md",
    },
}

DATA_FILES = {
    "schematic-json": {
        "title": "giacomo-schematic.json",
        "note": "EasyEDA schematic — symbols, wires, BOM",
        "path": ROOT / "giacomo-schematic.json",
    },
    "pcb-json": {
        "title": "giacomo-pcb-layout.json",
        "note": "EasyEDA PCB — footprints, layers, DRC rules",
        "path": ROOT / "giacomo-pcb-layout.json",
    },
    "manifest-json": {
        "title": "giacomo-project-manifest.json",
        "note": "Project index — UUID, documents, embedded BOM",
        "path": ROOT / "giacomo-project-manifest.json",
    },
}

IMAGES = {
    "img-core-power-mcu-gps": {
        "title": "Core Power / MCU / GPS",
        "path": ROOT / "schematic-view-core-power-mcu-gps.jpeg",
    },
    "img-audio-usb-modem": {
        "title": "Audio / USB / Modem",
        "path": ROOT / "schematic-view-audio-usb-modem.jpeg",
    },
    "img-audio-usbc-imu": {
        "title": "Audio / USB-C / IMU",
        "path": ROOT / "schematic-view-audio-usbc-imu.jpeg",
    },
    "img-modem-pinout-antennas": {
        "title": "Modem Pinout / Antennas",
        "path": ROOT / "schematic-view-modem-pinout-antennas.jpeg",
    },
}

SIMULATION_ORIGIN = "http://127.0.0.1:5057"


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        nav = {
            "docs": [
                {
                    "key": k,
                    "title": v["title"],
                    "group": v["group"],
                    "source": str(v["path"].relative_to(ROOT)),
                }
                for k, v in DOCS.items()
            ],
            "data": [{"key": k, "title": v["title"], "note": v["note"]} for k, v in DATA_FILES.items()],
            "images": [{"key": k, "title": v["title"]} for k, v in IMAGES.items()],
            "simulationOrigin": SIMULATION_ORIGIN,
        }
        return render_template("index.html", nav_json=json.dumps(nav))

    @app.get("/api/doc/<key>")
    def api_doc(key):
        entry = DOCS.get(key)
        if entry is None:
            abort(404)
        text = entry["path"].read_text(encoding="utf-8")
        html = md.markdown(text, extensions=MD_EXTENSIONS)
        return jsonify({
            "title": entry["title"],
            "html": html,
            "source": str(entry["path"].relative_to(ROOT)),
        })

    @app.get("/api/json/<key>")
    def api_json(key):
        entry = DATA_FILES.get(key)
        if entry is None:
            abort(404)
        parsed = json.loads(entry["path"].read_text(encoding="utf-8"))
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        return jsonify({
            "title": entry["title"],
            "note": entry["note"],
            "pretty": pretty,
            "size": entry["path"].stat().st_size,
            "source": str(entry["path"].relative_to(ROOT)),
        })

    @app.get("/raw/doc/<key>")
    def raw_doc(key):
        entry = DOCS.get(key)
        if entry is None:
            abort(404)
        return send_file(entry["path"], mimetype="text/markdown")

    @app.get("/raw/json/<key>")
    def raw_json(key):
        entry = DATA_FILES.get(key)
        if entry is None:
            abort(404)
        return send_file(entry["path"], mimetype="application/json")

    @app.get("/image/<key>")
    def image(key):
        entry = IMAGES.get(key)
        if entry is None:
            abort(404)
        return send_file(entry["path"])

    @app.get("/diagrams")
    def diagrams():
        return send_file(ROOT / "analysis" / "visualization.html")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5058, threaded=True)
