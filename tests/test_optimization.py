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


def _ev(max_discharge_kw, soc_kwh=10.0):
    return {"vehicle_id": "ev1", "capacity_kwh": 60.0, "soc_kwh": soc_kwh, "max_charge_kw": 11.0,
            "max_discharge_kw": max_discharge_kw, "eta": 0.9}


MIDDAY = range(10, 16)


def _midday_solar_crud(prices, solar_kw=8.0, load_kw=1.0):
    """Six hours of midday solar surplus on top of a flat household load."""
    window = hours(WINDOW_START, 24)
    solar = [solar_kw if h in MIDDAY else 0.0 for h in range(24)]
    return FakeCrud(history={
        "solar": series(window, solar, "pv"),
        "load": series(window, [load_kw] * 24),
        "market": series(window, prices),
    })


CHEAP_MIDDAY = [0.02 if h in MIDDAY else 0.35 for h in range(24)]


def test_optimize_returns_an_hourly_plan():
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=_midday_solar_crud(CHEAP_MIDDAY), sell_price_factor=0.3)

    assert len(result) == 24
    assert (result["status"] == "Optimal").all()
    assert result["price"].tolist() == CHEAP_MIDDAY
    assert result["sell_price"].tolist() == pytest.approx([0.3 * p for p in CHEAP_MIDDAY])
    assert set(result.columns) >= {"time", "battery_id", "charge", "discharge", "soc", "grid_buy", "grid_sell",
                                   "solar", "load", "price", "sell_price", "total_cost",
                                   "stored_energy_price", "stored_energy_value", "objective"}


def test_costs_buy_at_market_price_and_sell_at_the_factor():
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=_midday_solar_crud(CHEAP_MIDDAY), sell_price_factor=0.3)

    grid_cost = (result["price"] * result["grid_buy"] - result["sell_price"] * result["grid_sell"]).sum()
    assert result["total_cost"].iloc[0] == pytest.approx(grid_cost)
    stored_price = sum(CHEAP_MIDDAY) / 24
    assert result["stored_energy_price"].iloc[0] == pytest.approx(stored_price)
    assert result["stored_energy_value"].iloc[0] == pytest.approx(stored_price * (result["soc"].iloc[-1] - 10.0))
    assert result["objective"].iloc[0] == pytest.approx(grid_cost - result["stored_energy_value"].iloc[0])


def test_cheap_solar_surplus_is_stored_rather_than_sold():
    """Selling midday surplus earns 0.006/kWh; storing it is worth 0.9 x the average price."""
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=_midday_solar_crud(CHEAP_MIDDAY), sell_price_factor=0.3)

    midday = result.iloc[list(MIDDAY)]
    surplus = (midday["solar"] - midday["load"]).sum()
    assert midday["grid_sell"].sum() == pytest.approx(0.0, abs=1e-6)
    # All surplus goes into the EV, topped up with 0.02 grid power until the battery is full.
    assert midday["charge"].sum() >= surplus - 1e-6
    assert result["soc"].iloc[max(MIDDAY)] == pytest.approx(60.0)


def test_surplus_is_sold_when_selling_pays_more_than_storing():
    """With a flat price and full sell price, a stored kWh (worth 0.9 x price) loses to selling it."""
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=_midday_solar_crud([0.30] * 24), sell_price_factor=1.0)

    assert result["charge"].sum() == pytest.approx(0.0, abs=1e-6)
    assert result["grid_sell"].sum() == pytest.approx(7.0 * 6)


def test_grid_power_is_not_bought_to_fill_the_battery_at_the_average_price():
    """Charging from the grid at a price above eta x the stored-energy price is not worth it."""
    crud = _midday_solar_crud([0.30] * 24, solar_kw=0.0)
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=crud, sell_price_factor=0.3)
    assert result["charge"].sum() == pytest.approx(0.0, abs=1e-6)


def test_v2g_ev_covers_expensive_load_without_selling_stored_energy():
    """Cheap morning, expensive afternoon, no solar: stored energy is worth 0.30/kWh.

    Discharging saves 0.50/kWh in the afternoon, but selling there only earns 0.15 and
    there is no cheaper refill afterwards, so the EV covers the load and sells nothing.
    """
    prices = [0.10] * 12 + [0.50] * 12
    crud = _midday_solar_crud(prices, solar_kw=0.0)
    result = optimize([_ev(11.0, soc_kwh=30.0)], start=WINDOW_START, crud=crud, sell_price_factor=0.3)

    afternoon = result.iloc[12:]
    assert afternoon["discharge"].tolist() == pytest.approx([1.0] * 12)  # exactly the load
    assert afternoon["grid_buy"].sum() == pytest.approx(0.0, abs=1e-6)
    assert result["grid_sell"].sum() == pytest.approx(0.0, abs=1e-6)


def test_energy_is_conserved():
    result = optimize([_ev(11.0, soc_kwh=30.0)], start=WINDOW_START, crud=_midday_solar_crud(CHEAP_MIDDAY),
                      sell_price_factor=0.3)

    soc_change = result["soc"].iloc[-1] - 30.0
    assert soc_change == pytest.approx(0.9 * result["charge"].sum() - result["discharge"].sum())
    grid_net = (result["grid_buy"] - result["grid_sell"]).sum()
    assert grid_net == pytest.approx((result["load"] - result["solar"]).sum() + result["charge"].sum()
                                     - result["discharge"].sum())


def test_sell_price_factor_defaults_to_settings(monkeypatch):
    from backend.src.config import get_settings

    monkeypatch.setattr(get_settings(), "optimization_sell_price_factor", 0.5)
    result = optimize([_ev(0.0)], start=WINDOW_START, crud=_midday_solar_crud(CHEAP_MIDDAY))
    assert result["sell_price"].tolist() == pytest.approx([0.5 * p for p in CHEAP_MIDDAY])
