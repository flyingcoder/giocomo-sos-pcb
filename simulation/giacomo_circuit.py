#!/usr/bin/env python3
"""PySpice model of the Giacomo board's analog/discrete circuitry.

Built from the four EasyEDA schematic screenshots in the project root —
see README.md for the full component/connection inventory and for why
the digital SoCs (A7670C, ESP32-S3, L76KB-A58, ES8311, LSM6DS3TR-C,
CH340C) are represented as behavioral supply loads rather than simulated
at the transistor level.

Run:
    python3 giacomo_circuit.py

Produces printed rail-voltage/current summaries and waveform plots under
./output/.

Every `build_X_circuit()`/`run_X_analysis()` pair also accepts the
board/analysis parameters as keyword arguments (defaulting to the module
constants below) and `run_X_analysis()` returns a structured dict of
results, so the same functions can be driven interactively (see
webapp/app.py) without touching module state -- important since nothing
here may read or write a shared global while a request is in flight on
another thread.
"""

import io
import os

import PySpice.Logging.Logging as Logging
from PySpice.Spice.Netlist import Circuit, SubCircuitFactory
from PySpice.Unit import u_V, u_Ohm, u_F, u_A, u_H, u_ms, u_us, u_ns

from models import (QMOD_2N3904, DMOD_1N4148WS, SWMOD_IDEAL, IP5306Boost,
                     AP2112LDO, ICLoad)
import scoring

Logging.setup_logging()

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# ---------------------------------------------------------------------------
# Datasheet-typical supply currents used for the behavioral IC loads.
# These are NOT measured on real silicon -- they size the loads so the
# power-tree simulation sees realistic conditions. See README.md
# "Simulation scope & approach". They are also the default values for the
# corresponding keyword arguments below -- callers (CLI or web) can
# override any of them without touching these module constants.
# ---------------------------------------------------------------------------
I_ESP32S3_ACTIVE = 240e-3       # WiFi/BT off, CPU + peripherals active
I_L76KB_A58 = 25e-3             # GNSS module, acquisition/tracking
I_ES8311 = 8e-3                 # audio codec, playback active
I_LSM6DS3TR_C = 0.6e-3          # IMU, normal power mode, both axes active
I_CH340C = 10e-3                # USB-UART bridge
I_A7670C_IDLE = 25e-3           # modem idle/registered, no TX
I_A7670C_TX_BURST = 1.8         # LTE/2G TX burst peak (pulsed, ms-scale)

BATTERY_ESR = 0.12              # single-cell Li-ion ESR, documented estimate
VBAT_NOMINAL = 3.85             # nominal single-cell Li-ion voltage


def scalar(node):
    """Extract a Python float from a length-1 PySpice operating-point node."""
    return float(node[0])


def add_bjt_model(circuit):
    circuit.raw_spice += QMOD_2N3904 + "\n"


def add_diode_model(circuit):
    circuit.raw_spice += DMOD_1N4148WS + "\n"


def add_switch_model(circuit):
    circuit.raw_spice += SWMOD_IDEAL + "\n"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Power tree: BATT_RAW -> IP5306 -> VBUS_5V -> AP2112K-3.3 -> 3V3,
#    loaded by every 3V3-rail IC's idle current, with the BOM's
#    decoupling caps in place at each node.
# ---------------------------------------------------------------------------
def build_power_tree_circuit(vbat_nominal=VBAT_NOMINAL,
                              i_esp32s3=I_ESP32S3_ACTIVE,
                              i_gnss=I_L76KB_A58,
                              i_codec=I_ES8311,
                              i_imu=I_LSM6DS3TR_C,
                              i_ch340=I_CH340C):
    circuit = Circuit("Giacomo power tree")

    circuit.subcircuit(IP5306Boost(output_voltage=5.0, r_out=0.15))
    circuit.subcircuit(AP2112LDO(output_voltage=3.3, r_out=0.09))
    circuit.subcircuit(ICLoad(i_esp32s3))
    circuit.subcircuit(ICLoad(i_gnss))
    circuit.subcircuit(ICLoad(i_codec))
    circuit.subcircuit(ICLoad(i_imu))
    circuit.subcircuit(ICLoad(i_ch340))

    # BATT_RAW (main cell) into U5 IP5306 BAT pin
    circuit.V("batt", "batt_raw", circuit.gnd, u_V(vbat_nominal))
    circuit.X("U5", "IP5306_BOOST", "batt_raw", "vbus_5v", circuit.gnd)

    # C4 (10uF) on IP5306 VOUT, C5 (10uF) after L3 on the VBUS_5V node
    circuit.C("4", "vbus_5v", circuit.gnd, u_F(10e-6))
    circuit.C("5", "vbus_5v", circuit.gnd, u_F(10e-6))

    # U6 AP2112K-3.3: VIN from VBUS_5V, C6 (100nF) in, C7 (10uF) out
    circuit.C("6", "vbus_5v", circuit.gnd, u_F(100e-9))
    circuit.X("U6", "AP2112_LDO", "vbus_5v", "3v3", circuit.gnd)
    circuit.C("7", "3v3", circuit.gnd, u_F(10e-6))

    # Every 3V3-rail IC's decoupling + behavioral load
    for ref, cap in (("18", 100e-9), ("19", 100e-9), ("14", 100e-9),
                      ("16", 100e-9), ("17", 100e-9), ("21", 100e-9)):
        circuit.C(ref, "3v3", circuit.gnd, u_F(cap))

    circuit.X("U2_load", "IC_LOAD_%.4g" % i_esp32s3, "3v3", circuit.gnd)
    circuit.X("U3_load", "IC_LOAD_%.4g" % i_gnss, "3v3", circuit.gnd)
    circuit.X("U4_load", "IC_LOAD_%.4g" % i_codec, "3v3", circuit.gnd)
    circuit.X("U7_load", "IC_LOAD_%.4g" % i_imu, "3v3", circuit.gnd)
    circuit.X("U10_load", "IC_LOAD_%.4g" % i_ch340, "3v3", circuit.gnd)

    return circuit


def run_power_tree_analysis(vbat_nominal=VBAT_NOMINAL,
                             i_esp32s3=I_ESP32S3_ACTIVE,
                             i_gnss=I_L76KB_A58,
                             i_codec=I_ES8311,
                             i_imu=I_LSM6DS3TR_C,
                             i_ch340=I_CH340C,
                             temperature=25):
    circuit = build_power_tree_circuit(
        vbat_nominal=vbat_nominal, i_esp32s3=i_esp32s3, i_gnss=i_gnss,
        i_codec=i_codec, i_imu=i_imu, i_ch340=i_ch340)
    simulator = circuit.simulator(temperature=temperature,
                                   nominal_temperature=temperature)
    op = simulator.operating_point()

    vbus_5v = scalar(op["vbus_5v"])
    v3v3 = scalar(op["3v3"])
    total_3v3_current = i_esp32s3 + i_gnss + i_codec + i_imu + i_ch340

    print("\n=== Power tree (DC operating point) ===")
    print(f"  BATT_RAW (cell)          : {vbat_nominal:.3f} V")
    print(f"  VBUS_5V  (IP5306 output) : {vbus_5v:.3f} V")
    print(f"  3V3      (AP2112K output): {v3v3:.3f} V")
    print(f"  Combined 3V3 load        : {total_3v3_current * 1e3:.1f} mA "
          "(sum of ESP32-S3 + GNSS + codec + IMU + CH340C idle currents)")

    return {
        "summary": {
            "vbat_nominal": vbat_nominal,
            "vbus_5v": vbus_5v,
            "v3v3": v3v3,
            "total_3v3_current_ma": total_3v3_current * 1e3,
        },
        "series": None,
        "plot_bytes": None,
    }


# ---------------------------------------------------------------------------
# 2. VBAT_LTE sag under an A7670C TX burst. The modem's battery feed
#    bypasses the IP5306/LDO chain entirely (see README §1/§3), so this is
#    modeled as its own rail with the battery's internal ESR in series.
# ---------------------------------------------------------------------------
EXPECTED_VBAT_LTE_IDLE = 3.1     # post-D2-drop estimate, for load resistor sizing
EXPECTED_VBAT_LTE_BURST = 2.6    # post-D2-drop estimate under heavy load


def build_modem_burst_circuit(vbat_nominal=VBAT_NOMINAL,
                               battery_esr=BATTERY_ESR,
                               vbat_lte_idle=EXPECTED_VBAT_LTE_IDLE,
                               vbat_lte_burst=EXPECTED_VBAT_LTE_BURST,
                               i_idle=I_A7670C_IDLE,
                               i_tx_burst=I_A7670C_TX_BURST):
    circuit = Circuit("A7670C TX burst on VBAT_LTE")
    add_diode_model(circuit)
    add_switch_model(circuit)

    circuit.V("cell", "cell_p", circuit.gnd, u_V(vbat_nominal))
    circuit.R("esr", "cell_p", "batt_lte_raw_pre_d2", u_Ohm(battery_esr))

    # D2 1N4148WS reverse-polarity protection diode into VBAT_LTE
    circuit.Diode("2", "batt_lte_raw_pre_d2", "vbat_lte", model="D1N4148WS")

    # C11 (330uF bulk) + C12 (100nF) + C13 (33pF) at the A7670C VBAT pins
    circuit.C("11", "vbat_lte", circuit.gnd, u_F(330e-6))
    circuit.C("12", "vbat_lte", circuit.gnd, u_F(100e-9))
    circuit.C("13", "vbat_lte", circuit.gnd, u_F(33e-12))

    # Idle draw, constant -- modeled as a resistor (see ICLoad docstring
    # in models.py for why: independent current sources are silently
    # zeroed by this ngspice 47 / PySpice 1.5 combination).
    r_idle = vbat_lte_idle / i_idle
    circuit.R("idle", "vbat_lte", circuit.gnd, u_Ohm(r_idle))

    # TX burst: switched-in low-value resistor emulating the ~1.8A pulsed
    # load, ~2ms burst width, GSM-style 4.6ms period. The switch is
    # driven by a PulseVoltageSource (confirmed working primitive).
    r_burst = vbat_lte_burst / (i_tx_burst - i_idle)
    circuit.PulseVoltageSource(
        "burst_ctrl", "burst_ctrl", circuit.gnd,
        initial_value=0, pulsed_value=3.3,
        pulse_width=u_ms(2), period=u_ms(4.6),
        delay_time=u_ms(5), rise_time=u_us(50), fall_time=u_us(50),
    )
    circuit.R("burst", "vbat_lte", "burst_sw", u_Ohm(r_burst))
    circuit.S("1", "burst_sw", circuit.gnd, "burst_ctrl", circuit.gnd,
              model="SWMOD")
    return circuit


def run_modem_burst_analysis(vbat_nominal=VBAT_NOMINAL,
                              battery_esr=BATTERY_ESR,
                              vbat_lte_idle=EXPECTED_VBAT_LTE_IDLE,
                              vbat_lte_burst=EXPECTED_VBAT_LTE_BURST,
                              i_idle=I_A7670C_IDLE,
                              i_tx_burst=I_A7670C_TX_BURST,
                              temperature=25,
                              plot_to_bytes=False):
    circuit = build_modem_burst_circuit(
        vbat_nominal=vbat_nominal, battery_esr=battery_esr,
        vbat_lte_idle=vbat_lte_idle, vbat_lte_burst=vbat_lte_burst,
        i_idle=i_idle, i_tx_burst=i_tx_burst)
    simulator = circuit.simulator(temperature=temperature,
                                   nominal_temperature=temperature)
    analysis = simulator.transient(step_time=u_us(20), end_time=u_ms(20))

    t = analysis.time
    v = analysis["vbat_lte"]
    v_min = min(float(x) for x in v)
    v_idle = float(v[0])

    print("\n=== VBAT_LTE sag under A7670C TX burst (transient) ===")
    print(f"  Idle VBAT_LTE            : {v_idle:.3f} V")
    print(f"  Minimum during TX burst  : {v_min:.3f} V")
    print(f"  Sag                      : {(v_idle - v_min) * 1e3:.0f} mV")

    t_ms = [float(x) * 1e3 for x in t]
    v_list = [float(x) for x in v]
    plot_bytes = _plot(t, [("VBAT_LTE", v)], "VBAT_LTE sag under A7670C TX burst",
                        "vbat_lte_burst.png", ylabel="Voltage (V)",
                        return_bytes=plot_to_bytes)

    return {
        "summary": {
            "v_idle": v_idle,
            "v_min": v_min,
            "sag_mv": (v_idle - v_min) * 1e3,
        },
        "series": {"t_ms": t_ms, "vbat_lte": v_list},
        "plot_bytes": plot_bytes,
    }


# ---------------------------------------------------------------------------
# 3. CH340C auto-reset network (Q8/Q9 + U11-U14 bias resistors) driving
#    EN and IO0, emulating an esptool-style DTR/RTS toggle sequence.
# ---------------------------------------------------------------------------
def build_autoreset_circuit(vcc=3.3):
    circuit = Circuit("CH340 auto-reset network")
    add_bjt_model(circuit)

    circuit.V("3v3", "3v3", circuit.gnd, u_V(vcc))

    # R4 (10k) EN pull-up, C9 (10uF) + C8 (100nF) RC delay on EN
    circuit.R("4", "3v3", "en", u_Ohm(10e3))
    circuit.C("9", "en", circuit.gnd, u_F(10e-6))
    circuit.C("8", "en", circuit.gnd, u_F(100e-9))

    # R5 (10k) IO0 pull-up (boot-mode strap)
    circuit.R("5", "3v3", "io0", u_Ohm(10e3))

    # esptool-style sequence: DTR asserted first (resets), then RTS
    # (sets boot strap), then DTR released while RTS still held, then RTS
    # released -- produces EN low-pulse fully inside an IO0 low-window.
    circuit.PulseVoltageSource(
        "dtr", "ch340_dtr", circuit.gnd,
        initial_value=0, pulsed_value=3.3,
        delay_time=u_ms(1), rise_time=u_ns(100), fall_time=u_ns(100),
        pulse_width=u_ms(3), period=u_ms(20),
    )
    circuit.PulseVoltageSource(
        "rts", "ch340_rts", circuit.gnd,
        initial_value=0, pulsed_value=3.3,
        delay_time=u_ms(2), rise_time=u_ns(100), fall_time=u_ns(100),
        pulse_width=u_ms(6), period=u_ms(20),
    )

    # U11 (10k) CH340_DTR -> Q8 base -> Q8 collector pulls EN low
    circuit.R("U11", "ch340_dtr", "q8_base", u_Ohm(10e3))
    circuit.BJT("8", "en", "q8_base", circuit.gnd, model="Q2N3904")

    # U12 (10k) CH340_RTS -> Q9 base -> Q9 collector pulls IO0 low
    circuit.R("U12", "ch340_rts", "q9_base", u_Ohm(10e3))
    circuit.BJT("9", "io0", "q9_base", circuit.gnd, model="Q2N3904")

    return circuit


def run_autoreset_analysis(vcc=3.3, temperature=25, plot_to_bytes=False):
    circuit = build_autoreset_circuit(vcc=vcc)
    simulator = circuit.simulator(temperature=temperature,
                                   nominal_temperature=temperature)
    analysis = simulator.transient(step_time=u_us(20), end_time=u_ms(20))

    t = analysis.time
    en = analysis["en"]
    io0 = analysis["io0"]
    en_min = min(float(x) for x in en)
    io0_min = min(float(x) for x in io0)

    print("\n=== CH340C auto-reset sequence (EN / IO0) ===")
    print(f"  EN min : {en_min:.3f} V "
          f"(reset asserted while low)")
    print(f"  IO0 min: {io0_min:.3f} V "
          f"(boot-strap asserted while low)")

    t_ms = [float(x) * 1e3 for x in t]
    en_list = [float(x) for x in en]
    io0_list = [float(x) for x in io0]
    plot_bytes = _plot(t, [("EN", en), ("IO0", io0)],
                        "CH340C auto-reset: EN / IO0", "autoreset_en_io0.png",
                        ylabel="Voltage (V)", return_bytes=plot_to_bytes)

    return {
        "summary": {"en_min": en_min, "io0_min": io0_min},
        "series": {"t_ms": t_ms, "en": en_list, "io0": io0_list},
        "plot_bytes": plot_bytes,
    }


# ---------------------------------------------------------------------------
# 4. LTE_PWRKEY driver (Q5 + R6), a single >=100ms low pulse into the
#    modem's PWRKEY pin, per the SIMCom power-on procedure.
# ---------------------------------------------------------------------------
def build_pwrkey_circuit(vcc=3.3):
    circuit = Circuit("LTE_PWRKEY driver")
    add_bjt_model(circuit)

    circuit.V("3v3", "3v3", circuit.gnd, u_V(vcc))
    # PWRKEY is internally pulled up inside the A7670C module; modeled
    # here as a 3V3 pull-up through a stand-in 100k so the node has a
    # defined idle-high state without a real modem model attached.
    circuit.R("pullup", "3v3", "pwrkey", u_Ohm(100e3))

    circuit.PulseVoltageSource(
        "gpio", "lte_pwrkey_gpio", circuit.gnd,
        initial_value=0, pulsed_value=3.3,
        delay_time=u_ms(1), rise_time=u_ns(100), fall_time=u_ns(100),
        pulse_width=u_ms(150), period=u_ms(500),
    )
    circuit.R("6", "lte_pwrkey_gpio", "q5_base", u_Ohm(4.7e3))
    circuit.BJT("5", "pwrkey", "q5_base", circuit.gnd, model="Q2N3904")

    return circuit


def run_pwrkey_analysis(vcc=3.3, temperature=25, plot_to_bytes=False):
    circuit = build_pwrkey_circuit(vcc=vcc)
    simulator = circuit.simulator(temperature=temperature,
                                   nominal_temperature=temperature)
    analysis = simulator.transient(step_time=u_us(50), end_time=u_ms(200))

    t = analysis.time
    pwrkey = analysis["pwrkey"]
    low_time_ms = sum(1 for x in pwrkey if float(x) < 0.3) * 50e-3

    print("\n=== LTE_PWRKEY driver (Q5) ===")
    print(f"  PWRKEY held low for ~{low_time_ms:.0f} ms "
          "(SIMCom spec requires >=100ms low pulse to power on)")

    t_ms = [float(x) * 1e3 for x in t]
    pwrkey_list = [float(x) for x in pwrkey]
    plot_bytes = _plot(t, [("PWRKEY", pwrkey)], "LTE_PWRKEY low-pulse",
                        "lte_pwrkey.png", ylabel="Voltage (V)",
                        return_bytes=plot_to_bytes)

    return {
        "summary": {"low_time_ms": low_time_ms},
        "series": {"t_ms": t_ms, "pwrkey": pwrkey_list},
        "plot_bytes": plot_bytes,
    }


# ---------------------------------------------------------------------------
# 5. Buzzer (Q7/R14) and vibration motor (Q6/R13/D1) drivers.
#    BUZZER1 is a fixed-tone (2700 Hz) SMD part, which for that
#    form factor is normally a piezo transducer -- an electrically
#    capacitive load, not a magnetic coil -- modeled as a series resistor
#    (leakage/ESR) into a capacitor. Documented typical values, not
#    measured on the real part.
# ---------------------------------------------------------------------------
BUZZER_ESR = 32.0
BUZZER_C = 15e-9
MOTOR_R = 45.0


def build_haptics_circuit(vbat_nominal=VBAT_NOMINAL,
                           buzzer_esr=BUZZER_ESR,
                           buzzer_c=BUZZER_C,
                           motor_r=MOTOR_R):
    circuit = Circuit("Buzzer + vibration motor drivers")
    add_bjt_model(circuit)
    add_diode_model(circuit)

    circuit.V("vbat_lte", "vbat_lte", circuit.gnd, u_V(vbat_nominal))
    circuit.V("3v3", "3v3", circuit.gnd, u_V(3.3))

    # Buzzer: VBAT_LTE -> D2 -> BUZZER1 (piezo, R+C) -> Q7 collector;
    # Q7 base via R14
    circuit.Diode("2", "vbat_lte", "buzz_hi", model="D1N4148WS")
    circuit.R("buzz_esr", "buzz_hi", "q7_coll", u_Ohm(buzzer_esr))
    circuit.C("buzz", "q7_coll", circuit.gnd, u_F(buzzer_c))
    circuit.PulseVoltageSource(
        "buzzer_pwm", "buzzer_pwm", circuit.gnd,
        initial_value=0, pulsed_value=3.3,
        delay_time=u_us(100), rise_time=u_ns(100), fall_time=u_ns(100),
        pulse_width=u_us(185), period=u_us(370),  # ~2700 Hz per BUZZER1 spec
    )
    circuit.R("14", "buzzer_pwm", "q7_base", u_Ohm(1e3))
    circuit.BJT("7", "q7_coll", "q7_base", circuit.gnd, model="Q2N3904")

    # Vibration motor: 3V3 -> motor -> Q6 collector; D1 flyback across
    # motor; Q6 base via R13 from VIB_MOTOR (IO0-shared GPIO)
    circuit.R("motor", "3v3", "q6_coll", u_Ohm(motor_r))
    circuit.Diode("1", "q6_coll", "3v3", model="D1N4148WS")  # flyback
    circuit.PulseVoltageSource(
        "vib_motor", "vib_motor", circuit.gnd,
        initial_value=0, pulsed_value=3.3,
        delay_time=u_ms(1), rise_time=u_ns(100), fall_time=u_ns(100),
        pulse_width=u_ms(3), period=u_ms(8),
    )
    circuit.R("13", "vib_motor", "q6_base", u_Ohm(1e3))
    circuit.BJT("6", "q6_coll", "q6_base", circuit.gnd, model="Q2N3904")

    return circuit


def run_haptics_analysis(vbat_nominal=VBAT_NOMINAL,
                          buzzer_esr=BUZZER_ESR,
                          buzzer_c=BUZZER_C,
                          motor_r=MOTOR_R,
                          temperature=25,
                          plot_to_bytes=False):
    circuit = build_haptics_circuit(
        vbat_nominal=vbat_nominal, buzzer_esr=buzzer_esr, buzzer_c=buzzer_c,
        motor_r=motor_r)
    simulator = circuit.simulator(temperature=temperature,
                                   nominal_temperature=temperature)
    analysis = simulator.transient(step_time=u_us(2), end_time=u_ms(10))

    t = analysis.time
    buzz_node = analysis["q7_coll"]
    motor_node = analysis["q6_coll"]
    buzz_min = min(float(x) for x in buzz_node)
    buzz_max = max(float(x) for x in buzz_node)
    motor_min = min(float(x) for x in motor_node)
    motor_max = max(float(x) for x in motor_node)

    print("\n=== Buzzer / vibration motor drivers ===")
    print(f"  Buzzer node swings between "
          f"{buzz_min:.2f} V and "
          f"{buzz_max:.2f} V at ~2700 Hz PWM")
    print(f"  Motor node swings between "
          f"{motor_min:.2f} V and "
          f"{motor_max:.2f} V during pulse drive")

    t_ms = [float(x) * 1e3 for x in t]
    buzz_list = [float(x) for x in buzz_node]
    motor_list = [float(x) for x in motor_node]
    plot_bytes = _plot(t, [("Buzzer drive node", buzz_node), ("Motor drive node", motor_node)],
                        "Buzzer & vibration-motor driver nodes", "haptics.png",
                        ylabel="Voltage (V)", return_bytes=plot_to_bytes)

    return {
        "summary": {
            "buzz_min": buzz_min, "buzz_max": buzz_max,
            "motor_min": motor_min, "motor_max": motor_max,
        },
        "series": {"t_ms": t_ms, "buzz": buzz_list, "motor": motor_list},
        "plot_bytes": plot_bytes,
    }


# ---------------------------------------------------------------------------
# 6. LED current-limiting networks (LED1-4 + R9-R12), modeled as an
#    ideal forward-voltage source + small dynamic resistance in series
#    with the BOM's 1k series resistor.
# ---------------------------------------------------------------------------
class LEDModel(SubCircuitFactory):
    NAME = "LED_MODEL"
    NODES = ("anode", "cathode")

    def __init__(self, vf, rd=20):
        super().__init__()
        # Override the class-level NAME per-instance so LEDs with
        # different forward voltages don't collide on one subckt name.
        self._name = "LED_MODEL_%.4g" % vf
        self.V("f", "anode", "mid", u_V(vf))
        self.R("d", "mid", "cathode", u_Ohm(rd))


LED_SPECS = {
    "LED1_red": 2.0,
    "LED2_blue": 3.0,
    "LED3_green": 2.1,
    "LED4_white": 3.0,
}


def build_led_circuit(led_specs=LED_SPECS):
    circuit = Circuit("LED current-limiting networks")
    circuit.V("3v3", "3v3", circuit.gnd, u_V(3.3))

    for name, vf in led_specs.items():
        circuit.subcircuit(LEDModel(vf))
        node = f"{name}_a"
        circuit.R(f"series_{name}", "3v3", node, u_Ohm(1e3))
        circuit.X(name, "LED_MODEL_%.4g" % vf, node, circuit.gnd)

    return circuit


def run_led_analysis(led_specs=LED_SPECS, temperature=25):
    circuit = build_led_circuit(led_specs=led_specs)
    simulator = circuit.simulator(temperature=temperature,
                                   nominal_temperature=temperature)
    op = simulator.operating_point()

    print("\n=== LED current-limiting networks (3V3, 1k series resistors) ===")
    summary = {}
    for name, vf in led_specs.items():
        node_v = scalar(op[f"{name}_a"])
        i_ma = (3.3 - node_v) / 1e3 * 1e3
        print(f"  {name:<12s} Vf~{vf:.1f}V -> node {node_v:.2f}V, "
              f"I~{i_ma:.2f} mA")
        summary[name] = {"vf": vf, "node_v": node_v, "i_ma": i_ma}

    return {"summary": summary, "series": None, "plot_bytes": None}


# ---------------------------------------------------------------------------
# 7. USB-C CC termination check (device-side pull-downs only, both ports).
# ---------------------------------------------------------------------------
def build_usb_cc_circuit(host_rp=None):
    circuit = Circuit("USB-C CC termination")
    circuit.V("5v", "vbus_host", circuit.gnd, u_V(5.0))

    if host_rp is not None:
        circuit.R("host_rp1", "vbus_host", "cc1", u_Ohm(host_rp))
        circuit.R("host_rp2", "vbus_host", "cc2", u_Ohm(host_rp))
    else:
        # Unconnected / no host: CC floats except for the device pull-down
        circuit.R("stub1", "cc1", "cc1", u_Ohm(1e12))
        circuit.R("stub2", "cc2", "cc2", u_Ohm(1e12))

    # R2/R3 on USBC1 (main power/data port)
    circuit.R("2", "cc1", circuit.gnd, u_Ohm(5.1e3))
    circuit.R("3", "cc2", circuit.gnd, u_Ohm(5.1e3))

    return circuit


DEFAULT_USB_HOST_RP_CASES = (
    ("no host attached", None),
    ("host Rp=56k (default 900mA/1.5A source)", 56e3),
    ("host Rp=22k (1.5A source)", 22e3),
    ("host Rp=10k (3A source)", 10e3),
)


def run_usb_cc_analysis(host_rp_cases=DEFAULT_USB_HOST_RP_CASES, temperature=25):
    print("\n=== USB-C CC termination (USBC1, Rd=5.1k device pull-downs) ===")
    summary = {}
    for label, rp in host_rp_cases:
        circuit = build_usb_cc_circuit(host_rp=rp)
        simulator = circuit.simulator(temperature=temperature,
                                       nominal_temperature=temperature)
        op = simulator.operating_point()
        v_cc1 = scalar(op["cc1"])
        print(f"  {label:<45s} CC1 = {v_cc1:.2f} V")
        summary[label] = v_cc1

    return {"summary": summary, "series": None, "plot_bytes": None}


def _plot(t, series, title, filename, ylabel="Voltage (V)", return_bytes=False):
    """Render a transient waveform plot.

    Builds the figure via the explicit Figure/FigureCanvasAgg object API
    rather than the `matplotlib.pyplot` global-state API, so concurrent
    callers (e.g. multiple Flask request threads) never share mutable
    figure state. When `return_bytes` is True, renders to an in-memory
    buffer and returns the PNG bytes instead of writing to OUTPUT_DIR.
    """
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    t_ms = [float(x) * 1e3 for x in t]
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    for label, values in series:
        ax.plot(t_ms, [float(x) for x in values], label=label)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    canvas = FigureCanvasAgg(fig)

    if return_bytes:
        buf = io.BytesIO()
        canvas.print_png(buf)
        return buf.getvalue()

    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=120)
    print(f"  [plot saved: {os.path.relpath(path)}]")
    return None


def main():
    print("Giacomo board -- PySpice analog/discrete subsystem simulation")
    print("=" * 64)
    results = {
        "power_tree": run_power_tree_analysis(),
        "modem_burst": run_modem_burst_analysis(),
        "autoreset": run_autoreset_analysis(),
        "pwrkey": run_pwrkey_analysis(),
        "haptics": run_haptics_analysis(),
        "led": run_led_analysis(),
        "usb_cc": run_usb_cc_analysis(),
    }
    print("\nDone.")

    board = scoring.compute_board_score(results)
    print("\n" + "=" * 64)
    print(f"Board health score: {board['overall_score']:.1f}%  --  {board['verdict']}")
    print("(heuristic margin score against typical-operation thresholds, not a")
    print(" certified reliability estimate -- see scoring.py for methodology)")
    for check in board["checks"]:
        flag = " " if check["score_pct"] >= 90 else ("!" if check["score_pct"] >= 40 else "X")
        print(f"  {flag} [{check['score_pct']:5.1f}%] {check['label']}: {check['detail']}")


if __name__ == "__main__":
    main()
