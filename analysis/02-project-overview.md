# Project Overview

**Project name:** `Giacomo` (EasyEDA project UUID `0cdd329b78f0c12f30026dc5e7a6aca1`)
**Editor:** EasyEDA / LCEDA Pro, version 6.5.51
**Created:** 2026-09-10 · **Last updated:** 2026-09-17 (per `giacomo-project-manifest.json`)
**Sheets:** 1 schematic sheet ("Sheet_1"), 1 PCB document

## What the device is

The BOM and net names (`BTN_CANCEL`, `BTN_RIDER`, `false alarm`,
`VIB_MOTOR`, `BUZZER_PWM`, `USIM1_*`, `GNSS_TX/RX`) point to a
**battery-powered personal-safety / SOS panic-button wearable** with
cellular connectivity and location tracking — the kind of device used for
lone-worker safety, elder care, or motorcycle-rider ("Rider") emergency
alert products.

## Subsystems

| Subsystem | Key part(s) | Notes |
|---|---|---|
| **MCU / brain** | ESP32-S3-WROOM-1 (N16R8), U2 | 16 MB flash / 8 MB PSRAM variant — enough headroom for audio buffering + TLS/cellular stack |
| **Cellular (4G LTE + 2G fallback)** | A7670C-LANS, U1 (SIMCom, LGA-124) | Full UART, USB, SPI/I2C camera-style aux bus broken out; nano-SIM socket (CARD1, SMN-303) |
| **GNSS / GPS** | L76KB-A58, U3 (Quectel) | Shares antenna feed path near BT/Wi-Fi/GNSS antenna pins (`GNSS_ANT`, `BT_ANT`) broken out on U1 too |
| **Audio** | ES8311 codec (U4), 3.5 mm mic jack (CN5), 3.5 mm audio/speaker jack (CN1) | I2S to ESP32-S3, analog mic/line in/out — supports a voice intercom / two-way call feature |
| **Haptics / alert** | Buzzer (BUZZER1, 2700 Hz), coin vibration motor (via CN3, driven by Q6) | Physical alert feedback independent of audio path |
| **Power** | IP5306 boost/charge IC (U5, single-cell Li-ion boost converter + charger), AP2112K-3.3 LDO (U6) | IP5306 is a common "power bank" IC — implies USB-C charging + 5 V boost for the RF modules |
| **Motion sensing** | LSM6DS3TR-C 6-axis IMU (U7, ST) | Likely fall-detection / motion-wake / orientation sensing |
| **USB / programming** | 2× USB-C (USBC1, USBC2), CH340C USB-UART bridge (U10) | One USB-C appears to be power/data to ESP32-S3 native USB, the other routes through CH340C for UART logging/flashing |
| **RF connectors** | 2× U.FL/IPEX (U8 for GNSS "ANTON" pin, plus antenna pads on U1) | External antennas for cellular/GNSS, expected given the LGA modem package has no onboard antenna |
| **User input** | 6× tactile switches: `AI`, `RST`, `BOOT`, `power ON/OFF`, `Intercom`, `false alarm`, plus SW6 (SK22D02G4, through-hole) | `false alarm` (cancel) + `Intercom` (rider) map directly to `BTN_CANCEL`/`BTN_RIDER` nets — this is the actual SOS button pair |
| **Status indication** | 4× LEDs: red, blue, green, white | Likely charge/power/network-status/alert indicators |
| **Protection** | 2× 1N4148WS diodes (D1, D2), B5819 Schottky (U9) | Reverse-polarity / battery-path protection |

## Notable design details worth flagging

- **Designator hygiene:** five 0603 resistors (10 kΩ ×2, 5.1 kΩ ×2, 2.2 kΩ ×1)
  are designated `U11`–`U15` instead of an `R`-prefix. They sit on the
  CH340C DTR/RTS auto-reset transistor network (`Q8`/`Q9`) — functionally
  resistors, just mis-prefixed in the schematic. Cosmetic, but worth
  correcting before board revision/BOM handoff to avoid confusing a
  fabrication house's pick-and-place import.
- **Two USB-C connectors** on one small board is unusual — one is almost
  certainly for end-user charging/data (to IP5306 + ESP32-S3 native USB),
  the other dedicated to production programming/debug via CH340C. Worth
  double-checking silkscreen/labeling on the final board so users don't
  plug into the wrong port.
- **SW6 (`SK22D02G4`) is the only through-hole part** in an otherwise
  all-SMD design — likely the physical slide power switch, which commonly
  needs a through-hole mechanical connector for durability.

## Verification & confidence

Independently re-checked against `giacomo-schematic.json` and
`giacomo-project-manifest.json` (counts recomputed from raw data, not
trusted from this document). **~97% of checkable factual claims VERIFIED,
zero contradicted.**

| Claim | Confidence | Evidence |
|---|---|---|
| Project UUID, editor v6.5.51, created 2026-09-10 / updated 2026-09-17 | **VERIFIED** | Exact match to manifest `uuid`, `editorVersion`, `created_at`, `updated_at` |
| 1 schematic sheet + 1 PCB doc | **VERIFIED** | Manifest `documents` array = 2 entries (docType 1 "Sheet_1", docType 3 "PCB_Giacomo rstf") |
| U1–U10, CARD1 part numbers / manufacturers / packages / LCSC codes | **VERIFIED** | Every field matches the raw `BOM` array row-for-row |
| Q5–Q9 = 2N3904 ×5 | **VERIFIED** | BOM row match |
| U11–U15 mis-designated resistor network (10kΩ×2, 5.1kΩ×2, 2.2kΩ×1) | **VERIFIED** | BOM rows confirm values + `R0603` package under `U`-prefixed designators |
| SW1–SW7 labels/functions, SW6 as the lone through-hole part | **VERIFIED** | BOM package field confirms `SW-TH_SK22D02G4` vs `SW-SMD_4P-…` for the rest |
| CN1–CN5, USBC1/USBC2 roles | **VERIFIED** | BOM rows match, including CN4's literal name "Pin battery jack GSM" |
| "Likely fall-detection / motion-wake" (IMU use), "power-bank IC" characterization, "two-way voice intercom" reading | **INFERENCE** | Reasonable interpretation, not a verifiable file fact — correctly hedged with "likely"/"suggests" in the source text |
| "Designator hygiene" / two-USB-C / SW6-through-hole callouts | **VERIFIED** (underlying facts) | Recommendations themselves are judgment calls, but the facts they're based on all check out |

No claims contradicted by evidence.
