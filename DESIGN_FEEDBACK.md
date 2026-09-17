# Design Feedback — Giacomo Board

Plain-English feedback on the actual hardware design (schematic, PCB layout,
BOM) exported from EasyEDA. Written for someone who wants to know "is this
board going to work" without wading through raw JSON.

**How this differs from the earlier analysis-accuracy audit:** a prior
`ANALYSIS_FEEDBACK.md` (since removed — its findings are folded in below)
graded the write-ups in `analysis/*.md` against the raw data. This file
grades the **design itself** — every claim below was checked against
`giacomo-schematic.json`, `giacomo-pcb-layout.json`, and
`giacomo-project-manifest.json` directly, not copied from the analysis docs.
Anywhere that audit found the analysis docs wrong or incomplete, the
correction is folded in here rather than repeated as a separate error. New
in this file: the design has been run through the project's built-in
circuit simulator (`simulation/giacomo_circuit.py` + `scoring.py`), which
gives actual measured/simulated evidence — not just a read of the
schematic — for whether specific parts of the circuit will behave
correctly.

---

## Bottom line: will it work?

**Board health score: 79.3 / 100 — "Likely to work, some margins are
tight."** (Source: `webapp/static/sim-data/score.json`, produced by running
all 7 of the project's SPICE analyses at their default/nominal parameters.)

In plain terms: most of the board's power and reset circuitry checks out
with healthy margin. There is **one real, specific risk** worth fixing
before building this: **the cellular modem's battery feed dips dangerously
low every time it transmits.** Everything else — the two main voltage
rails, the auto-reset/auto-program circuit, the modem's power-on pulse, the
LEDs, buzzer, motor, and USB-C connections — simulated within safe margins.

| # | What was checked | Result | Confidence |
|---|---|---|---|
| 1 | Modem battery feed (`VBAT_LTE`) survives a transmit burst | ❌ **Fails** — dips to 1.90 V | **Simulated (SPICE transient)** |
| 2 | Main 5 V rail (`VBUS_5V`) regulation | ✅ 5.00 V, on target | **Simulated (SPICE DC)** |
| 3 | Main 3.3 V logic rail (`3V3`) regulation | ✅ 3.27 V, on target | **Simulated (SPICE DC)** |
| 4 | Auto-reset circuit pulls `EN` low enough to reset the MCU | ✅ 0.04 V | **Simulated (SPICE transient)** |
| 5 | Auto-program circuit pulls `IO0` low enough for flashing | ✅ 0.03 V | **Simulated (SPICE transient)** |
| 6 | Modem power-on pulse width | ✅ 151 ms (spec needs ≥100 ms) | **Simulated (SPICE transient)** |
| 7 | USB-C cable-orientation/current-detect resistors | ✅ within spec bands | **Simulated (SPICE DC)** |
| 8 | Buzzer / vibration motor drive swing | ✅ both healthy | **Simulated (SPICE DC)** |
| 9 | LED current-limiting resistors | ⚠️ working, but two LEDs are dim | **Simulated (SPICE DC)** |

See "Running it through the simulator" below for the full evidence and how
much to trust the 79.3% number itself.

---

## 1. What the device is (plain English)

This is a **wearable panic-button / SOS device** — the kind you'd wear as a
pendant or wristband for personal safety, elder care, or a motorcycle
rider's emergency alert. It can:

- Make a cellular (4G/LTE, with 2G fallback) connection to call for help,
  using a nano-SIM card.
- Know its GPS location.
- Let the wearer talk through a built-in mic/speaker (a basic intercom).
- Buzz and vibrate to alert the wearer.
- Sense motion (likely for fall-detection or "wake on movement," though the
  firmware isn't part of this export so that's a reasonable guess, not a
  verified fact).
- Charge over USB-C like a phone.

It's built around one main chip, the ESP32-S3 (the "brain"), talking to a
separate cellular modem chip and a separate GPS chip. **Confidence: verified**
— directly from the parts list and the wiring between them, not an inference.

## 2. Schematic feedback (the circuit design)

**What's there:** 84 parts placed, 266 wires, 104 junctions, 113 net
labels, wired into one sheet. That adds up to a complete, single-sheet
circuit design — not a stub or a partial export. **Confidence: verified**
(recounted directly from the raw file).

**What's good about the design, as actually wired:**

- The modem's battery feed is kept **physically separate** from the logic
  battery feed (two different battery connectors). This is the right call
  — the modem can pull 1–2 A in short bursts while transmitting, and if
  that shared a battery path with the logic circuitry, it would risk
  resetting the whole board every time it transmits. (This separation is
  correct in principle — see the simulator section below for why it's
  *not yet enough* in practice.)
- The auto-reset/auto-program circuit (the two transistors driven by the
  USB-UART chip's DTR/RTS lines) is the standard, well-proven pattern used
  by ESP32 dev boards everywhere — nothing unusual or risky here.
- The modem's power-on button circuit (one transistor pulling its `PWRKEY`
  pin low) is the textbook circuit SIMCom's own datasheet recommends.

**What to fix or double-check:**

- Five resistors on the auto-reset network are labeled `U11`–`U15` instead
  of `R11`–`R15`. Not a functional problem — they're wired correctly — but
  a real pick-and-place / BOM-import risk, since most manufacturing
  tooling assumes an "U" designator means a chip, not a resistor.
  **Confidence: verified.**
- One GPIO pin (`IO0`) does two jobs at once — it's both the ESP32's
  boot-mode strap pin *and* the signal that drives the vibration motor
  transistor. This is only safe if the motor driver's pull doesn't
  interfere with the boot-strap read at power-up. Worth confirming in
  firmware/timing, not something the schematic alone can settle.
  **Confidence: verified wiring, unverified consequence** (i.e., the fact
  that they share a node is confirmed; whether it actually causes a
  problem depends on timing this export doesn't contain).
- Camera and LCD interface pins are broken out on the modem chip's
  footprint but not wired to anything — normal for this chip (it's a
  shared footprint across module variants), not a mistake.

## 3. PCB layout feedback (the physical board)

**This is the most important thing to know about the PCB file:**

**82 of 83 parts are placed on the board, but only 1 copper track has been
drawn.** There are no vias, no ground/power pours, and no completed
routing. **Confidence: verified** — recounted directly from the shape
data (82 `LIB`/footprint entries, 1 `TRACK` entry, 0 `VIA` entries).

**In plain terms: this is a component-placement file, not a finished,
buildable board.** Routing — connecting all those placed parts with actual
copper — is the next major task, not something already done. This is a
completely normal stage to be at, but it means "PCB design" is still
ahead, not behind you.

**Other findings, checked against the raw layout file:**

- **The missing part is U9**, the small Schottky protection diode. It's
  in the schematic and the parts list, but its footprint was never placed
  on the board. (The earlier analysis docs noted "82 of 83 placed" but
  didn't say which one — this was traced down directly.) **Confidence:
  verified.**
- The layer settings hint that this board is meant to be **4 layers**, not
  2 — two of the internal copper layers are turned on and marked as
  signal layers, the rest are switched off. Worth locking this in
  explicitly before routing starts, since it changes how RF traces
  (cellular/GPS) and USB data pairs need to be routed. **Confidence:
  likely** (a real signal in the data, not a hard label like "layer count:
  4" would be).
- The design uses fine-pitch parts (a 0.4 mm-pitch audio chip, a
  0.5 mm-pitch motion sensor, and 0201-size resistors — these are smaller
  than a grain of rice). The board-wide clearance/track-width rules
  currently saved in the file are generic defaults, not yet tuned for
  those fine-pitch areas. This needs attention once routing starts, or
  those chips will be very hard to route cleanly. **Confidence: verified**
  (settings and part sizes both read directly from source data).

## 4. BOM feedback (the parts list)

**48 unique parts, 83 total placed instances, all sourced through LCSC.**
**Confidence: verified** — recomputed directly from the raw parts list, not
copied from `analysis/04-bom.md`.

Every part number, manufacturer, package, and supplier code checked came
back correct, with three specific corrections to what the analysis
write-up said:

| Correction | What the analysis doc said | What the raw data actually says |
|---|---|---|
| U9 manufacturer | Blank / unknown | `晶导微电子` (a real manufacturer — just wasn't pulled into the doc) |
| "USB Type-C **3.1**" | Stated as USB 3.1 spec | Raw part number is `TYPE-C-31-M-12` — "31" is a connector model number, not a confirmed USB-3.1 data-rate claim. Treat both USB-C ports as USB-C only unless confirmed elsewhere |
| Manifest BOM copy | Called "identical" to the schematic's BOM | The project manifest actually stores the parts list **twice**. The copy attached to the PCB document is **stale** — it's missing rows (e.g. the C11 330 µF cap, one of the ten 100 nF caps). **If anyone pulls BOM data for manufacturing from the manifest, they must use the schematic-document copy, not the PCB-document copy.** |

Everything else in the parts list — LED colors (literally `RED`/`BLUE`/
`GREEN`/`WHITE` in the data, not a guess), the through-hole power switch,
the battery jacks, the five 2N3904 transistors — checked out exactly as
listed. **Confidence: verified.**

---

## Running it through the simulator (the real evidence)

The project ships a real circuit simulator
(`simulation/giacomo_circuit.py`, built on PySpice/ngspice) that models the
board's actual analog circuitry — battery paths, regulators, transistor
drive networks, LED/motor/buzzer drivers, USB-C detect resistors — using
real component values from the BOM and real datasheet parameters for the
transistors and diodes. It does **not** try to simulate the digital chips'
internal logic (the ESP32, the modem, the GPS chip, the audio codec) —
there's no meaningful SPICE model for "what a modem's firmware does," so
those are represented only as realistic current loads on the power rails.
That's an honest limitation, not a shortcut — see
`simulation/README.md` §"Simulation scope & approach" for the full
reasoning.

Running the CLI (`python3 simulation/giacomo_circuit.py`) and the scoring
pass (`simulation/scoring.py`) reproduces the same numbers already saved
in `webapp/static/sim-data/score.json`:

### Overall score: 79.3% — "Likely to work, some margins are tight"

| Check | Result | Score | Weight | Confidence |
|---|---|---|---|---|
| **Modem battery feed sag during a transmit burst** | Dips to **1.90 V** (typical brownout floor for this kind of modem is ~3.0 V) | **0%** | 3.0 (tied-highest) | Simulated (transient SPICE) |
| 3.3 V logic rail regulation | 3.27 V (target 3.30 V ±5%) | 100% | 3.0 (tied-highest) | Simulated (DC) |
| Reset circuit pulls MCU's `EN` pin low enough | 0.04 V | 100% | 2.0 | Simulated (transient) |
| Modem's power-on pulse width | 151 ms (needs ≥100 ms per SIMCom spec) | 100% | 2.5 | Simulated (transient) |
| 5 V boost rail regulation | 5.00 V (target 5.00 V ±5%) | 100% | 2.0 | Simulated (DC) |
| Auto-program circuit pulls `IO0` low enough | 0.03 V | 100% | 1.5 | Simulated (transient) |
| USB-C cable-detect resistor bands (both ports, 3 host current levels) | all within spec | 100% | 1.0 | Simulated (DC) |
| LED forward currents | 1.27 mA / 0.29 mA / 1.18 mA / 0.29 mA (2 of 4 LEDs are dim but safe) | 48.5% | 1.0 | Simulated (DC) |
| Buzzer drive swing | 3.64 V swing | 100% | 0.5 | Simulated (DC) |
| Vibration motor drive swing | 3.11 V swing | 100% | 0.5 | Simulated (DC) |

### The one thing to actually fix

**The modem's battery feed (`VBAT_LTE`) is not up to the job as currently
designed.** When the modem transmits — which happens constantly, since
that's its entire job — it pulls a short, sharp burst of up to ~1.8 A.
The current design cushions that burst with a single 330 µF capacitor
(`C11`) plus a reverse-polarity diode (`D2`) in series with the battery.
The simulator shows that combination isn't enough: the voltage at the
modem's power pins **drops to 1.90 V during the burst**, well under the
roughly 3.0 V floor where this class of cellular modem typically
browns out, resets, or drops its network registration.

This matters because it's exactly the moment the device most needs to
work — sending an SOS. **This is the single highest-weighted failing
check in the whole scorecard** (tied for the highest weight alongside the
3.3 V rail, because both gate whether the board functions at all, not just
peripheral niceties like LED brightness).

Reasonable fixes, roughly cheapest-to-most-invasive: add a larger bulk/low-ESR
capacitor bank at the modem's VBAT pins (or a supercapacitor, which is the
common industry fix for exactly this problem), source a battery with lower
internal resistance, or verify the diode `D2`'s voltage drop and forward
current rating aren't adding to the problem. This should be resolved and
re-simulated before committing to the current PCB layout.

### Two minor items, not blocking

- **Two of the four status LEDs run dim** (0.29 mA vs. ~1.2 mA for the
  other two) — likely a resistor-value mismatch across the four LED
  branches. Not a failure, just visibly inconsistent brightness. Worth a
  quick check of `R9`–`R12`'s values against each LED's forward-voltage
  spec.
- The `IO0` shared-node concern flagged in the schematic section above
  (boot-strap pin doubling as the vibration-motor driver signal) is outside
  what this circuit simulator checks — it's a firmware/timing question,
  not a SPICE question.

### How much to trust the 79.3% number itself

This score is a **heuristic engineering-margin estimate, not a certified
reliability number.** It's built from real, typical-case component
behavior (2N3904 datasheet parameters, standard Li-ion internal
resistance, datasheet-typical IC quiescent currents), not from measuring
an actual built board. Two honest caveats:

1. The current draw values for each chip (ESP32, modem, GPS, audio codec,
   etc.) are typical/datasheet estimates, not measurements — a real board
   could measure somewhat differently.
2. The pass/fail thresholds in `scoring.py` (e.g., "3.0 V is roughly where
   a modem browns out") are reasonable engineering estimates the project
   documents openly, not values copied verbatim from a specific chip's
   datasheet.

Given those caveats, treat the 79.3% and the "likely to work" verdict as a
**strong, evidence-based signal that this design will mostly work but has
one specific, fixable risk** — not as a guarantee. The individual
simulated numbers (voltages, pulse widths, currents) are the trustworthy
part; the single rolled-up percentage is a convenience summary on top of
them.

---

## Summary

- **Schematic:** essentially complete and sound. One cosmetic labeling
  issue (`U11`–`U15`), one wiring choice worth a firmware-level
  double-check (`IO0` sharing boot-strap and motor-driver duty).
- **PCB layout:** placement-only. Routing, the 4-layer decision, fine-pitch
  clearance rules, and placing the missing `U9` footprint are the open
  work — this is expected at this stage, not a defect.
- **BOM:** accurate and buildable, with three data-quality corrections
  applied above (U9 manufacturer, USB-C spec claim, stale manifest copy).
- **Will it work?** Mostly yes, with one real risk backed by simulation
  evidence: **the modem's battery feed needs a stronger reservoir before
  this board can reliably survive its own transmit bursts.** Fix that one
  thing, then route the board, and the underlying circuit design is sound.
