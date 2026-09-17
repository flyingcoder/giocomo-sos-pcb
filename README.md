# Giacomo PCB

A compact, battery-powered **personal safety / SOS panic-button wearable**
built around an **ESP32-S3** paired with a **4G LTE + GPS cellular module**
(A7670C-LANS), standalone GPS (L76KB-A58), a SIM card slot, a speaker/mic
audio path (ES8311 codec + 3.5 mm jacks), a vibration motor, a buzzer, an
IMU (LSM6DS3TR-C), single-cell LiPo charging/boost (IP5306), and two USB-C
ports (one through a CH340C USB-UART bridge for logging/flashing).

This repository holds the exported EasyEDA (LCEDA) project data for the
board — schematic, PCB layout, and BOM — plus tooling built on top of it:
a written analysis of the design, a PySpice circuit simulation of its
analog/discrete subsystems, and two small Flask web apps for browsing all
of it.

There is no firmware or embedded source code here; this is a hardware
design repo.

## Repository layout

```
giacomo-schematic.json          Exported EasyEDA schematic (source of truth for nets/BOM)
giacomo-pcb-layout.json         Exported EasyEDA PCB layout (footprints, layers, routing)
giacomo-project-manifest.json   EasyEDA project/document metadata
schematic-view-*.jpeg           Screenshots of the four schematic sheets/regions
analysis/                       Written analysis of the design (see below)
DESIGN_FEEDBACK.md              Plain-English design review (schematic/PCB/BOM) backed by simulator evidence
simulation/                     PySpice model of the board's analog/discrete circuits
webapp/                         Read-only dashboard over everything in this repo
```

### `analysis/`

A written breakdown of the EasyEDA export, since this is a hardware
project rather than a codebase:

| File | Covers |
|---|---|
| [01-folder-inventory.md](analysis/01-folder-inventory.md) | Raw file listing, types, sizes |
| [02-project-overview.md](analysis/02-project-overview.md) | What the device is, subsystem summary |
| [03-schematic-analysis.md](analysis/03-schematic-analysis.md) | Circuit-block breakdown, net names, notable design choices |
| [04-bom.md](analysis/04-bom.md) | Full bill of materials with manufacturer/supplier part numbers |
| [05-pcb-layout-analysis.md](analysis/05-pcb-layout-analysis.md) | Board file status: layers, DRC rules, routing progress |
| [06-images.md](analysis/06-images.md) | What each JPEG in the folder actually shows |

[DESIGN_FEEDBACK.md](DESIGN_FEEDBACK.md) is a plain-English review of the
*design itself* — schematic, PCB layout, and BOM — checked directly against
the raw JSON rather than against the six documents above, and backed by
evidence from running the board through the circuit simulator (see
`simulation/` below). Read this first if you want the "will it work"
answer.

**Board status:** every schematic component has a footprint placed on the
PCB, but the board is effectively unrouted (one copper track total) — this
project is at the placement/pre-routing stage, not manufacturing-ready.

### `simulation/`

A SPICE-accurate model (via PySpice/ngspice) of the parts of the board
that are actual analog/discrete circuit design — power tree, CH340
auto-reset network, LTE_PWRKEY driver, buzzer/vibration motor drivers, LED
current-limiting, USB-C CC termination. Digital SoCs/ICs (ESP32-S3, A7670C,
L76KB-A58, ES8311, LSM6DS3TR-C, CH340C) are represented as behavioral
supply loads rather than simulated at the transistor level, since no
public SPICE models exist for them and their internal logic isn't a
circuit-simulation problem.

Also includes `scoring.py`, which turns the simulation results into a
heuristic 0–100% "board health" score.

See [simulation/README.md](simulation/README.md) for the full
component/connection inventory (built by reading the schematic
pin-by-pin) and simulation methodology.

Run the CLI:

```bash
pip3 install -r simulation/requirements.txt   # also requires ngspice (brew install ngspice)
python3 simulation/giacomo_circuit.py
```

Or the interactive web app (lets you tweak parameters like battery
voltage, load currents, host Rp, temperature and re-run each analysis):

```bash
python3 simulation/webapp/app.py
# open http://127.0.0.1:5057
```

### `webapp/`

A unified read-only dashboard over everything in this repo: every analysis
doc, the raw source JSON, the four schematic screenshots, and a live embed
of the simulation web app.

```bash
pip3 install -r webapp/requirements.txt
python3 webapp/app.py
# open http://127.0.0.1:5058
```

Start `simulation/webapp/app.py` separately (port 5057) if you also want
the embedded Circuit Simulation tab to work.

## Source data

`giacomo-schematic.json` and `giacomo-pcb-layout.json` are the
authoritative source of truth for nets, components, and layout — the BOM
copy embedded in `giacomo-project-manifest.json` is a stale, incomplete
snapshot and should not be used (see
[DESIGN_FEEDBACK.md](DESIGN_FEEDBACK.md)).
