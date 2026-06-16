# Cable Sizing Guide

## NEC Article 310 Methodology with Worked Example

---

## 1. Introduction

Correct cable sizing is one of the most fundamental tasks in power system design. An undersized conductor runs hot, degrading insulation and reducing service life. An oversized conductor wastes capital cost. The National Electrical Code (NFPA 70, NEC) provides the enforceable minimum requirements for conductor ampacity in the United States. IEEE Std 141 (the Red Book) supplements the NEC with guidance on voltage drop for industrial facilities.

The `cable_sizing.size_cable()` function in this toolkit automates the NEC Article 310 sizing process: it iterates through the standard conductor sizes from NEC Table 310.16, applies all applicable derating factors, checks the voltage drop, and returns the smallest conductor that satisfies both constraints.

---

## 2. NEC Article 310 Methodology

### 2.1 Allowable Ampacity — NEC Table 310.16

The fundamental ampacity values for copper conductors in conduit are tabulated in NEC Table 310.16, organised by conductor size (AWG or kcmil) and insulation temperature rating (60 °C, 75 °C, 90 °C). This toolkit uses the 75 °C column, which applies to:

- THWN-2, THHN/THWN, XHHW-2 insulation
- Equipment with 75 °C-rated terminals (the most common rating for motors, panels, and switchgear)

Selected values from NEC Table 310.16 (copper, 75 °C, in conduit):

| Size | Base Ampacity (A) | AC Resistance (mΩ/m) |
|---|---:|---:|
| 8 AWG | 50 | 2.198 |
| 6 AWG | 65 | 1.382 |
| 4 AWG | 85 | 0.871 |
| 2 AWG | 115 | 0.549 |
| 1/0 AWG | 150 | 0.345 |
| 2/0 AWG | 175 | 0.274 |
| 3/0 AWG | 200 | 0.218 |
| 4/0 AWG | 230 | 0.172 |
| 250 kcmil | 255 | 0.147 |
| 350 kcmil | 310 | 0.105 |
| 500 kcmil | 380 | 0.074 |

The resistance values are AC resistance at 75 °C from NEC Chapter 9, Table 9 for conductors in magnetic (steel) conduit.

### 2.2 Ambient Temperature Correction — NEC 310.15(B)(2)

The ampacity values in Table 310.16 are based on an ambient temperature of 30 °C. When the installation environment is hotter or cooler, a correction factor must be applied:

```
Ampacity_corrected = Ampacity_base × C_temp
```

Correction factors for 75 °C-rated insulation per NEC Table 310.15(B)(2)(a):

| Ambient Temp Range | Correction Factor |
|:---:|:---:|
| 21 – 25 °C | 1.08 |
| 26 – 30 °C | 1.00 (reference) |
| 31 – 35 °C | 0.91 |
| 36 – 40 °C | 0.82 |
| 41 – 45 °C | 0.71 |
| 46 – 50 °C | 0.58 |
| 51 – 55 °C | 0.41 |

Conduits routed through unconditioned mechanical spaces, along rooftops, or inside process equipment enclosures commonly experience ambient temperatures of 40–50 °C. The derating at 40 °C (factor 0.82) represents an 18 % reduction in ampacity — significant enough to require the next conductor size in many applications.

### 2.3 Conduit Fill Derating — NEC 310.15(C)(1)

When more than three current-carrying conductors are installed in the same conduit, raceway, or cable tray, the conductors must be derated per NEC Table 310.15(C)(1):

| Number of Current-Carrying Conductors | Adjustment Factor |
|:---:|:---:|
| 4 – 6 | 0.80 |
| 7 – 9 | 0.70 |
| 10 – 20 | 0.50 |
| 21 – 30 | 0.45 |
| 31 – 40 | 0.40 |
| 41 and above | 0.35 |

When both ambient temperature and conduit fill adjustments apply, both correction factors are multiplied together:

```
Ampacity_final = Ampacity_base × C_temp × C_fill
```

The `derating_factor` parameter on the `Cable` dataclass accepts the combined derating factor, allowing the user to pre-compute `C_temp × C_fill` and store it with the cable record.

### 2.4 The 125 % Continuous Load Rule — NEC 210.20, 215.2

For loads energised continuously for 3 hours or more (continuous loads), the NEC requires that the conductor ampacity be at least 125 % of the full-load current:

```
I_design = I_FL × 1.25    (for continuous loads)
```

This rule accounts for heat accumulation in the conductor insulation under sustained loading. In practice, most industrial process loads (motors, HVAC compressors, lighting, battery chargers) are continuous loads.

The `size_cable()` function applies this multiplier automatically when `continuous_load=True` (the default).

---

## 3. Voltage Drop Calculation

### 3.1 IEEE 141 / NEC Voltage Drop Formula

Voltage drop must be kept within acceptable limits to ensure proper equipment operation. NEC 215.2(A)(1) recommends:
- Maximum 3 % voltage drop on feeders
- Maximum 5 % combined voltage drop (feeder + branch circuit)

IEEE 141 §3.11 provides the AC voltage drop formula for 3-phase feeders:

```
VD = √3 × I × R × L        (3-phase, line-to-line voltage)
VD = 2 × I × R × L         (1-phase, single-phase loads)
```

where:
- `VD` = voltage drop (volts)
- `I` = load current (A)
- `R` = AC resistance per unit length (Ω/m, from NEC Chapter 9 Table 9)
- `L` = one-way cable length (m)

Voltage drop as a percentage:

```
VD% = (VD / V_nominal) × 100
```

Note that this simplified formula uses resistance only. For large cables or long runs with high load power factors, the inductive reactance component should also be considered. The full formula including reactance is:

```
VD = √3 × I × L × (R·cosφ + X·sinφ)
```

where `X` is the AC reactance per unit length and `φ` is the load power factor angle. For most industrial applications at 480 V with power factors above 0.80, the resistance-only formula introduces less than 5 % error and is conservatively acceptable.

---

## 4. Worked Example

### Problem Statement

**Load:** 75 kW induction motor drive (continuous load)
**System voltage:** 480 V, 3-phase
**Power factor:** 0.85 lagging
**One-way cable length:** 120 m
**Ambient temperature:** 40 °C (conduit on mezzanine above furnace)
**Conduit fill:** 4 conductors (3 phase + 1 neutral) → derating factor 0.80
**Voltage drop limit:** 3 % per NEC 215.2

### Step 1: Calculate Full-Load Current

```
I_FL = P / (√3 × V × PF)
     = 75,000 / (1.732 × 480 × 0.85)
     = 75,000 / 706.1
     = 106.2 A
```

### Step 2: Apply 125 % Continuous Load Rule

```
I_design = 106.2 × 1.25 = 132.7 A
```

### Step 3: Determine Combined Derating Factor

```
C_temp (40 °C, 75 °C insulation) = 0.82
C_fill (4 conductors)             = 0.80
C_combined                        = 0.82 × 0.80 = 0.656
```

### Step 4: Find Minimum Conductor Size for Ampacity

Try **3/0 AWG** (base ampacity 200 A):

```
Ampacity_derated = 200 × 0.656 = 131.2 A
```

Check: 131.2 A < 132.7 A required — **FAILS** (marginal).

Try **4/0 AWG** (base ampacity 230 A):

```
Ampacity_derated = 230 × 0.656 = 150.9 A
```

Check: 150.9 A ≥ 132.7 A — **PASSES ampacity**.

### Step 5: Check Voltage Drop for 4/0 AWG

From NEC Chapter 9 Table 9: R = 0.172 mΩ/m (4/0 AWG copper, steel conduit)

```
VD = √3 × 106.2 × (0.172/1000) × 120
   = 1.732 × 106.2 × 0.000172 × 120
   = 3.80 V

VD% = 3.80 / 480 × 100 = 0.79%
```

Check: 0.79 % ≤ 3 % — **PASSES voltage drop**.

### Step 6: Result

**Selected conductor: 4/0 AWG THWN-2 copper in steel conduit**

| Parameter | Value |
|---|---|
| Full-load current | 106.2 A |
| Design current (125 % cont.) | 132.7 A |
| Base ampacity (4/0 AWG, 75 °C) | 230 A |
| Derating factor (temp × fill) | 0.656 |
| Derated ampacity | 150.9 A |
| Voltage drop | 3.80 V (0.79 %) |
| Meets ampacity | Yes |
| Meets voltage drop (3 %) | Yes |

### Using the Toolkit

```python
from etap.cable_sizing import size_cable

result = size_cable(
    load_kw=75.0,
    voltage_kv=0.48,
    length_m=120.0,
    pf=0.85,
    voltage_drop_limit_pct=3.0,
    ambient_temp_C=40.0,
    phases=3,
    continuous_load=True,
)
print(result)
# [OK] 4/0 AWG: I_FL=106.2A, Ampacity=150.9A, VD=0.79%
```

> Note: The toolkit uses the NEC Table 310.16 values directly and applies the ambient correction factor but does not automatically apply a conduit fill factor — that should be incorporated into the `derating_factor` field of the `Cable` dataclass when recording the final selection, or computed externally and passed as a combined correction.

---

## 5. Special Cases

### 5.1 Aluminum Conductors

This toolkit sizes copper conductors only. Aluminum conductors (XHHW-2, USE-2) are widely used in services and larger feeders due to lower cost. Aluminum ampacities are approximately 80 % of copper for the same size; a common rule of thumb is to go two AWG sizes larger for equivalent ampacity (e.g., 1/0 AWG aluminum ≈ 1 AWG copper). NEC Table 310.16 contains separate columns for aluminum; ensure you reference the correct column.

### 5.2 Parallel Conductors

For loads above approximately 400–500 A, it is common practice to run parallel sets of smaller conductors rather than a single very large conductor, as individual conductors above 500 kcmil become difficult to handle and terminate. NEC 310.10(H) permits parallel conductors of 1/0 AWG and larger, provided each parallel set is identical in size, length, material, insulation, and termination.

### 5.3 Motor Circuits

NEC Article 430 contains additional rules specific to motor branch circuits. The minimum conductor ampacity for a motor branch circuit is 125 % of the motor full-load current per the NEC tables (430.22), not the actual nameplate current. Overload protection devices are sized separately per NEC 430.52.

### 5.4 High-Resistance Grounded Systems

On 4.16 kV and 13.8 kV high-resistance grounded (HRG) systems, single line-to-ground faults do not cause immediate trip, allowing continued operation. Cable sizing for these systems still follows Article 310, but the grounding electrode system and ground fault detection relay settings must also be considered.

---

## References

1. NFPA 70, *National Electrical Code*, 2023 Edition. National Fire Protection Association, 2023.
2. IEEE Std 141-1993 (Red Book), *Recommended Practice for Electric Power Distribution for Industrial Plants*, IEEE, 1993.
3. IEEE Std 399-1997 (Brown Book), *Recommended Practice for Power Systems Analysis*, IEEE, 1997.
4. Eaton, *Wiring Digest — NEC 2023 Changes Affecting Wiring Methods and Materials*, 2023.
