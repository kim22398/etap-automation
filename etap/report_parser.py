"""
ETAPReportParser — parse ETAP CSV/Excel study exports into pandas DataFrames.

ETAP typically exports study results as Excel workbooks or CSV files with a
fixed header block followed by tabular data.  The methods here handle both
formats and normalise column names so downstream code can rely on consistent
field names regardless of the ETAP version that produced the file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_raw(filepath: str | Path, sheet_name: str = 0) -> pd.DataFrame:
    """
    Load a CSV or Excel file into a raw DataFrame with no header parsing.

    All values are read as strings so that the header-detection step can
    inspect cell contents without type coercion. Blank / comment rows at the
    top of the file (the ETAP project-info block) are preserved; they are
    removed later by ``_find_header_row``.

    Parameters
    ----------
    filepath : str or Path
        Path to the .csv, .xls, or .xlsx file.
    sheet_name : str or int
        Sheet name or 0-based index for Excel files (default: first sheet).

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with integer-indexed rows and columns.

    Raises
    ------
    ValueError
        If the file extension is not .csv, .xls, or .xlsx.
    """
    p = Path(filepath)
    suffix = p.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(p, sheet_name=sheet_name, header=None, dtype=str)
    elif suffix == ".csv":
        df = pd.read_csv(p, header=None, dtype=str)
    else:
        raise ValueError(f"Unsupported file type: {suffix!r}. Expected .csv, .xls, or .xlsx.")
    return df


def _find_header_row(df: pd.DataFrame, keywords: list[str]) -> int:
    """
    Return the index of the first row that contains all supplied keywords.

    ETAP exports prepend several rows of project metadata (project name,
    study case, date, revision) before the actual data table. This function
    locates the column-header row by scanning for a row whose combined text
    contains all of the provided keywords (case-insensitive).

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame loaded by ``_load_raw`` (all string values).
    keywords : list[str]
        Substrings that must all appear in the header row, e.g.
        ``["bus", "kv"]`` or ``["bus", "incident"]``.

    Returns
    -------
    int
        Row index of the header row. Falls back to the first non-blank row
        if no row matches all keywords, and to 0 if the DataFrame is empty.
    """
    kw_lower = [k.lower() for k in keywords]
    for idx, row in df.iterrows():
        row_text = " ".join(str(v) for v in row.values).lower()
        if all(k in row_text for k in kw_lower):
            return int(idx)
    # Fall back: first non-blank row
    for idx, row in df.iterrows():
        if row.notna().any():
            return int(idx)
    return 0


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise DataFrame column names to snake_case for consistent downstream access.

    Transformations applied (in order):
    1. Strip leading/trailing whitespace
    2. Convert to lowercase
    3. Remove parentheses ``(`` and ``)``
    4. Replace ``%`` with ``pct``
    5. Collapse one or more whitespace characters to a single underscore

    This makes column matching robust against ETAP version differences where
    the same field may be labelled ``"Bus Name"``, ``"bus_name"``, or
    ``"Bus_Name"`` depending on the export format.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame whose columns should be normalised.

    Returns
    -------
    pd.DataFrame
        The same DataFrame with normalised column names (modified in-place).
    """
    df.columns = [
        re.sub(r"\s+", "_", str(c).strip().lower().replace("(", "").replace(")", "").replace("%", "pct"))
        for c in df.columns
    ]
    return df


# ---------------------------------------------------------------------------
# Public parser class
# ---------------------------------------------------------------------------

class ETAPReportParser:
    """
    Parse ETAP study exports (load flow, short circuit, arc flash) into
    tidy pandas DataFrames.

    Parameters
    ----------
    encoding : str
        Character encoding for CSV files (default ``"utf-8"``).
    """

    def __init__(self, encoding: str = "utf-8") -> None:
        self.encoding = encoding

    # ------------------------------------------------------------------
    # Load Flow
    # ------------------------------------------------------------------

    def parse_load_flow(self, filepath: str | Path) -> pd.DataFrame:
        """
        Parse an ETAP load flow results export.

        Expected columns in the ETAP output (flexible matching):
            Bus ID, kV (nominal), kV (operating), % V, MW, MVAR, MVA, PF

        Returns
        -------
        pd.DataFrame
            One row per bus with normalised column names:
            ``bus_id``, ``kv_nominal``, ``kv_operating``, ``voltage_pct``,
            ``mw``, ``mvar``, ``mva``, ``power_factor``.
        """
        raw = _load_raw(filepath)
        hdr = _find_header_row(raw, keywords=["bus", "kv"])
        df = raw.iloc[hdr:].reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
        df = _normalise_columns(df)
        df = df.dropna(how="all")

        # Map flexible ETAP column names → canonical names
        rename_map = {
            "bus_name": "bus_id",
            "bus_id": "bus_id",
            "nominal_kv": "kv_nominal",
            "kv_nom": "kv_nominal",
            "operating_kv": "kv_operating",
            "kv_oper": "kv_operating",
            "voltage_pct": "voltage_pct",
            "pct_v": "voltage_pct",
            "%_v": "voltage_pct",
            "load_mw": "mw",
            "load_mvar": "mvar",
            "load_mva": "mva",
            "pf": "power_factor",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        numeric_cols = ["kv_nominal", "kv_operating", "voltage_pct", "mw", "mvar", "mva", "power_factor"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    # ------------------------------------------------------------------
    # Short Circuit
    # ------------------------------------------------------------------

    def parse_short_circuit(self, filepath: str | Path) -> pd.DataFrame:
        """
        Parse an ETAP short circuit (fault) results export.

        Handles both 3-phase symmetrical (3LG) and line-to-ground (SLG)
        formats.  Typical ETAP columns:
            Bus ID, Fault Type, 3Ø kA, 1Ø kA, X/R Ratio, MVA sc

        Returns
        -------
        pd.DataFrame
            ``bus_id``, ``fault_type``, ``fault_kA_3ph``, ``fault_kA_slg``,
            ``xr_ratio``, ``fault_mva``.
        """
        raw = _load_raw(filepath)
        hdr = _find_header_row(raw, keywords=["bus", "fault"])
        df = raw.iloc[hdr:].reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
        df = _normalise_columns(df)
        df = df.dropna(how="all")

        rename_map = {
            "bus_name": "bus_id",
            "3ø_ka": "fault_kA_3ph",
            "3ph_ka": "fault_kA_3ph",
            "sym_ka": "fault_kA_3ph",
            "1ø_ka": "fault_kA_slg",
            "slg_ka": "fault_kA_slg",
            "xr": "xr_ratio",
            "x/r": "xr_ratio",
            "fault_mva": "fault_mva",
            "sc_mva": "fault_mva",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        numeric_cols = ["fault_kA_3ph", "fault_kA_slg", "xr_ratio", "fault_mva"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    # ------------------------------------------------------------------
    # Arc Flash
    # ------------------------------------------------------------------

    def parse_arc_flash(self, filepath: str | Path) -> pd.DataFrame:
        """
        Parse an ETAP arc flash study export.

        Typical ETAP columns:
            Bus ID, System Voltage (kV), Bolted Fault (kA), Arcing Fault (kA),
            Incident Energy (cal/cm²), Arc Flash Boundary (m), PPE Category,
            Working Distance (mm)

        Returns
        -------
        pd.DataFrame
            ``bus_id``, ``voltage_kv``, ``bolted_fault_kA``, ``arcing_fault_kA``,
            ``incident_energy_cal_cm2``, ``arc_flash_boundary_m``,
            ``ppe_category``, ``working_distance_mm``.
        """
        raw = _load_raw(filepath)
        hdr = _find_header_row(raw, keywords=["bus", "incident"])
        df = raw.iloc[hdr:].reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:].reset_index(drop=True)
        df = _normalise_columns(df)
        df = df.dropna(how="all")

        rename_map = {
            "bus_name": "bus_id",
            "system_voltage_kv": "voltage_kv",
            "voltage_kv": "voltage_kv",
            "bolted_fault_ka": "bolted_fault_kA",
            "bolted_ka": "bolted_fault_kA",
            "arcing_fault_ka": "arcing_fault_kA",
            "arcing_ka": "arcing_fault_kA",
            "incident_energy_cal/cm2": "incident_energy_cal_cm2",
            "ie_cal/cm2": "incident_energy_cal_cm2",
            "arc_flash_boundary_m": "arc_flash_boundary_m",
            "afb_m": "arc_flash_boundary_m",
            "ppe_category": "ppe_category",
            "ppe_cat": "ppe_category",
            "working_distance_mm": "working_distance_mm",
            "wd_mm": "working_distance_mm",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        numeric_cols = [
            "voltage_kv", "bolted_fault_kA", "arcing_fault_kA",
            "incident_energy_cal_cm2", "arc_flash_boundary_m", "working_distance_mm",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df
