# ETAP Automation Toolkit

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Standards](https://img.shields.io/badge/Standards-IEEE%201584--2018%20%7C%20NFPA%2070E--2021%20%7C%20NEC%202023-orange)
![Tests](https://img.shields.io/badge/Tests-pytest-brightgreen)

A professional Python toolkit for power engineers working with **ETAP** (Electrical Transient Analyzer Program) study outputs. Automates the post-processing pipeline from raw ETAP exports through arc flash assessment, cable sizing, load scheduling, and polished Excel deliverables — all traceable to published IEEE and NEC standards.

---

## Run it (main.py)

A single entry point at the repo root exposes the toolkit's key calculations — no `PYTHONPATH` or imports required:

```bash
python main.py                 # run the flagship arc flash study demo
python main.py --help          # list every subcommand
python main.py test            # run the pytest suite

# Domain calculations straight from the CLI (all flags have sensible defaults):
python main.py arcflash --voltage-kv 0.48 --bolted-ka 25 --duration-s 0.033 --equipment mcc
python main.py cable --load-kw 250 --voltage-kv 0.48 --length-m 120
```

`arcflash` reports incident energy, arc flash boundary, and NFPA 70E PPE category for a bus; `cable` selects the smallest NEC-compliant copper conductor that meets both ampacity and voltage-drop limits.

---

## What is ETAP?

**ETAP** is the industry-standard power systems analysis software used by engineers worldwide for load flow, short circuit, arc flash, motor starting, protective device coordination, and cable ampacity studies. It is widely used in oil and gas, utilities, data centres, petrochemical, mining, and industrial facilities.

ETAP produces detailed study reports in Excel and CSV format. This toolkit automates the extraction, validation, and post-processing of those reports so that engineers can:

- Reproduce and audit ETAP results programmatically
- Batch-process hundreds of buses without manual copy-paste
- Generate standardised deliverable documents in a repeatable, version-controlled workflow
- Perform quick sanity checks and sensitivity studies against IEEE reference equations

---

## Features

| Feature | Description |
|---|---|
| **Report Parser** | Import ETAP CSV/Excel exports for load flow, short circuit, and arc flash studies |
| **Equipment Models** | Typed dataclasses for cables, breakers, and transformers with validation |
| **Load Schedule** | Build and evaluate load schedules with demand/load factors per IEEE 141 |
| **Cable Sizing** | Size copper cables per NEC Table 310.16 with ambient derating and voltage drop |
| **Arc Flash** | Incident energy and PPE category calculations per IEEE 1584-2018 / NFPA 70E-2021 |
| **Report Generator** | Formatted Excel equipment schedules via openpyxl |

---

## Theory & Standards

### IEEE 1584-2018 — Arc Flash

The 2018 edition of IEEE 1584, *Guide for Performing Arc Flash Hazard Calculations*, replaced the 2002 model with a comprehensive empirical database covering 1,800+ laboratory tests. Key improvements:

- Voltage range extended to **208 V – 15 kV**
- Electrode gap and enclosure geometry explicitly modelled (VCB, VCBB, HCB, OA)
- Separate arcing current equations for LV (< 1 kV) and MV (1–15 kV) systems
- Mandatory two-current calculation (maximum and minimum arcing current) to capture the worst-case protective device response

The core incident energy equation (simplified log-linear form):

```
log10(E) = C1 + C2·log10(Ia) + C3·log10(t) − C4·log10(D)
```

where `E` = incident energy (cal/cm²), `Ia` = arcing current (kA), `t` = arc duration (s), `D` = working distance (mm).

See [docs/arc_flash_guide.md](docs/arc_flash_guide.md) for the full derivation, boundary calculations, and site application procedure.

### NFPA 70E-2021 — PPE Categories

NFPA 70E, *Standard for Electrical Safety in the Workplace*, Table 130.5(G) defines four PPE categories based on incident energy:

| PPE Category | Incident Energy Range | Minimum Arc Rating |
|:---:|:---:|:---:|
| 1 | 1.2 – < 4 cal/cm² | 4 cal/cm² |
| 2 | 4 – < 8 cal/cm² | 8 cal/cm² |
| 3 | 8 – < 25 cal/cm² | 25 cal/cm² |
| 4 | 25 – 40 cal/cm² | 40 cal/cm² |
| Danger | > 40 cal/cm² | Equipment must be de-energised |

### NEC Article 310 — Cable Sizing

The National Electrical Code (NFPA 70) Article 310 governs conductor sizing. Key rules implemented in this toolkit:

- **Table 310.16** — Allowable ampacities for copper conductors in conduit at 75 °C
- **310.15(B)(2)** — Ambient temperature correction factors
- **310.15(C)(1)** — Conduit fill derating (more than three current-carrying conductors)
- **210.20 / 215.2** — 125 % multiplier for continuous loads (loads energised ≥ 3 hours)
- **215.2(A)(1)** — 3 % maximum voltage drop on feeders (5 % total including branch circuit)

See [docs/cable_sizing_guide.md](docs/cable_sizing_guide.md) for the full methodology and a worked example.

### IEEE 141 (Red Book) — Load Scheduling

IEEE Std 141, *Recommended Practice for Electric Power Distribution for Industrial Plants*, defines the demand factor and load factor methodology used to right-size electrical infrastructure:

- **Demand factor** — ratio of maximum demand to total connected load
- **Load factor** — ratio of average demand to peak demand over a period
- **Diversity factor** — ratio of the sum of individual peak demands to the simultaneous peak demand of the group

See [docs/load_schedule_guide.md](docs/load_schedule_guide.md) for a detailed example industrial load schedule.

---

## Project Structure

```
etap-automation/
├── etap/                        # Core library package
│   ├── __init__.py              # Package initialiser
│   ├── report_parser.py         # ETAPReportParser — CSV/Excel import
│   ├── equipment.py             # Cable, Breaker, Transformer dataclasses
│   ├── load_schedule.py         # LoadSchedule builder and IEEE 141 calculations
│   ├── cable_sizing.py          # NEC ampacity and voltage drop sizing
│   ├── arc_flash.py             # IEEE 1584-2018 arc flash calculations
│   └── report_generator.py      # openpyxl Excel report generation
│
├── examples/
│   └── demo_arc_flash.py        # Full arc flash study for a 3-bus industrial system
│
├── tests/
│   ├── __init__.py
│   └── test_load_schedule.py    # pytest suite for LoadSchedule
│
├── docs/
│   ├── arc_flash_guide.md       # IEEE 1584-2018 theory and site procedure
│   ├── cable_sizing_guide.md    # NEC Article 310 methodology and worked example
│   ├── load_schedule_guide.md   # IEEE 141 demand/load factor guide
│   ├── etap_report_parsing.md   # How to export and parse ETAP reports
│   └── getting_started.md       # End-to-end tutorial
│
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## Installation

```bash
git clone https://github.com/kim22398/etap-automation.git
cd etap-automation
pip install -r requirements.txt
```

**Python 3.10+ required.**

Dependencies:

| Package | Purpose |
|---|---|
| `pandas` | DataFrame processing for parsed reports |
| `openpyxl` | Excel report generation |
| `matplotlib` | Plotting (load profiles, TCC curves) |
| `jinja2` | HTML report templating |
| `python-docx` | Word document generation |
| `pytest` | Test suite |

---

## Quick Start

### 1. Parse an ETAP Arc Flash Export

```python
from etap.report_parser import ETAPReportParser

parser = ETAPReportParser()
df = parser.parse_arc_flash("etap_exports/arc_flash_results.xlsx")
print(df[["bus_id", "incident_energy_cal_cm2", "ppe_category"]].head())
```

### 2. Calculate Arc Flash for a Single Bus

```python
from etap.arc_flash import ArcFlashCalc

calc = ArcFlashCalc(system_voltage_kv=0.48, equipment_type="switchgear")
result = calc.calculate(
    bus_id="480V-SWG-A",
    bolted_fault_kA=20.0,
    working_distance_mm=610,
    arc_duration_s=0.050,
)
print(result)
# Incident energy:  3.47 cal/cm²
# AFB:              1.70 m
# PPE category:     PPE Category 1 (4 cal/cm² min arc rating)
```

### 3. Build a Load Schedule

```python
from etap.load_schedule import LoadSchedule

sched = LoadSchedule(name="MCC-1", voltage_kv=0.48)
sched.add_load("Pump-A",  kw=75, kvar=56.25, demand_factor=0.85, load_factor=0.70)
sched.add_load("HVAC-1",  kw=45, kvar=33.75, demand_factor=0.90, load_factor=0.80)
sched.add_load("Lighting", kw=10, kvar=0.0,  demand_factor=1.00, load_factor=0.95)

print(f"Total demand:  {sched.total_demand_kw():.1f} kW")
print(f"Total kVA:     {sched.total_kva():.1f} kVA")
print(f"Power factor:  {sched.power_factor():.3f}")
print(f"FLC at 480 V:  {sched.full_load_current_A():.1f} A")
```

### 4. Size a Feeder Cable

```python
from etap.cable_sizing import size_cable

result = size_cable(
    load_kw=75.0,
    voltage_kv=0.48,
    length_m=120.0,
    pf=0.85,
    ambient_temp_C=40.0,    # hot conduit
    continuous_load=True,
)
print(result)
# [OK] 3/0 AWG: I_FL=106.2A, Ampacity=164.0A, VD=2.84%
```

### 5. Generate an Excel Equipment Report

```python
from etap.equipment import Cable, Breaker, Transformer
from etap.report_generator import generate_equipment_report

items = [
    Cable("CB-001", "350 kcmil", length_m=120, voltage_kv=0.48, ampacity=310, derating_factor=0.8),
    Breaker("52-MCC1", rating_A=400, interrupting_kA=22, trip_time_s=0.033),
    Transformer("T-1", kva=1000, primary_kv=13.8, secondary_kv=0.48, impedance_pct=5.75),
]
path = generate_equipment_report(items, "output/equipment_schedule.xlsx", "Unit 5 Substation")
print(f"Report written to: {path}")
```

---

## Workflow

The typical engineering workflow this toolkit supports:

```
ETAP Study Files (.xlsx / .csv)
          │
          ▼
   ETAPReportParser              ← parse_load_flow(), parse_short_circuit(), parse_arc_flash()
          │
          ▼
   pandas DataFrames             ← bus_id, fault_kA, incident_energy, ppe_category …
          │
    ┌─────┴──────┐
    ▼            ▼
ArcFlashCalc  size_cable()       ← re-calculate / verify / sensitivity study
    │            │
    ▼            ▼
ArcFlashResult  CableSizingResult
    │            │
    └─────┬──────┘
          ▼
  LoadSchedule.summary()        ← aggregate kW / kVA / PF per bus
          │
          ▼
generate_equipment_report()     ← formatted .xlsx deliverable
```

For a step-by-step walkthrough see [docs/getting_started.md](docs/getting_started.md).

---

## API Reference

### `ETAPReportParser`

```python
class ETAPReportParser(encoding: str = "utf-8")
```

Parses ETAP CSV/Excel study exports into tidy DataFrames. Handles the variable header block that ETAP prepends to all exports and normalises column names to snake_case regardless of the ETAP version.

| Method | Returns | Description |
|---|---|---|
| `parse_load_flow(filepath)` | `pd.DataFrame` | Bus voltages, MW, MVAR, MVA, PF |
| `parse_short_circuit(filepath)` | `pd.DataFrame` | 3-phase and SLG fault kA, X/R ratio, fault MVA |
| `parse_arc_flash(filepath)` | `pd.DataFrame` | Incident energy, AFB, PPE category per bus |

---

### `ArcFlashCalc`

```python
class ArcFlashCalc(system_voltage_kv: float, equipment_type: str = "switchgear")
```

IEEE 1584-2018 arc flash calculator. Supported `equipment_type` values: `"switchgear"`, `"switchboard"`, `"mcc"`, `"cable_junction"`, `"panel"`.

| Method | Returns | Description |
|---|---|---|
| `calculate(bus_id, bolted_fault_kA, working_distance_mm, arc_duration_s)` | `ArcFlashResult` | Full single-bus arc flash study |
| `incident_energy_cal_cm2(bolted_fault_kA, arcing_fault_kA, distance_mm, duration_s)` | `float` | Incident energy at working distance (cal/cm²) |
| `arcing_current_kA(bolted_fault_kA)` | `float` | Estimated arcing fault current from bolted current |
| `protection_boundary_m(incident_energy_cal_cm2)` | `float` | Arc flash boundary distance (m) |
| `ppe_category(incident_energy_cal_cm2)` | `str` | NFPA 70E-2021 PPE category string |

**`ArcFlashResult` fields:** `bus_id`, `system_voltage_kv`, `equipment_type`, `bolted_fault_kA`, `arcing_fault_kA`, `working_distance_mm`, `arc_duration_s`, `incident_energy_cal_cm2`, `arc_flash_boundary_m`, `ppe_category`, `notes`.

---

### `size_cable`

```python
def size_cable(
    load_kw: float,
    voltage_kv: float,
    length_m: float,
    pf: float = 0.85,
    voltage_drop_limit_pct: float = 3.0,
    ambient_temp_C: float = 30.0,
    phases: int = 3,
    continuous_load: bool = True,
) -> CableSizingResult
```

Selects the smallest NEC-compliant copper conductor satisfying both ampacity and voltage drop. Applies the 125 % continuous load rule and ambient temperature derating per NEC 310.15.

**`CableSizingResult` fields:** `size`, `ampacity_base_A`, `ampacity_derated_A`, `full_load_current_A`, `voltage_drop_pct`, `voltage_drop_V`, `length_m`, `ambient_temp_C`, `ambient_correction`, `meets_ampacity`, `meets_voltage_drop`, `ok`.

---

### `LoadSchedule`

```python
class LoadSchedule(name: str, voltage_kv: float, phases: int = 3)
```

Builds and evaluates an electrical load schedule per IEEE 141.

| Method | Returns | Description |
|---|---|---|
| `add_load(name, kw, kvar, demand_factor, load_factor)` | `self` | Add a load entry (fluent) |
| `remove_load(name)` | `None` | Remove first load matching name |
| `total_connected_kw()` | `float` | Sum of nameplate kW |
| `total_demand_kw()` | `float` | Σ(kW × demand_factor) |
| `total_kva()` | `float` | Vectorial kVA from demand kW and kVAR |
| `power_factor()` | `float` | Composite PF of schedule |
| `full_load_current_A()` | `float` | FLC at bus voltage (A) |
| `average_kw()` | `float` | Σ(kW × demand_factor × load_factor) |
| `load_factor()` | `float` | average_kW / demand_kW |
| `to_dataframe()` | `pd.DataFrame` | All load entries as a pandas table |
| `summary()` | `dict` | Key totals suitable for reports |

---

### Equipment Dataclasses

#### `Cable`
```python
Cable(id, size, length_m, voltage_kv, ampacity, derating_factor=1.0, conductor="copper", insulation="THWN-2")
```
Properties: `derated_ampacity`. Method: `summary() → dict`.

#### `Breaker`
```python
Breaker(id, rating_A, interrupting_kA, trip_time_s, voltage_kv=0.48, type="MCCB")
```
Method: `summary() → dict`.

#### `Transformer`
```python
Transformer(id, kva, primary_kv, secondary_kv, impedance_pct, tap_position=1.0, vector_group="Dyn11", cooling="ONAN")
```
Properties: `turns_ratio`, `full_load_current_primary_A`, `full_load_current_secondary_A`, `base_impedance_secondary_ohm`, `impedance_ohm_secondary`. Method: `summary() → dict`.

---

### `generate_equipment_report`

```python
def generate_equipment_report(
    equipment_list: list[Cable | Breaker | Transformer],
    output_path: str | Path,
    project_title: str = "Electrical Equipment Schedule",
) -> Path
```

Generates a formatted multi-sheet Excel workbook with a Summary sheet plus individual sheets for Cables, Breakers, and Transformers. Automatically skips sheets for equipment categories with no entries.

---

## Running the Demo

```bash
python examples/demo_arc_flash.py
```

Calculates arc flash results for three typical industrial buses (480 V MCC, 480 V main switchgear, 4.16 kV feeder) and prints a summary table with incident energy, arc flash boundary, and PPE category for each.

---

## Testing

```bash
pytest tests/ -v
```

The test suite covers `LoadSchedule` in detail: empty schedule edge cases, single/multi-load aggregation, vectorial kVA calculation, power factor correctness, 3-phase and 1-phase FLC, fluent interface, `remove_load`, input validation, and `to_dataframe` shape and values.

---

## Documentation

| Guide | Contents |
|---|---|
| [Arc Flash Guide](docs/arc_flash_guide.md) | IEEE 1584-2018 model, PPE category selection, AFB calculation, site application |
| [Cable Sizing Guide](docs/cable_sizing_guide.md) | NEC Article 310 methodology, derating factors, voltage drop, worked example |
| [Load Schedule Guide](docs/load_schedule_guide.md) | IEEE 141 demand/load/diversity factors, example industrial panel schedule |
| [ETAP Report Parsing](docs/etap_report_parsing.md) | How to export from ETAP, expected columns, version differences, troubleshooting |
| [Getting Started](docs/getting_started.md) | End-to-end tutorial: parse → calculate → size → report |

---

## Safety Notice

> **Arc flash is a life-threatening electrical hazard.**
>
> All calculations produced by this toolkit are for **engineering study and pre-planning purposes only**. They must be reviewed and approved by a **licensed professional electrical engineer** before being used to establish PPE requirements, label electrical equipment, or authorise live-work tasks.
>
> Arc flash labels must be produced in compliance with NFPA 70E and local regulatory requirements. No software tool — including ETAP itself — replaces the engineering judgement, site verification, and formal study documentation required by the standard.
>
> Before performing any energised electrical work:
> - Obtain a current arc flash hazard analysis signed by a licensed PE
> - Verify the protective device settings and clearing times match the study
> - Use PPE rated at or above the calculated incident energy
> - Follow your site's Electrical Safety Program and LOTO procedures

---

## Standards Referenced

- **IEEE Std 1584-2018** — Guide for Performing Arc Flash Hazard Calculations
- **NFPA 70E-2021** — Standard for Electrical Safety in the Workplace
- **NFPA 70 (NEC) 2023** — National Electrical Code (cable ampacity, voltage drop)
- **IEEE Std 141-1993 (Red Book)** — Recommended Practice for Electric Power Distribution for Industrial Plants
- **IEEE Std 242 (Buff Book)** — Recommended Practice for Protection and Coordination of Industrial and Commercial Power Systems

---

## License

MIT — see [LICENSE](LICENSE) for details.
