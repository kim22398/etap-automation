"""
ETAP Automation Toolkit
=======================

Python utilities for power engineers working with ETAP study outputs.

Modules
-------
report_parser
    Parse ETAP CSV/Excel exports (load flow, short circuit, arc flash)
    into tidy pandas DataFrames.
equipment
    Typed dataclasses for power system components: Cable, Breaker, Transformer.
load_schedule
    Build and evaluate electrical load schedules per IEEE Std 141.
cable_sizing
    Select NEC-compliant copper conductor sizes with ampacity and voltage-drop
    checks per NEC Article 310 and IEEE 141.
arc_flash
    Incident energy and PPE category calculations per IEEE 1584-2018 and
    NFPA 70E-2021.
report_generator
    Generate formatted Excel equipment schedules via openpyxl.

Standards
---------
- IEEE Std 1584-2018: Guide for Performing Arc Flash Hazard Calculations
- NFPA 70E-2021: Standard for Electrical Safety in the Workplace
- NFPA 70 (NEC) 2023: National Electrical Code — cable ampacity and voltage drop
- IEEE Std 141-1993 (Red Book): Electric Power Distribution for Industrial Plants
"""

__version__ = "0.1.0"
__author__ = "ETAP Automation Toolkit Contributors"
