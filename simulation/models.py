"""Reusable SPICE subcircuit models for the Giacomo board simulation.

Discrete parts (2N3904, 1N4148WS) use published SPICE model parameters.
The multi-function ICs that have no public SPICE model (IP5306 PMIC,
AP2112K-3.3 LDO) are represented as small behavioral macro-models that
reproduce the one or two behaviors that matter for this simulation
(regulated output with finite output impedance and a load/line limit)
rather than pretending to model their internal silicon.
"""

from PySpice.Spice.Netlist import SubCircuitFactory
from PySpice.Unit import u_Ohm, u_V


# 2N3904 NPN — parameters from the widely-published Philips/ON Semi model,
# used as-is (this is a standard library model, not board-specific data).
QMOD_2N3904 = (
    ".model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 "
    "ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p "
    "MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 TR=239.5n TF=301.2p "
    "ITF=.4 VTF=4 XTF=2 RB=10)"
)

# 1N4148WS small-signal switching diode.
DMOD_1N4148WS = (
    ".model D1N4148WS D(IS=4.352n N=1.906 BV=110 IBV=0.0001 RS=0.6458 "
    "CJO=7.048p VJ=0.869 M=0.03 FC=0.5 TT=3.48n)"
)

# Ideal voltage-controlled switch, used to build pulsed resistive loads
# (see PulsedLoad below) instead of independent current sources -- ngspice
# 47's shared/subprocess interface to PySpice 1.5 silently zeroes `I`
# elements in this toolchain (verified against a standalone `ngspice -b`
# run of the identical netlist), while R/V/switch primitives are correct.
SWMOD_IDEAL = ".model SWMOD SW(Ron=0.01 Roff=1e9 Vt=1.5 Vh=0.1)"


class IP5306Boost(SubCircuitFactory):
    """Behavioral macro-model of the IP5306 charge/boost PMIC.

    Only the BAT -> VOUT boost path is modeled (this board never runs the
    charge-from-USB path and the discharge/boost path simultaneously, and
    the charge path isn't part of any of the analyses below). Modeled as
    an ideal 5 V source behind a small output resistance and a series
    inductor placeholder for the L3 boost inductor already present on the
    board net, so real load transients still sag the rail realistically.
    """

    NAME = "IP5306_BOOST"
    NODES = ("bat", "vout", "gnd")

    def __init__(self, output_voltage=5.0, r_out=0.15):
        super().__init__()
        # Ideal regulated source, referenced to local ground, then a real
        # output resistance so VOUT sags under load exactly like a real
        # boost converter with finite loop bandwidth / inductor DCR.
        self.V("ref", "vout_ideal", "gnd", u_V(output_voltage))
        self.R("out", "vout_ideal", "vout", u_Ohm(r_out))


class AP2112LDO(SubCircuitFactory):
    """Behavioral macro-model of the AP2112K-3.3 LDO.

    Ideal 3.3 V reference behind the datasheet-typical dropout-equivalent
    output resistance (~35 mV / 400 mA => ~0.09 Ohm) so line/load
    regulation on the 3V3 rail is visible under the transient current
    sinks used below.
    """

    NAME = "AP2112_LDO"
    NODES = ("vin", "vout", "gnd")

    def __init__(self, output_voltage=3.3, r_out=0.09):
        super().__init__()
        self.V("ref", "vout_ideal", "gnd", u_V(output_voltage))
        self.R("out", "vout_ideal", "vout", u_Ohm(r_out))


class ICLoad(SubCircuitFactory):
    """Behavioral supply-current load standing in for a digital IC.

    Implemented as a plain resistor sized to draw `idle_current` at
    `rail_voltage`, rather than an ideal current sink: the installed
    ngspice 47 / PySpice 1.5 combination silently zeroes independent
    current sources (`I` elements) in both shared-library and
    subprocess-server modes -- confirmed by comparing against a
    standalone `ngspice -b` batch run of the same netlist, which computes
    the expected non-zero node voltage. A resistor draws essentially the
    same current for a well-regulated rail and only relies on primitives
    (R/V/C/D/Q) verified to work correctly in this toolchain. Values are
    datasheet-typical estimates, not measured silicon — see README.md
    "Simulation scope & approach".
    """

    NAME = "IC_LOAD"
    NODES = ("vdd", "gnd")

    def __init__(self, idle_current, rail_voltage=3.3):
        super().__init__()
        # SubCircuitFactory pins the subcircuit name to the class-level
        # NAME; override per-instance so multiple differently-sized loads
        # in the same circuit don't collide on one ".subckt IC_LOAD" name.
        self._name = "IC_LOAD_%.4g" % idle_current
        self.R("idle", "vdd", "gnd", u_Ohm(rail_voltage / idle_current))
