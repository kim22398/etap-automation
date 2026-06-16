"""
Arc flash incident energy and PPE category calculations.

References
----------
- IEEE Std 1584-2002: Guide for Performing Arc Flash Hazard Calculations
- NFPA 70E-2021: Standard for Electrical Safety in the Workplace
  - Table 130.5(G): PPE categories by incident energy
  - Annex D: Sample arc flash calculations

This implementation follows the IEEE 1584-2002 empirical model: arcing current
(Eq 1/2), normalized incident energy (Eq 3/4), and the arc flash boundary
obtained by inverting the distance term.  Valid for 208 V – 15 kV systems with
bolted fault current in the 0.7 – 106 kA range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Equipment-type configuration constants (IEEE 1584-2018 Table 1)
# Gap (mm) and box model parameters
# ---------------------------------------------------------------------------

_EQUIPMENT_CONFIG: dict[str, dict] = {
    # gap_mm        : typical electrode gap (IEEE 1584-2002 Table 2)
    # enclosure     : enclosure descriptor
    # typical_wd_mm : default working distance (IEEE 1584-2002 Table 3)
    # box_factor_k1 : K1 enclosure factor (-0.555 box, -0.792 open air)
    # distance_x    : distance exponent x (IEEE 1584-2002 Table 4)
    "switchgear":      {"gap_mm": 32,  "enclosure": "VCB",  "typical_wd_mm": 610, "box_factor_k1": -0.555, "distance_x": 1.473},
    "switchboard":     {"gap_mm": 32,  "enclosure": "VCBB", "typical_wd_mm": 455, "box_factor_k1": -0.555, "distance_x": 1.473},
    "mcc":             {"gap_mm": 25,  "enclosure": "HCB",  "typical_wd_mm": 455, "box_factor_k1": -0.555, "distance_x": 1.473},
    "cable_junction":  {"gap_mm": 13,  "enclosure": "OA",   "typical_wd_mm": 455, "box_factor_k1": -0.792, "distance_x": 2.000},
    "panel":           {"gap_mm": 25,  "enclosure": "HCB",  "typical_wd_mm": 455, "box_factor_k1": -0.555, "distance_x": 1.473},
}

# IEEE 1584-2002 empirical model constants (normalized incident energy form).
#   log10(Ia)  = K + 0.662*log10(Ibf) + 0.0966*V + 0.000526*G
#                + 0.5588*V*log10(Ibf) - 0.00304*G*log10(Ibf)   (V < 1 kV)
#   log10(En)  = K1 + K2 + 1.081*log10(Ia) + 0.0011*G
#   E (cal/cm2)= Cf * En * (t/0.2) * (610/D)^x
# where En is the normalized incident energy at t=0.2 s and D=610 mm.
_K_ARC_LV = -0.153   # arcing-current intercept, V < 1 kV, box configuration
_K2_GROUNDING = 0.0  # ungrounded / high-resistance grounded system
_CF_LV = 1.5         # calculation factor, V <= 1 kV
_CF_MV = 1.0         # calculation factor, V > 1 kV
_T_REF_S = 0.2       # normalization time (s)
_D_REF_MM = 610.0    # normalization distance (mm)


@dataclass
class ArcFlashResult:
    """Detailed result of an arc flash calculation."""
    bus_id: str
    system_voltage_kv: float
    equipment_type: str
    bolted_fault_kA: float
    arcing_fault_kA: float
    working_distance_mm: float
    arc_duration_s: float
    incident_energy_cal_cm2: float
    arc_flash_boundary_m: float
    ppe_category: str
    notes: list[str]

    def __str__(self) -> str:
        return (
            f"Bus: {self.bus_id}\n"
            f"  Voltage:          {self.system_voltage_kv:.3f} kV\n"
            f"  Equipment:        {self.equipment_type}\n"
            f"  Bolted fault:     {self.bolted_fault_kA:.2f} kA\n"
            f"  Arcing fault:     {self.arcing_fault_kA:.2f} kA\n"
            f"  Working distance: {self.working_distance_mm:.0f} mm\n"
            f"  Arc duration:     {self.arc_duration_s*1000:.0f} ms\n"
            f"  Incident energy:  {self.incident_energy_cal_cm2:.2f} cal/cm²\n"
            f"  AFB:              {self.arc_flash_boundary_m:.2f} m\n"
            f"  PPE category:     {self.ppe_category}\n"
        )


class ArcFlashCalc:
    """
    Arc flash incident energy and hazard classification calculator.

    Implements a parametric form of the IEEE 1584-2018 empirical model for
    low- and medium-voltage systems.

    Parameters
    ----------
    system_voltage_kv : float
        Nominal system voltage in kV (e.g. 0.48, 4.16, 13.8).
    equipment_type : str
        One of: ``"switchgear"``, ``"switchboard"``, ``"mcc"``,
        ``"cable_junction"``, ``"panel"``.
    """

    def __init__(
        self,
        system_voltage_kv: float,
        equipment_type: str = "switchgear",
    ) -> None:
        if system_voltage_kv <= 0:
            raise ValueError("system_voltage_kv must be positive")
        equipment_type = equipment_type.lower()
        if equipment_type not in _EQUIPMENT_CONFIG:
            raise ValueError(
                f"equipment_type {equipment_type!r} not recognised. "
                f"Choose from: {list(_EQUIPMENT_CONFIG)}"
            )
        self.system_voltage_kv = system_voltage_kv
        self.equipment_type = equipment_type
        self._cfg = _EQUIPMENT_CONFIG[equipment_type]

    # ------------------------------------------------------------------
    # Core calculations
    # ------------------------------------------------------------------

    def _arcing_current_reduction(self, bolted_fault_kA: float) -> float:
        """
        IEEE 1584-2018 §4.4: estimated arcing current from bolted fault current.

        For 480 V–15 kV the arcing fault current is typically 0.85× the bolted
        fault current (conservative low end).  IEEE 1584-2018 provides a
        polynomial; this function approximates it.
        """
        v = self.system_voltage_kv
        g = self._cfg["gap_mm"]
        lg_ibf = math.log10(bolted_fault_kA)
        if v < 1.0:
            # IEEE 1584-2002 Eq 1 (V < 1 kV), arcing current in kA
            log_ia = (
                _K_ARC_LV
                + 0.662 * lg_ibf
                + 0.0966 * v
                + 0.000526 * g
                + 0.5588 * v * lg_ibf
                - 0.00304 * g * lg_ibf
            )
            return 10 ** log_ia
        else:
            # IEEE 1584-2002 Eq 2 (V >= 1 kV)
            log_ia = 0.00402 + 0.983 * lg_ibf
            return 10 ** log_ia

    def incident_energy_cal_cm2(
        self,
        bolted_fault_kA: float,
        arcing_fault_kA: float,
        distance_mm: float,
        duration_s: float,
    ) -> float:
        """
        Calculate incident energy at working distance.

        Uses the IEEE 1584-2002 normalized-energy empirical model:

            log10(En) = K1 + K2 + 1.081·log10(Ia) + 0.0011·G
            E = Cf · En · (t / 0.2) · (610 / D)^x

        where:
            En  = normalized incident energy at t=0.2 s, D=610 mm (cal/cm²)
            E   = incident energy at the working distance (cal/cm²)
            Ia  = arcing current (kA)
            t   = arc duration (s)        — energy scales linearly with time
            D   = working distance (mm)
            G   = electrode gap (mm), x = distance exponent, Cf = calc factor

        Parameters
        ----------
        bolted_fault_kA : float
            Maximum bolted (3-phase) fault current at the bus (kA sym. rms).
        arcing_fault_kA : float
            Estimated arcing fault current (kA).  If unsure, pass the result
            of ``arcing_current_kA()`` or use 0.85 × bolted_fault_kA.
        distance_mm : float
            Working distance from the arc point (mm).
        duration_s : float
            Arc clearing time in seconds (from upstream protective device
            time-current curve at the arcing fault current).

        Returns
        -------
        float
            Incident energy in cal/cm².
        """
        if bolted_fault_kA <= 0 or arcing_fault_kA <= 0:
            raise ValueError("Fault currents must be positive")
        if distance_mm <= 0:
            raise ValueError("distance_mm must be positive")
        if duration_s <= 0:
            raise ValueError("duration_s must be positive")

        v_kv = self.system_voltage_kv
        g = self._cfg["gap_mm"]
        k1 = self._cfg["box_factor_k1"]
        x = self._cfg["distance_x"]
        cf = _CF_LV if v_kv <= 1.0 else _CF_MV

        # Normalized incident energy En (cal/cm^2) at t = 0.2 s, D = 610 mm
        # log10(En) = K1 + K2 + 1.081*log10(Ia) + 0.0011*G
        log_En = k1 + _K2_GROUNDING + 1.081 * math.log10(arcing_fault_kA) + 0.0011 * g
        En = 10 ** log_En

        # Scale to actual time (linear) and working distance (D^-x)
        ie = cf * En * (duration_s / _T_REF_S) * (_D_REF_MM / distance_mm) ** x
        return ie

    def arcing_current_kA(self, bolted_fault_kA: float) -> float:
        """
        Estimate arcing fault current from bolted fault current.

        Per IEEE 1584-2018, calculations must be performed at both the
        "maximum" and "minimum" arcing currents; this returns the estimated
        arcing current.
        """
        return self._arcing_current_reduction(bolted_fault_kA)

    def protection_boundary_m(self, incident_energy_cal_cm2: float) -> float:
        """
        Arc flash protection boundary (AFB) in metres.

        The AFB is the distance at which incident energy equals 1.2 cal/cm²
        (second-degree burn threshold, NFPA 70E Annex D).

        Derived by inverting the incident energy equation:
            D = D_ref × (E / E_limit) ^ (1 / C4)

        where D_ref is the working distance used in the IE calculation and
        E_limit = 1.2 cal/cm².

        Parameters
        ----------
        incident_energy_cal_cm2 : float
            Incident energy at the reference working distance (cal/cm²).

        Returns
        -------
        float
            Arc flash boundary in metres.
        """
        IE_LIMIT_CAL_CM2 = 1.2  # NFPA 70E onset of second-degree burn
        d_ref_mm = self._cfg["typical_wd_mm"]
        x = self._cfg["distance_x"]
        if incident_energy_cal_cm2 <= 0:
            return 0.0
        # Incident energy varies with distance as E ∝ D^(-x). Inverting:
        #   AFB = D_ref × (E_ref / E_limit) ^ (1/x)
        # where E_ref is the incident energy at the reference working distance.
        afb_mm = d_ref_mm * (incident_energy_cal_cm2 / IE_LIMIT_CAL_CM2) ** (1.0 / x)
        return afb_mm / 1000  # convert mm → m

    def ppe_category(self, incident_energy_cal_cm2: float) -> str:
        """
        Determine PPE category per NFPA 70E-2021 Table 130.5(G).

        PPE categories are defined by incident energy levels:

        =========  ==================  ===========================
        Category   IE range (cal/cm²)  Minimum arc rating (cal/cm²)
        =========  ==================  ===========================
        PPE 1      1.2 – < 4           4
        PPE 2      4   – < 8           8
        PPE 3      8   – < 25          25
        PPE 4      25  – 40            40
        Danger     > 40                —
        =========  ==================  ===========================

        Values below 1.2 cal/cm² are below the onset of second-degree burn;
        no PPE is required (though safe work practices still apply).

        Parameters
        ----------
        incident_energy_cal_cm2 : float
            Calculated incident energy at the working distance.

        Returns
        -------
        str
            PPE category string.
        """
        ie = incident_energy_cal_cm2
        if ie < 1.2:
            return "No PPE Required (<1.2 cal/cm²)"
        elif ie < 4.0:
            return "PPE Category 1 (4 cal/cm² min arc rating)"
        elif ie < 8.0:
            return "PPE Category 2 (8 cal/cm² min arc rating)"
        elif ie < 25.0:
            return "PPE Category 3 (25 cal/cm² min arc rating)"
        elif ie <= 40.0:
            return "PPE Category 4 (40 cal/cm² min arc rating)"
        else:
            return f"DANGER — Exceeds PPE Category 4 ({ie:.1f} cal/cm² > 40 cal/cm²)"

    # ------------------------------------------------------------------
    # Full study
    # ------------------------------------------------------------------

    def calculate(
        self,
        bus_id: str,
        bolted_fault_kA: float,
        working_distance_mm: Optional[float] = None,
        arc_duration_s: float = 0.033,
    ) -> ArcFlashResult:
        """
        Run a complete arc flash study for a single bus.

        Parameters
        ----------
        bus_id : str
            Bus identifier label.
        bolted_fault_kA : float
            Maximum 3-phase bolted fault current (kA sym. rms).
        working_distance_mm : float, optional
            Working distance in mm.  Defaults to the equipment-type default.
        arc_duration_s : float
            Arc duration / clearing time in seconds (default 33 ms = 2-cycle
            at 60 Hz, typical for instantaneous trip).

        Returns
        -------
        ArcFlashResult
        """
        if working_distance_mm is None:
            working_distance_mm = float(self._cfg["typical_wd_mm"])

        arcing_kA = self._arcing_current_reduction(bolted_fault_kA)
        ie = self.incident_energy_cal_cm2(
            bolted_fault_kA, arcing_kA, working_distance_mm, arc_duration_s
        )
        afb = self.protection_boundary_m(ie)
        ppe = self.ppe_category(ie)

        notes: list[str] = []
        if bolted_fault_kA > 106:
            notes.append("WARNING: Bolted fault exceeds IEEE 1584-2018 validated range (106 kA).")
        if self.system_voltage_kv > 15:
            notes.append("WARNING: Voltage exceeds IEEE 1584-2018 validated range (15 kV).")

        return ArcFlashResult(
            bus_id=bus_id,
            system_voltage_kv=self.system_voltage_kv,
            equipment_type=self.equipment_type,
            bolted_fault_kA=bolted_fault_kA,
            arcing_fault_kA=round(arcing_kA, 3),
            working_distance_mm=working_distance_mm,
            arc_duration_s=arc_duration_s,
            incident_energy_cal_cm2=round(ie, 3),
            arc_flash_boundary_m=round(afb, 2),
            ppe_category=ppe,
            notes=notes,
        )
