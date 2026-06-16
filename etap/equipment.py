"""
Equipment dataclasses for power system components.

Each class provides:
  - Typed attributes matching common ETAP / one-line diagram fields
  - A ``summary()`` method returning a human-readable dict suitable for
    tabular reports
  - Basic validation in ``__post_init__``
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Cable
# ---------------------------------------------------------------------------

@dataclass
class Cable:
    """
    Power cable descriptor.

    Parameters
    ----------
    id : str
        Unique cable tag (e.g. ``"CB-001"``).
    size : str
        AWG / kcmil size string (e.g. ``"350 kcmil"``, ``"4/0 AWG"``).
    length_m : float
        Route length in metres.
    voltage_kv : float
        Rated system voltage in kV.
    ampacity : float
        Base ampacity from NEC Table 310.16 at 75 °C (amperes).
    derating_factor : float
        Combined derating factor (0–1) for conduit fill, ambient temperature,
        and continuous loading.  NEC 310.15 adjustment factors apply.
    conductor : str
        Conductor material: ``"copper"`` or ``"aluminum"`` (default copper).
    insulation : str
        Insulation type, e.g. ``"THWN-2"``, ``"XHHW-2"`` (default THWN-2).
    """

    id: str
    size: str
    length_m: float
    voltage_kv: float
    ampacity: float
    derating_factor: float = 1.0
    conductor: str = "copper"
    insulation: str = "THWN-2"

    def __post_init__(self) -> None:
        if not (0.0 < self.derating_factor <= 1.0):
            raise ValueError(f"derating_factor must be in (0, 1], got {self.derating_factor}")
        if self.ampacity <= 0:
            raise ValueError("ampacity must be positive")
        if self.length_m <= 0:
            raise ValueError("length_m must be positive")

    @property
    def derated_ampacity(self) -> float:
        """Ampacity after applying all derating factors (A)."""
        return self.ampacity * self.derating_factor

    def summary(self) -> dict:
        return {
            "id": self.id,
            "size": self.size,
            "length_m": self.length_m,
            "voltage_kv": self.voltage_kv,
            "conductor": self.conductor,
            "insulation": self.insulation,
            "base_ampacity_A": self.ampacity,
            "derating_factor": self.derating_factor,
            "derated_ampacity_A": round(self.derated_ampacity, 1),
        }


# ---------------------------------------------------------------------------
# Breaker
# ---------------------------------------------------------------------------

@dataclass
class Breaker:
    """
    Low- or medium-voltage circuit breaker descriptor.

    Parameters
    ----------
    id : str
        Unique breaker tag (e.g. ``"52-MCC1"``).
    rating_A : float
        Continuous current rating in amperes.
    interrupting_kA : float
        Rated interrupting (breaking) capacity in kA (symmetrical RMS).
    trip_time_s : float
        Clearing / trip time in seconds (used in arc flash duration).
    voltage_kv : float
        Maximum rated voltage in kV.
    type : str
        ``"MCCB"``, ``"ACB"``, ``"VCB"``, ``"SF6"``, etc.
    """

    id: str
    rating_A: float
    interrupting_kA: float
    trip_time_s: float
    voltage_kv: float = 0.48
    type: str = "MCCB"

    def __post_init__(self) -> None:
        if self.rating_A <= 0:
            raise ValueError("rating_A must be positive")
        if self.interrupting_kA <= 0:
            raise ValueError("interrupting_kA must be positive")
        if self.trip_time_s <= 0:
            raise ValueError("trip_time_s must be positive")

    def summary(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "voltage_kv": self.voltage_kv,
            "rating_A": self.rating_A,
            "interrupting_kA": self.interrupting_kA,
            "trip_time_s": self.trip_time_s,
        }


# ---------------------------------------------------------------------------
# Transformer
# ---------------------------------------------------------------------------

@dataclass
class Transformer:
    """
    Power transformer descriptor.

    Parameters
    ----------
    id : str
        Unique transformer tag (e.g. ``"T-1"``).
    kva : float
        Nameplate rating in kVA.
    primary_kv : float
        Primary (HV) voltage in kV.
    secondary_kv : float
        Secondary (LV) voltage in kV.
    impedance_pct : float
        Nameplate percent impedance (e.g. ``5.75`` for 5.75 %).
    tap_position : float
        Current tap position as a multiplier (1.0 = nominal, 1.025 = +2.5 % tap).
    vector_group : str
        Winding connection, e.g. ``"Dyn11"``, ``"YNyn0"`` (default Dyn11).
    cooling : str
        Cooling type: ``"ONAN"``, ``"ONAF"``, ``"OFAF"``, etc. (default ONAN).
    """

    id: str
    kva: float
    primary_kv: float
    secondary_kv: float
    impedance_pct: float
    tap_position: float = 1.0
    vector_group: str = "Dyn11"
    cooling: str = "ONAN"

    def __post_init__(self) -> None:
        if self.kva <= 0:
            raise ValueError("kva must be positive")
        if self.impedance_pct <= 0:
            raise ValueError("impedance_pct must be positive")
        if not (0.9 <= self.tap_position <= 1.1):
            raise ValueError(f"tap_position {self.tap_position} outside typical ±10 % range")

    @property
    def turns_ratio(self) -> float:
        """Nominal turns ratio (primary / secondary)."""
        return self.primary_kv / self.secondary_kv

    @property
    def full_load_current_primary_A(self) -> float:
        """Full-load current on the primary side (A)."""
        return (self.kva * 1000) / (math.sqrt(3) * self.primary_kv * 1000)

    @property
    def full_load_current_secondary_A(self) -> float:
        """Full-load current on the secondary side (A)."""
        return (self.kva * 1000) / (math.sqrt(3) * self.secondary_kv * 1000)

    @property
    def base_impedance_secondary_ohm(self) -> float:
        """Base impedance referred to the secondary (Ω)."""
        return (self.secondary_kv ** 2 * 1e6) / (self.kva * 1000)

    @property
    def impedance_ohm_secondary(self) -> float:
        """Transformer impedance referred to secondary (Ω)."""
        return (self.impedance_pct / 100) * self.base_impedance_secondary_ohm

    def summary(self) -> dict:
        return {
            "id": self.id,
            "kva": self.kva,
            "primary_kv": self.primary_kv,
            "secondary_kv": self.secondary_kv,
            "impedance_pct": self.impedance_pct,
            "tap_position": self.tap_position,
            "vector_group": self.vector_group,
            "cooling": self.cooling,
            "turns_ratio": round(self.turns_ratio, 4),
            "flc_primary_A": round(self.full_load_current_primary_A, 1),
            "flc_secondary_A": round(self.full_load_current_secondary_A, 1),
            "Z_secondary_ohm": round(self.impedance_ohm_secondary, 4),
        }
