# Folder Inventory

| File | Original name | Size | Type | Role |
|---|---|---|---|---|
| `giacomo-schematic.json` | `Giacomo rstf.json` | 229,882 B (~225 KB) | EasyEDA schematic document (`docType: 5`, editor v6.5.51) | The schematic: components, wiring, BOM, single sheet ("Sheet_1") |
| `giacomo-pcb-layout.json` | `PCB_Giacomo rstf.json` | 811,902 B (~793 KB) | EasyEDA PCB document (`docType: 3`, editor v6.5.51) | The physical board layout: footprints, layers, DRC rules |
| `giacomo-project-manifest.json` | `info` | 33,300 B (~33 KB) | EasyEDA project manifest (JSON) | Top-level project metadata: UUID, document list, per-sheet component map, embedded BOM |
| `schematic-view-audio-usb-modem.jpeg` | `395745bd-...jpeg` | 194,416 B | JPEG screenshot | Schematic canvas view (audio codec / USB-C / CH340C / A7670C area) |
| `schematic-view-core-power-mcu-gps.jpeg` | `39a24fbf-...jpeg` | 160,735 B | JPEG screenshot | Schematic canvas view (ESP32-S3 core, GPS, IP5306 power, SIM slot) |
| `schematic-view-audio-usbc-imu.jpeg` | `605dc082-...jpeg` | 187,042 B | JPEG screenshot | Schematic canvas view (audio codec, both USB-C ports, IMU, regulator) |
| `schematic-view-modem-pinout-antennas.jpeg` | `72c0c1ba-...jpeg` | 213,260 B | JPEG screenshot | Schematic canvas view (A7670C right-hand pinout, GNSS/BT antennas, mic in) |
| `.DS_Store` | — | 6,148 B | macOS Finder metadata | Not project content |

Files were renamed from their original EasyEDA export names (right column)
to descriptive names (left column) after this analysis — see the note in
[README.md](README.md).

All four `.jpeg` files are **screenshots of the same single schematic sheet**
at different pan/zoom positions inside the EasyEDA editor (identifiable by
the "Sheet_1" tab and EasyEDA UI chrome visible in two of them) — they are
not separate photos of hardware or distinct design views. See
[06-images.md](06-images.md) for detail.

There is no README, license, revision history, Gerber/fabrication output, or
3D model in the folder — this is a raw EasyEDA project export plus a few
reference screenshots, not a packaged release.

> **Note on renaming:** `giacomo-project-manifest.json` had no file
> extension in its original form (`info`) — it is JSON content, so `.json`
> was added. If you re-import this project into EasyEDA, re-check that the
> tool doesn't expect the original literal filenames (EasyEDA typically
> keys off in-file UUIDs/paths rather than the OS filename, but this
> wasn't verified against a live import).

## Verification & confidence

Independently re-checked against `stat` output and the raw JSON files (not
trusted from this document). **~95% of claims VERIFIED.**

| Claim | Confidence | Evidence |
|---|---|---|
| All 8 file byte-sizes (229,882 / 811,902 / 33,300 / 194,416 / 160,735 / 187,042 / 213,260 / 6,148 B) | **VERIFIED** | Exact match via `stat -f "%z"` on every file |
| `giacomo-schematic.json` original name `Giacomo rstf.json` | **VERIFIED** | Manifest field `"schfilename": "Giacomo rstf.json"` |
| `giacomo-pcb-layout.json` original name `PCB_Giacomo rstf.json` | **VERIFIED** | Literal string found in `giacomo-project-manifest.json` |
| `giacomo-project-manifest.json` original name `info` | **UNVERIFIABLE** | No field inside the manifest records its own original filename; plausible (EasyEDA cloud export convention) but not provable from this file alone |
| 4 JPEG original UUID filenames (`395745bd-…`, `39a24fbf-…`, `605dc082-…`, `72c0c1ba-…`) | **UNVERIFIABLE** | None of the 4 UUID strings appear anywhere in the three JSON files — no corroborating or contradicting evidence found |
| No README/license/revision history/Gerber/3D model in original export | **VERIFIED** | Confirmed via `ls -la` of project root at export-content level |

No claims contradicted by evidence.
