# ETAP Automation Toolkit

A Python toolkit for power engineers working with ETAP (Electrical Transient Analyzer Program) outputs. Automates report parsing, equipment modeling, load scheduling, cable sizing, arc flash calculations, and report generation.

## Features

- **Report Parser** — Import ETAP CSV/Excel exports for load flow, short circuit, and arc flash studies
- **Equipment Models** — Typed dataclasses for cables, breakers, and transformers
- **Load Schedule** — Build and evaluate load schedules with demand/load factors per ANSI/IEEE standards
- **Cable Sizing** — Size cables per NEC ampacity tables with voltage drop verification (IEEE 141 / NEC 215)
- **Arc Flash** — Incident energy and PPE category calculations per IEEE 1584-2018 and NFPA 70E-2021
- **Report Generator** — Formatted Excel equipment reports via openpyxl

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from etap.load_schedule import LoadSchedule
from etap.arc_flash import ArcFlashCalc

# Build a load schedule
sched = LoadSchedule(name="MCC-1", voltage_kv=0.48)
sched.add_load("Pump-A", kw=75, kvar=56.25, demand_factor=0.85, load_factor=0.70)
sched.add_load("HVAC-1", kw=45, kvar=33.75, demand_factor=0.90, load_factor=0.80)
print(f"Total demand: {sched.total_demand_kw():.1f} kW")
print(f"Total kVA:    {sched.total_kva():.1f} kVA")
print(f"Power factor: {sched.power_factor():.3f}")

# Arc flash study
calc = ArcFlashCalc(system_voltage_kv=0.48, equipment_type="switchgear")
ie = calc.incident_energy_cal_cm2(
    bolted_fault_kA=20.0,
    arcing_fault_kA=16.5,
    distance_mm=610,
    duration_s=0.033,
)
print(f"Incident energy: {ie:.2f} cal/cm²")
print(f"PPE category:    {calc.ppe_category(ie)}")
```

## Module Overview

| Module | Description |
|---|---|
| `etap/report_parser.py` | Parse ETAP CSV/Excel study exports |
| `etap/equipment.py` | Cable, Breaker, Transformer dataclasses |
| `etap/load_schedule.py` | Load schedule builder and calculator |
| `etap/cable_sizing.py` | NEC/IEEE cable sizing with voltage drop |
| `etap/arc_flash.py` | IEEE 1584-2018 arc flash calculations |
| `etap/report_generator.py` | Excel report generation |

## Standards Implemented

- **IEEE 1584-2018** — Guide for Performing Arc Flash Hazard Calculations
- **NFPA 70E-2021** — Standard for Electrical Safety in the Workplace (PPE categories)
- **NEC (NFPA 70)** — Cable ampacity and voltage drop limits
- **IEEE 141 (Red Book)** — Recommended Practice for Electric Power Distribution

## Examples

```bash
python examples/demo_arc_flash.py
```

## Testing

```bash
pytest tests/
```

## License

MIT
