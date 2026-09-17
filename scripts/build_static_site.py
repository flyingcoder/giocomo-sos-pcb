#!/usr/bin/env python3
"""Builds the static Netlify site for the Giacomo dashboard into dist/.

Pure Python, no native dependencies (just Markdown + Jinja2) -- this is
the command Netlify actually runs (see netlify.toml). It reuses
webapp/content_registry.py so the doc/data/image allowlist can't drift
from the local Flask dev server, renders webapp/templates/index.html
with Jinja2 directly (no Flask needed at build time), and copies the
already-committed simulation fixtures from
webapp/static/sim-data/ (see simulation/webapp/build_fixtures.py --
that script needs PySpice/ngspice and is run by hand, not by this build).

Usage:
    python3 scripts/build_static_site.py
"""

import json
import shutil
import sys
from pathlib import Path

import markdown as md
from jinja2 import Environment, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "webapp"))
from content_registry import DATA_FILES, DOCS, IMAGES, ROOT, build_nav  # noqa: E402

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc"]

DIST = REPO_ROOT / "dist"


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def build_docs():
    for key, entry in DOCS.items():
        text = entry["path"].read_text(encoding="utf-8")
        html = md.markdown(text, extensions=MD_EXTENSIONS)
        _write_json(DIST / "api" / "doc" / f"{key}.json", {
            "title": entry["title"],
            "html": html,
            "source": str(entry["path"].relative_to(ROOT)),
        })
        raw_dest = DIST / "raw" / "doc" / f"{key}.md"
        raw_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(entry["path"], raw_dest)


def build_data_files():
    for key, entry in DATA_FILES.items():
        parsed = json.loads(entry["path"].read_text(encoding="utf-8"))
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        _write_json(DIST / "api" / "json" / f"{key}.json", {
            "title": entry["title"],
            "note": entry["note"],
            "pretty": pretty,
            "size": entry["path"].stat().st_size,
            "source": str(entry["path"].relative_to(ROOT)),
        })
        raw_dest = DIST / "raw" / "json" / f"{key}.json"
        raw_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(entry["path"], raw_dest)


def build_images():
    dest_dir = DIST / "image"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for key, entry in IMAGES.items():
        shutil.copyfile(entry["path"], dest_dir / f"{key}.jpeg")


def build_diagrams():
    dest_dir = DIST / "diagrams"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "analysis" / "visualization.html", dest_dir / "index.html")


def build_static_assets():
    src = ROOT / "webapp" / "static"
    dest = DIST / "static"
    if dest.exists():
        shutil.rmtree(dest)
    # sim-data is committed fixture data, not a source asset to re-copy
    # verbatim from -- copytree it along with style.css/app.js since it
    # already lives under webapp/static/.
    shutil.copytree(src, dest)


def build_index():
    env = Environment(loader=FileSystemLoader(str(ROOT / "webapp" / "templates")))
    template = env.get_template("index.html")
    nav = build_nav(simulation_origin=None)
    html = template.render(
        nav_json=json.dumps(nav),
        url_for=_static_url_for,
    )
    (DIST / "index.html").write_text(html, encoding="utf-8")


def _static_url_for(_endpoint, filename):
    return f"/static/{filename}"


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    build_docs()
    build_data_files()
    build_images()
    build_diagrams()
    build_static_assets()
    build_index()

    print(f"Built static site into {DIST}")


if __name__ == "__main__":
    main()
