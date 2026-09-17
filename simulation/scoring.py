"""Heuristic "board health" scoring over the giacomo_circuit.py results.

Not a certified reliability estimate. Each check below maps one simulated
metric onto a 0-1 score via a linear margin ramp between a "safe" value
(full score) and a "fail" value (zero score) -- the same
"datasheet-typical, not measured on real silicon" caveat that applies
throughout this simulation applies to these thresholds too; they're
reasonable operating-margin estimates, not verbatim datasheet limits.

The overall score is a weight-averaged percentage across all checks
(weighted toward the subsystems that gate whether the board powers up,
boots, and connects at all -- power tree, modem power integrity, ESP32
reset/boot-strap, modem power-on -- over peripheral niceties like LED
brightness). It's meant to surface which margins are thin, not to
predict manufacturing yield.

This module has no dependency on giacomo_circuit.py or PySpice -- it
consumes plain `{"summary": {...}}` result dicts (the same shape
run_X_analysis() returns), so it can be unit-tested and reused by both
the CLI and the web app without any import cycle.
"""


def _clamp01(x):
    return max(0.0, min(1.0, x))


def score_within(value, safe_lo, safe_hi, fail_lo, fail_hi):
    """1.0 inside [safe_lo, safe_hi], ramps to 0.0 at fail_lo/fail_hi."""
    if safe_lo <= value <= safe_hi:
        return 1.0
    if value < safe_lo:
        if value <= fail_lo:
            return 0.0
        return _clamp01(1.0 - (safe_lo - value) / (safe_lo - fail_lo))
    if value >= fail_hi:
        return 0.0
    return _clamp01(1.0 - (value - safe_hi) / (fail_hi - safe_hi))


def score_at_least(value, safe, fail):
    """"Higher is better" metric: 1.0 at/above safe, 0.0 at/below fail."""
    if value >= safe:
        return 1.0
    if value <= fail:
        return 0.0
    return _clamp01(1.0 - (safe - value) / (safe - fail))


def score_at_most(value, safe, fail):
    """"Lower is better" metric: 1.0 at/below safe, 0.0 at/above fail."""
    if value <= safe:
        return 1.0
    if value >= fail:
        return 0.0
    return _clamp01(1.0 - (value - safe) / (fail - safe))


def _evaluate_vbus_5v(summary):
    v = summary["vbus_5v"]
    return score_within(v, 4.75, 5.25, 4.5, 5.5), f"VBUS_5V = {v:.2f} V (target 5.00 V ±5%)"


def _evaluate_v3v3(summary):
    v = summary["v3v3"]
    return score_within(v, 3.135, 3.465, 2.97, 3.63), f"3V3 = {v:.2f} V (target 3.30 V ±5%)"


def _evaluate_vbat_lte_sag(summary):
    v = summary["v_min"]
    return (score_at_least(v, 3.3, 3.0),
            f"VBAT_LTE min during TX burst = {v:.2f} V "
            "(typical single-cell modem brownout floor ~3.0 V)")


def _evaluate_en_low(summary):
    v = summary["en_min"]
    return (score_at_most(v, 0.3, 1.0),
            f"EN min = {v:.2f} V (must pull well below ~1 V to reliably reset)")


def _evaluate_io0_low(summary):
    v = summary["io0_min"]
    return (score_at_most(v, 0.3, 1.0),
            f"IO0 min = {v:.2f} V (must pull well below ~1 V to enter download mode)")


def _evaluate_pwrkey_pulse(summary):
    ms = summary["low_time_ms"]
    return (score_at_least(ms, 100, 50),
            f"PWRKEY held low for {ms:.0f} ms (SIMCom spec requires >=100 ms)")


def _evaluate_buzzer_swing(summary):
    swing = summary["buzz_max"] - summary["buzz_min"]
    return score_at_least(swing, 2.0, 0.5), f"Buzzer drive swing = {swing:.2f} V"


def _evaluate_motor_swing(summary):
    swing = summary["motor_max"] - summary["motor_min"]
    return score_at_least(swing, 2.0, 0.5), f"Motor drive swing = {swing:.2f} V"


def _evaluate_led_currents(summary):
    scores = []
    details = []
    for name, vals in summary.items():
        scores.append(score_within(vals["i_ma"], 0.5, 20.0, 0.1, 30.0))
        details.append(f"{name}={vals['i_ma']:.2f}mA")
    return min(scores), ", ".join(details)


# Labels must match giacomo_circuit.DEFAULT_USB_HOST_RP_CASES. Bands are
# typical Type-C Rd=5.1k/Rp voltage-divider ranges for each advertised
# source current, not copied verbatim from the USB-C spec table.
_USB_CC_BANDS = (
    ("host Rp=56k (default 900mA/1.5A source)", 0.25, 0.61, 0.15, 0.75),
    ("host Rp=22k (1.5A source)", 0.70, 1.16, 0.55, 1.35),
    ("host Rp=10k (3A source)", 1.31, 2.04, 1.05, 2.35),
)


def _evaluate_usb_cc(summary):
    scores = []
    details = []
    for label, safe_lo, safe_hi, fail_lo, fail_hi in _USB_CC_BANDS:
        v = summary[label]
        scores.append(score_within(v, safe_lo, safe_hi, fail_lo, fail_hi))
        details.append(f"{label.split(' (')[0]}: {v:.2f} V")
    return min(scores), "; ".join(details)


CHECKS = (
    {"analysis": "power_tree", "id": "vbus_5v", "label": "VBUS_5V regulation",
     "weight": 2.0, "evaluate": _evaluate_vbus_5v},
    {"analysis": "power_tree", "id": "v3v3", "label": "3V3 regulation",
     "weight": 3.0, "evaluate": _evaluate_v3v3},
    {"analysis": "modem_burst", "id": "vbat_lte_sag", "label": "VBAT_LTE TX-burst sag",
     "weight": 3.0, "evaluate": _evaluate_vbat_lte_sag},
    {"analysis": "autoreset", "id": "en_low", "label": "EN reset assertion",
     "weight": 2.0, "evaluate": _evaluate_en_low},
    {"analysis": "autoreset", "id": "io0_low", "label": "IO0 boot-strap assertion",
     "weight": 1.5, "evaluate": _evaluate_io0_low},
    {"analysis": "pwrkey", "id": "pwrkey_pulse", "label": "LTE_PWRKEY low-pulse width",
     "weight": 2.5, "evaluate": _evaluate_pwrkey_pulse},
    {"analysis": "usb_cc", "id": "usb_cc_bands", "label": "USB-C CC termination bands",
     "weight": 1.0, "evaluate": _evaluate_usb_cc},
    {"analysis": "haptics", "id": "buzzer_swing", "label": "Buzzer drive swing",
     "weight": 0.5, "evaluate": _evaluate_buzzer_swing},
    {"analysis": "haptics", "id": "motor_swing", "label": "Motor drive swing",
     "weight": 0.5, "evaluate": _evaluate_motor_swing},
    {"analysis": "led", "id": "led_currents", "label": "LED forward currents",
     "weight": 1.0, "evaluate": _evaluate_led_currents},
)


def _verdict(score):
    if score >= 90:
        return "Likely to work"
    if score >= 70:
        return "Likely to work, some margins are tight"
    if score >= 40:
        return "At risk -- review the flagged checks before building"
    return "Likely to fail -- critical margins are violated"


def compute_board_score(results):
    """`results` maps analysis name -> its run_X_analysis() return dict."""
    check_results = []
    weighted_sum = 0.0
    weight_total = 0.0
    for check in CHECKS:
        summary = results[check["analysis"]]["summary"]
        score, detail = check["evaluate"](summary)
        score = _clamp01(score)
        weighted_sum += score * check["weight"]
        weight_total += check["weight"]
        check_results.append({
            "id": check["id"],
            "analysis": check["analysis"],
            "label": check["label"],
            "weight": check["weight"],
            "score_pct": round(score * 100, 1),
            "detail": detail,
        })

    overall = round((weighted_sum / weight_total) * 100, 1) if weight_total else 0.0
    check_results.sort(key=lambda c: c["score_pct"])

    return {
        "overall_score": overall,
        "verdict": _verdict(overall),
        "checks": check_results,
    }
