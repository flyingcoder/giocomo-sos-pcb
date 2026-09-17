# Bill of Materials

Extracted from the `BOM` array in `giacomo-schematic.json` (identical data
is also duplicated inside `giacomo-project-manifest.json`). 48 line items, 83 total placed component
instances. All parts are sourced through **LCSC**; most manufacturers are
mainland-China passive/connector vendors plus name-brand silicon (ST,
Espressif, Quectel, SIMCom, ADI/Diodes-class parts).

## Key ICs / modules

| Designator | Part | Manufacturer | Package | LCSC # |
|---|---|---|---|---|
| U1 | A7670C-LANS (4G LTE modem) | SIMCom | LGA-124 | C18548274 |
| U2 | ESP32-S3-WROOM-1-N16R8 | Espressif | SMD module | C2913202 |
| U3 | L76KB-A58 (GPS/GNSS) | Quectel | 18-pin SMD module | C2916234 |
| U4 | ES8311 (audio codec) | Everest Semi | WQFN-20 | C962342 |
| U5 | IP5306 (charge + boost PMIC) | Injoinic | ESOP-8 | C181692 |
| U6 | AP2112K-3.3TRG1 (LDO) | Diodes Inc. | SOT-25-5 | C51118 |
| U7 | LSM6DS3TR-C (6-axis IMU) | STMicroelectronics | LGA-14 | C967633 |
| U8 | BWU.FL-IPEX1 (U.FL connector) | Bat Wireless | SMD | C5137195 |
| U9 | B5819 (Schottky diode) | — | SOD-323FL | C7469119 |
| U10 | CH340C (USB-UART bridge) | WCH | SOP-16 | C84681 |
| CARD1 | SMN-303 (nano-SIM socket) | Xunpu | SMD | C266888 |

## Passives

| Value | Qty | Package | Designators |
|---|---|---|---|
| 100 nF | 10 | C0603 | C6, C8, C12, C14, C16, C17, C18, C19, C20, C21 |
| 10 µF | 6 | C0603 | C3, C4, C5, C7, C9, C15 |
| 1 µF | 3 | C0603 | C10, C23, C24 |
| 330 µF | 1 | CASE-A 3216 | C11 |
| 33 pF | 1 | C0603 | C13 |
| 100 µF | 1 | C0603 (marked "100muF") | C22 |
| 1 µF | 1 | C0603 (marked "1muF") | C25 |
| 1 kΩ | 7 | R0201 | R9–R14, R16 |
| 10 kΩ | 3 | R0201 | R1, R4, R5 |
| 4.7 kΩ | 3 | R0201 | R6, R7, R8 |
| 5.1 kΩ | 2 | R0201 | R2, R3 |
| 1.8 kΩ | 1 | R0201 | R15 |
| 10 kΩ | 2 | R0603 *(designated U11, U12 — see note below)* | U11, U12 |
| 5.1 kΩ | 2 | R0603 *(designated U13, U14)* | U13, U14 |
| 2.2 kΩ | 1 | R0603 *(designated U15)* | U15 |
| 2.2 µH | 1 | L1206 (inductor) | L3 |
| 47 nH | 1 | IND-SMD L4.7×W4.7 | L4 |

> **Note:** R0603 resistors on rows `U11`–`U15` are true resistors
> (CH340C auto-reset bias network) but keep a `U`-prefix designator instead
> of `R`. Not a functional issue, but worth renaming before a board rev to
> avoid confusing BOM/pick-and-place tooling that assumes `U` = IC.

## Connectors / mechanical

| Designator | Part | Package |
|---|---|---|
| CN1 | 3.5 mm audio jack | AUDIO-TH PJ-342-2C |
| CN5 | 3.5 mm mic jack | AUDIO-TH PJ-342-2C |
| CN2 | Battery jack (main) | XH2.54 2-pin |
| CN3 | Vibration motor connector | XH2.54 2-pin |
| CN4 | Battery jack (GSM/modem) | XH2.54 2-pin |
| USBC1, USBC2 | USB Type-C 3.1 receptacle | SMD, ×2 |

## Switches / buttons

| Designator | Function label | Package |
|---|---|---|
| SW1 | AI | 4-pin SMD tact |
| SW2 | RST | 4-pin SMD tact |
| SW3 | BOOT | 4-pin SMD tact |
| SW4 | power ON/OFF | 4-pin SMD tact |
| SW5 | Intercom | 4-pin SMD tact |
| SW7 | false alarm | 4-pin SMD tact |
| SW6 | SK22D02G4 | Through-hole (only non-SMD switch) |

## Indicators / alert

| Designator | Part | Color |
|---|---|---|
| LED1 | LED-SMD 0603 | Red |
| LED2 | LED0603 | Blue |
| LED3 | LED0603 | Green |
| LED4 | LED0603 | White |
| BUZZER1 | 2700 Hz SMD buzzer | — |

## Discretes

| Designator | Part | Function |
|---|---|---|
| D1, D2 | 1N4148WS | Signal/protection diodes |
| Q5–Q9 | 2N3904 (×5) | NPN switching (power/RTS/DTR/vibration-motor drive) |

## Verification & confidence

Independently recomputed against the raw `.BOM` array in
`giacomo-schematic.json` via `jq` (all 48 line items, quantities, and
designator lists recounted from scratch, not trusted from this document).
**~98% of checkable claims VERIFIED — the most accurate file in this
analysis set.** Two real issues found:

| Claim | Confidence | Evidence |
|---|---|---|
| 48 line items, 83 total instances | **VERIFIED** | Recomputed: `.BOM\|length-1` = 48; summed quantities = 83 |
| U1–U8, U10, CARD1 part/manufacturer/package/LCSC fields | **VERIFIED** | Exact match to raw BOM rows |
| **U9 manufacturer listed as `—`** | **INCORRECT** | Raw data has `"Manufacturer": "晶导微电子"` — not blank. Part number, package, and LCSC # for U9 are all still correct |
| All passive tables (caps, resistors, inductors — values/qty/package/designators) | **VERIFIED** | Every row recomputed independently from raw BOM data, including the "100muF"/"1muF" literal value-string quirks |
| LED1–4 = Red/Blue/Green/White | **VERIFIED (not inference)** | Raw BOM `Value` field is literally `RED`/`BLUE`/`GREEN`/`WHITE` — explicit data, not a color inferred from part number |
| CN1/CN5 3.5mm jacks, CN3 vibration connector, SW1–SW7, BUZZER1, D1/D2, Q5–Q9 | **VERIFIED** | All match raw BOM rows |
| CN2/CN4 "XH2.54 2-pin" | **LIKELY** | Fair simplification of the raw package string `CONN-SMD_2P-P2.54_MEGASTAR_ZX-XH2.54-2PWT`, not a literal field copy |
| USBC1/USBC2 described as "USB Type-C **3.1** receptacle" | **INFERENCE (overstated)** | Raw part number is `TYPE-C-31-M-12` — the "31" is a connector model-series digit, not a confirmed USB 3.1 data-rate spec. The BOM doesn't actually support a USB-3.1 claim |
| "Identical data duplicated inside `giacomo-project-manifest.json`" | **LIKELY (incomplete)** | The manifest actually embeds BOM data **twice** — once per document. Only the schematic-doc copy is byte-identical; the PCB-doc copy is a **stale snapshot** missing several rows/quantities (e.g. only 9× 100nF instead of 10, missing C21; only 1× 1µF instead of 3, missing C23/C24; missing the C11 330µF row entirely). This second, divergent copy is never mentioned |

No other claims contradicted by evidence.

