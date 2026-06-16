# Load Schedule Guide

## IEEE 141 Demand Factor, Load Factor, and Diversity Factor for Industrial Facilities

---

## 1. Introduction

An electrical load schedule (also called a load list or panel schedule) is the foundational document for sizing electrical distribution equipment — transformers, switchgear, MCC buses, feeders, and service entrances. An incorrect or poorly structured load schedule leads to oversized (wasteful) or undersized (dangerous) electrical infrastructure.

IEEE Std 141, *Recommended Practice for Electric Power Distribution for Industrial Plants*, defines the statistical factors that relate the theoretical maximum (connected) load to the realistic operating demand. This guide explains these factors, shows how to build a load schedule for an industrial facility, and demonstrates the `LoadSchedule` class.

---

## 2. Key Definitions

### 2.1 Connected Load

The **connected load** is the sum of the nameplate ratings of all electrical loads served by a circuit or system. It represents the theoretical maximum if every load operated simultaneously at full rated capacity. In practice, no industrial system ever operates at 100 % of connected load.

```
Connected Load = Σ (nameplate kW of all loads)
```

### 2.2 Demand Factor

The **demand factor** (DF) is the ratio of the maximum demand of a system (or part of a system) to the total connected load of that system:

```
Demand Factor = Maximum Demand / Total Connected Load
```

Demand factors are applied per load or per group to account for loads that are:
- Not all running simultaneously (e.g., one of two pumps is a standby)
- Typically operated at less than full nameplate rating (e.g., a variable-speed drive at 70 % speed)
- Intermittent in nature (e.g., a crane, welder, or batch process)

Typical demand factors for industrial loads (from IEEE 141 Table 3-1):

| Load Type | Typical Demand Factor |
|---|---|
| Continuous process motors | 0.85 – 1.00 |
| HVAC compressors | 0.80 – 0.95 |
| Lighting (fluorescent/LED) | 0.90 – 1.00 |
| Welding equipment | 0.40 – 0.70 |
| Cranes and hoists | 0.25 – 0.50 |
| Batch process motors (one of N) | 1/N to 0.75 |
| Office receptacles | 0.10 – 0.50 |

### 2.3 Load Factor

The **load factor** (LF) is the ratio of the average load to the peak (demand) load over a defined period (usually one hour, one day, or one year):

```
Load Factor = Average Load / Peak Demand
```

A high load factor (close to 1.0) means the load is relatively constant over time. A low load factor indicates a peaky load profile. Load factor is used for:
- Sizing distribution transformers (energy-based sizing vs. demand-based)
- Calculating energy costs (kWh billing vs. kVA demand billing)
- Estimating transformer loss-of-life

### 2.4 Diversity Factor

The **diversity factor** (DF_div) is the ratio of the sum of individual peak demands to the coincident (simultaneous) peak demand of the group:

```
Diversity Factor = Σ (individual peak demands) / Coincident group peak demand
```

The diversity factor is always ≥ 1.0 because the individual peaks rarely occur at the same instant. It is essentially the reciprocal of the demand factor applied at the system level.

Example: If three feeders have individual peak demands of 200 kW, 150 kW, and 100 kW, but they never all peak simultaneously and the transformer peak is only 350 kW:

```
Diversity Factor = (200 + 150 + 100) / 350 = 1.29
```

### 2.5 Relationship Between Factors

```
System Demand = Connected Load / Diversity Factor
             = Connected Load × (1 / Diversity Factor)
             = Σ (Connected_i × Demand_Factor_i)   [when diversity is built in]
```

IEEE 141 §3.4 notes that when individual demand factors are applied to each load, the system diversity is implicitly captured by those factors, and a separate diversity factor should not be double-applied.

---

## 3. Building a Load Schedule for an Industrial Facility

### Step 1: Enumerate All Loads

Start with the equipment list from the P&ID (process and instrumentation diagram) and electrical area classification drawings. For each load record:

- Tag number (instrument/equipment number)
- Description
- Nameplate kW (or HP × 0.746 for motors)
- Power factor (from manufacturer data sheet, or use defaults: motors 0.85, lighting 0.95)
- Demand factor (from IEEE 141 table or engineering judgement)
- Load factor (from process schedule or operational data)
- Bus / panel assignment

### Step 2: Assign to Buses

Group loads by their physical MCC or panel. Each MCC or distribution panel becomes a `LoadSchedule` object.

### Step 3: Calculate Bus Totals

For each MCC/panel bus, sum the demand kW, demand kVAR, and compute the kVA and power factor. This determines the bus full-load current and the required transformer kVA.

### Step 4: Aggregate to Substation Level

Sum the MCC bus demands to determine the main switchgear loading and the total facility demand. Apply diversity factors where appropriate to account for the fact that all MCCs will not simultaneously be at their individual peak demands.

---

## 4. Example Industrial Panel Schedule

The following example represents a 480 V MCC serving a typical process area in an industrial facility. This schedule can be reproduced using the `LoadSchedule` class.

### MCC-A1 — Process Area Motor Control Centre (480 V, 3-Phase)

| Tag | Description | kW | kVAR | PF | DF | LF | Demand kW | Demand kVA |
|---|---|---:|---:|:---:|:---:|:---:|---:|---:|
| P-101A | Feed pump A (duty) | 75.0 | 56.2 | 0.80 | 1.00 | 0.85 | 75.0 | 93.8 |
| P-101B | Feed pump B (standby) | 75.0 | 56.2 | 0.80 | 0.00 | — | 0.0 | 0.0 |
| P-102 | Transfer pump | 45.0 | 33.8 | 0.80 | 0.85 | 0.70 | 38.3 | 47.8 |
| C-201 | Compressor | 110.0 | 73.3 | 0.83 | 0.90 | 0.75 | 99.0 | 118.8 |
| FAN-301 | Cooling fan | 18.5 | 11.1 | 0.86 | 1.00 | 0.65 | 18.5 | 21.5 |
| FAN-302 | Exhaust fan | 11.0 | 6.6 | 0.86 | 1.00 | 0.80 | 11.0 | 12.8 |
| HX-401 | Electric heater | 30.0 | 0.0 | 1.00 | 0.60 | 0.45 | 18.0 | 18.0 |
| LT-501 | Area lighting | 8.0 | 0.8 | 0.99 | 1.00 | 0.95 | 8.0 | 8.1 |

**DF = Demand Factor, LF = Load Factor. Standby pump (P-101B) assigned DF = 0 as only one pump operates at a time.**

### Schedule Totals

| Quantity | Value |
|---|---|
| Total connected kW | 372.5 kW |
| Total demand kW | 267.8 kW |
| Total demand kVAR | 145.2 kVAR |
| Total demand kVA | 305.6 kVA |
| Composite power factor | 0.876 lagging |
| Full-load current (480 V, 3Ø) | 367 A |
| Recommended MCC bus rating | 400 A (next standard size) |
| Recommended transformer kVA | 400 kVA (305.6 / 0.80 safety margin) |

### Reproducing with the Toolkit

```python
from etap.load_schedule import LoadSchedule

mcc = LoadSchedule(name="MCC-A1", voltage_kv=0.48)

mcc.add_load("P-101A Feed Pump (duty)",   kw=75.0,  kvar=56.2, demand_factor=1.00, load_factor=0.85)
# P-101B is standby — excluded (demand_factor=0 is not allowed; simply omit standby loads)
mcc.add_load("P-102 Transfer Pump",        kw=45.0,  kvar=33.8, demand_factor=0.85, load_factor=0.70)
mcc.add_load("C-201 Compressor",           kw=110.0, kvar=73.3, demand_factor=0.90, load_factor=0.75)
mcc.add_load("FAN-301 Cooling Fan",        kw=18.5,  kvar=11.1, demand_factor=1.00, load_factor=0.65)
mcc.add_load("FAN-302 Exhaust Fan",        kw=11.0,  kvar=6.6,  demand_factor=1.00, load_factor=0.80)
mcc.add_load("HX-401 Electric Heater",     kw=30.0,  kvar=0.0,  demand_factor=0.60, load_factor=0.45)
mcc.add_load("LT-501 Area Lighting",       kw=8.0,   kvar=0.8,  demand_factor=1.00, load_factor=0.95)

s = mcc.summary()
print(f"Total demand kW:    {s['total_demand_kW']:.1f} kW")
print(f"Total demand kVA:   {s['total_kVA']:.1f} kVA")
print(f"Composite PF:       {s['composite_PF']:.3f}")
print(f"Full-load current:  {s['full_load_current_A']:.0f} A")
print(f"Average kW:         {s['average_kW']:.1f} kW")
print(f"Schedule load factor: {s['schedule_load_factor']:.3f}")

# Export to pandas DataFrame for further analysis or Excel output
df = mcc.to_dataframe()
print(df[["Name", "Demand_kW", "Demand_kVA", "Average_kW"]].to_string(index=False))
```

---

## 5. Substation-Level Aggregation

Once individual MCC schedules are complete, aggregate them to the substation level:

```python
# Hypothetical multi-MCC facility
# Each MCC was sized as above; here we record the demand totals
import math

mccs = [
    {"name": "MCC-A1 Process Area",    "demand_kw": 267.8, "demand_kvar": 145.2},
    {"name": "MCC-A2 Utilities",        "demand_kw": 180.0, "demand_kvar": 110.0},
    {"name": "MCC-B1 Packaging",        "demand_kw": 95.0,  "demand_kvar": 45.0},
    {"name": "MCC-B2 Warehouse",        "demand_kw": 40.0,  "demand_kvar": 5.0},
]

# Sum of individual MCC demands (before diversity)
total_kw   = sum(m["demand_kw"]   for m in mccs)   # 582.8 kW
total_kvar = sum(m["demand_kvar"] for m in mccs)   # 305.2 kVAR
total_kva  = math.sqrt(total_kw**2 + total_kvar**2)  # 657.2 kVA

# Apply diversity factor at the substation level (IEEE 141 §3.4)
# Diversity factor of 1.15 means coincident peak is 582.8 / 1.15 = 506.8 kW
diversity_factor = 1.15
coincident_kw = total_kw / diversity_factor

print(f"Sum of MCC demands:    {total_kw:.0f} kW  /  {total_kva:.0f} kVA")
print(f"Diversity factor:      {diversity_factor}")
print(f"Coincident demand:     {coincident_kw:.0f} kW")
print(f"Recommended main SWGR: 800 A at 480 V  (covers {coincident_kw:.0f} kW / 0.876 PF)")
```

---

## 6. Common Pitfalls

### 6.1 Double-Counting Diversity

If individual demand factors are carefully assigned per load, the diversity is already embedded. Applying an additional system-level diversity factor will undersize the equipment.

### 6.2 Ignoring Future Growth

NEC 220.14 and good engineering practice recommend sizing infrastructure with a growth margin. A common rule is to add 20–25 % spare capacity to the main switchgear and transformer, and to leave 20 % spare breaker slots in each MCC.

### 6.3 Using HP Instead of kW

Motor nameplate ratings in North America are in horsepower. Convert using: `kW = HP × 0.746`. However, for load schedule purposes, use the *input* kW (shaft output / motor efficiency), not the shaft horsepower. For a 75 HP motor with 95 % efficiency: input kW = 75 × 0.746 / 0.95 = 58.9 kW (not 55.95 kW from nameplate HP alone).

### 6.4 Power Factor Assumptions

Where manufacturer data is unavailable, use these conservative defaults:
- NEMA Design B induction motors > 10 HP: PF = 0.85
- Lighting (LED drivers): PF = 0.90–0.95
- Electric heaters and resistive loads: PF = 1.00
- Variable frequency drives (VFDs): PF ≈ 0.95 (input, at drive terminals)

---

## References

1. IEEE Std 141-1993, *Recommended Practice for Electric Power Distribution for Industrial Plants (Red Book)*, IEEE, 1993.
2. NFPA 70, *National Electrical Code*, 2023 Edition, Article 220.
3. R. Beeman, Ed., *Industrial Power Systems Handbook*, McGraw-Hill, 1955.
4. Eaton, *Consulting Application Guide: Load Scheduling and Demand Factor Analysis*, Eaton Corporation, 2019.
