"""Unit tests for optimization input loading and the EV optimizer (no database)."""
import pandas as pd
import pytest

from backend.src.optimization.optimization import (
    OptimizationDataError,
    load_optimization_data,
    optimization_window,
    optimize,
)

WINDOW_START = "2026-03-01 00:00"


def hours(start, n, freq="h"):
    return pd.date_range(start, periods=n, freq=freq, tz="UTC")


class FakeCrud:
    """In-memory stand-in for CrudManager's time-series reads (inclusive start/end, like the SQL)."""

    def __init__(self, history=None, forecasts=None):
        # {table: [(time, source_id, value), ...]}
        self.history = history or {}
        self.forecasts = forecasts or {}

    @staticmethod
    def _select(rows, source_id, start, end):
        return [
            (t, v) for t, sid, v in rows
            if (source_id is None or sid == source_id) and (start is None or t >= start) and (end is None or t <= end)
        ]

    def query_source_ids(self, table):
        return sorted({sid for _, sid, _ in self.history.get(table, [])})

    def get_time_bounds(self, table, source_id=None):
        times = [t for t, _ in self._select(self.history.get(table, []), source_id, None, None)]
        return (min(times), max(times)) if times else None

    def load_historical_data(self, table, source_id=None, start=None, end=None, top=None):
        return [{"time": t, "value": v} for t, v in self._select(self.history.get(table, []), source_id, start, end)]

    def load_forecasted_data(self, kind, source_id=None, start=None, end=None, top=None):
        return [{"time": t, "yhat": v} for t, v in self._select(self.forecasts.get(kind, []), source_id, start, end)]


def series(times, values, source_id=None):
    return [(t.to_pydatetime(), source_id, float(v)) for t, v in zip(times, values)]


def test_window_defaults_to_24_hours_from_the_hour():
    index = optimization_window("2026-03-01 10:37")
    assert len(index) == 24
    assert index[0] == pd.Timestamp("2026-03-01 10:00", tz="UTC")
    assert index[-1] == pd.Timestamp("2026-03-02 09:00", tz="UTC")


def test_forecasts_are_preferred_over_history():
    window = hours(WINDOW_START, 24)
    crud = FakeCrud(
        history={"load": series(window, [9.0] * 24), "market": series(window, [9.0] * 24)},
        forecasts={"load": series(window, [1.0] * 24), "market": series(window, [0.2] * 24)},
    )
    df = load_optimization_data(start=WINDOW_START, crud=crud)
    assert df["load"].tolist() == [1.0] * 24
    assert df["price"].tolist() == [0.2] * 24
    assert df["solar"].tolist() == [0.0] * 24
    assert df.attrs["sources"] == {"load": "forecast", "price": "forecast"}


def test_history_at_the_window_hours_is_used_and_bucketed_hourly():
    # Household load is stored at odd minutes (the time the household was created).
    load_times = hours("2026-03-01 00:42", 24)
    crud = FakeCrud(history={
        "load": series(load_times, range(24)),
        "market": series(hours(WINDOW_START, 24), [0.3] * 24),
    })
    df = load_optimization_data(start=WINDOW_START, crud=crud)
    assert df["load"].tolist() == [float(v) for v in range(24)]
    assert df.attrs["sources"]["load"] == "history"


def test_past_history_becomes_an_hour_of_day_profile():
    # Market prices exist only for a week long before the window: price = hour of day.
    past = hours("2025-01-07 00:00", 24 * 7)
    crud = FakeCrud(history={
        "load": series(hours(WINDOW_START, 24), [2.0] * 24),
        "market": series(past, [t.hour / 10 for t in past]),
    })
    df = load_optimization_data(start="2026-03-01 06:00", crud=crud)
    assert df["price"].tolist() == [((6 + h) % 24) / 10 for h in range(24)]


def test_future_only_history_uses_its_first_days_as_profile():
    later = hours("2026-04-01 00:00", 48)
    crud = FakeCrud(history={
        "load": series(later, [t.hour for t in later]),
        "market": series(later, [0.1] * 48),
    })
    df = load_optimization_data(start=WINDOW_START, crud=crud)
    assert df["load"].tolist() == [float(h) for h in range(24)]


def test_history_starting_inside_the_window_fills_its_first_hours_from_a_profile():
    # Household load that starts two hours into the window (and runs for days).
    later = hours("2026-03-01 02:00", 24 * 3)
    crud = FakeCrud(history={
        "load": series(later, [t.hour for t in later]),
        "market": series(hours(WINDOW_START, 24), [0.1] * 24),
    })
    df = load_optimization_data(start=WINDOW_START, crud=crud)
    assert df["load"].tolist() == [float(h) for h in range(24)]


def test_forecast_gaps_are_filled_from_history():
    window = hours(WINDOW_START, 24)
    crud = FakeCrud(
        history={"load": series(window, [5.0] * 24), "market": series(window, [0.1] * 24)},
        forecasts={"load": series(window[:12], [1.0] * 12)},
    )
    df = load_optimization_data(start=WINDOW_START, crud=crud)
    assert df["load"].tolist() == [1.0] * 12 + [5.0] * 12
    assert df.attrs["sources"]["load"] == "forecast+history"


def test_solar_is_summed_over_sources_and_missing_sources_count_as_zero():
    window = hours(WINDOW_START, 24)
    crud = FakeCrud(history={
        "solar": series(window, [1.0] * 24, "a") + series(window[:6], [2.0] * 6, "b"),
        "load": series(window, [3.0] * 24),
        "market": series(window, [0.1] * 24),
    })
    df = load_optimization_data(start=WINDOW_START, crud=crud)
    # Source b has 6 hours of data; the profile covers its other hours of day only where it has values.
    assert df["solar"].iloc[:6].tolist() == [3.0] * 6
    assert df["solar"].iloc[6:].tolist() == [1.0] * 18
    assert set(df.attrs["sources"]) == {"solar:a", "solar:b", "load", "price"}


@pytest.mark.parametrize("missing, message", [("load", "No load data"), ("market", "No market data")])
def test_missing_required_input_raises(missing, message):
    window = hours(WINDOW_START, 24)
    history = {"load": series(window, [1.0] * 24), "market": series(window, [0.1] * 24)}
    del history[missing]
    with pytest.raises(OptimizationDataError, match=message):
        load_optimization_data(start=WINDOW_START, crud=FakeCrud(history=history))


def _ev(max_discharge_kw):
    return {"vehicle_id": "ev1", "capacity_kwh": 60.0, "soc_kwh": 30.0, "max_charge_kw": 11.0,
            "max_discharge_kw": max_discharge_kw, "eta": 0.9}


@pytest.fixture
def two_price_crud():
    window = hours(WINDOW_START, 24)
    prices = [0.05 if h < 6 else 0.40 for h in range(24)]
    return FakeCrud(history={"load": series(window, [1.0] * 24), "market": series(window, prices)}), prices


def test_optimize_returns_an_hourly_plan(two_price_crud):
    crud, prices = two_price_crud
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=crud)

    assert len(result) == 24
    assert (result["status"] == "Optimal").all()
    assert result["price"].tolist() == prices
    assert set(result.columns) >= {"time", "battery_id", "charge", "discharge", "soc", "grid_buy", "grid_sell",
                                   "solar", "load", "price", "total_cost"}


def test_charging_costs_money(two_price_crud):
    """Charging draws from the grid, so a charge-only EV can never beat the load-only cost."""
    crud, prices = two_price_crud
    load_only_cost = sum(1.0 * p for p in prices)

    result = optimize([_ev(0.0)], start=WINDOW_START, crud=crud)

    assert result["discharge"].abs().max() == 0
    assert result["total_cost"].iloc[0] == pytest.approx(load_only_cost + (result["charge"] * result["price"]).sum())
    assert result["total_cost"].iloc[0] >= load_only_cost - 1e-6


def test_discharging_covers_expensive_load(two_price_crud):
    """A V2G EV may discharge its stored energy into expensive hours, but cannot create energy."""
    crud, prices = two_price_crud
    load_only_cost = sum(1.0 * p for p in prices)

    result = optimize([_ev(11.0)], start=WINDOW_START, crud=crud)

    grid_net = (result["grid_buy"] - result["grid_sell"]).sum()
    assert grid_net == pytest.approx(24.0 + result["charge"].sum() - result["discharge"].sum())
    assert result["discharge"].sum() <= 30.0 + 0.9 * result["charge"].sum() + 1e-6
    assert result["total_cost"].iloc[0] < load_only_cost
