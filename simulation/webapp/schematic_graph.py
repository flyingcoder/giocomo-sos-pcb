"""Static, hand-authored schematic graph for the web frontend.

Not parsed from giacomo-schematic.json -- built directly from the
designators/nets documented in simulation/README.md and the node names
actually used as PySpice circuit-node strings in giacomo_circuit.py.

Every node ID is prefixed by its subsystem (`f"{subsystem}__{local_id}"`)
because some real nets/components (3V3, EN/IO0, D2, ...) appear in more
than one analysis's circuit. Cytoscape compound (grouped) nodes require a
single parent, so each subsystem gets its own node instance rather than
one shared node with two parents. For net nodes, `local_id` is kept
identical (including case) to the PySpice node name / summary key used in
giacomo_circuit.py, so webapp/app.py's overlay builders can address graph
nodes by simple string formatting with no translation table.
"""

SUBSYSTEMS = (
    ("power_tree", "Power tree"),
    ("modem_burst", "Modem TX burst (VBAT_LTE)"),
    ("autoreset", "CH340 auto-reset"),
    ("pwrkey", "LTE_PWRKEY driver"),
    ("haptics", "Buzzer / vibration motor"),
    ("leds", "LED networks"),
    ("usb_cc", "USB-C CC termination"),
)

ANALYSIS_TO_SUBSYSTEM = {
    "power_tree": "power_tree",
    "modem_burst": "modem_burst",
    "autoreset": "autoreset",
    "pwrkey": "pwrkey",
    "haptics": "haptics",
    "led": "leds",
    "usb_cc": "usb_cc",
}


def subsystem_for_analysis(analysis_name):
    return ANALYSIS_TO_SUBSYSTEM[analysis_name]


def _node(subsystem, local_id, label, x, y, kind="component"):
    return {
        "data": {
            "id": f"{subsystem}__{local_id}",
            "label": label,
            "kind": kind,
            "parent": f"group:{subsystem}",
        },
        "position": {"x": x, "y": y},
    }


def _edge(subsystem, src_local, dst_local, label=None):
    data = {
        "id": f"{subsystem}__{src_local}--{dst_local}",
        "source": f"{subsystem}__{src_local}",
        "target": f"{subsystem}__{dst_local}",
    }
    if label:
        data["label"] = label
    return {"data": data}


def _group_node(subsystem, label):
    return {"data": {"id": f"group:{subsystem}", "label": label, "kind": "group"}}


def _power_tree_elements():
    s = "power_tree"
    nodes = [
        _node(s, "battery", "Battery cell", 40, 80),
        _node(s, "U5", "U5 IP5306 boost", 220, 80, "ic"),
        _node(s, "vbus_5v", "VBUS_5V", 400, 80, "net"),
        _node(s, "U6", "U6 AP2112K-3.3 LDO", 580, 80, "ic"),
        _node(s, "3v3", "3V3", 760, 80, "net"),
        _node(s, "C4", "C4 10uF", 350, 180),
        _node(s, "C5", "C5 10uF", 410, 180),
        _node(s, "C6", "C6 100nF", 500, 180),
        _node(s, "C7", "C7 10uF", 760, 180),
        _node(s, "U2", "U2 ESP32-S3 load", 600, 280, "ic"),
        _node(s, "U3", "U3 GNSS load", 680, 280, "ic"),
        _node(s, "U4", "U4 audio codec load", 760, 280, "ic"),
        _node(s, "U7", "U7 IMU load", 840, 280, "ic"),
        _node(s, "U10", "U10 CH340C load", 920, 280, "ic"),
    ]
    edges = [
        _edge(s, "battery", "U5", "BATT_RAW"),
        _edge(s, "U5", "vbus_5v"),
        _edge(s, "vbus_5v", "C4"),
        _edge(s, "vbus_5v", "C5"),
        _edge(s, "vbus_5v", "C6"),
        _edge(s, "vbus_5v", "U6"),
        _edge(s, "U6", "3v3"),
        _edge(s, "3v3", "C7"),
        _edge(s, "3v3", "U2"),
        _edge(s, "3v3", "U3"),
        _edge(s, "3v3", "U4"),
        _edge(s, "3v3", "U7"),
        _edge(s, "3v3", "U10"),
    ]
    return nodes, edges


def _modem_burst_elements():
    s = "modem_burst"
    nodes = [
        _node(s, "battery", "Battery cell", 40, 780),
        _node(s, "D2", "D2 1N4148WS", 220, 780),
        _node(s, "vbat_lte", "VBAT_LTE", 400, 780, "net"),
        _node(s, "C11", "C11 330uF", 560, 740),
        _node(s, "C12", "C12 100nF", 560, 820),
        _node(s, "C13", "C13 33pF", 620, 860),
        _node(s, "idle_load", "A7670C idle load", 480, 900, "ic"),
        _node(s, "burst_load", "A7670C TX burst (pulsed)", 480, 970, "ic"),
    ]
    edges = [
        _edge(s, "battery", "D2"),
        _edge(s, "D2", "vbat_lte"),
        _edge(s, "vbat_lte", "C11"),
        _edge(s, "vbat_lte", "C12"),
        _edge(s, "vbat_lte", "C13"),
        _edge(s, "vbat_lte", "idle_load"),
        _edge(s, "vbat_lte", "burst_load"),
    ]
    return nodes, edges


def _autoreset_elements():
    s = "autoreset"
    nodes = [
        _node(s, "3v3", "3V3", 40, 1450, "net"),
        _node(s, "R4", "R4 10k EN pull-up", 220, 1420),
        _node(s, "en", "EN", 400, 1420, "net"),
        _node(s, "C9", "C9 10uF", 400, 1500),
        _node(s, "C8", "C8 100nF", 460, 1500),
        _node(s, "ch340_dtr", "CH340 DTR#", 200, 1600),
        _node(s, "U11", "U11 10k", 300, 1600),
        _node(s, "Q8", "Q8 2N3904", 400, 1600),
        _node(s, "R5", "R5 10k IO0 pull-up", 220, 1700),
        _node(s, "io0", "IO0", 400, 1700, "net"),
        _node(s, "ch340_rts", "CH340 RTS#", 200, 1780),
        _node(s, "U12", "U12 10k", 300, 1780),
        _node(s, "Q9", "Q9 2N3904", 400, 1780),
    ]
    edges = [
        _edge(s, "3v3", "R4"),
        _edge(s, "R4", "en"),
        _edge(s, "en", "C9"),
        _edge(s, "en", "C8"),
        _edge(s, "ch340_dtr", "U11"),
        _edge(s, "U11", "Q8"),
        _edge(s, "Q8", "en"),
        _edge(s, "3v3", "R5"),
        _edge(s, "R5", "io0"),
        _edge(s, "ch340_rts", "U12"),
        _edge(s, "U12", "Q9"),
        _edge(s, "Q9", "io0"),
    ]
    return nodes, edges


def _pwrkey_elements():
    s = "pwrkey"
    nodes = [
        _node(s, "3v3", "3V3", 40, 2160, "net"),
        _node(s, "R_pullup", "100k pull-up", 220, 2160),
        _node(s, "pwrkey", "PWRKEY", 400, 2160, "net"),
        _node(s, "lte_pwrkey_gpio", "ESP32 LTE_PWRKEY GPIO", 40, 2260),
        _node(s, "R6", "R6 4.7k", 220, 2260),
        _node(s, "Q5", "Q5 2N3904", 400, 2260),
    ]
    edges = [
        _edge(s, "3v3", "R_pullup"),
        _edge(s, "R_pullup", "pwrkey"),
        _edge(s, "lte_pwrkey_gpio", "R6"),
        _edge(s, "R6", "Q5"),
        _edge(s, "Q5", "pwrkey"),
    ]
    return nodes, edges


def _haptics_elements():
    s = "haptics"
    nodes = [
        _node(s, "vbat_lte", "VBAT_LTE", 40, 2860, "net"),
        _node(s, "D2", "D2 1N4148WS", 200, 2860),
        _node(s, "buzz_hi", "Buzzer high side", 360, 2860, "net"),
        _node(s, "R_buzz_esr", "Piezo ESR 32R", 520, 2860),
        _node(s, "q7_coll", "Buzzer drive node", 680, 2860, "net"),
        _node(s, "C_buzz", "Piezo C 15nF", 680, 2940),
        _node(s, "buzzer_pwm", "BUZZER_PWM (GPIO)", 360, 2980),
        _node(s, "R14", "R14 1k", 520, 2980),
        _node(s, "Q7", "Q7 2N3904", 680, 2980),
        _node(s, "3v3", "3V3", 40, 3080, "net"),
        _node(s, "R_motor", "Motor coil 45R", 220, 3080),
        _node(s, "q6_coll", "Motor drive node", 400, 3080, "net"),
        _node(s, "D1", "D1 flyback", 300, 3020),
        _node(s, "vib_motor", "VIB_MOTOR (GPIO/IO0)", 40, 3160),
        _node(s, "R13", "R13 1k", 220, 3160),
        _node(s, "Q6", "Q6 2N3904", 400, 3160),
    ]
    edges = [
        _edge(s, "vbat_lte", "D2"),
        _edge(s, "D2", "buzz_hi"),
        _edge(s, "buzz_hi", "R_buzz_esr"),
        _edge(s, "R_buzz_esr", "q7_coll"),
        _edge(s, "q7_coll", "C_buzz"),
        _edge(s, "buzzer_pwm", "R14"),
        _edge(s, "R14", "Q7"),
        _edge(s, "Q7", "q7_coll"),
        _edge(s, "3v3", "R_motor"),
        _edge(s, "R_motor", "q6_coll"),
        _edge(s, "q6_coll", "D1"),
        _edge(s, "D1", "3v3"),
        _edge(s, "vib_motor", "R13"),
        _edge(s, "R13", "Q6"),
        _edge(s, "Q6", "q6_coll"),
    ]
    return nodes, edges


_LED_LAYOUT = (
    ("LED1_red", 220),
    ("LED2_blue", 380),
    ("LED3_green", 540),
    ("LED4_white", 700),
)


def _leds_elements():
    s = "leds"
    nodes = [_node(s, "3v3", "3V3", 40, 3560, "net")]
    edges = []
    for name, x in _LED_LAYOUT:
        r_id = f"R_series_{name}"
        anode_id = f"{name}_a"
        led_id = name
        nodes.append(_node(s, r_id, f"1k series R ({name})", x, 3560))
        nodes.append(_node(s, anode_id, f"{name} anode", x, 3640, "net"))
        nodes.append(_node(s, led_id, name.replace("_", " "), x, 3720, "component"))
        edges.append(_edge(s, "3v3", r_id))
        edges.append(_edge(s, r_id, anode_id))
        edges.append(_edge(s, anode_id, led_id))
    return nodes, edges


def _usb_cc_elements():
    s = "usb_cc"
    nodes = [
        _node(s, "vbus_host", "Host VBUS (5V)", 40, 4260, "net"),
        _node(s, "R_host_rp1", "Host Rp (CC1)", 220, 4260),
        _node(s, "cc1", "CC1", 400, 4260, "net"),
        _node(s, "R2", "R2 5.1k", 560, 4260),
        _node(s, "R_host_rp2", "Host Rp (CC2)", 220, 4340),
        _node(s, "cc2", "CC2", 400, 4340, "net"),
        _node(s, "R3", "R3 5.1k", 560, 4340),
    ]
    edges = [
        _edge(s, "vbus_host", "R_host_rp1"),
        _edge(s, "R_host_rp1", "cc1"),
        _edge(s, "cc1", "R2"),
        _edge(s, "vbus_host", "R_host_rp2"),
        _edge(s, "R_host_rp2", "cc2"),
        _edge(s, "cc2", "R3"),
    ]
    return nodes, edges


_SUBSYSTEM_BUILDERS = {
    "power_tree": _power_tree_elements,
    "modem_burst": _modem_burst_elements,
    "autoreset": _autoreset_elements,
    "pwrkey": _pwrkey_elements,
    "haptics": _haptics_elements,
    "leds": _leds_elements,
    "usb_cc": _usb_cc_elements,
}


def get_graph():
    nodes = []
    edges = []
    for subsystem, label in SUBSYSTEMS:
        nodes.append(_group_node(subsystem, label))
        build = _SUBSYSTEM_BUILDERS[subsystem]
        sub_nodes, sub_edges = build()
        nodes.extend(sub_nodes)
        edges.extend(sub_edges)
    return {"nodes": nodes, "edges": edges}
