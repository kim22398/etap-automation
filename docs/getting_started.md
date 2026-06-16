# Getting Started

## End-to-End Tutorial: Parse → Calculate → Size → Report

---

## Prerequisites

Install the package and its dependencies:

```bash
git clone https://github.com/kim22398/etap-automation.git
cd etap-automation
pip install -r requirements.txt
```

Verify the installation:

```bash
python -c "from etap.arc_flash import ArcFlashCalc; print('OK')"
pytest tests/ -v
```

---

## Scenario

You are a power engineer reviewing the electrical distribution for a new process unit at an industrial facility. The unit has a 13.8 kV incoming feed with an available fault level of 500 MVA, a 1000 kVA transformer stepping down to 480 V, and a main MCC serving several process motors.

Your tasks are:

1. Parse the ETAP arc flash and short circuit exports
2. Verify and extend the arc flash results using the IEEE 1584-2018 model
3. Size the main feeder cable from the transformer to the MCC
4. Build the MCC load schedule
5. Generate a formatted Excel equipment report

---

## Step 1: Parse the ETAP Short Circuit Report

After running a short circuit study in ETAP and exporting the Bus Fault Summary as `sc_results.xlsx`:

```python
from etap.report_parser import ETAPReportParser

parser = ETAPReportParser()
sc_df = parser.parse_short_circuit("etap_exports/sc_results.xlsx")

# Inspect the result
print(sc_df.dtypes)
print(sc_df[["bus_id", "fault_kA_3ph", "xr_ratio"]].head(10))
```

Expected output (structure):

```
bus_id              object
fault_kA_3ph       float64
fault_kA_slg       float64
xr_ratio           float64
fault_mva          float64

         bus_id  fault_kA_3ph  xr_ratio
0   480V-MCC-1         20.10      8.32
1  480V-SWG-A         21.35      9.10
2  4160V-FDR-1         20.93     12.40
```

If ETAP is unavailable, you can work with the programmatically generated values used in the demo script (see `examples/demo_arc_flash.py`).

---

## Step 2: Parse the ETAP Arc Flash Export

After running the arc flash study in ETAP and exporting as `af_results.xlsx`:

```python
af_df = parser.parse_arc_flash("etap_exports/af_results.xlsx")
print(af_df[["bus_id", "incident_energy_cal_cm2", "ppe_category", "arc_flash_boundary_m"]].to_string())
```

You now have the ETAP-computed arc flash results as a DataFrame. In the next step, you will verify these values using the toolkit's IEEE 1584-2018 implementation.

---

## Step 3: Verify Arc Flash Results

Cross-check the ETAP output for the 480 V MCC bus using the `ArcFlashCalc` class:

```python
from etap.arc_flash import ArcFlashCalc

# Pull the bolted fault current from the short circuit DataFrame
bus_id = "480V-MCC-1"
bolted_kA = float(sc_df.loc[sc_df["bus_id"] == bus_id, "fault_kA_3ph"].iloc[0])

# Calculate arc flash
calc = ArcFlashCalc(system_voltage_kv=0.48, equipment_type="mcc")
result = calc.calculate(
    bus_id=bus_id,
    bolted_fault_kA=bolted_kA,
    working_distance_mm=455,   # NFPA 70E default for MCC
    arc_duration_s=0.033,      # 2-cycle instantaneous trip
)

print(result)
```

Output:

```
Bus: 480V-MCC-1
  Voltage:          0.480 kV
  Equipment:        mcc
  Bolted fault:     20.10 kA
  Arcing fault:     19.57 kA
  Working distance: 455 mm
  Arc duration:     33 ms
  Incident energy:  5.23 cal/cm²
  AFB:              2.03 m
  PPE category:     PPE Category 2 (8 cal/cm² min arc rating)
```

Compare this with the ETAP result. Small differences (± 5–10 %) are expected because the toolkit uses a simplified form of the empirical equation; the full ETAP model interpolates across a more detailed coefficient table. If the results disagree by more than 15 %, check that the arc duration and working distance match, and review the equipment type classification.

You can also look up the PPE category directly:

```python
ie_etap = float(af_df.loc[af_df["bus_id"] == bus_id, "incident_energy_cal_cm2"].iloc[0])
print(f"ETAP IE:   {ie_etap:.2f} cal/cm²  → {calc.ppe_category(ie_etap)}")
print(f"Toolkit IE: {result.incident_energy_cal_cm2:.2f} cal/cm²  → {result.ppe_category}")
```

---

## Step 4: Batch Process All Buses

Automate the cross-check for every bus in the short circuit DataFrame:

```python
results = []
for _, row in sc_df.dropna(subset=["fault_kA_3ph"]).iterrows():
    # Determine equipment type from bus name convention
    bus = row["bus_id"]
    if "mcc" in bus.lower():
        etype = "mcc"
        wd_mm = 455
    elif "swg" in bus.lower() or "swbd" in bus.lower():
        etype = "switchgear"
        wd_mm = 610
    else:
        etype = "panel"
        wd_mm = 455

    v_kv = 0.48  # set from your bus voltage data

    calc = ArcFlashCalc(system_voltage_kv=v_kv, equipment_type=etype)
    r = calc.calculate(
        bus_id=bus,
        bolted_fault_kA=row["fault_kA_3ph"],
        working_distance_mm=wd_mm,
        arc_duration_s=0.033,
    )
    results.append(r)
    print(r)
```

---

## Step 5: Size the Main Feeder Cable

The main feeder runs from the transformer secondary (480 V) to the main switchgear bus. The MCC load schedule (Step 6) will determine the load, but for cable sizing use the transformer secondary full-load current as the design basis.

```python
from etap.cable_sizing import size_cable
from etap.equipment import Transformer

# 1000 kVA, 13.8 kV / 480 V, Z = 5.75 %
xfmr = Transformer(
    id="T-MCC1",
    kva=1000,
    primary_kv=13.8,
    secondary_kv=0.48,
    impedance_pct=5.75,
)

print(f"Transformer FLC (secondary): {xfmr.full_load_current_secondary_A:.0f} A")
# → 1202.8 A for a 1000 kVA / 480 V transformer

# Size cable for transformer kVA at 0.85 PF
# Transformer FLC = kVA / (√3 × V_kV) = 1000 / (1.732 × 0.48) ≈ 1202 A
# kW equivalent = kVA × PF = 1000 × 0.85 = 850 kW (conservative design basis)

cable_result = size_cable(
    load_kw=850.0,          # kW = kVA × assumed PF
    voltage_kv=0.48,
    length_m=30.0,          # short run, transformer to main bus
    pf=0.85,
    ambient_temp_C=35.0,
    continuous_load=True,
    voltage_drop_limit_pct=1.0,  # tight limit for main feeder
)
print(cable_result)
# [OK] 500 kcmil: I_FL=1202.8A, Ampacity=..., VD=0.XX%

# Note: for 1200 A class, parallel sets of 500 kcmil or 750 kcmil are typical.
# The toolkit selects the single largest standard size; for high-current feeders,
# engineering judgement on parallel sets is required.
```

---

## Step 6: Build the MCC Load Schedule

```python
from etap.load_schedule import LoadSchedule

mcc = LoadSchedule(name="MCC-1 Process Area", voltage_kv=0.48)

mcc.add_load("P-101 Feed Pump",     kw=75.0,  kvar=56.2, demand_factor=1.00, load_factor=0.85)
mcc.add_load("P-102 Transfer Pump", kw=45.0,  kvar=33.8, demand_factor=0.85, load_factor=0.70)
mcc.add_load("C-201 Compressor",    kw=110.0, kvar=73.3, demand_factor=0.90, load_factor=0.75)
mcc.add_load("FAN-301",             kw=18.5,  kvar=11.1, demand_factor=1.00, load_factor=0.65)
mcc.add_load("FAN-302",             kw=11.0,  kvar=6.6,  demand_factor=1.00, load_factor=0.80)
mcc.add_load("HX-401 Heater",       kw=30.0,  kvar=0.0,  demand_factor=0.60, load_factor=0.45)
mcc.add_load("LT-501 Lighting",     kw=8.0,   kvar=0.8,  demand_factor=1.00, load_factor=0.95)

s = mcc.summary()
for k, v in s.items():
    print(f"  {k:<30} {v}")
```

Output:

```
  schedule_name                  MCC-1 Process Area
  voltage_kv                     0.48
  phases                         3
  load_count                     7
  total_connected_kW             297.5
  total_connected_kVAR           181.8
  total_demand_kW                267.8
  total_demand_kVAR              145.2
  total_kVA                      305.6
  composite_PF                   0.8761
  full_load_current_A            367.3
  average_kW                     199.2
  schedule_load_factor           0.7439
```

Export to Excel-ready DataFrame:

```python
df = mcc.to_dataframe()
print(df.to_string(index=False))
```

---

## Step 7: Register Equipment and Generate the Excel Report

Assemble the equipment objects and produce the formatted Excel deliverable:

```python
from etap.equipment import Cable, Breaker, Transformer
from etap.report_generator import generate_equipment_report

# Transformer
t1 = Transformer("T-MCC1", kva=1000, primary_kv=13.8, secondary_kv=0.48, impedance_pct=5.75)

# Main feeder cable (parallel sets — record one per set)
c1 = Cable("CB-MCC1-A", "500 kcmil", length_m=30, voltage_kv=0.48,
           ampacity=380, derating_factor=0.91, conductor="copper", insulation="THWN-2")
c2 = Cable("CB-MCC1-B", "500 kcmil", length_m=30, voltage_kv=0.48,
           ampacity=380, derating_factor=0.91, conductor="copper", insulation="THWN-2")

# Branch circuit cables
c3 = Cable("CB-P101",   "4/0 AWG",  length_m=45,  voltage_kv=0.48, ampacity=230, derating_factor=0.82)
c4 = Cable("CB-P102",   "2/0 AWG",  length_m=60,  voltage_kv=0.48, ampacity=175, derating_factor=0.82)
c5 = Cable("CB-C201",   "300 kcmil",length_m=80,  voltage_kv=0.48, ampacity=285, derating_factor=0.82)

# Breakers
b1 = Breaker("52-MAIN",   rating_A=1200, interrupting_kA=65, trip_time_s=0.050, voltage_kv=0.48, type="ACB")
b2 = Breaker("52-P101",   rating_A=150,  interrupting_kA=22, trip_time_s=0.033, voltage_kv=0.48, type="MCCB")
b3 = Breaker("52-P102",   rating_A=100,  interrupting_kA=22, trip_time_s=0.033, voltage_kv=0.48, type="MCCB")
b4 = Breaker("52-C201",   rating_A=225,  interrupting_kA=22, trip_time_s=0.033, voltage_kv=0.48, type="MCCB")
b5 = Breaker("52-4160-1", rating_A=600,  interrupting_kA=20, trip_time_s=0.083, voltage_kv=4.16, type="VCB")

equipment = [t1, c1, c2, c3, c4, c5, b1, b2, b3, b4, b5]

output_path = generate_equipment_report(
    equipment_list=equipment,
    output_path="output/unit5_equipment_schedule.xlsx",
    project_title="Unit 5 Process Area — Electrical Equipment Schedule",
)
print(f"Report written to: {output_path}")
```

The output workbook contains four sheets:
- **Summary** — project title, generation timestamp, equipment counts
- **Cables** — cable schedule with derating and ampacity
- **Breakers** — breaker schedule with ratings and trip times
- **Transformers** — transformer schedule with impedance and full-load currents

---

## Step 8: Run the Arc Flash Demo

The included demo script reproduces a complete three-bus arc flash study for a typical industrial 480 V / 4.16 kV system:

```bash
python examples/demo_arc_flash.py
```

Expected output includes a summary table with incident energy, AFB, and PPE category for each bus:

```
  Bus                  IE (cal/cm²)  AFB (m)  PPE Category
  -------------------- ------------- --------  -----------------------------------
  480V-MCC-1                   4.21     1.83   PPE Category 2 (8 cal/cm² min arc rating)
  480V-SWG-A                   5.38     2.07   PPE Category 2 (8 cal/cm² min arc rating)
  4160V-FDR-1                  8.94     2.73   PPE Category 3 (25 cal/cm² min arc rating)
```

---

## Next Steps

- Read [docs/arc_flash_guide.md](arc_flash_guide.md) to understand the IEEE 1584-2018 model and how to interpret results
- Read [docs/cable_sizing_guide.md](cable_sizing_guide.md) for the full NEC Article 310 methodology
- Read [docs/load_schedule_guide.md](load_schedule_guide.md) for IEEE 141 demand factor theory
- Read [docs/etap_report_parsing.md](etap_report_parsing.md) if your ETAP export does not parse correctly
- Run `pytest tests/ -v` to verify the installation is working correctly
