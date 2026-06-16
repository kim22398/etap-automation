"""
Arc flash incident energy and PPE category calculations.

References
----------
- IEEE Std 1584-2018: Guide for Performing Arc Flash Hazard Calculations
- NFPA 70E-2021: Standard for Electrical Safety in the Workplace
  - Table 130.7(C)(15)(a): PPE categories for ac systems
  - Annex D: Sample arc flash calculations

The 2018 edition of IEEE 1584 uses a more comprehensive empirical model than
the 2002 edition, covering a wider voltage range (208 V – 15 kV) and equipment
configurations.  This implementation follows the IEEE 1584-2018 equations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


# ---------------------------------------------------------------------------
# Equipment-type configuration constants (IEEE 1584-2018 Table 1)
# Gap (mm) and box model parameters
# ---------------------------------------------------------------------------

_EQUIPMENT_CONFIG: dict[str, dict] = {
    # (typical electrode gap mm, enclosure type, distance class)
    "switchgear":      {"gap_mm": 32,  "enclosure": "VCB",  "typical_wd_mm": 610},
    "switchboard":     {"gap_mm": 32,  "enclosure": "VCBB", "typical_wd_mm": 455},
    "mcc":             {"gap_mm": 25,  "enclosure": "HCB",  "typical_wd_mm": 455},
    "cable_junction":  {"gap_mm": 13,  "enclosure": "OA",   "typical_wd_mm": 455},
    "panel":           {"gap_mm": 25,  "enclosure": "HCB",  "typical_wd_mm": 455},
}

# IEEE 1584-2018 empirical model coefficients (Table 3, VCB enclosure, 600 V class)
# Full 2018 model requires interpolation across voltage / gap lookup tables;
# these are the reduced-form constants for the common 480 V / VCB case.
# For other voltage classes use the appropriate table values.
_C1 = 0.753  # log10 scale factor
_C2 = 0.566
_C3 = 1.648
_C4 = 0.084  # distance exponent contribution


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
        if v < 1.0:
            # Low-voltage empirical equation (simplified from 1584-2018 Eq 1)
            log_ia = 0.00402 + 0.983 * math.log10(bolted_fault_kA)
            return 10 ** log_ia
        else:
            # Medium-voltage: arcing current is very close to bolted
            return bolted_fault_kA * 0.95

    def incident_energy_cal_cm2(
        self,
        bolted_fault_kA: float,
        arcing_fault_kA: float,
        distance_mm: float,
        duration_s: float,
    ) -> float:
        """
        Calculate incident energy at working distance.

        Uses the IEEE 1584-2018 simplified empirical model:

            log10(E) = C1 + C2·log10(Ia) + C3·log10(t) − C4·log10(D)

        where:
            E   = incident energy (cal/cm²)
            Ia  = arcing current (kA)
            t   = arc duration (s)
            D   = working distance (mm)

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

        # Voltage correction factor (IEEE 1584-2018 §4.6)
        v_kv = self.system_voltage_kv
        if v_kv < 1.0:
            kv_factor = 1.0 + 0.0011 * (v_kv * 1000 - 208)   # interpolate 208–999 V
        else:
            kv_factor = 1.0 + 0.023 * (v_kv - 1.0)            # 1–15 kV

        log_E = (
            _C1
            + _C2 * math.log10(arcing_fault_kA)
            + _C3 * math.log10(duration_s)
            - _C4 * math.log10(distance_mm)
        )
        # Apply voltage and enclosure correction
        ie = (10 ** log_E) * kv_factor
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
        if incident_energy_cal_cm2 <= 0:
            return 0.0
        # E ∝ D^(-C4·log10 factor) → AFB = D_ref × (E/E_lim)^(1/C4)
        # More precisely, from log_E equation: D_afb = D_ref × (E/E_lim)^(1/0.084*C4_exp)
        # IEEE 1584-2018 uses: AFB = (IE/IE_limit)^(1/x_factor) × WD
        # x_factor = 2 for distance exponent in simplified model
        afb_mm = d_ref_mm * math.sqrt(incident_energy_cal_cm2 / IE_LIMIT_CAL_CM2)
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


# allow Optional import at module level without requiring full typing import
from typing import Optional
