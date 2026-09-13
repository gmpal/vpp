from typing import Any, Dict, List

import pandas as pd
import pulp

from backend.src.config import get_settings
from backend.src.db import CrudManager, DatabaseManager
from backend.src.utils.logger import get_logger

db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)
logger = get_logger(__name__)

DEFAULT_HORIZON_HOURS = 24
HISTORY_PROFILE_DAYS = 7


class OptimizationDataError(ValueError):
    """Raised when there is not enough load or price data to build the optimization inputs."""


def _hourly(rows: List[Dict[str, Any]], value_key: str) -> pd.Series:
    """Average rows of {"time", value_key} into UTC hourly buckets."""
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    buckets = pd.to_datetime(df["time"], utc=True).dt.floor("h")
    return df[value_key].astype(float).groupby(pd.DatetimeIndex(buckets)).mean()


def _history_fallback(crud: CrudManager, table: str, source_id: str | None, index: pd.DatetimeIndex) -> pd.Series:
    """Historical values for each hour of the window.

    Uses the value recorded at that hour when there is one. Remaining hours get the
    hour-of-day average of the HISTORY_PROFILE_DAYS of history closest to the window,
    so a past profile stands in for hours that have no data yet.
    """
    bounds = crud.get_time_bounds(table, source_id)
    if bounds is None:
        return pd.Series(float("nan"), index=index)

    start, end = index[0], index[-1] + pd.Timedelta(hours=1)
    rows = crud.load_historical_data(table, source_id, start=start.to_pydatetime(), end=end.to_pydatetime())
    exact = _hourly(rows, "value").reindex(index)
    if exact.notna().all():
        return exact

    # The HISTORY_PROFILE_DAYS of history closest to the window: its most recent days when
    # history ends before the window, its first days when history starts inside or after it.
    first, last = (pd.Timestamp(b).tz_convert("UTC") for b in bounds)
    span = pd.Timedelta(days=HISTORY_PROFILE_DAYS)
    profile_end = min(max(end, first + span), last + pd.Timedelta(hours=1))
    profile_start = profile_end - span
    rows = crud.load_historical_data(table, source_id, start=profile_start.to_pydatetime(), end=profile_end.to_pydatetime())
    history = _hourly(rows, "value")
    profile = history.groupby(history.index.hour).mean()
    return exact.fillna(pd.Series(index.hour.map(profile).astype(float), index=index))


def _input_series(crud: CrudManager, kind: str, source_id: str | None, index: pd.DatetimeIndex) -> tuple[pd.Series, str]:
    """Forecast for the window, with gaps filled from history. Returns (series, origin)."""
    start, end = index[0], index[-1] + pd.Timedelta(hours=1)
    rows = crud.load_forecasted_data(kind, source_id, start=start.to_pydatetime(), end=end.to_pydatetime())
    forecast = _hourly(rows, "yhat").reindex(index)
    if forecast.notna().all():
        return forecast, "forecast"

    combined = forecast.combine_first(_history_fallback(crud, kind, source_id, index))
    if combined.isna().all():
        return combined, "none"
    return combined, "forecast+history" if forecast.notna().any() else "history"


def optimization_window(start: str | None = None, end: str | None = None) -> pd.DatetimeIndex:
    """Hourly UTC steps from start (default: the current hour) up to end (default: +24 h), end exclusive."""
    start_ts = pd.Timestamp(start) if start else pd.Timestamp.now(tz="UTC")
    start_ts = (start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")).floor("h")
    if end:
        end_ts = pd.Timestamp(end)
        end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
    else:
        end_ts = start_ts + pd.Timedelta(hours=DEFAULT_HORIZON_HOURS)
    index = pd.date_range(start_ts, end_ts, freq="h", inclusive="left")
    if index.empty:
        raise OptimizationDataError(f"Empty optimization window: start={start_ts}, end={end_ts}")
    return index


def load_optimization_data(start: str = None, end: str = None, crud: CrudManager | None = None) -> pd.DataFrame:
    """Hourly solar, load and price for the optimization window.

    Each input prefers forecasts and falls back to history (see _history_fallback).
    Solar without any data counts as zero production; load and price are required.
    The origin of each input is stored in ``df.attrs["sources"]``.
    """
    crud = crud or crud_manager
    index = optimization_window(start, end)
    sources: Dict[str, str] = {}

    solar = pd.Series(0.0, index=index)
    for source_id in crud.query_source_ids("solar"):
        series, origin = _input_series(crud, "solar", source_id, index)
        solar = solar.add(series.fillna(0.0))
        sources[f"solar:{source_id}"] = origin

    df = pd.DataFrame({"solar": solar}, index=index)
    for column, kind, hint in (
        ("load", "load", "create a household to generate load"),
        ("price", "market", "run init-db to seed market prices"),
    ):
        series, origin = _input_series(crud, kind, None, index)
        if series.isna().any():
            missing = int(series.isna().sum())
            raise OptimizationDataError(f"No {kind} data for {missing} of {len(index)} hours: {hint}")
        df[column] = series
        sources[column] = origin

    df.attrs["sources"] = sources
    logger.info("Optimization inputs for %s .. %s: %s", index[0], index[-1], sources)
    return df


def stored_energy_price(buy_prices: pd.Series) -> float:
    """Value of a kWh left in an EV at the end of the window: the average buy price, never negative.

    Without it the optimizer sees stored energy as worthless, so charge-only EVs never charge
    and V2G EVs drain to empty.
    """
    return max(float(buy_prices.mean()), 0.0)


def optimize(
    evs: List[Dict[str, Any]],
    start: str = None,
    end: str = None,
    crud: CrudManager | None = None,
    sell_price_factor: float | None = None,
) -> pd.DataFrame:
    """
    Performs an optimization over the specified time range [start, end],
    using the aggregated solar, load, and market price from the database,
    and a list of EV dicts (rows from the electric_vehicles table).

    Parameters
    ----------
    evs : List[Dict[str, Any]]
        EV rows from the DB. Each dict must have: vehicle_id, capacity_kwh,
        soc_kwh, max_charge_kw, max_discharge_kw, eta.
    start : str
        Start time (inclusive); defaults to the current hour.
    end : str
        End time (exclusive); defaults to start + 24 h.
    crud : CrudManager
        Data access; defaults to the module-level manager.
    sell_price_factor : float
        Sell price as a fraction of the buy (market) price; defaults to the
        ``optimization_sell_price_factor`` setting.

    The objective minimizes grid cost (buying at the market price, selling at
    sell_price_factor times it) minus the value of the energy added to the EVs,
    priced by ``stored_energy_price``. So surplus is stored rather than sold when
    eta * stored_energy_price exceeds the sell price.

    Returns
    -------
    pd.DataFrame
        Columns: time, battery_id, charge, discharge, soc, grid_buy, grid_sell,
        solar, load, price, sell_price, status, total_cost (net grid cost),
        stored_energy_price, stored_energy_value (value of the SOC change) and objective.

    Raises
    ------
    OptimizationDataError
        If load or price data is missing for the window.
    """
    df = load_optimization_data(start=start, end=end, crud=crud)
    if sell_price_factor is None:
        sell_price_factor = get_settings().optimization_sell_price_factor
    df["sell_price"] = df["price"] * sell_price_factor
    storage_price = stored_energy_price(df["price"])

    time_index = df.index
    time_steps = range(len(time_index))
    logger.debug("Optimization time steps: %d", len(time_steps))

    problem = pulp.LpProblem("VPP_Optimization", pulp.LpMinimize)

    battery_charge: Dict = {}
    battery_discharge: Dict = {}
    battery_soc: Dict = {}

    grid_buy = pulp.LpVariable.dicts("GridBuy", time_steps, lowBound=0)
    grid_sell = pulp.LpVariable.dicts("GridSell", time_steps, lowBound=0)
    delta = pulp.LpVariable.dicts("Delta", time_steps, cat=pulp.LpBinary)

    M = 1_000

    for ev in evs:
        b_label = ev["vehicle_id"]
        logger.debug(
            "EV %s: max_charge_kw=%s, max_discharge_kw=%s, capacity_kwh=%s, soc_kwh=%s, eta=%s",
            b_label, ev["max_charge_kw"], ev["max_discharge_kw"],
            ev["capacity_kwh"], ev["soc_kwh"], ev["eta"],
        )

        for t in time_steps:
            battery_charge[(b_label, t)] = pulp.LpVariable(f"Charge_{b_label}_{t}", lowBound=0, upBound=ev["max_charge_kw"])
            battery_discharge[(b_label, t)] = pulp.LpVariable(f"Discharge_{b_label}_{t}", lowBound=0, upBound=ev["max_discharge_kw"])
            battery_soc[(b_label, t)] = pulp.LpVariable(f"SOC_{b_label}_{t}", lowBound=0, upBound=ev["capacity_kwh"])

        # soc[t] is the state of charge after step t, so step 0 starts from the current SOC.
        for t in time_steps:
            previous_soc = ev["soc_kwh"] if t == 0 else battery_soc[(b_label, t - 1)]
            problem += (
                battery_soc[(b_label, t)]
                == previous_soc
                + ev["eta"] * battery_charge[(b_label, t)]
                - battery_discharge[(b_label, t)]
            )

    for t in time_steps:
        total_charge_t = pulp.lpSum([battery_charge[(b_label, t)] for b_label, _t in battery_charge if _t == t])
        total_discharge_t = pulp.lpSum([battery_discharge[(b_label, t)] for b_label, _t in battery_discharge if _t == t])

        # Power left over for the grid: charging EVs consumes power, discharging supplies it.
        net_excess = df["solar"].iloc[t] - df["load"].iloc[t] - total_charge_t + total_discharge_t

        problem += grid_sell[t] >= net_excess
        problem += grid_sell[t] >= 0
        problem += grid_sell[t] <= net_excess + M * (1 - delta[t])
        problem += grid_sell[t] <= M * delta[t]

        problem += grid_buy[t] >= -net_excess
        problem += grid_buy[t] >= 0
        problem += grid_buy[t] <= -net_excess + M * delta[t]
        problem += grid_buy[t] <= M * (1 - delta[t])

    total_cost = pulp.lpSum(
        [df["price"].iloc[t] * grid_buy[t] - df["sell_price"].iloc[t] * grid_sell[t] for t in time_steps]
    )
    last = len(time_index) - 1
    stored_energy_value = storage_price * pulp.lpSum(
        [battery_soc[(ev["vehicle_id"], last)] - ev["soc_kwh"] for ev in evs]
    )
    problem += total_cost - stored_energy_value

    problem.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[problem.status]
    logger.info("Optimization status: %s", status)

    results = []
    for t in time_steps:
        gb = pulp.value(grid_buy[t])
        gs = pulp.value(grid_sell[t])
        for ev in evs:
            b_label = ev["vehicle_id"]
            results.append({
                "time": time_index[t],
                "battery_id": b_label,
                "charge": pulp.value(battery_charge[(b_label, t)]),
                "discharge": pulp.value(battery_discharge[(b_label, t)]),
                "soc": pulp.value(battery_soc[(b_label, t)]),
                "grid_buy": gb,
                "grid_sell": gs,
                "solar": float(df["solar"].iloc[t]),
                "load": float(df["load"].iloc[t]),
                "price": float(df["price"].iloc[t]),
                "sell_price": float(df["sell_price"].iloc[t]),
            })

    df_results = pd.DataFrame(results)
    df_results["status"] = status
    df_results["total_cost"] = pulp.value(total_cost)
    df_results["stored_energy_price"] = storage_price
    df_results["stored_energy_value"] = pulp.value(stored_energy_value)
    df_results["objective"] = pulp.value(problem.objective)

    logger.debug("Optimization result shape: %s", df_results.shape)
    return df_results
