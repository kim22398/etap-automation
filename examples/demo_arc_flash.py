"""
Demo: Arc Flash Study for a Sample Industrial Distribution System
=================================================================

This script demonstrates arc flash calculations for three typical buses
in an industrial facility:

  Bus 480V-MCC-1   480 V MCC fed from 1000 kVA transformer
  Bus 480V-SWG-A   480 V main switchgear
  Bus 4160V-FDR-1  4.16 kV medium-voltage feeder bus

All calculations follow:
  - IEEE Std 1584-2018 (incident energy model)
  - NFPA 70E-2021 Table 130.5(G) (PPE category assignment)

Run this script from the project root:
    python examples/demo_arc_flash.py
"""

import sys
from pathlib import Path

# Allow running from either the project root or the examples/ directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etap.arc_flash import ArcFlashCalc
from etap.equipment import Breaker, Transformer


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def print_section(title: str) -> None:
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# System data
# ---------------------------------------------------------------------------

# 1000 kVA, 13.8 kV / 480 V, Z = 5.75 %, Dyn11
xfmr = Transformer(
    id="T-MCC1",
    kva=1000,
    primary_kv=13.8,
    secondary_kv=0.48,
    impedance_pct=5.75,
)

# Upstream medium-voltage available fault: 500 MVA (36.23 kA at 13.8 kV)
MV_FAULT_KA = 500 / (1.732 * 13.8)   # ≈ 20.9 kA

# Transformer secondary bolted fault current (LV side)
# I_sc_sec = FLC_sec / (Z_pct / 100)
# FLC_sec  = kVA / (√3 × V_sec_kV)  [in kA = kVA / (√3 × V_kV × 1000)]
I_flc_sec_kA = xfmr.kva / (1.732 * xfmr.secondary_kv * 1000)   # kA
I_sc_lv_kA   = I_flc_sec_kA / (xfmr.impedance_pct / 100)

print_section("System Data")
print(f"  Transformer:            {xfmr.id}  {xfmr.kva} kVA  "
      f"{xfmr.primary_kv}/{xfmr.secondary_kv} kV  Z={xfmr.impedance_pct}%")
print(f"  MV available fault:     {MV_FAULT_KA:.2f} kA at {xfmr.primary_kv} kV")
print(f"  LV bolted fault (calc): {I_sc_lv_kA:.2f} kA at {xfmr.secondary_kv} kV")


# ---------------------------------------------------------------------------
# Bus 1: 480 V MCC — MCCB upstream, instantaneous trip @ 2 cycles (33 ms)
# ---------------------------------------------------------------------------

breaker_mcc = Breaker(
    id="52-MCC1",
    rating_A=400,
    interrupting_kA=22.0,
    trip_time_s=0.033,   # 2-cycle instantaneous
    voltage_kv=0.48,
    type="MCCB",
)

print_section("Bus 480V-MCC-1  (480 V Motor Control Centre)")
calc_mcc = ArcFlashCalc(system_voltage_kv=0.48, equipment_type="mcc")
result_mcc = calc_mcc.calculate(
    bus_id="480V-MCC-1",
    bolted_fault_kA=I_sc_lv_kA,
    working_distance_mm=455,       # NFPA 70E default for MCC
    arc_duration_s=breaker_mcc.trip_time_s,
)
print(result_mcc)
if result_mcc.notes:
    for note in result_mcc.notes:
        print(f"  [!] {note}")


# ---------------------------------------------------------------------------
# Bus 2: 480 V Main Switchgear — 3-cycle breaker (50 ms)
# ---------------------------------------------------------------------------

breaker_swg = Breaker(
    id="52-SWG-A",
    rating_A=1200,
    interrupting_kA=65.0,
    trip_time_s=0.050,   # 3-cycle
    voltage_kv=0.48,
    type="ACB",
)

print_section("Bus 480V-SWG-A  (480 V Main Switchgear)")
calc_swg = ArcFlashCalc(system_voltage_kv=0.48, equipment_type="switchgear")
result_swg = calc_swg.calculate(
    bus_id="480V-SWG-A",
    bolted_fault_kA=I_sc_lv_kA * 1.15,    # slightly higher upstream
    working_distance_mm=610,                # IEEE 1584 switchgear default
    arc_duration_s=breaker_swg.trip_time_s,
)
print(result_swg)


# ---------------------------------------------------------------------------
# Bus 3: 4.16 kV Feeder Bus — vacuum circuit breaker, 5-cycle (83 ms)
# ---------------------------------------------------------------------------

breaker_mv = Breaker(
    id="52-4160-FDR1",
    rating_A=600,
    interrupting_kA=20.0,
    trip_time_s=0.083,   # 5-cycle
    voltage_kv=4.16,
    type="VCB",
)

print_section("Bus 4160V-FDR-1  (4.16 kV Medium Voltage Feeder)")
calc_mv = ArcFlashCalc(system_voltage_kv=4.16, equipment_type="switchgear")
result_mv = calc_mv.calculate(
    bus_id="4160V-FDR-1",
    bolted_fault_kA=MV_FAULT_KA,
    working_distance_mm=910,               # IEEE 1584 MV switchgear default
    arc_duration_s=breaker_mv.trip_time_s,
)
print(result_mv)


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

print_section("Arc Flash Study Summary")
print(f"  {'Bus':<20} {'IE (cal/cm²)':>13} {'AFB (m)':>8}  PPE Category")
print(f"  {'-'*20} {'-'*13} {'-'*8}  {'-'*35}")
for result in (result_mcc, result_swg, result_mv):
    print(
        f"  {result.bus_id:<20} "
        f"{result.incident_energy_cal_cm2:>13.2f} "
        f"{result.arc_flash_boundary_m:>8.2f}  "
        f"{result.ppe_category}"
    )

print("\n  Note: All calculations per IEEE 1584-2018 / NFPA 70E-2021.")
print("        Verify against ETAP or SKM for final label values.\n")
