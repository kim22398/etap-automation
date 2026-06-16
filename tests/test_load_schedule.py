"""
pytest tests for etap.load_schedule.LoadSchedule

Coverage:
  - Empty schedule edge cases
  - Single and multiple load addition
  - Demand kW / kVAR aggregation
  - total_kva() vectorial correctness
  - power_factor() range and accuracy
  - full_load_current_A() 3-phase and 1-phase
  - load_factor() computation
  - to_dataframe() shape and columns
  - summary() keys
  - remove_load()
  - Input validation (bad demand/load factors, negative kW)
  - Fluent interface (chained add_load)
"""

from __future__ import annotations

import math
import pytest

from etap.load_schedule import LoadSchedule, LoadEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_schedule() -> LoadSchedule:
    return LoadSchedule(name="Test-Bus", voltage_kv=0.48)


@pytest.fixture
def single_load_schedule() -> LoadSchedule:
    sched = LoadSchedule(name="MCC-1", voltage_kv=0.48)
    sched.add_load("Motor-A", kw=75.0, kvar=56.25, demand_factor=1.0, load_factor=1.0)
    return sched


@pytest.fixture
def multi_load_schedule() -> LoadSchedule:
    """Three loads with varying demand and load factors."""
    sched = LoadSchedule(name="MCC-2", voltage_kv=0.48)
    sched.add_load("Pump-A",  kw=75.0,  kvar=56.25, demand_factor=0.85, load_factor=0.70)
    sched.add_load("HVAC-1",  kw=45.0,  kvar=33.75, demand_factor=0.90, load_factor=0.80)
    sched.add_load("Lights",  kw=10.0,  kvar=0.0,   demand_factor=1.00, load_factor=0.95)
    return sched


# ---------------------------------------------------------------------------
# Empty schedule
# ---------------------------------------------------------------------------

class TestEmptySchedule:
    def test_total_demand_kw_zero(self, empty_schedule):
        assert empty_schedule.total_demand_kw() == 0.0

    def test_total_kva_zero(self, empty_schedule):
        assert empty_schedule.total_kva() == 0.0

    def test_power_factor_unity_when_empty(self, empty_schedule):
        """Avoid division by zero — return 1.0 for empty schedule."""
        assert empty_schedule.power_factor() == 1.0

    def test_full_load_current_zero(self, empty_schedule):
        assert empty_schedule.full_load_current_A() == 0.0

    def test_load_factor_unity_when_empty(self, empty_schedule):
        assert empty_schedule.load_factor() == 1.0

    def test_to_dataframe_empty(self, empty_schedule):
        df = empty_schedule.to_dataframe()
        assert len(df) == 0

    def test_summary_keys(self, empty_schedule):
        s = empty_schedule.summary()
        required = {
            "schedule_name", "voltage_kv", "phases", "load_count",
            "total_connected_kW", "total_demand_kW", "total_kVA",
            "composite_PF", "full_load_current_A",
        }
        assert required.issubset(s.keys())


# ---------------------------------------------------------------------------
# Single load
# ---------------------------------------------------------------------------

class TestSingleLoad:
    def test_demand_kw_equals_kw_when_factor_1(self, single_load_schedule):
        assert single_load_schedule.total_demand_kw() == pytest.approx(75.0, rel=1e-6)

    def test_kva_correct(self, single_load_schedule):
        expected = math.sqrt(75.0**2 + 56.25**2)
        assert single_load_schedule.total_kva() == pytest.approx(expected, rel=1e-4)

    def test_power_factor_in_range(self, single_load_schedule):
        pf = single_load_schedule.power_factor()
        assert 0.0 < pf <= 1.0

    def test_power_factor_value(self, single_load_schedule):
        kva = math.sqrt(75**2 + 56.25**2)
        expected_pf = 75.0 / kva
        assert single_load_schedule.power_factor() == pytest.approx(expected_pf, rel=1e-4)

    def test_full_load_current_3phase(self, single_load_schedule):
        kva = math.sqrt(75**2 + 56.25**2)
        expected = (kva * 1000) / (math.sqrt(3) * 0.48 * 1000)
        assert single_load_schedule.full_load_current_A() == pytest.approx(expected, rel=1e-4)

    def test_full_load_current_1phase(self):
        sched = LoadSchedule("Bus-1ph", voltage_kv=0.12, phases=1)
        sched.add_load("Heater", kw=10.0, kvar=0.0)
        expected = (10.0 * 1000) / (0.12 * 1000)
        assert sched.full_load_current_A() == pytest.approx(expected, rel=1e-4)


# ---------------------------------------------------------------------------
# Multiple loads
# ---------------------------------------------------------------------------

class TestMultipleLoads:
    def test_total_demand_kw(self, multi_load_schedule):
        expected = 75.0*0.85 + 45.0*0.90 + 10.0*1.00
        assert multi_load_schedule.total_demand_kw() == pytest.approx(expected, rel=1e-6)

    def test_total_demand_kvar(self, multi_load_schedule):
        expected = 56.25*0.85 + 33.75*0.90 + 0.0*1.00
        assert multi_load_schedule.total_demand_kvar() == pytest.approx(expected, rel=1e-6)

    def test_total_kva_vectorial(self, multi_load_schedule):
        kw   = 75.0*0.85 + 45.0*0.90 + 10.0*1.00
        kvar = 56.25*0.85 + 33.75*0.90
        expected = math.sqrt(kw**2 + kvar**2)
        assert multi_load_schedule.total_kva() == pytest.approx(expected, rel=1e-4)

    def test_power_factor_lagging(self, multi_load_schedule):
        """Mixed inductive loads → PF < 1."""
        pf = multi_load_schedule.power_factor()
        assert pf < 1.0
        assert pf > 0.0

    def test_average_kw(self, multi_load_schedule):
        expected = 75*0.85*0.70 + 45*0.90*0.80 + 10*1.00*0.95
        assert multi_load_schedule.average_kw() == pytest.approx(expected, rel=1e-6)

    def test_load_factor_less_than_one(self, multi_load_schedule):
        lf = multi_load_schedule.load_factor()
        assert 0.0 < lf < 1.0

    def test_load_count_in_summary(self, multi_load_schedule):
        assert multi_load_schedule.summary()["load_count"] == 3

    def test_to_dataframe_shape(self, multi_load_schedule):
        df = multi_load_schedule.to_dataframe()
        assert df.shape[0] == 3
        assert "Demand_kW" in df.columns
        assert "Demand_kVA" in df.columns

    def test_to_dataframe_demand_kw_values(self, multi_load_schedule):
        df = multi_load_schedule.to_dataframe()
        assert df["Demand_kW"].iloc[0] == pytest.approx(75.0 * 0.85, rel=1e-4)
        assert df["Demand_kW"].iloc[1] == pytest.approx(45.0 * 0.90, rel=1e-4)
        assert df["Demand_kW"].iloc[2] == pytest.approx(10.0 * 1.00, rel=1e-4)


# ---------------------------------------------------------------------------
# Fluent interface
# ---------------------------------------------------------------------------

def test_add_load_returns_self():
    sched = LoadSchedule("Bus", voltage_kv=0.48)
    result = sched.add_load("Load-1", kw=10, kvar=0)
    assert result is sched


def test_chained_add_load():
    sched = (
        LoadSchedule("Bus", voltage_kv=0.48)
        .add_load("L1", kw=10, kvar=0)
        .add_load("L2", kw=20, kvar=15)
        .add_load("L3", kw=5,  kvar=3)
    )
    assert sched.summary()["load_count"] == 3


# ---------------------------------------------------------------------------
# Remove load
# ---------------------------------------------------------------------------

def test_remove_load():
    sched = LoadSchedule("Bus", voltage_kv=0.48)
    sched.add_load("L1", kw=10, kvar=0)
    sched.add_load("L2", kw=20, kvar=0)
    sched.remove_load("L1")
    assert sched.summary()["load_count"] == 1
    assert sched.total_demand_kw() == pytest.approx(20.0)


def test_remove_nonexistent_load_raises():
    sched = LoadSchedule("Bus", voltage_kv=0.48)
    with pytest.raises(KeyError):
        sched.remove_load("does-not-exist")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_phases(self):
        with pytest.raises(ValueError):
            LoadSchedule("Bus", voltage_kv=0.48, phases=2)

    def test_negative_voltage(self):
        with pytest.raises(ValueError):
            LoadSchedule("Bus", voltage_kv=-1.0)

    def test_demand_factor_zero_raises(self):
        sched = LoadSchedule("Bus", voltage_kv=0.48)
        with pytest.raises(ValueError):
            sched.add_load("L1", kw=10, kvar=0, demand_factor=0.0)

    def test_demand_factor_gt_one_raises(self):
        sched = LoadSchedule("Bus", voltage_kv=0.48)
        with pytest.raises(ValueError):
            sched.add_load("L1", kw=10, kvar=0, demand_factor=1.1)

    def test_load_factor_zero_raises(self):
        sched = LoadSchedule("Bus", voltage_kv=0.48)
        with pytest.raises(ValueError):
            sched.add_load("L1", kw=10, kvar=0, load_factor=0.0)

    def test_negative_kw_raises(self):
        sched = LoadSchedule("Bus", voltage_kv=0.48)
        with pytest.raises(ValueError):
            sched.add_load("L1", kw=-5, kvar=0)


# ---------------------------------------------------------------------------
# Unity power factor load (purely resistive)
# ---------------------------------------------------------------------------

def test_unity_pf_load():
    sched = LoadSchedule("Bus", voltage_kv=0.48)
    sched.add_load("Heaters", kw=100.0, kvar=0.0)
    assert sched.power_factor() == pytest.approx(1.0, abs=1e-9)
    assert sched.total_kva() == pytest.approx(100.0, rel=1e-6)


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

def test_repr(single_load_schedule):
    r = repr(single_load_schedule)
    assert "MCC-1" in r
    assert "kVA" in r
