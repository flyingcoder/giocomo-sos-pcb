"""Shared content registry for the Giacomo dashboard.

DOCS / DATA_FILES / IMAGES are the single allowlist of what the dashboard
serves, keyed by short slug -- consumed by both the local Flask dev server
(webapp/app.py) and the static Netlify build (scripts/build_static_site.py)
so the two never drift out of sync.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS = {
    "overview": {
        "title": "Overview",
        "group": "Analysis",
        "path": ROOT / "analysis" / "README.md",
    },
    "feedback": {
        "title": "Design Feedback",
        "group": "Analysis",
        "path": ROOT / "DESIGN_FEEDBACK.md",
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


def build_nav(simulation_origin=None):
    """The `nav` blob embedded in index.html for the SPA router.

    `simulation_origin` is only meaningful for the local Flask dev server
    (used to probe/embed the live simulation webapp); the static build
    passes None since that concept doesn't apply there.
    """
    return {
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
        "simulationOrigin": simulation_origin,
    }
