"""
ETAP Automation Toolkit — command line entry point.
====================================================

A single, dependency-free entry point that makes the toolkit easy to run::

    python main.py                 # run the flagship arc flash demo
    python main.py --help          # list every subcommand
    python main.py test            # run the pytest suite
    python main.py arcflash ...    # incident energy + PPE category for one bus
    python main.py cable ...       # NEC-compliant copper cable sizing

The domain subcommands expose the library's key calculations directly with
sensible defaults, so an engineer can get a quick answer without writing any
Python.  All results trace to the same IEEE 1584-2018 / NFPA 70E-2021 / NEC
Article 310 implementations used by the library and the demo.
"""

from __future__ import annotations

# Make the ``etap`` package importable when this file is run as
# ``python main.py`` from anywhere, without needing PYTHONPATH set.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import subprocess

from etap.arc_flash import ArcFlashCalc, _EQUIPMENT_CONFIG
from etap.cable_sizing import size_cable


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def _print_header(title: str) -> None:
    """Print a boxed section header to stdout."""
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


# ---------------------------------------------------------------------------
# Subcommand: demo  (also the no-subcommand default)
# ---------------------------------------------------------------------------

def cmd_demo(_args: argparse.Namespace) -> int:
    """Run the flagship arc flash study demo (examples/demo_arc_flash.py)."""
    demo = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "examples",
        "demo_arc_flash.py",
    )
    return subprocess.call([sys.executable, demo])


# ---------------------------------------------------------------------------
# Subcommand: test
# ---------------------------------------------------------------------------

def cmd_test(_args: argparse.Namespace) -> int:
    """Run the pytest suite (``python -m pytest tests/ -q``)."""
    root = os.path.dirname(os.path.abspath(__file__))
    env = dict(os.environ, PYTHONPATH=root)
    return subprocess.call(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=root,
        env=env,
    )


# ---------------------------------------------------------------------------
# Subcommand: arcflash
# ---------------------------------------------------------------------------

def cmd_arcflash(args: argparse.Namespace) -> int:
    """Compute incident energy, arc flash boundary, and PPE category for a bus."""
    calc = ArcFlashCalc(
        system_voltage_kv=args.voltage_kv,
        equipment_type=args.equipment,
    )
    result = calc.calculate(
        bus_id=args.bus_id,
        bolted_fault_kA=args.bolted_ka,
        working_distance_mm=args.distance_mm,
        arc_duration_s=args.duration_s,
    )

    _print_header(f"Arc Flash Result — {result.bus_id}")
    print(result, end="")
    for note in result.notes:
        print(f"  [!] {note}")
    print()
    return 0


# ---------------------------------------------------------------------------
# Subcommand: cable
# ---------------------------------------------------------------------------

def cmd_cable(args: argparse.Namespace) -> int:
    """Select the smallest NEC copper cable meeting ampacity and voltage drop."""
    result = size_cable(
        load_kw=args.load_kw,
        voltage_kv=args.voltage_kv,
        length_m=args.length_m,
        pf=args.pf,
        voltage_drop_limit_pct=args.vd_limit,
        ambient_temp_C=args.ambient_c,
        phases=args.phases,
        continuous_load=not args.non_continuous,
    )

    _print_header("Cable Sizing Result")
    print(f"  Load:               {args.load_kw:.1f} kW @ {args.voltage_kv:.3f} kV, "
          f"{args.phases}-phase, PF={args.pf:.2f}")
    print(f"  Route length:       {result.length_m:.0f} m (one-way)")
    print(f"  Ambient:            {result.ambient_temp_C:.0f} °C "
          f"(correction {result.ambient_correction:.3f})")
    print("  " + "-" * 45)
    print(f"  Selected size:      {result.size}")
    print(f"  Full-load current:  {result.full_load_current_A:.1f} A")
    print(f"  Derated ampacity:   {result.ampacity_derated_A:.1f} A "
          f"(base {result.ampacity_base_A:.0f} A)")
    print(f"  Voltage drop:       {result.voltage_drop_pct:.2f} % "
          f"({result.voltage_drop_V:.1f} V), limit {args.vd_limit:.1f} %")
    print(f"  Meets ampacity:     {'yes' if result.meets_ampacity else 'NO'}")
    print(f"  Meets voltage drop: {'yes' if result.meets_voltage_drop else 'NO'}")
    print(f"  Overall:            {'OK' if result.ok else 'FAIL — no standard size satisfies both criteria'}")
    print()
    return 0 if result.ok else 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="ETAP Automation Toolkit — power-engineering calculations from the CLI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=cmd_demo)  # no subcommand → run the demo

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # demo
    p_demo = sub.add_parser(
        "demo",
        help="Run the flagship arc flash study demo (default when no command given).",
        description="Run examples/demo_arc_flash.py — a 3-bus industrial arc flash study.",
    )
    p_demo.set_defaults(func=cmd_demo)

    # test
    p_test = sub.add_parser(
        "test",
        help="Run the pytest suite.",
        description="Shell out to `python -m pytest tests/ -q`.",
    )
    p_test.set_defaults(func=cmd_test)

    # arcflash
    p_af = sub.add_parser(
        "arcflash",
        help="Arc flash incident energy + PPE category for a single bus.",
        description="Compute incident energy, arc flash boundary, and NFPA 70E PPE "
                    "category per IEEE 1584-2018.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_af.add_argument("--voltage-kv", dest="voltage_kv", type=float, default=0.48,
                      help="Nominal system voltage (kV).")
    p_af.add_argument("--bolted-ka", dest="bolted_ka", type=float, default=25.0,
                      help="Maximum 3-phase bolted fault current (kA sym. rms).")
    p_af.add_argument("--distance-mm", dest="distance_mm", type=float, default=None,
                      help="Working distance (mm). Defaults to the equipment-type default.")
    p_af.add_argument("--duration-s", dest="duration_s", type=float, default=0.033,
                      help="Arc clearing time (s); 0.033 s = 2-cycle at 60 Hz.")
    p_af.add_argument("--equipment", choices=sorted(_EQUIPMENT_CONFIG), default="switchgear",
                      help="Equipment type (sets electrode gap and distance exponent).")
    p_af.add_argument("--bus-id", dest="bus_id", default="BUS-1",
                      help="Bus identifier label for the report.")
    p_af.set_defaults(func=cmd_arcflash)

    # cable
    p_cab = sub.add_parser(
        "cable",
        help="Size a copper cable per NEC Table 310.16 + voltage drop.",
        description="Select the smallest standard copper conductor satisfying both "
                    "ampacity (NEC 310.16) and voltage drop (IEEE 141) criteria.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p_cab.add_argument("--load-kw", dest="load_kw", type=float, default=100.0,
                       help="Load (kW).")
    p_cab.add_argument("--voltage-kv", dest="voltage_kv", type=float, default=0.48,
                       help="System voltage (kV, line-to-line for 3-phase).")
    p_cab.add_argument("--length-m", dest="length_m", type=float, default=50.0,
                       help="One-way cable route length (m).")
    p_cab.add_argument("--pf", type=float, default=0.85,
                       help="Load power factor.")
    p_cab.add_argument("--vd-limit", dest="vd_limit", type=float, default=3.0,
                       help="Maximum allowable voltage drop (%%).")
    p_cab.add_argument("--ambient-c", dest="ambient_c", type=float, default=30.0,
                       help="Ambient temperature (°C).")
    p_cab.add_argument("--phases", type=int, choices=(1, 3), default=3,
                       help="Number of phases.")
    p_cab.add_argument("--non-continuous", dest="non_continuous", action="store_true",
                       help="Skip the NEC 125%% continuous-load multiplier.")
    p_cab.set_defaults(func=cmd_cable)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the selected subcommand."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
