#!/usr/bin/env python3
"""Flask web frontend over the Giacomo board PySpice simulation.

Read-only schematic + "run one of the 7 existing analyses with a small
set of adjusted parameters" -- no netlist editing, no adding/rewiring
components. See simulation/README.md "Web app" section.

Launch (from anywhere): `python3 simulation/webapp/app.py`, then open
http://127.0.0.1:5057. (Not port 5000 -- macOS's AirPlay Receiver squats
on it by default, and reclaims it instantly if this server ever exits.)

The parameter schema below (`ANALYSES`) is a hand-maintained allowlist of
which giacomo_circuit.py kwargs are exposed to the UI -- deliberately not
auto-introspected from function signatures, so internal-only kwargs never
leak into the form. Keep it in sync by hand whenever a
build_X_circuit()/run_X_analysis() signature changes.

PySpice's ngspice binding (NgSpiceShared) is a process-wide singleton, not
safe for concurrent circuit builds/simulations -- two overlapping
`circuit.simulator(...)` calls from different threads reliably crash the
whole process with a C-level assertion in ngspice's matrix factorization
(confirmed empirically, not just suspected). `_SIMULATION_LOCK` below
serializes every `/api/run/<name>` call through PySpice so requests queue
instead of racing; this is a hard requirement, not a defensive nicety.
"""

import base64
import os
import sys
import threading

from flask import Flask, jsonify, render_template, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import giacomo_circuit  # noqa: E402
import schematic_graph  # noqa: E402
import scoring  # noqa: E402


ANALYSES = [
    {
        "name": "power_tree",
        "label": "Power tree",
        "kind": "operating_point",
        "params": [
            {"name": "vbat_nominal", "label": "Battery voltage", "type": "number",
             "default": giacomo_circuit.VBAT_NOMINAL, "min": 2.5, "max": 4.5, "step": 0.01, "unit": "V"},
            {"name": "i_esp32s3", "label": "ESP32-S3 active current", "type": "number",
             "default": giacomo_circuit.I_ESP32S3_ACTIVE, "min": 0, "max": 1.0, "step": 0.001, "unit": "A"},
            {"name": "i_gnss", "label": "GNSS module current", "type": "number",
             "default": giacomo_circuit.I_L76KB_A58, "min": 0, "max": 0.2, "step": 0.001, "unit": "A"},
            {"name": "i_codec", "label": "Audio codec current", "type": "number",
             "default": giacomo_circuit.I_ES8311, "min": 0, "max": 0.1, "step": 0.001, "unit": "A"},
            {"name": "i_imu", "label": "IMU current", "type": "number",
             "default": giacomo_circuit.I_LSM6DS3TR_C, "min": 0, "max": 0.01, "step": 0.0001, "unit": "A"},
            {"name": "i_ch340", "label": "CH340C current", "type": "number",
             "default": giacomo_circuit.I_CH340C, "min": 0, "max": 0.1, "step": 0.001, "unit": "A"},
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
    {
        "name": "modem_burst",
        "label": "Modem TX burst (VBAT_LTE sag)",
        "kind": "transient",
        "params": [
            {"name": "vbat_nominal", "label": "Battery voltage", "type": "number",
             "default": giacomo_circuit.VBAT_NOMINAL, "min": 2.5, "max": 4.5, "step": 0.01, "unit": "V"},
            {"name": "battery_esr", "label": "Battery ESR", "type": "number",
             "default": giacomo_circuit.BATTERY_ESR, "min": 0.01, "max": 1.0, "step": 0.01, "unit": "Ω"},
            {"name": "vbat_lte_idle", "label": "Expected idle VBAT_LTE", "type": "number",
             "default": giacomo_circuit.EXPECTED_VBAT_LTE_IDLE, "min": 2.0, "max": 4.0, "step": 0.01, "unit": "V"},
            {"name": "vbat_lte_burst", "label": "Expected burst VBAT_LTE", "type": "number",
             "default": giacomo_circuit.EXPECTED_VBAT_LTE_BURST, "min": 1.5, "max": 3.5, "step": 0.01, "unit": "V"},
            {"name": "i_idle", "label": "A7670C idle current", "type": "number",
             "default": giacomo_circuit.I_A7670C_IDLE, "min": 0, "max": 0.1, "step": 0.001, "unit": "A"},
            {"name": "i_tx_burst", "label": "A7670C TX burst current", "type": "number",
             "default": giacomo_circuit.I_A7670C_TX_BURST, "min": 0.5, "max": 3.0, "step": 0.01, "unit": "A"},
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
    {
        "name": "autoreset",
        "label": "CH340 auto-reset (EN / IO0)",
        "kind": "transient",
        "params": [
            {"name": "vcc", "label": "Supply voltage", "type": "number",
             "default": 3.3, "min": 2.5, "max": 3.6, "step": 0.01, "unit": "V"},
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
    {
        "name": "pwrkey",
        "label": "LTE_PWRKEY driver",
        "kind": "transient",
        "params": [
            {"name": "vcc", "label": "Supply voltage", "type": "number",
             "default": 3.3, "min": 2.5, "max": 3.6, "step": 0.01, "unit": "V"},
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
    {
        "name": "haptics",
        "label": "Buzzer / vibration motor drivers",
        "kind": "transient",
        "params": [
            {"name": "vbat_nominal", "label": "Battery voltage", "type": "number",
             "default": giacomo_circuit.VBAT_NOMINAL, "min": 2.5, "max": 4.5, "step": 0.01, "unit": "V"},
            {"name": "buzzer_esr", "label": "Piezo ESR", "type": "number",
             "default": giacomo_circuit.BUZZER_ESR, "min": 1, "max": 200, "step": 1, "unit": "Ω"},
            {"name": "buzzer_c", "label": "Piezo capacitance", "type": "number",
             "default": giacomo_circuit.BUZZER_C, "min": 1e-9, "max": 1e-6, "step": 1e-9, "unit": "F"},
            {"name": "motor_r", "label": "Motor coil resistance", "type": "number",
             "default": giacomo_circuit.MOTOR_R, "min": 5, "max": 200, "step": 1, "unit": "Ω"},
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
    {
        "name": "led",
        "label": "LED current-limiting networks",
        "kind": "operating_point",
        "params": [
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
    {
        "name": "usb_cc",
        "label": "USB-C CC termination",
        "kind": "operating_point",
        "params": [
            {"name": "temperature", "label": "Temperature", "type": "number",
             "default": 25, "min": -20, "max": 85, "step": 1, "unit": "°C"},
        ],
    },
]

ANALYSES_BY_NAME = {a["name"]: a for a in ANALYSES}

RUN_FUNCS = {
    "power_tree": giacomo_circuit.run_power_tree_analysis,
    "modem_burst": giacomo_circuit.run_modem_burst_analysis,
    "autoreset": giacomo_circuit.run_autoreset_analysis,
    "pwrkey": giacomo_circuit.run_pwrkey_analysis,
    "haptics": giacomo_circuit.run_haptics_analysis,
    "led": giacomo_circuit.run_led_analysis,
    "usb_cc": giacomo_circuit.run_usb_cc_analysis,
}

TRANSIENT_ANALYSES = {"modem_burst", "autoreset", "pwrkey", "haptics"}


def _overlay_power_tree(summary):
    return {
        "battery": summary["vbat_nominal"],
        "vbus_5v": summary["vbus_5v"],
        "3v3": summary["v3v3"],
    }


def _overlay_modem_burst(summary):
    return {"vbat_lte": summary["v_min"]}


def _overlay_autoreset(summary):
    return {"en": summary["en_min"], "io0": summary["io0_min"]}


def _overlay_pwrkey(summary):
    return {"pwrkey": summary["low_time_ms"]}


def _overlay_haptics(summary):
    return {"q7_coll": summary["buzz_max"], "q6_coll": summary["motor_max"]}


def _overlay_led(summary):
    return {f"{name}_a": vals["node_v"] for name, vals in summary.items()}


def _overlay_usb_cc(summary):
    # Scenario-swept results (one value per host-Rp case) don't map onto
    # single schematic nodes -- shown in the text summary only.
    return {}


OVERLAY_BUILDERS = {
    "power_tree": _overlay_power_tree,
    "modem_burst": _overlay_modem_burst,
    "autoreset": _overlay_autoreset,
    "pwrkey": _overlay_pwrkey,
    "haptics": _overlay_haptics,
    "led": _overlay_led,
    "usb_cc": _overlay_usb_cc,
}


class ValidationError(Exception):
    pass


_SIMULATION_LOCK = threading.Lock()


def _validate_params(analysis, body):
    schema_by_name = {p["name"]: p for p in analysis["params"]}
    unknown = set(body) - set(schema_by_name)
    if unknown:
        raise ValidationError(f"Unknown parameter(s): {', '.join(sorted(unknown))}")

    kwargs = {}
    for name, value in body.items():
        spec = schema_by_name[name]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(f"Parameter '{name}' must be a number")
        if not (spec["min"] <= value <= spec["max"]):
            raise ValidationError(
                f"Parameter '{name}' must be between {spec['min']} and {spec['max']}"
            )
        kwargs[name] = float(value)
    return kwargs


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/schematic")
    def api_schematic():
        return jsonify(schematic_graph.get_graph())

    @app.route("/api/analyses")
    def api_analyses():
        return jsonify(ANALYSES)

    @app.route("/api/score")
    def api_score():
        """Board health score, computed from all 7 analyses at their
        nominal/default parameters (not whatever a user has tweaked in a
        tab) -- this reflects the baseline design, not a what-if scenario.
        """
        try:
            with _SIMULATION_LOCK:
                results = {}
                for name, run_func in RUN_FUNCS.items():
                    kwargs = {"plot_to_bytes": True} if name in TRANSIENT_ANALYSES else {}
                    results[name] = run_func(**kwargs)
        except Exception as exc:  # noqa: BLE001 - ngspice/PySpice raise assorted types
            return jsonify({"error": f"Simulation failed: {exc}"}), 422

        return jsonify(scoring.compute_board_score(results))

    @app.route("/api/run/<analysis_name>", methods=["POST"])
    def api_run(analysis_name):
        analysis = ANALYSES_BY_NAME.get(analysis_name)
        if analysis is None:
            return jsonify({"error": f"Unknown analysis '{analysis_name}'"}), 404

        body = request.get_json(silent=True) or {}
        try:
            kwargs = _validate_params(analysis, body)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400

        run_func = RUN_FUNCS[analysis_name]
        if analysis_name in TRANSIENT_ANALYSES:
            kwargs["plot_to_bytes"] = True

        try:
            with _SIMULATION_LOCK:
                result = run_func(**kwargs)
        except Exception as exc:  # noqa: BLE001 - ngspice/PySpice raise assorted types
            return jsonify({"error": f"Simulation failed: {exc}"}), 422

        plot_bytes = result.get("plot_bytes")
        subsystem = schematic_graph.subsystem_for_analysis(analysis_name)
        raw_overlay = OVERLAY_BUILDERS[analysis_name](result["summary"])
        overlay = {f"{subsystem}__{net}": value for net, value in raw_overlay.items()}

        return jsonify({
            "summary": result["summary"],
            "series": result["series"],
            "plot_png_base64": base64.b64encode(plot_bytes).decode() if plot_bytes else None,
            "overlay": overlay,
        })

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5057, threaded=True)
