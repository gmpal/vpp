from typing import Any, Dict, List

import pandas as pd
import pulp

from backend.src.db import CrudManager, DatabaseManager
from backend.src.utils.logger import get_logger

db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)
logger = get_logger(__name__)


def load_optimization_data(start: str = None, end: str = None) -> pd.DataFrame:
    # Aggregate all renewable forecasts (solar + wind)
    def _aggregate_renewable_forecasts(source_type, start, end):
        ids = crud_manager.query_source_ids(source_type)
        total = None
        ref_index = None
        for s_id in ids:
            df = crud_manager.load_forecasted_data(source_type, source_id=s_id, start=start, end=end)
            if total is None:
                total = df.copy()
                ref_index = total.index
            else:
                df.index = ref_index
                total["yhat"] = total["yhat"].add(df["yhat"], fill_value=0)
        return total, ref_index

    df_solar_total, reference_index = _aggregate_renewable_forecasts("solar", start, end)
    if df_solar_total is None:
        df_solar_total = pd.DataFrame(
            columns=["solar"],
            index=(reference_index if reference_index is not None else pd.date_range(start or "2025-01-01", periods=1, freq="h")),
        )

    df_solar_total.rename(columns={"yhat": "solar"}, inplace=True)

    # Add wind production
    df_wind_total, wind_ref = _aggregate_renewable_forecasts("wind", start, end)
    if df_wind_total is not None:
        df_wind_total.rename(columns={"yhat": "wind"}, inplace=True)
        if reference_index is None:
            reference_index = wind_ref
    else:
        df_wind_total = pd.DataFrame(
            {"wind": 0.0},
            index=(reference_index if reference_index is not None else pd.date_range(start or "2025-01-01", periods=1, freq="h")),
        )

    df_load = crud_manager.load_forecasted_data("load", source_id=None, start=start, end=end)
    df_load.rename(columns={"yhat": "load"}, inplace=True)

    df_market = crud_manager.load_forecasted_data("market", source_id=None, start=start, end=end)
    df_market.rename(columns={"yhat": "price"}, inplace=True)

    df_solar_total = df_solar_total["solar"].to_frame()
    df_wind_total = df_wind_total["wind"].to_frame()
    df_load = df_load["load"].to_frame()
    df_market = df_market["price"].to_frame()

    reference_index = df_solar_total.index
    df_wind_total.index = reference_index
    df_load.index = reference_index
    df_market.index = reference_index

    df = pd.concat([df_solar_total, df_wind_total, df_load, df_market], axis=1)
    df["wind"] = df["wind"].fillna(0)
    logger.debug("Optimization input shape: %s", df.shape)
    return df


def optimize(
    evs: List[Dict[str, Any]],
    start: str = None,
    end: str = None,
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
        Start time (inclusive).
    end : str
        End time (inclusive).

    Returns
    -------
    pd.DataFrame
        Columns: time, battery_id, charge, discharge, soc, grid_buy, grid_sell, status, total_cost.
    """
    df = load_optimization_data(start=start, end=end)

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

        problem += battery_soc[(b_label, 0)] == ev["soc_kwh"]

        for t in time_steps:
            if t == 0:
                continue
            problem += (
                battery_soc[(b_label, t)]
                == battery_soc[(b_label, t - 1)]
                + ev["eta"] * battery_charge[(b_label, t)]
                - battery_discharge[(b_label, t)]
            )

    for t in time_steps:
        total_charge_t = pulp.lpSum([battery_charge[(b_label, t)] for b_label, _t in battery_charge if _t == t])
        total_discharge_t = pulp.lpSum([battery_discharge[(b_label, t)] for b_label, _t in battery_discharge if _t == t])

        net_excess = df["solar"].iloc[t] + df["wind"].iloc[t] - df["load"].iloc[t] + total_charge_t - total_discharge_t

        problem += grid_sell[t] >= net_excess
        problem += grid_sell[t] >= 0
        problem += grid_sell[t] <= net_excess + M * (1 - delta[t])
        problem += grid_sell[t] <= M * delta[t]

        problem += grid_buy[t] >= -net_excess
        problem += grid_buy[t] >= 0
        problem += grid_buy[t] <= -net_excess + M * delta[t]
        problem += grid_buy[t] <= M * (1 - delta[t])

    total_cost = pulp.lpSum([df["price"].iloc[t] * (grid_buy[t] - grid_sell[t]) for t in time_steps])
    problem += total_cost

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
            })

    df_results = pd.DataFrame(results)
    df_results["status"] = status
    df_results["total_cost"] = pulp.value(total_cost)

    logger.debug("Optimization result shape: %s", df_results.shape)
    return df_results
