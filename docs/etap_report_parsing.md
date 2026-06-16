# ETAP Report Parsing Guide

## Exporting from ETAP, Expected Columns, Version Differences, and Troubleshooting

---

## 1. Overview

The `ETAPReportParser` class reads Excel (.xlsx, .xls) and CSV (.csv) files exported from ETAP and returns clean pandas DataFrames with standardised column names. This guide explains how to export the right files from ETAP, what columns the parser expects, how results differ across ETAP versions, and how to diagnose common problems.

---

## 2. Exporting Study Results from ETAP

ETAP exports study results from the **Study Case** output reports. The procedure is similar across all study types (load flow, short circuit, arc flash):

### 2.1 Load Flow Report

1. Run your load flow study case in ETAP (Study Case toolbar → **Load Flow**).
2. In the **Output Report** window, select the **Bus** tab (or the relevant equipment tab).
3. Click **Export** → **Excel** (or **CSV**). Save as `lf_results.xlsx`.

The exported file will contain a header block with the project name, date, and study case name, followed by tabular data starting a few rows down. The parser automatically skips the header block by searching for the row containing the keywords "bus" and "kv".

**Tip:** Export the "Bus" results table, not the "Summary" or "Input Data" table. The Bus table contains the per-bus voltage and power flow results that the parser expects.

### 2.2 Short Circuit Report

1. Run the short circuit study (AC Short Circuit → **3-Phase Fault** or **Unbalanced Fault**).
2. In the output report, select the **Bus Fault Summary** view.
3. Export as Excel or CSV. Save as `sc_results.xlsx`.

Export the 3-phase symmetrical fault results. If you also need line-to-ground (SLG) results, export the unbalanced fault report separately; the parser's `parse_short_circuit()` method will pick up both `fault_kA_3ph` and `fault_kA_slg` columns if they are present in the same table.

### 2.3 Arc Flash Report

1. Run the arc flash study (Arc Flash Analysis → **Calculate**).
2. In the output, select the **Bus Arc Flash Results** view.
3. Export as Excel. Save as `af_results.xlsx`.

The arc flash report is the most information-rich export and typically includes: bus ID, system voltage, bolted fault current, arcing fault current, incident energy, arc flash boundary, PPE category, and working distance. All of these are parsed by `parse_arc_flash()`.

---

## 3. Expected Column Names

The parser performs flexible column matching by normalising all column names to snake_case and then applying a rename map. This means the parser is tolerant of minor variations in ETAP's column naming between versions.

### 3.1 Load Flow — `parse_load_flow()`

| Canonical Column | ETAP Column Variants | Type |
|---|---|---|
| `bus_id` | Bus Name, Bus ID, Bus_Name | str |
| `kv_nominal` | Nominal kV, kV Nom, Nominal_kV | float |
| `kv_operating` | Operating kV, kV Oper | float |
| `voltage_pct` | % V, Voltage %, Pct V | float |
| `mw` | Load MW, MW | float |
| `mvar` | Load MVAR, MVAR | float |
| `mva` | Load MVA, MVA | float |
| `power_factor` | PF, Power Factor | float |

### 3.2 Short Circuit — `parse_short_circuit()`

| Canonical Column | ETAP Column Variants | Type |
|---|---|---|
| `bus_id` | Bus Name, Bus ID | str |
| `fault_type` | Fault Type | str |
| `fault_kA_3ph` | 3Ø kA, 3Ph kA, Sym kA | float |
| `fault_kA_slg` | 1Ø kA, SLG kA | float |
| `xr_ratio` | X/R, XR | float |
| `fault_mva` | Fault MVA, SC MVA | float |

### 3.3 Arc Flash — `parse_arc_flash()`

| Canonical Column | ETAP Column Variants | Type |
|---|---|---|
| `bus_id` | Bus Name, Bus ID | str |
| `voltage_kv` | System Voltage kV, Voltage kV | float |
| `bolted_fault_kA` | Bolted Fault kA, Bolted kA | float |
| `arcing_fault_kA` | Arcing Fault kA, Arcing kA | float |
| `incident_energy_cal_cm2` | Incident Energy cal/cm², IE cal/cm² | float |
| `arc_flash_boundary_m` | Arc Flash Boundary m, AFB m | float |
| `ppe_category` | PPE Category, PPE Cat | str |
| `working_distance_mm` | Working Distance mm, WD mm | float |

---

## 4. ETAP Version Differences

ETAP has evolved significantly over its history. The most common version-related differences that affect the parser are:

### ETAP 16.x and earlier
Column names often used mixed case with parenthetical units, e.g., `"Bus Name"`, `"Nominal kV"`, `"Incident Energy (cal/cm²)"`. The `_normalise_columns()` function strips parentheses and converts to snake_case, handling these automatically.

### ETAP 18.x and 19.x (2018 arc flash model)
After IEEE 1584-2018 was published, ETAP 18 and 19 added the new model. The arc flash report gained additional columns including electrode gap, enclosure type, and the two arcing current values (maximum and minimum). The parser reads whichever columns are present and ignores unknowns.

### ETAP 22.x (current as of 2024)
ETAP 22 uses a unified output framework. Some column headers may include the study case name as a prefix. If your export has prefixed columns (e.g., `"SC1_Bus Name"`), the normalisation step will produce `"sc1_bus_name"`. In this case, manually rename the column after parsing:

```python
df = parser.parse_short_circuit("sc_results.xlsx")
if "sc1_bus_name" in df.columns and "bus_id" not in df.columns:
    df = df.rename(columns={"sc1_bus_name": "bus_id"})
```

### CSV vs. Excel
Both formats are supported. CSV exports from ETAP use UTF-8 encoding and comma delimiters. The `ETAPReportParser` constructor accepts an `encoding` parameter (default `"utf-8"`); older ETAP versions may export with `"latin-1"` or `"cp1252"` encoding on Windows:

```python
parser = ETAPReportParser(encoding="cp1252")
```

---

## 5. Column Normalisation Details

The `_normalise_columns()` internal function performs the following transformations to make column matching robust:

1. Strip leading and trailing whitespace from column names
2. Convert to lowercase
3. Remove parentheses `(` and `)`
4. Replace `%` with `pct`
5. Replace one or more whitespace characters with a single underscore `_`

Example transformations:

| ETAP Original | After Normalisation |
|---|---|
| `"Bus Name"` | `"bus_name"` |
| `"Nominal kV"` | `"nominal_kv"` |
| `"Incident Energy (cal/cm²)"` | `"incident_energy_cal/cm²"` |
| `"% V"` | `"pct_v"` |
| `"3Ø kA"` | `"3ø_ka"` |

The rename maps in each parser method then map these normalised names to the canonical column names (`bus_id`, `fault_kA_3ph`, etc.).

---

## 6. Troubleshooting

### Problem: `ValueError: Unsupported file type`
The file extension is not `.csv`, `.xls`, or `.xlsx`. ETAP sometimes exports as `.txt` (tab-delimited). Rename the file with a `.csv` extension after confirming the delimiter is a comma, or pre-process with pandas:

```python
import pandas as pd
df = pd.read_csv("export.txt", sep="\t")
df.to_csv("export.csv", index=False)
```

### Problem: All columns are `NaN` after parsing
The header row detection failed. The `_find_header_row()` function searches for rows containing the keywords (e.g., "bus", "kv"). If ETAP exported extra metadata rows before the table, or the column names do not contain the expected keywords, the parser may use the wrong row as the header.

Diagnosis:
```python
import pandas as pd
raw = pd.read_excel("lf_results.xlsx", header=None, dtype=str)
print(raw.head(20))
```

This shows the raw file content. Identify the row number of the actual column headers and pass it directly:

```python
# Manual override — read from row 7 (0-indexed)
df = pd.read_excel("lf_results.xlsx", header=7)
```

### Problem: `bus_id` column missing
The column rename map does not contain a matching entry for the ETAP column name in your file. Print the raw column names after normalisation to identify the correct name:

```python
from etap.report_parser import _load_raw, _find_header_row, _normalise_columns

raw = _load_raw("af_results.xlsx")
hdr = _find_header_row(raw, ["bus", "incident"])
df = raw.iloc[hdr:].reset_index(drop=True)
df.columns = df.iloc[0]
df = df.iloc[1:].reset_index(drop=True)
df = _normalise_columns(df)
print(df.columns.tolist())
```

Then add the missing mapping to the `rename_map` dictionary in `parse_arc_flash()`, or rename the column in your calling code after parsing.

### Problem: Numeric columns contain strings like `"---"` or `"N/A"`
ETAP sometimes inserts placeholder strings for buses with no data (e.g., a bus with no connected load). The parser applies `pd.to_numeric(..., errors="coerce")` which converts these to `NaN`. Filter them out after parsing:

```python
df = parser.parse_arc_flash("af_results.xlsx")
df = df.dropna(subset=["incident_energy_cal_cm2"])
```

### Problem: Duplicate bus IDs
ETAP occasionally outputs the same bus multiple times (once per study mode or per fault type). After parsing, deduplicate by keeping the maximum incident energy per bus:

```python
df = parser.parse_arc_flash("af_results.xlsx")
df = df.sort_values("incident_energy_cal_cm2", ascending=False)
df = df.drop_duplicates(subset="bus_id", keep="first")
```

---

## 7. Extending the Parser

To support additional ETAP study types (motor starting, protective device coordination, harmonic analysis), add a new method to `ETAPReportParser` following the same pattern:

```python
def parse_motor_starting(self, filepath: str | Path) -> pd.DataFrame:
    """Parse an ETAP motor starting study export."""
    raw = _load_raw(filepath)
    hdr = _find_header_row(raw, keywords=["bus", "motor"])
    df = raw.iloc[hdr:].reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df = _normalise_columns(df)
    df = df.dropna(how="all")

    rename_map = {
        "bus_name": "bus_id",
        "motor_id": "motor_id",
        "starting_voltage_pct": "starting_voltage_pct",
        # Add mappings from your specific ETAP export
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df
```

The key pattern is: load raw → find header → slice to data → normalise columns → rename to canonical names → coerce numerics.
