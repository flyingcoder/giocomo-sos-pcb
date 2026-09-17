#!/usr/bin/env python3
"""Unified read-only dashboard for the Giacomo PCB project.

Single place to browse everything produced about this EasyEDA export:
every analysis markdown doc (including the root-level design feedback
and the simulation notes), the raw source JSON files, the four schematic
screenshots, the mermaid diagram page, and a live embed of the PySpice
circuit-simulation webapp.

All served content is looked up through the fixed allowlist dicts in
content_registry.py (DOCS / DATA_FILES / IMAGES) keyed by short slug --
routes never take a raw filesystem path from the client, so there's no
path-traversal surface even though this reads arbitrary project files.

Launch (from anywhere): `python3 webapp/app.py`, then open
http://127.0.0.1:5058. (5057 is already used by
simulation/webapp/app.py -- start that separately if you want the
Circuit Simulation tab to work; see simulation/README.md.)

There is also a static build of this dashboard for Netlify (see
scripts/build_static_site.py) -- it shares content_registry.py but
pre-bakes the simulation tab from committed fixtures instead of embedding
a live simulation server. app.js branches on `nav.simulationOrigin`
(set here, null in the static build) to pick which of the two behaviors
to render.
"""

import json

import markdown as md
from flask import Flask, abort, jsonify, render_template, send_file

from content_registry import DATA_FILES, DOCS, IMAGES, ROOT, build_nav

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc"]

SIMULATION_ORIGIN = "http://127.0.0.1:5057"


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        nav = build_nav(simulation_origin=SIMULATION_ORIGIN)
        return render_template("index.html", nav_json=json.dumps(nav))

    @app.get("/api/doc/<key>.json")
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

    @app.get("/api/json/<key>.json")
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

    @app.get("/raw/doc/<key>.md")
    def raw_doc(key):
        entry = DOCS.get(key)
        if entry is None:
            abort(404)
        return send_file(entry["path"], mimetype="text/markdown")

    @app.get("/raw/json/<key>.json")
    def raw_json(key):
        entry = DATA_FILES.get(key)
        if entry is None:
            abort(404)
        return send_file(entry["path"], mimetype="application/json")

    @app.get("/image/<key>.jpeg")
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
