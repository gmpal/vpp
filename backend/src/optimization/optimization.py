from typing import Any, Dict, List

import pandas as pd
import pulp

from backend.src.db import CrudManager, DatabaseManager
from backend.src.utils.logger import get_logger

db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)
logger = get_logger(__name__)


def load_optimization_data(start: str = None, end: str = None) -> pd.DataFrame:
    solar_ids = crud_manager.query_source_ids("solar")
    df_solar_total = None
    reference_index = None
    for s_id in solar_ids:
        df_solar = crud_manager.load_forecasted_data("solar", source_id=s_id, start=start, end=end)
        if df_solar_total is None:
            df_solar_total = df_solar.copy()
            reference_index = df_solar_total.index
        else:
            df_solar.index = reference_index
            df_solar_total["yhat"] = df_solar_total["yhat"].add(df_solar["yhat"], fill_value=0)
    if df_solar_total is None:
        df_solar_total = pd.DataFrame(
            columns=["solar"],
            index=(reference_index if reference_index is not None else pd.date_range(start or "2025-01-01", periods=1, freq="h")),
        )

    df_solar_total.rename(columns={"yhat": "solar"}, inplace=True)

    df_load = crud_manager.load_forecasted_data("load", source_id=None, start=start, end=end)
    df_load.rename(columns={"yhat": "load"}, inplace=True)

    df_market = crud_manager.load_forecasted_data("market", source_id=None, start=start, end=end)
    df_market.rename(columns={"yhat": "price"}, inplace=True)

    df_solar_total = df_solar_total["solar"].to_frame()
    df_load = df_load["load"].to_frame()
    df_market = df_market["price"].to_frame()

    reference_index = df_solar_total.index
    df_load.index = reference_index
    df_market.index = reference_index

    df = pd.concat([df_solar_total, df_load, df_market], axis=1)
    logger.debug("Optimization input shape: %s", df.shape)
    return df


def optimize(
    evs: List[Dict[str, Any]],
    start: str = None,
    end: str = None,
    batteries: List[Dict[str, Any]] = None,
    export_limit_kw: float = None,
    import_limit_kw: float = None,
) -> pd.DataFrame:
    """
    Performs an optimization over the specified time range [start, end],
    using the aggregated solar, load, and market price from the database,
    a list of EV dicts, optional stationary battery dicts, and optional
    grid export/import hard constraints.

    Parameters
    ----------
    evs : List[Dict[str, Any]]
        EV rows from the DB. Each dict must have: vehicle_id, capacity_kwh,
        soc_kwh, max_charge_kw, max_discharge_kw, eta.
    start : str
        Start time (inclusive).
    end : str
        End time (inclusive).
    batteries : List[Dict[str, Any]] | None
        Stationary battery_assets rows. Each dict must have: battery_id,
        capacity_kwh, soc_kwh, max_charge_kw, max_discharge_kw, eta.
    export_limit_kw : float | None
        Hard feeder export cap (kW). No constraint if None.
    import_limit_kw : float | None
        Hard feeder import cap (kW). No constraint if None.

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

    # Combine EVs and stationary batteries into a single asset list
    all_assets = list(evs)
    for b in (batteries or []):
        # Normalise field names: battery_assets uses battery_id, EVs use vehicle_id
        all_assets.append({
            "vehicle_id": b["battery_id"],
            "capacity_kwh": b["capacity_kwh"],
            "soc_kwh": b["soc_kwh"],
            "max_charge_kw": b["max_charge_kw"],
            "max_discharge_kw": b["max_discharge_kw"],
            "eta": b["eta"],
        })

    for asset in all_assets:
        b_label = asset["vehicle_id"]
        logger.debug(
            "Asset %s: max_charge_kw=%s, max_discharge_kw=%s, capacity_kwh=%s, soc_kwh=%s, eta=%s",
            b_label, asset["max_charge_kw"], asset["max_discharge_kw"],
            asset["capacity_kwh"], asset["soc_kwh"], asset["eta"],
        )

        for t in time_steps:
            battery_charge[(b_label, t)] = pulp.LpVariable(f"Charge_{b_label}_{t}", lowBound=0, upBound=asset["max_charge_kw"])
            battery_discharge[(b_label, t)] = pulp.LpVariable(f"Discharge_{b_label}_{t}", lowBound=0, upBound=asset["max_discharge_kw"])
            battery_soc[(b_label, t)] = pulp.LpVariable(f"SOC_{b_label}_{t}", lowBound=0, upBound=asset["capacity_kwh"])

        problem += battery_soc[(b_label, 0)] == asset["soc_kwh"]

        for t in time_steps:
            if t == 0:
                continue
            problem += (
                battery_soc[(b_label, t)]
                == battery_soc[(b_label, t - 1)]
                + asset["eta"] * battery_charge[(b_label, t)]
                - battery_discharge[(b_label, t)]
            )

    for t in time_steps:
        total_charge_t = pulp.lpSum([battery_charge[(b_label, t)] for b_label, _t in battery_charge if _t == t])
        total_discharge_t = pulp.lpSum([battery_discharge[(b_label, t)] for b_label, _t in battery_discharge if _t == t])

        net_excess = df["solar"].iloc[t] - df["load"].iloc[t] + total_charge_t - total_discharge_t

        problem += grid_sell[t] >= net_excess
        problem += grid_sell[t] >= 0
        problem += grid_sell[t] <= net_excess + M * (1 - delta[t])
        problem += grid_sell[t] <= M * delta[t]

        problem += grid_buy[t] >= -net_excess
        problem += grid_buy[t] >= 0
        problem += grid_buy[t] <= -net_excess + M * delta[t]
        problem += grid_buy[t] <= M * (1 - delta[t])

        # --- Grid hard constraints ---
        if export_limit_kw is not None:
            problem += grid_sell[t] <= export_limit_kw
        if import_limit_kw is not None:
            problem += grid_buy[t] <= import_limit_kw

    total_cost = pulp.lpSum([df["price"].iloc[t] * (grid_buy[t] - grid_sell[t]) for t in time_steps])
    problem += total_cost

    problem.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[problem.status]
    logger.info("Optimization status: %s", status)

    results = []
    for t in time_steps:
        gb = pulp.value(grid_buy[t])
        gs = pulp.value(grid_sell[t])
        for asset in all_assets:
            b_label = asset["vehicle_id"]
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
