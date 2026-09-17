# Image Contents

All four JPEGs are EasyEDA editor screenshots of the **same schematic
sheet** (`Sheet_1` from `giacomo-schematic.json`), captured at different
pan/zoom positions — not photographs of a physical board and not distinct
design revisions. Two of them show visible EasyEDA UI chrome (the sheet
tab, drawing toolbar), confirming they're in-app screenshots.

| File | Original name | Visible region |
|---|---|---|
| `schematic-view-audio-usb-modem.jpeg` | `395745bd-27ff-4925-afe1-c8ca379af984.jpeg` | ES8311 audio codec, `false alarm`/`Intercom` buttons, USB-C (USBC2) + CH340C USB-UART bridge, top of A7670C pinout, LSM6DS3TR-C IMU |
| `schematic-view-core-power-mcu-gps.jpeg` | `39a24fbf-75c1-4f40-b716-7c2915c08904.jpeg` | Core power/MCU block: buzzer + L76KB-A58 GPS, IP5306 power management, ESP32-S3-WROOM-1 main module, SIM socket (CARD1), status LEDs, vibration motor drive |
| `schematic-view-audio-usbc-imu.jpeg` | `605dc082-534b-4cd5-b698-d4f29266205e.jpeg` | ES8311 codec detail, both USB-C connectors (USBC1 + USBC2) side by side, 3.5 mm mic/audio jacks, AP2112K-3.3 LDO, LSM6DS3TR-C IMU, CH340C |
| `schematic-view-modem-pinout-antennas.jpeg` | `72c0c1ba-4346-4a19-bf7e-6f64a2ebcd15.jpeg` | Right-hand/full A7670C pin breakout (camera bus, LCD bus, USIM1/2, GNSS/BT antenna pins, `RF_ANT` pin column), IMU, GPS module, ESP32-S3 left edge |

Together the four crops cover essentially the entire schematic sheet, which
is how the full circuit picture in
[03-schematic-analysis.md](03-schematic-analysis.md) was reconstructed —
the underlying JSON encodes wires/symbols as coordinate data rather than
human-readable net names in an easily-dumped form, so the rendered
screenshots were the practical source for net-name-level detail.

## Verification & confidence

Independently re-verified by directly viewing all four JPEGs and comparing
against each claimed "visible region." **~95% of claims VERIFIED.**

| Claim | Confidence | Evidence |
|---|---|---|
| All 4 images are the same schematic sheet at different pan/zoom (not photos or distinct revisions) | **VERIFIED** | Consistent net names/component labels across all four; two show the identical `*Sheet_1` tab |
| Per-image "visible region" descriptions (each of the 4 rows) | **VERIFIED** | Every listed component/net was directly observed in the corresponding image on re-inspection |
| "Two of them show visible EasyEDA UI chrome" | **LIKELY (off by one)** | Direct inspection found the sheet tab visible in 2 images, but a 3rd (`schematic-view-audio-usbc-imu.jpeg`) also shows the drawing-toolbar icon strip — so **3 of 4** show some UI chrome, not exactly 2. Doesn't affect the substantive point (these are in-app screenshots) |
| "The underlying JSON encodes wires/symbols as coordinate data rather than human-readable net names... screenshots were the practical source for net-name-level detail" | **INCORRECT** | Net labels are stored as plain literal strings in `N~` shape entries in `giacomo-schematic.json` (e.g. `N~345~-345~0~#0000ff~BATT_RAW~gge33963~start~...`) and are directly greppable without the screenshots. This overstates the necessity of the screenshot-based method — the JSON alone was sufficient and more reliable |

No net-name-level claims elsewhere in the analysis set turned out wrong
because of this methodology overstatement — cross-checking against the raw
JSON (see [03-schematic-analysis.md](03-schematic-analysis.md#verification--confidence))
confirmed all the net names independently, but the *reasoning* given here
for how they were obtained doesn't hold up.
