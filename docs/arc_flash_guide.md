# Arc Flash Hazard Analysis Guide

## IEEE 1584-2018 Theory and Site Application

---

## 1. Background and Regulatory Context

An arc flash is the sudden release of electrical energy through air when insulation or isolation between energised conductors fails. The resulting plasma fireball can reach temperatures exceeding 35,000 °F (19,400 °C) — approximately four times the surface temperature of the sun — generating intense radiant heat, pressure waves, molten metal droplets, and toxic vapours. Even brief exposure can cause severe burns, blast trauma, or death.

NFPA 70E, *Standard for Electrical Safety in the Workplace*, requires employers to perform an arc flash risk assessment before any employee performs work on or near energised equipment (NFPA 70E-2021 §130.5). The quantitative method for this assessment is IEEE Std 1584-2018, *Guide for Performing Arc Flash Hazard Calculations*.

---

## 2. IEEE 1584-2018 Model Overview

The 2018 edition replaced the 2002 model after an extensive multi-year research programme that compiled over 1,800 laboratory arc flash tests across a range of voltages (208 V – 15 kV), electrode configurations, enclosure types, and electrode gaps. The resulting empirical model is significantly more accurate than the 2002 version, particularly for low-voltage (< 1 kV) systems.

### 2.1 Equipment Configurations

IEEE 1584-2018 defines five electrode configurations, each modelling a different type of electrical equipment:

| Code | Configuration | Typical Equipment |
|------|--------------|-------------------|
| VCB | Vertical electrodes in a box | Low-voltage switchgear |
| VCBB | Vertical electrodes in a box with a barrier | Switchboard |
| HCB | Horizontal electrodes in a box | MCC, panelboard |
| VOA | Vertical electrodes in open air | Open bus, disconnect |
| HOA | Horizontal electrodes in open air | Open bus |

The toolkit uses the VCB/HCB/VCBB configurations, matching the equipment type to the `equipment_type` parameter of `ArcFlashCalc`.

### 2.2 Arcing Current Calculation

Before incident energy can be calculated, the arcing fault current must be estimated from the bolted (3-phase symmetrical) fault current. IEEE 1584-2018 provides polynomial equations for this conversion.

**For low-voltage systems (< 1 kV):**

```
log10(Ia) = 0.00402 + 0.983 × log10(Ibf)
```

where `Ia` = arcing current (kA) and `Ibf` = bolted fault current (kA).

**For medium-voltage systems (1–15 kV):**

The arcing current is very close to the bolted fault current. A conservative reduction factor of 0.95 is commonly applied:

```
Ia ≈ 0.95 × Ibf
```

**Critical requirement — two current calculation:** IEEE 1584-2018 mandates calculating incident energy at both the estimated arcing current (`Ia`) and a reduced arcing current (`0.85 × Ia` or as determined by the standard). This is because a lower arcing current may result in a slower protective device response, longer arc duration, and therefore higher incident energy. Engineers must use the worst-case result from both calculations.

### 2.3 Incident Energy Equation

The incident energy at a given working distance is calculated using a log-linear empirical equation. The simplified (single-voltage) form used in this toolkit is:

```
log10(E) = C1 + C2 × log10(Ia) + C3 × log10(t) − C4 × log10(D)
```

where:
- `E` = incident energy at working distance (cal/cm²)
- `Ia` = arcing current (kA)
- `t` = arc duration / clearing time (seconds)
- `D` = working distance from the arc point (mm)
- `C1, C2, C3, C4` = empirical coefficients from IEEE 1584-2018 Table 3 (vary by voltage class and electrode configuration)

For the common 480 V / VCB case, the approximate coefficients are:

| Coefficient | Value | Meaning |
|---|---|---|
| C1 | 0.753 | Log-scale intercept |
| C2 | 0.566 | Arcing current exponent |
| C3 | 1.648 | Time exponent (energy scales nearly linearly with time) |
| C4 | 0.084 | Distance exponent (inverse: longer distance = lower energy) |

A voltage correction factor is then applied to account for the actual system voltage relative to the 480 V reference test conditions.

### 2.4 Arc Duration

The arc duration `t` is determined by the time-current curve (TCC) of the upstream protective device at the calculated arcing fault current. This is a critical input:

- **Instantaneous trip (MCCB):** typically 2 cycles = 33 ms at 60 Hz
- **Short-time delay (ACB, vacuum breaker):** may be 3–30 cycles depending on trip settings
- **Fuse:** determined from the published TCC at the arcing current
- **Relay + breaker:** relay operating time + breaker interrupting time

If the protective device does not clear at the arcing current (e.g., the arcing current falls below the instantaneous pickup), the arc can persist for many seconds, resulting in very high incident energy. This is a common finding in low-voltage 480 V systems where the arcing current can be significantly less than the bolted fault current.

### 2.5 Working Distance

The working distance is the distance from the arc source to the worker's face and chest. IEEE 1584-2018 specifies default working distances for common equipment types:

| Equipment Type | Default Working Distance |
|---|---|
| Low-voltage switchgear (VCB) | 610 mm (24 in) |
| Switchboard (VCBB) | 455 mm (18 in) |
| MCC / panel (HCB) | 455 mm (18 in) |
| Cable junction box | 455 mm (18 in) |
| Medium-voltage switchgear | 910 mm (36 in) |

Engineers may use site-specific distances where task analysis confirms the actual working distance differs from the default.

---

## 3. Arc Flash Boundary (AFB)

The arc flash boundary (also called the flash protection boundary) is the distance from the arc source at which the incident energy equals 1.2 cal/cm². This value is the Stoll skin model threshold for the onset of a second-degree burn in one second.

Anyone inside the AFB must wear appropriate PPE. Anyone outside the AFB is at low risk of burn injury but may still be exposed to pressure waves, sound, and arc blast.

The AFB is calculated by inverting the incident energy equation to solve for distance:

```
AFB = D_ref × sqrt(E / 1.2)
```

where `D_ref` is the reference working distance (mm) and `E` is the incident energy at that distance (cal/cm²). This simplified inverse-square relationship assumes a point source; the full IEEE 1584-2018 model uses the distance exponent from the empirical coefficients.

---

## 4. PPE Category Selection (NFPA 70E Table 130.5(G))

Once the incident energy is known, PPE is selected per NFPA 70E-2021 Table 130.5(G):

| PPE Category | Incident Energy Range | Minimum Required Arc Rating |
|:---:|:---:|:---:|
| 1 | 1.2 – < 4 cal/cm² | 4 cal/cm² |
| 2 | 4 – < 8 cal/cm² | 8 cal/cm² |
| 3 | 8 – < 25 cal/cm² | 25 cal/cm² |
| 4 | 25 – 40 cal/cm² | 40 cal/cm² |
| Danger | > 40 cal/cm² | De-energise — no PPE provides adequate protection |

### PPE Category 1 — Minimum Protection
- Arc-rated shirt and pants or coverall (≥ 4 cal/cm²)
- Arc-rated face shield or arc flash suit hood
- Safety glasses, hard hat Class E
- Leather gloves or rubber insulating gloves with leather protectors

### PPE Category 2 — Standard Protection
- Arc-rated shirt and pants or coverall (≥ 8 cal/cm²)
- Arc flash suit hood
- Safety glasses, hard hat Class E
- Rubber insulating gloves with leather protectors, Class 00 or Class 0

### PPE Category 3 — Heavy Protection
- Arc-rated coverall or jacket/pants (≥ 25 cal/cm²), double-layer system
- Arc flash suit hood rated ≥ 25 cal/cm²
- Safety glasses, hard hat Class E
- Rubber insulating gloves with leather protectors, Class 2

### PPE Category 4 — Maximum Protection
- Arc-rated suit (multi-layer, ≥ 40 cal/cm²)
- Arc flash suit hood
- Safety glasses, hard hat Class E
- Rubber insulating gloves with leather protectors, Class 2

> **Note:** For incident energy above 40 cal/cm², the task must be re-evaluated. Consideration should be given to remote operation, de-energising the equipment, or engineering controls to reduce the hazard level before any work is performed.

---

## 5. Practical Site Application Steps

Performing a compliant arc flash study requires the following steps, of which this toolkit automates steps 4–7:

### Step 1: Collect System Data
Gather the one-line diagram, transformer nameplate data (kVA, Z%), utility fault contribution (MVA available at the point of common coupling), and short circuit study results for each bus.

### Step 2: Verify Protective Device Settings
Obtain the current trip settings for all upstream circuit breakers, fuses, and relays. Verify settings match the coordination study and that instantaneous elements are enabled where applicable.

### Step 3: Run Short Circuit Study in ETAP
Generate bolted fault currents (3LG and SLG) for each bus. Export the results as CSV or Excel.

### Step 4: Parse ETAP Output
```python
from etap.report_parser import ETAPReportParser
parser = ETAPReportParser()
sc_df = parser.parse_short_circuit("etap_sc_results.xlsx")
```

### Step 5: Calculate Arcing Current and Incident Energy
```python
from etap.arc_flash import ArcFlashCalc

for _, row in sc_df.iterrows():
    calc = ArcFlashCalc(system_voltage_kv=row["voltage_kv"], equipment_type="switchgear")
    result = calc.calculate(
        bus_id=row["bus_id"],
        bolted_fault_kA=row["fault_kA_3ph"],
        arc_duration_s=0.033,   # from protective device TCC
    )
    print(result)
```

### Step 6: Review Results Against AFB and PPE Categories
Identify buses where incident energy exceeds PPE Category 2 (8 cal/cm²). These locations typically require engineering controls (bus differential protection, zone-selective interlocking, faster trip times) to reduce hazard level before safe energised work is possible.

### Step 7: Generate Equipment Labels
Using the calculated incident energy and AFB, produce arc flash warning labels compliant with NFPA 70E §130.5(H). Labels must include:
- Nominal system voltage
- Arc flash boundary distance
- Incident energy at the working distance
- Required PPE category or minimum arc rating
- Date of the study

### Step 8: Periodic Review
IEEE 1584-2018 and NFPA 70E require the arc flash study to be reviewed when:
- A major modification is made to the electrical distribution system
- Protective device settings change
- Utility available fault current changes
- At intervals not exceeding 5 years (NFPA 70E §130.5(A))

---

## 6. Validation and Limitations

The calculations in this toolkit implement the **simplified log-linear form** of the IEEE 1584-2018 empirical model. This is suitable for feasibility studies, sensitivity analyses, and cross-checking ETAP output. For formal arc flash hazard labels applied to physical equipment, use a validated power systems analysis tool (ETAP, SKM PowerTools, EasyPower) and have the results reviewed by a licensed professional electrical engineer.

The IEEE 1584-2018 model is valid for:
- System voltages: 208 V – 15 kV
- Bolted fault currents: 0.5 kA – 106 kA
- Electrode gaps: as specified per equipment type
- Arc durations: per the standard's validated range

Results outside these limits are flagged with a warning in `ArcFlashResult.notes`.

---

## References

1. IEEE Std 1584-2018, *Guide for Performing Arc Flash Hazard Calculations*, IEEE, 2018.
2. NFPA 70E-2021, *Standard for Electrical Safety in the Workplace*, National Fire Protection Association, 2021.
3. R. Wilkins, M. Allison, and M. Lang, "Effect of Electrode Orientation in Arc Flash Testing," *IEEE Trans. Ind. Appl.*, vol. 44, no. 5, Sep/Oct 2008.
4. D. R. Doan, "Arc Flash Calculations for Exposures to DC Systems," *IEEE Trans. Ind. Appl.*, vol. 46, no. 6, Nov/Dec 2010.
