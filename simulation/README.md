# Giacomo PCB — Component & Connection Inventory + PySpice Model

Source material: the four EasyEDA schematic screenshots in the project root —

| File | Subsystem shown |
|---|---|
| `schematic-view-core-power-mcu-gps.jpeg` | Power tree (IP5306, LDO), ESP32-S3 core, GNSS module, buzzer, status LEDs, battery jacks |
| `schematic-view-audio-usb-modem.jpeg` | Audio codec, IMU, LDO, both USB-C ports, CH340C bridge, A7670C modem front-end |
| `schematic-view-audio-usbc-imu.jpeg` | Same region as above from a different pan/zoom — used to cross-check pin numbers |
| `schematic-view-modem-pinout-antennas.jpeg` | Full A7670C pin-out, antenna nets, SIM socket, second battery jack, LTE_PWRKEY driver |

This inventory was built by visually reading all four images pin-by-pin and
cross-checking designators/values against the BOM embedded in
`giacomo-schematic.json` (`analysis/04-bom.md`). Net names quoted are the
literal labels printed on the schematic.

## 1. Power architecture

Two independent single-cell Li-ion battery feeds:

- **`BATT_RAW`** — from `CN2` ("Pin battery jack", main). Routed through
  `SW6` (`SK22D02G4`, the only through-hole part — the physical slide power
  switch) to the logic side of the board.
- **`VBAT_LTE` / `BATT_LTE_RAW`** — from `CN4` ("Pin battery jack GSM").
  Feeds the A7670C's `VBAT` pins (57/58/59) directly and separately from the
  logic battery feed, because the modem pulls 1–2 A pulsed current during
  TX bursts and would otherwise drag down the logic rail. `D2` (1N4148WS)
  sits in this path for reverse-polarity protection, and `BUZZER1` returns
  to this rail on its high side.

Charge + boost:

- **`U5` (IP5306, ESOP-8)** — `VIN` from `USB_IN` (USB-C `VBUS`), `BAT` to
  the battery cell, `VOUT`/`SW` form the boost converter producing
  **`VBUS_5V`** through `L3` (2.2 µH) with `C5` (10 µF) output cap. `C3`
  (10 µF) sits on `VIN`, `C4` (10 µF) on `VOUT`. `R1` (10 kΩ) biases the
  `KEY` pin (auto power-on tie, per IP5306 typical application circuit).
  `LED1`/`LED2`/`LED3` pins on the IC itself are marked no-connect (×) —
  the four status LEDs on the board are independent GPIO-driven LEDs, not
  driven by the PMIC.
- **`U6` (AP2112K-3.3TRG1, SOT-25-5)** — `VIN` from `VBUS_5V`/`5V`, `EN`
  tied high (always enabled), `VOUT` → **`3V3`** rail, `NC` unconnected.
  `C6` (100 nF) on input, `C7` (10 µF) on output.

`3V3` fans out to: ESP32-S3, IMU, audio codec, CH340C, all pull-ups/LED
rails, and the digital side of the modem interface.

## 2. MCU core — `U2` ESP32-S3-WROOM-1(N16R8)

Confirmed pin/net pairs read directly off the schematic:

| Pin | Net | Notes |
|---|---|---|
| 1 | GND | |
| 2 | 3V3 | main supply |
| 3 | EN | pulled up by `R4` (10 kΩ) to 3V3, `C9` (10 µF) + `C8` (100 nF) to GND — RC-delayed reset, also driven low by the CH340 auto-reset network |
| IO4 | `LTE_PWRKEY` | drives `Q5` base through `R6` |
| IO5 | `LTE_TX` | to A7670C RX |
| IO6 | `LTE_RX` | from A7670C TX (through `R15`/`R16` divider, see §5) |
| IO7 | `GNSS_TX` | to L76KB-A58 RXD |
| — | `GNSS_RX` | from L76KB-A58 TXD |
| IO15/16 | `IMU_INT1`, `IMU_SDA` | |
| IO17 | `IMU_SCL` | |
| IO18/19/20 | `CODEC_SDA`, I2S lines | ES8311 control/data |
| 40 | `LED_BLUE` | |
| 39 | `LED_GREEN` | |
| IO1/IO2 | `UART_TXD`/`UART_RXD` | to CH340C |
| 35 | `LED_RED` | |
| IO42/41 | `BTN_RIDER`, `BTN_AI` | |
| IO39/38 | `BTN_CANCEL`, `BTN_PWR` | |
| IO0 | `VIB_MOTOR` out / boot-strap in | shared: `R5` (10 kΩ) pull-up (boot strap) **and** drives `Q6` base through `R13` for the vibration motor — these are on the same silkscreen node per the schematic |
| — | `BUZZER_PWM` | drives `Q7` base through `R14` |

## 3. Cellular modem — `U1` A7670C-LANS (SIMCom, LGA-124)

- Power: `VBAT` pins 57/58/59 from `BATT_LTE_RAW`, decoupled with `C11`
  (330 µF bulk), `C12` (100 nF), `C13` (33 pF). `GND` pins tied in a large
  ground pour (pins 60–96 mostly GND on the right column).
- `PWRKEY` (pin 1) driven low by `Q5` (2N3904) collector; `Q5` base via
  `R6` (4.7 kΩ) from `LTE_PWRKEY` (ESP32 IO4); emitter to GND. Standard
  SIMCom power-on pulse circuit.
- `TXD`/`RXD` (pins ~9/10) → `LTE_TX`/`LTE_RX`, through a resistive divider
  `R16` (1 kΩ) / `R15` (1.8 kΩ) toward the ESP32 UART.
- `RESET`, `USB_BOOT`, `DTR`, `RI`, `DCD` broken out but not further wired
  (module reset-pin conventions, unused here).
- Camera bus (`CAM_SPI_*`, `CAM_I2C_*`), LCD bus (`LCD_SPI_*`, `LCD_DCX`,
  `LCD_RST`), and `SPI_CLK/CS/MOSI/MISO` are all broken out to pads with
  **no further net** — present only because they share the LGA footprint
  across SIMCom module variants.
- Dual SIM: `USIM1_VDD/DATA/CLK/RST/DET` → `CARD1` (SMN-303 nano-SIM
  socket). `USIM2_*` pins are unconnected — single-SIM design.
- Antenna pads: `RF_ANT` (cellular main), `BT_ANT`, `GNSS_ANT` broken out
  to pads/GND stitching — no U.FL connector populated for these three in
  this view (only the discrete GNSS module gets a U.FL, see §4).

## 4. GNSS — `U3` L76KB-A58 (Quectel, 18-pin)

- `VCC` and `VDD_RF` from `3V3`, decoupled by `C14` (100 nF) / `C15`
  (10 µF).
- `TXD`/`RXD` → `GNSS_TX`/`GNSS_RX` directly to the ESP32-S3 (GPS parsed
  in firmware, not via the modem's AT-command GNSS passthrough).
- `ANTON`/`RF_IN` → through `L4` (47 nH) to **`U8`** (BWU.FL-IPEX1, U.FL
  connector) — the board's one populated RF connector, for an external
  active GNSS antenna.
- `1PPS`, `WAKE_UP`, `V_BCKP`, `RESET_N`, `SET`, three `RESERVED` pins
  broken out per the module footprint; only `RESET_N`/`SET` tie to GND/3V3
  as static straps, the rest unconnected.

## 5. UART bridge / auto-reset — `U10` CH340C

- `VCC` from 3V3, `GND` common.
- `TXD`/`RXD` → `UART_LOG_TX`/`UART_LOG_RX` (ESP32 IO1/IO2).
- `D+`/`D-` → `USBC2` (`TYPE-C-31-M-12`), the dedicated programming/debug
  port. `U13` (5.1 kΩ) bleeds `VBUS_5V` sensed from this port; `U14`
  (5.1 kΩ) is the CC-line pull-down for USB-C sink detection.
- `DTR#` → `U11` (10 kΩ) → `Q8` (2N3904) base; `Q8` collector →
  **`EN`** node (ESP32 reset).
- `RTS#` → `U12` (10 kΩ) → `Q9` (2N3904) base; `Q9` collector →
  **`IO0`** node (ESP32 boot-strap), with `R5` (10 kΩ) pull-up to 3V3
  already present on that node.
- This is the textbook auto-program circuit: `esptool`/PlatformIO toggling
  DTR/RTS produces the EN-low-then-IO0-low sequence needed to enter the
  ESP32-S3's UART download mode without a manual button press.

## 6. USB-C ports

- **`USBC1`** (main power/data): `VBUS` → `USB_IN` → `U5` IP5306 `VIN`;
  `D+`/`D-` → ESP32-S3 native USB pins; `CC1`/`CC2` pulled down by `R2`,
  `R3` (5.1 kΩ each, standard USB-C sink termination).
- **`USBC2`** (programming/debug): as described in §5, routes to CH340C
  instead of the ESP32 native USB peripheral; `VBUS` sensed through `U9`
  (B5819 Schottky) into the `VBUS_5V`-adjacent sense node.

## 7. Audio — `U4` ES8311 (WQFN-20)

- `PVDD`/`DVDD`/`AVDD` from 3V3 (`C18`, `C19`, `C20` — 100 nF each local
  decoupling).
- I2S: `MCLK`/`SCLK`/`LRCK`/`ASDOUT`/`DSDIN` to ESP32-S3; I2C control:
  `CE`/`CDATA` → `CODEC_SDA`/`CODEC_SCL`.
- Mic in: `MIC1P`/`MIC1N` from `CN5` (3.5 mm mic jack) with `U15` (2.2 kΩ)
  bias pull-up to 3V3 on `MIC1P`, AC-coupled by `C25` (1 µF)/`C24` (1 µF).
- Line out: `OUTP` → `C22` (100 µF, AC-coupling) → `CN1` (3.5 mm audio
  jack), plus `C23` (1 µF) and `C20` (100 nF) support caps on the codec
  side.

## 8. IMU — `U7` LSM6DS3TR-C (LGA-14)

- `VDDIO`/`VDD` from 3V3, decoupled by `C16`/`C17` (100 nF each).
- I2C mode strapped: `SDO/SA0`, `SDA`→`IMU_SDA`, `SCL`→`IMU_SCL`,
  `CS`→3V3 (forces I2C mode). `INT1`→`IMU_INT1` to ESP32. `R7`/`R8`
  (4.7 kΩ) tie off unused `NC` pins.

## 9. Human interface

| Switch | Net | Pull/return |
|---|---|---|
| `SW1` AI | `BTN_AI` | momentary to GND, no external pull (relies on ESP32 internal pull-up) |
| `SW2` RST | EN | momentary to GND |
| `SW3` BOOT | IO0 | momentary to GND (shares `R5` pull-up) |
| `SW4` power ON/OFF | `BTN_PWR` | momentary to GND |
| `SW5` Intercom | `BTN_RIDER` | momentary to GND |
| `SW7` false alarm | `BTN_CANCEL` | momentary to GND |
| `SW6` SK22D02G4 | `BATT_RAW` in series | slide switch, master power |

LEDs, all 3V3-fed through a 1 kΩ series resistor to a GPIO-sunk cathode:
`LED1` red/`R9`/`LED_RED`, `LED2` blue/`R10`/`LED_BLUE`, `LED3`
green/`R11`/`LED_GREEN`, `LED4` white/`R12`/`LED_WHITE`.

## 10. Haptics / alert drivers

- **Buzzer** (`BUZZER1`, 2700 Hz): high side to `VBAT_LTE` (through `D2`),
  low side to `Q7` (2N3904) collector; `Q7` base via `R14` (1 kΩ) from
  `BUZZER_PWM`; emitter to GND.
- **Vibration motor** (`CN3`, 3-pin coin motor connector): high side to
  3V3, low side to `Q6` (2N3904) collector, `D1` (1N4148WS) flyback diode
  across the motor; `Q6` base via `R13` (1 kΩ) from `VIB_MOTOR` (IO0).

## Full designator cross-reference

See `analysis/04-bom.md` for the exhaustive BOM table (all 48 line items /
83 instances) — reproduced here only where a designator's function needed
disambiguating (the `U11`–`U15` mis-prefixed resistors, `R1`/`R4`/`R5`
pull/bias resistors, `R15`/`R16` UART divider).

---

## Simulation scope & approach

`A7670C`, `ESP32-S3`, `L76KB-A58`, `ES8311`, `LSM6DS3TR-C`, and `CH340C`
are digital SoCs/ICs with no meaningful transistor-level SPICE
representation (no public SPICE models exist, and internal logic isn't a
circuit-simulation problem). Simulating "the whole board" in PySpice
would be dishonest theater if it pretended to model their internal
behavior.

Instead, `giacomo_circuit.py` builds a SPICE-accurate model of the parts
of the board that **are** analog/discrete circuit design, and represents
every IC as a behavioral supply load (measured/typical current draw) so
the power-tree and discrete networks see realistic conditions:

1. **Power tree** — battery → protection diode → IP5306 (behavioral
   charge/boost macro-model) → `VBUS_5V` → AP2112K-3.3 (behavioral LDO
   macro-model) → `3V3`, with every decoupling cap from the BOM in place,
   loaded by behavioral current sinks for each IC (idle currents, plus a
   pulsed high-current sink modeling an A7670C TX burst).
2. **CH340 auto-reset network** — `Q8`/`Q9` transistors with real 2N3904
   SPICE parameters, `R11`–`R14`-equivalent bias resistors, driven by
   PULSE sources emulating DTR/RTS toggling, observing the resulting
   `EN`/`IO0` waveforms.
3. **LTE_PWRKEY driver** — `Q5` pulse circuit into the modem's VBAT-backed
   node.
4. **Buzzer/vibration motor drivers** — `Q6`/`Q7` with flyback/return
   paths.
5. **LED current-limiting networks** — four LED+resistor branches, DC
   operating-point forward current check.
6. **USB-C CC termination** — resistor-divider DC check on both ports.

Everything else (I2S, I2C, UART, camera/LCD buses, antenna RF paths) is
listed in this document for completeness but is out of SPICE's problem
domain and is not part of the netlist.

## Web app

`webapp/` is a small Flask frontend over the same 7 analyses above. It
shows the board's simulated subsystems as a schematic-style graph
(Cytoscape.js), lets you pick one analysis at a time, adjust its exposed
parameters (battery voltage, load currents, host Rp, temperature, etc.),
and run it — results come back as the same matplotlib waveform plot the
CLI produces (for the 4 transient analyses) plus node voltages/currents
overlaid directly on the schematic.

It deliberately does **not** support netlist editing or adding/rewiring
components — it's a way to explore the existing 7 analyses interactively,
not a schematic capture tool.

Launch:

```
pip3 install -r requirements.txt
python3 simulation/webapp/app.py
```

Then open `http://127.0.0.1:5057` (not 5000 -- macOS's AirPlay Receiver
occupies that port by default). The CLI (`python3 giacomo_circuit.py`)
remains fully functional and produces the same PNGs under `output/` as
before — the web app calls the same `build_X_circuit()`/`run_X_analysis()`
functions with different parameters, it doesn't replace them.

## Board health score

`scoring.py` turns the 7 analyses' results into a single 0-100% "board
health" number plus a per-check breakdown, printed at the end of the CLI
run and available from the web app via a "Compute board health score"
button (which runs all 7 analyses at their nominal/default parameters --
it reflects the baseline design, not whatever you've tweaked in a tab).

This is a **heuristic margin score, not a certified reliability
estimate**. Each check maps one simulated metric (VBAT_LTE sag during a
TX burst, EN/IO0 reset-assertion depth, PWRKEY pulse width, rail
regulation, LED forward current, USB-C CC termination bands, buzzer/motor
drive swing) onto a 0-100% score via a linear ramp between a documented
"safe" value and a "fail" value, then weight-averages across checks
(weighted toward what gates the board powering up, resetting, and
connecting at all, over peripheral niceties like LED brightness). The
thresholds are reasonable operating-margin estimates in the same spirit
as this simulation's existing "datasheet-typical, not measured on real
silicon" caveats -- see the docstring and check definitions in
`scoring.py` for the exact numbers and reasoning behind each one.
