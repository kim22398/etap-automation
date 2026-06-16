"""
LoadSchedule — build and evaluate electrical load schedules.

Implements demand and load factor methodology per:
  - IEEE Std 141 (Red Book) — Electric Power Distribution for Industrial Plants
  - NFPA 70 (NEC) Article 220 — Branch-Circuit, Feeder, and Service Calculations
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class LoadEntry:
    """A single load item on the schedule."""
    name: str
    kw: float
    kvar: float
    demand_factor: float   # 0–1: fraction of connected load expected to operate simultaneously
    load_factor: float     # 0–1: fraction of the demand that represents average utilisation

    def __post_init__(self) -> None:
        for attr, val in [("kw", self.kw), ("kvar", self.kvar)]:
            if val < 0:
                raise ValueError(f"{attr} must be ≥ 0, got {val}")
        for attr, val in [("demand_factor", self.demand_factor), ("load_factor", self.load_factor)]:
            if not (0.0 < val <= 1.0):
                raise ValueError(f"{attr} must be in (0, 1], got {val}")

    @property
    def kva(self) -> float:
        return math.sqrt(self.kw ** 2 + self.kvar ** 2)

    @property
    def power_factor(self) -> float:
        if self.kva == 0:
            return 1.0
        return self.kw / self.kva

    @property
    def demand_kw(self) -> float:
        """Demand load in kW = connected kW × demand factor."""
        return self.kw * self.demand_factor

    @property
    def demand_kvar(self) -> float:
        """Demand reactive load in kVAR."""
        return self.kvar * self.demand_factor

    @property
    def demand_kva(self) -> float:
        return math.sqrt(self.demand_kw ** 2 + self.demand_kvar ** 2)

    @property
    def average_kw(self) -> float:
        """Average kW = demand kW × load factor."""
        return self.demand_kw * self.load_factor


class LoadSchedule:
    """
    Electrical load schedule for a bus, MCC, or switchboard.

    Parameters
    ----------
    name : str
        Descriptive name (e.g. ``"MCC-1"``).
    voltage_kv : float
        Bus voltage in kV (used for full-load current calculation).
    phases : int
        Number of phases: 1 or 3 (default 3).
    """

    def __init__(self, name: str, voltage_kv: float, phases: int = 3) -> None:
        if phases not in (1, 3):
            raise ValueError("phases must be 1 or 3")
        if voltage_kv <= 0:
            raise ValueError("voltage_kv must be positive")
        self.name = name
        self.voltage_kv = voltage_kv
        self.phases = phases
        self._loads: List[LoadEntry] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_load(
        self,
        name: str,
        kw: float,
        kvar: float,
        demand_factor: float = 1.0,
        load_factor: float = 1.0,
    ) -> "LoadSchedule":
        """
        Add a load to the schedule.

        Parameters
        ----------
        name : str
            Load tag or description.
        kw : float
            Connected active power (kW).
        kvar : float
            Connected reactive power (kVAR).
        demand_factor : float
            Fraction of connected load expected to be in service simultaneously
            (IEEE 141 §3.4).  Defaults to 1.0.
        load_factor : float
            Ratio of average load to maximum (demand) load over a period.
            Defaults to 1.0.

        Returns
        -------
        LoadSchedule
            Self (fluent interface).
        """
        self._loads.append(LoadEntry(name, kw, kvar, demand_factor, load_factor))
        return self

    def remove_load(self, name: str) -> None:
        """Remove a load by name (first match)."""
        for i, entry in enumerate(self._loads):
            if entry.name == name:
                del self._loads[i]
                return
        raise KeyError(f"Load {name!r} not found in schedule")

    # ------------------------------------------------------------------
    # Aggregate calculations
    # ------------------------------------------------------------------

    def total_connected_kw(self) -> float:
        """Sum of all connected (nameplate) kW."""
        return sum(e.kw for e in self._loads)

    def total_connected_kvar(self) -> float:
        """Sum of all connected kVAR."""
        return sum(e.kvar for e in self._loads)

    def total_demand_kw(self) -> float:
        """
        Total demand kW = Σ(kW × demand_factor) per IEEE 141.

        Note: this is a conservative worst-case sum.  For feeders serving
        diverse loads, a diversity factor > 1 may be applied externally.
        """
        return sum(e.demand_kw for e in self._loads)

    def total_demand_kvar(self) -> float:
        """Total demand kVAR."""
        return sum(e.demand_kvar for e in self._loads)

    def total_kva(self) -> float:
        """
        Total apparent power demand (kVA).

        Calculated from total demand kW and kVAR rather than summing
        individual kVA to properly account for the vectorial relationship.
        """
        return math.sqrt(self.total_demand_kw() ** 2 + self.total_demand_kvar() ** 2)

    def power_factor(self) -> float:
        """
        Composite power factor of the load schedule.

        Returns 1.0 when no loads are present to avoid division by zero.
        """
        kva = self.total_kva()
        if kva == 0.0:
            return 1.0
        return self.total_demand_kw() / kva

    def full_load_current_A(self) -> float:
        """
        Full-load current at bus voltage (A).

        For three-phase:  I = kVA × 1000 / (√3 × V_L-L)
        For single-phase: I = kVA × 1000 / V
        """
        kva = self.total_kva()
        if self.phases == 3:
            return (kva * 1000) / (math.sqrt(3) * self.voltage_kv * 1000)
        else:
            return (kva * 1000) / (self.voltage_kv * 1000)

    def average_kw(self) -> float:
        """Total average kW = Σ(kW × demand_factor × load_factor)."""
        return sum(e.average_kw for e in self._loads)

    def load_factor(self) -> float:
        """
        Schedule-level load factor = average_kW / demand_kW.

        Returns 1.0 when demand is zero.
        """
        demand = self.total_demand_kw()
        if demand == 0.0:
            return 1.0
        return self.average_kw() / demand

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def to_dataframe(self):
        """Return the load schedule as a pandas DataFrame (import deferred)."""
        import pandas as pd

        rows = []
        for e in self._loads:
            rows.append({
                "Name": e.name,
                "Connected_kW": e.kw,
                "Connected_kVAR": e.kvar,
                "Connected_kVA": round(e.kva, 1),
                "PF": round(e.power_factor, 3),
                "Demand_Factor": e.demand_factor,
                "Load_Factor": e.load_factor,
                "Demand_kW": round(e.demand_kw, 2),
                "Demand_kVAR": round(e.demand_kvar, 2),
                "Demand_kVA": round(e.demand_kva, 2),
                "Average_kW": round(e.average_kw, 2),
            })
        return pd.DataFrame(rows)

    def summary(self) -> dict:
        return {
            "schedule_name": self.name,
            "voltage_kv": self.voltage_kv,
            "phases": self.phases,
            "load_count": len(self._loads),
            "total_connected_kW": round(self.total_connected_kw(), 2),
            "total_connected_kVAR": round(self.total_connected_kvar(), 2),
            "total_demand_kW": round(self.total_demand_kw(), 2),
            "total_demand_kVAR": round(self.total_demand_kvar(), 2),
            "total_kVA": round(self.total_kva(), 2),
            "composite_PF": round(self.power_factor(), 4),
            "full_load_current_A": round(self.full_load_current_A(), 1),
            "average_kW": round(self.average_kw(), 2),
            "schedule_load_factor": round(self.load_factor(), 4),
        }

    def __repr__(self) -> str:
        return (
            f"LoadSchedule(name={self.name!r}, voltage_kv={self.voltage_kv}, "
            f"loads={len(self._loads)}, "
            f"demand_kW={self.total_demand_kw():.1f}, "
            f"kVA={self.total_kva():.1f}, "
            f"PF={self.power_factor():.3f})"
        )
