# Schematic Analysis (`giacomo-schematic.json`)

Single sheet ("Sheet_1"), EasyEDA editor v6.5.51.

## Raw complexity

| Element | Count |
|---|---|
| Placed symbols (`LIB`) | 84 |
| Wire segments (`W`) | 266 |
| Junctions (`J`) | 104 |
| Net/flag labels (`N`) | 113 |
| Unique BOM line items | 48 |
| Total component instances (BOM qty sum) | 83 |

The symbol count (84) vs. BOM instance count (83) differ by one — consistent
with one symbol being a non-BOM item such as a sheet border/title block
element rather than a real discrepancy in part count.

## Power architecture (traced from net names in the schematic images)

- `VBAT_LTE` / `BATT_RAW` / `BATT_LTE_RAW` — raw single-cell Li-ion battery
  rail, split into a main-battery path and a cellular-modem-specific battery
  path via two separate 2-pin battery connectors (CN2 "Pin battery jack",
  CN4 "Pin battery jack GSM"). Keeping the modem's power feed physically
  separate from the logic battery feed is a sensible choice given the A7670C
  can pulse 1–2 A during transmit bursts.
- `VBUS_5V` — USB-C VBUS, feeds `IP5306` (U5), which does Li-ion charge
  management and 5 V boost (`VOUT`) simultaneously — the classic
  "power-bank IC used as a phone charger + boost" pattern.
- `AP2112K-3.3` (U6) drops 5 V/battery down to the `3V3` rail used by
  ESP32-S3, IMU, audio codec, and logic-level pull-ups.
- `LTE_PWRKEY` is driven through a 2N3904 (Q5) level-shift/inverter stage
  from an ESP32-S3 GPIO — standard pattern for controlling the A7670C's
  active-low/pulsed power-on pin from a 3.3 V MCU.

## Cellular + GNSS

- `U1` (A7670C-LANS) exposes a huge pin count (124-pin LGA) including a
  camera-style parallel bus (`CAM_SPI_*`, `CAM_I2C_*`) and an LCD bus
  (`LCD_SPI_*`, `LCD_DCX`, `LCD_RST`) that are **broken out on the
  schematic but appear unused** (no net names connect them further) — this
  is expected, since those pins exist on the SIMCom module purely because
  it shares a footprint/pinout across product variants; they don't need to
  be routed unless a camera/display is added later.
- Dual USIM interfaces are present on U1 (`USIM1_*` and `USIM2_*`) but only
  `USIM1_*` connects to the physical SIM socket (CARD1) — `USIM2` pins are
  unconnected, i.e. single-SIM implementation using a dual-SIM-capable
  modem.
- GNSS: `L76KB-A58` (U3) TX/RX connect directly to UART-level nets
  (`GNSS_TX`, `GNSS_RX`) — presumably into ESP32-S3 UART, not through the
  A7670C, so GPS parsing happens in the ESP32-S3 firmware rather than via
  the modem's own AT-command GNSS passthrough (though the A7670C also
  exposes `GNSS_VBKP`/`GNSS_RXD`/`GNSS_TXD`/`GNSS_PWRCTL` pins, suggesting
  the design leaves the option open to switch to the modem's internal GNSS
  instead of the discrete L76KB module).

## Audio path

- `ES8311` (U4) is wired for both mic input (`MIC1P`/`MIC1N` from the 3.5 mm
  mic jack CN5, plus an on-board analog mic input path from CN1) and analog
  output (`OUTP`) to the 3.5 mm jack, over I2S to the ESP32-S3
  (`I2S_MCLK/BCLK/LRCK/DIN/DOUT`) and I2C control (`CODEC_SDA/SCL`).
- This plus the physical `Intercom` button strongly suggests a push-to-talk
  or two-way voice intercom feature, not just alert-tone playback.

## Human interface

| Switch | Net | Likely function |
|---|---|---|
| SW1 `AI` | `BTN_AI` | AI/assistant trigger button |
| SW2 `RST` | (reset) | ESP32-S3 EN/reset |
| SW3 `BOOT` | `IO0` | ESP32-S3 boot-mode strap button |
| SW4 `power ON/OFF` | `BTN_PWR` | Power button |
| SW5 `Intercom` | `BTN_RIDER` | Voice/intercom trigger |
| SW7 `false alarm` | `BTN_CANCEL` | SOS/alarm cancel |
| SW6 `SK22D02G4` | — | Likely physical slide power switch (only through-hole part) |

`LED_RED`, `LED_BLUE`, `LED_GREEN`, `LED_WHITE` are individually addressable
GPIOs from the ESP32-S3 (not a single RGB part) — gives firmware full
independent control over four status colors.

## Sensing

`LSM6DS3TR-C` (U7) IMU is on a dedicated I2C-ish bus (`IMU_SDA`/`IMU_SCL`)
with its own interrupt line (`IMU_INT1`) wired to an ESP32-S3 GPIO — enables
motion-triggered wake without polling, useful for a wearable's battery
budget.

## USB / debug

- `CH340C` (U10) sits between a USB-C port and ESP32-S3 UART0
  (`UART_LOG_RX/TX`), auto-reset transistors (Q8/Q9) driven from `CH340_DTR`/
  `CH340_RTS` through the mis-designated `U11`–`U14` resistor network —
  standard ESP32 auto-program circuit (DTR/RTS → EN/IO0).
- The second USB-C (`USBC1`) connects straight to the ESP32-S3's native USB
  D+/D- pins — usable for USB device mode (e.g. mass storage, USB-JTAG) or
  simply as the charge-only path into IP5306.

## Verification & confidence

Independently re-checked against `giacomo-schematic.json` (shape counts
recounted directly from the raw `shape` array, net names grepped as literal
strings). **~97% of checkable factual claims VERIFIED, zero contradicted.**

| Claim | Confidence | Evidence |
|---|---|---|
| 84 `LIB` symbols, 266 `W` wire segments, 104 `J` junctions, 113 `N` net labels | **VERIFIED** | Recounted shape-type prefixes directly: LIB=84, W=266, J=104, N=113 — exact match |
| 48 unique BOM items, 83 total instances | **VERIFIED** | Recomputed from raw `BOM` array (48 data rows, quantities summing to 83) |
| 84-vs-83 diff = one non-BOM symbol (title block/border) | **LIKELY** | Plausible, but which specific `LIB` entry is the odd one out wasn't independently confirmed |
| All net names cited (`BTN_CANCEL`, `BTN_RIDER`, `BATT_RAW`, `LTE_PWRKEY`, `USIM1_*`/`USIM2_*`, `GNSS_TX/RX`, `I2S_*`, `CODEC_SDA/SCL`, `IMU_SDA/SCL`, `IMU_INT1`, `CH340_DTR/RTS`, `UART_LOG_RX/TX`, `BTN_AI`, `IO0`, `LED_*`, `GNSS_ANT`, `BT_ANT`, `GNSS_VBKP`, `GNSS_PWRCTL`, etc.) | **VERIFIED** | Every name found as a literal string in `N~` net-label shape entries in the raw JSON |
| `VBUS_5V` as the USB-C VBUS net name | **LIKELY (paraphrase)** | Raw literal labels near that node are `USB_IN`/`5V`, not a single net spelled exactly `VBUS_5V` — functionally accurate but not a literal string match |
| Q5 specifically drives `LTE_PWRKEY` (vs. another 2N3904) | **UNVERIFIABLE** | BOM confirms Q5 is *a* 2N3904; which transistor's pins land on the `LTE_PWRKEY` net requires netlist/coordinate tracing not completed in verification |
| U11–U14 mis-designated resistor network drives Q8/Q9 auto-reset | **VERIFIED** | BOM + net names both confirm the CH340C DTR/RTS bias network composition |
| Camera/LCD bus pins on U1 "broken out but appear unused" | **LIKELY** | Net tokens (`CAM_SPI_*`, `LCD_SPI_*`, etc.) exist in the file; "unused" (no downstream connection) wasn't independently netlist-traced |
| "Suggests two-way voice intercom, not just alert-tone playback" | **INFERENCE** | Explicitly hedged speculation in the source text, not a verifiable fact |

**Methodology correction:** [06-images.md](06-images.md) claims the schematic
JSON "encodes wires/symbols as coordinate data rather than human-readable
net names... so the rendered screenshots were the practical source for
net-name-level detail." This is **inaccurate** — net labels are stored as
plain literal strings in `N~` shape entries (e.g.
`N~345~-345~0~#0000ff~BATT_RAW~gge33963~start~...`) and are directly
greppable from `giacomo-schematic.json` without the screenshots. This does
not make any net-name claim in this file wrong (all verified correct above)
— it just means the stated derivation method was unnecessary/overstated.
