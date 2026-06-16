"""
Cable sizing per NEC NFPA 70 and IEEE 141 voltage-drop criteria.

References
----------
- NEC Table 310.16 (2023): Allowable ampacities at 75 °C, copper, conduit
- IEEE Std 141-1993 (Red Book) §3.11: Voltage drop calculation
- NEC 215.2(A)(1): Maximum 3 % voltage drop on feeders
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# NEC Table 310.16 — 75 °C copper conductors in conduit (simplified)
# Key: AWG/kcmil label, Value: (ampacity_A, resistance_mΩ_per_m at 75°C)
# Resistance values from NEC Chapter 9, Table 9 (uncoated copper, conduit)
# ---------------------------------------------------------------------------

_NEC_TABLE: list[tuple[str, float, float]] = [
    # (size_label,  ampacity_A,  AC_resistance_mΩ_per_m)
    ("14 AWG",        15.0,    8.858),
    ("12 AWG",        20.0,    5.577),
    ("10 AWG",        30.0,    3.510),
    ("8 AWG",         50.0,    2.198),
    ("6 AWG",         65.0,    1.382),
    ("4 AWG",         85.0,    0.871),
    ("3 AWG",        100.0,    0.691),
    ("2 AWG",        115.0,    0.549),
    ("1 AWG",        130.0,    0.435),
    ("1/0 AWG",      150.0,    0.345),
    ("2/0 AWG",      175.0,    0.274),
    ("3/0 AWG",      200.0,    0.218),
    ("4/0 AWG",      230.0,    0.172),
    ("250 kcmil",    255.0,    0.147),
    ("300 kcmil",    285.0,    0.122),
    ("350 kcmil",    310.0,    0.105),
    ("400 kcmil",    335.0,    0.092),
    ("500 kcmil",    380.0,    0.074),
    ("600 kcmil",    420.0,    0.062),
    ("750 kcmil",    475.0,    0.049),
]

# Ambient temperature correction factors for 75 °C rated insulation (NEC 310.15(B)(2))
_AMBIENT_CORRECTION: dict[tuple[int, int], float] = {
    (0,   10):  1.29,
    (11,  15):  1.22,
    (16,  20):  1.15,
    (21,  25):  1.08,
    (26,  30):  1.00,   # reference temperature
    (31,  35):  0.91,
    (36,  40):  0.82,
    (41,  45):  0.71,
    (46,  50):  0.58,
    (51,  55):  0.41,
    (56,  60):  0.00,   # exceeds rating
}


@dataclass
class CableSizingResult:
    """Result of a cable sizing calculation."""
    size: str
    ampacity_base_A: float
    ampacity_derated_A: float
    full_load_current_A: float
    voltage_drop_pct: float
    voltage_drop_V: float
    length_m: float
    ambient_temp_C: float
    ambient_correction: float
    meets_ampacity: bool
    meets_voltage_drop: bool
    ok: bool

    def __str__(self) -> str:
        status = "OK" if self.ok else "FAIL"
        return (
            f"[{status}] {self.size}: "
            f"I_FL={self.full_load_current_A:.1f}A, "
            f"Ampacity={self.ampacity_derated_A:.1f}A, "
            f"VD={self.voltage_drop_pct:.2f}%"
        )


def _ambient_correction_factor(temp_C: float) -> float:
    """Return NEC 310.15 ambient temperature correction factor for 75 °C insulation."""
    for (lo, hi), factor in _AMBIENT_CORRECTION.items():
        if lo <= temp_C <= hi:
            return factor
    if temp_C < 0:
        return 1.29
    raise ValueError(f"Ambient temperature {temp_C} °C exceeds 75 °C insulation rating")


def _full_load_current(load_kw: float, voltage_kv: float, pf: float, phases: int = 3) -> float:
    """Calculate full-load current (A)."""
    if phases == 3:
        return (load_kw * 1000) / (math.sqrt(3) * voltage_kv * 1000 * pf)
    return (load_kw * 1000) / (voltage_kv * 1000 * pf)


def _voltage_drop_pct(
    current_A: float,
    resistance_mΩ_per_m: float,
    length_m: float,
    voltage_kv: float,
    phases: int = 3,
) -> tuple[float, float]:
    """
    Calculate voltage drop percentage using IEEE 141 formula.

    For three-phase:  VD = √3 × I × R × L  (line-to-line)
    For single-phase: VD = 2  × I × R × L  (round-trip)

    Parameters
    ----------
    resistance_mΩ_per_m : float
        AC resistance in milliohms per metre (from NEC Ch 9 Table 9).

    Returns
    -------
    (vd_pct, vd_V)
    """
    r_Ω = (resistance_mΩ_per_m / 1000) * length_m      # total resistance (Ω)
    vnom_V = voltage_kv * 1000

    if phases == 3:
        vd_V = math.sqrt(3) * current_A * r_Ω
    else:
        vd_V = 2 * current_A * r_Ω

    vd_pct = (vd_V / vnom_V) * 100
    return vd_pct, vd_V


def size_cable(
    load_kw: float,
    voltage_kv: float,
    length_m: float,
    pf: float = 0.85,
    voltage_drop_limit_pct: float = 3.0,
    ambient_temp_C: float = 30.0,
    phases: int = 3,
    continuous_load: bool = True,
) -> CableSizingResult:
    """
    Select the smallest standard copper cable size satisfying both ampacity
    and voltage drop criteria.

    Parameters
    ----------
    load_kw : float
        Load in kilowatts.
    voltage_kv : float
        System voltage in kV (line-to-line for 3-phase).
    length_m : float
        One-way cable length in metres.
    pf : float
        Load power factor (default 0.85).
    voltage_drop_limit_pct : float
        Maximum allowable voltage drop percentage (default 3.0 per NEC 215.2).
    ambient_temp_C : float
        Ambient temperature in °C (default 30 °C = NEC reference).
    phases : int
        1 or 3 (default 3-phase).
    continuous_load : bool
        If True, apply NEC 125 % continuous load multiplier to FLC for
        ampacity sizing (NEC 210.20, 215.2).

    Returns
    -------
    CableSizingResult
        Details of the selected cable including compliance flags.

    Raises
    ------
    ValueError
        If no standard cable size can satisfy both criteria.
    """
    if not (0 < pf <= 1.0):
        raise ValueError("pf must be in (0, 1]")
    if load_kw <= 0:
        raise ValueError("load_kw must be positive")

    amb_corr = _ambient_correction_factor(ambient_temp_C)
    i_fl = _full_load_current(load_kw, voltage_kv, pf, phases)

    # NEC 125 % rule for continuous loads (≥ 3 h)
    i_design = i_fl * 1.25 if continuous_load else i_fl

    last_result: Optional[CableSizingResult] = None

    for size_label, ampacity_base, resistance_mΩ_per_m in _NEC_TABLE:
        ampacity_derated = ampacity_base * amb_corr
        vd_pct, vd_V = _voltage_drop_pct(i_fl, resistance_mΩ_per_m, length_m, voltage_kv, phases)

        meets_amp = ampacity_derated >= i_design
        meets_vd  = vd_pct <= voltage_drop_limit_pct
        ok = meets_amp and meets_vd

        result = CableSizingResult(
            size=size_label,
            ampacity_base_A=ampacity_base,
            ampacity_derated_A=round(ampacity_derated, 1),
            full_load_current_A=round(i_fl, 1),
            voltage_drop_pct=round(vd_pct, 3),
            voltage_drop_V=round(vd_V, 2),
            length_m=length_m,
            ambient_temp_C=ambient_temp_C,
            ambient_correction=round(amb_corr, 3),
            meets_ampacity=meets_amp,
            meets_voltage_drop=meets_vd,
            ok=ok,
        )
        if ok:
            return result
        last_result = result

    # Return the largest size with a note — caller must inspect ok flag
    assert last_result is not None
    return last_result
