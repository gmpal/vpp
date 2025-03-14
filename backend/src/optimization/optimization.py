import pulp
import pandas as pd
from typing import List
from backend.src.storage.battery import (
    Battery,
)  # or wherever your Battery class is located
from backend.src.db import DatabaseManager, CrudManager

# TODO: right now this is aligned with the forecasted values
# change accordignly, if we extend the forecasting table

db_manager = DatabaseManager()
crud_manager = CrudManager(db_manager)


def load_optimization_data(start: str = None, end: str = None) -> pd.DataFrame:

    solar_ids = crud_manager.query_source_ids("solar")
    df_solar_total = None
    reference_index = None
    for s_id in solar_ids:
        df_solar = crud_manager.load_forecasted_data(
            "solar", source_id=s_id, start=start, end=end
        )
        if df_solar_total is None:
            df_solar_total = df_solar.copy()
            reference_index = df_solar_total.index
        else:
            # Sum the 'value' columns
            # reindex
            df_solar.index = reference_index
            df_solar_total["yhat"] = df_solar_total["yhat"].add(
                df_solar["yhat"], fill_value=0
            )
    if df_solar_total is None:
        df_solar_total = pd.DataFrame(
            columns=["solar"],
            index=(
                reference_index
                if reference_index is not None
                else pd.date_range(start or "2025-01-01", periods=1, freq="h")
            ),
        )

    df_solar_total.rename(columns={"yhat": "solar"}, inplace=True)

    # 1b) Aggregate all wind
    wind_ids = crud_manager.query_source_ids("wind")
    df_wind_total = None
    for w_id in wind_ids:
        df_wind = crud_manager.load_forecasted_data(
            "wind", source_id=w_id, start=start, end=end
        )
        if df_wind_total is None:
            df_wind_total = df_wind.copy()
            reference_index = df_wind_total.index
        else:
            # Sum the 'value' columns
            # reindex
            df_wind.index = reference_index
            df_wind_total["yhat"] = df_wind_total["yhat"].add(
                df_wind["yhat"], fill_value=0
            )
    if df_wind_total is None:
        df_wind_total = pd.DataFrame(
            columns=["wind"],
            index=(
                reference_index
                if reference_index is not None
                else pd.date_range(start or "2025-01-01", periods=1, freq="h")
            ),
        )
    df_wind_total.rename(columns={"yhat": "wind"}, inplace=True)

    # 1c) Load load and market price
    df_load = crud_manager.load_forecasted_data(
        "load", source_id=None, start=start, end=end
    )
    df_load.rename(columns={"yhat": "load"}, inplace=True)

    df_market = crud_manager.load_forecasted_data(
        "market", source_id=None, start=start, end=end
    )
    df_market.rename(columns={"yhat": "price"}, inplace=True)

    df_solar_total = df_solar_total["solar"].to_frame()
    df_wind_total = df_wind_total["wind"].to_frame()
    df_load = df_load["load"].to_frame()
    df_market = df_market["price"].to_frame()

    reference_index = df_solar_total.index
    df_wind_total.index = reference_index
    df_load.index = reference_index
    df_market.index = reference_index

    # 1d) Combine everything into one DataFrame
    # We do an outer join on index (time), fill missing with 0
    df = pd.concat([df_solar_total, df_wind_total, df_load, df_market], axis=1)
    # Ensure we have an hourly frequency in time
    # (adjust if your data is already guaranteed to be hourly)
    # TODO: adjust when moving back to hourr
    # df = df.asfreq("h", fill_value=0)
    print("The shape of the data before optimization is: ", df.shape)
    return df


def optimize(
    batteries: List[Battery],
    start: str = None,
    end: str = None,
) -> pd.DataFrame:
    """
    Performs an optimization over the specified time range [start, end],
    using the aggregated wind, solar, load, and market price from the database,
    and multiple Battery objects.

    Parameters
    ----------
    batteries : List[Battery]
        A list of Battery objects to be optimized (charge/discharge schedules).
    start : str
        Start time (inclusive), e.g. '2024-01-01 00:00:00+00'.
    end : str
        End time (inclusive), e.g. '2024-01-01 23:59:59+00'.

    Returns
    -------
    pd.DataFrame
        DataFrame with the optimization results. Columns include:
        ['time', 'battery_id', 'charge', 'discharge', 'soc', 'grid_buy', 'grid_sell'].
        The DataFrame contains one row per time step per battery.
    """

    # --------------------------------------------------------------------------
    # 1. Load and prepare data from the database
    # --------------------------------------------------------------------------
    # Example using the provided helper functions load_historical_data and query_source_ids.
    # We'll sum up all wind, sum up all solar from all source IDs, then merge with load & price.

    # 1a) Aggregate all solar
    df = load_optimization_data(start=start, end=end)

    # Our time steps are simply enumerated from 0..N-1
    time_index = df.index
    time_steps = range(len(time_index))
    print("The time steps of the data is: ", time_steps)
    # --------------------------------------------------------------------------
    # 2. Set up the PuLP problem
    # --------------------------------------------------------------------------
    problem = pulp.LpProblem("VPP_Optimization", pulp.LpMinimize)

    # Decision variables for each time and each battery
    # We'll store them in dictionaries keyed by (battery_id, t).
    battery_charge = {}
    battery_discharge = {}
    battery_soc = {}

    # For the aggregator's grid buy / sell, we assume *one* aggregator node
    grid_buy = pulp.LpVariable.dicts("GridBuy", time_steps, lowBound=0)
    grid_sell = pulp.LpVariable.dicts("GridSell", time_steps, lowBound=0)
    # Binary to control the big-M buy/sell logic
    delta = pulp.LpVariable.dicts("Delta", time_steps, cat=pulp.LpBinary)

    # --------------------------------------------------------------------------
    # 3. Define battery-related constraints
    # --------------------------------------------------------------------------
    M = 1_000  # Big-M for buy/sell constraints

    # Create variables for each battery
    for b_idx, bat in enumerate(batteries):
        print(
            f"Battery {bat.battery_id}: max_charge_kW={bat.max_charge_kW}, "
            f"max_discharge_kW={bat.max_discharge_kW}, capacity_kWh={bat.capacity_kWh}, "
            f"current_soc_kWh={bat.current_soc_kWh}, round_trip_efficiency={bat.round_trip_efficiency}"
        )
        # We'll label them based on battery ID or an index
        b_label = bat.battery_id if hasattr(bat, "battery_id") else f"bat{b_idx}"

        for t in time_steps:
            charge_var = pulp.LpVariable(
                f"Charge_{b_label}_{t}", lowBound=0, upBound=bat.max_charge_kW
            )
            discharge_var = pulp.LpVariable(
                f"Discharge_{b_label}_{t}", lowBound=0, upBound=bat.max_discharge_kW
            )
            soc_var = pulp.LpVariable(
                f"SOC_{b_label}_{t}", lowBound=0, upBound=bat.capacity_kWh
            )

            battery_charge[(b_label, t)] = charge_var
            battery_discharge[(b_label, t)] = discharge_var
            battery_soc[(b_label, t)] = soc_var

        # Initial SOC constraint for each battery
        problem += battery_soc[(b_label, 0)] == bat.current_soc_kWh

        # SOC update constraints
        for t in time_steps:
            if t == 0:
                continue
            # SOC(t) = SOC(t-1) + η * Charge(t) - Discharge(t)
            problem += (
                battery_soc[(b_label, t)]
                == battery_soc[(b_label, t - 1)]
                + (bat.round_trip_efficiency) * battery_charge[(b_label, t)]
                - battery_discharge[(b_label, t)]
            )

    # --------------------------------------------------------------------------
    # 4. Net excess and buy/sell constraints
    # --------------------------------------------------------------------------
    # For each time step, net_excess = (solar + wind) - load + sum of battery flows
    # battery flows = sum( Charge - Discharge ) across all batteries
    for t in time_steps:
        # Sum across all batteries
        total_battery_charge_t = pulp.lpSum(
            [battery_charge[(b_label, t)] for b_label, _t in battery_charge if _t == t]
        )
        total_battery_discharge_t = pulp.lpSum(
            [
                battery_discharge[(b_label, t)]
                for b_label, _t in battery_discharge
                if _t == t
            ]
        )

        net_excess = (
            df["solar"].iloc[t]
            + df["wind"].iloc[t]
            - df["load"].iloc[t]
            + total_battery_charge_t
            - total_battery_discharge_t
        )

        # Constraints:
        # grid_sell[t] >= net_excess and >= 0
        problem += grid_sell[t] >= net_excess
        problem += grid_sell[t] >= 0

        # grid_sell[t] <= net_excess + M*(1 - delta[t])
        # grid_sell[t] <= M*delta[t]
        problem += grid_sell[t] <= net_excess + M * (1 - delta[t])
        problem += grid_sell[t] <= M * delta[t]

        # grid_buy[t] >= -net_excess and >= 0
        problem += grid_buy[t] >= -net_excess
        problem += grid_buy[t] >= 0

        # grid_buy[t] <= -net_excess + M*delta[t]
        # grid_buy[t] <= M*(1 - delta[t])
        problem += grid_buy[t] <= -net_excess + M * delta[t]
        problem += grid_buy[t] <= M * (1 - delta[t])

    # --------------------------------------------------------------------------
    # 5. Objective function: Minimize total cost = sum over t of price[t] * (grid_buy[t] - grid_sell[t])
    # --------------------------------------------------------------------------
    total_cost = pulp.lpSum(
        [df["price"].iloc[t] * (grid_buy[t] - grid_sell[t]) for t in time_steps]
    )
    problem += total_cost

    # --------------------------------------------------------------------------
    # 6. Solve the optimization
    # --------------------------------------------------------------------------
    problem.solve(pulp.PULP_CBC_CMD(msg=0))  # or any other solver
    status = pulp.LpStatus[problem.status]
    print("Optimization Status:", status)

    # --------------------------------------------------------------------------
    # 7. Collect results
    # --------------------------------------------------------------------------
    # Build a DataFrame of results. We'll have one row per time step per battery,
    # plus columns for GridBuy and GridSell (shared across all).
    results = []
    for t in time_steps:
        # grid buy/sell for the aggregator
        gb = pulp.value(grid_buy[t])
        gs = pulp.value(grid_sell[t])

        for b_idx, bat in enumerate(batteries):
            b_label = bat.battery_id if hasattr(bat, "battery_id") else f"bat{b_idx}"
            c = pulp.value(battery_charge[(b_label, t)])
            d = pulp.value(battery_discharge[(b_label, t)])
            soc = pulp.value(battery_soc[(b_label, t)])

            row = {
                "time": time_index[t],
                "battery_id": b_label,
                "charge": c,
                "discharge": d,
                "soc": soc,
                "grid_buy": gb,
                "grid_sell": gs,
            }
            results.append(row)

    df_results = pd.DataFrame(results)
    df_results["status"] = status
    df_results["total_cost"] = pulp.value(total_cost)

    print("The shape of the data after optimization is: ", df_results.shape)
    # --------------------------------------------------------------------------
    # 8. Optionally update each Battery's final SoC or store states in the database
    #    if desired. For example:
    # --------------------------------------------------------------------------
    for b_idx, bat in enumerate(batteries):
        b_label = bat.battery_id if hasattr(bat, "battery_id") else f"bat{b_idx}"
        # Final SOC is the last time step's SOC from the solution
        final_soc = df_results.loc[df_results["battery_id"] == b_label, "soc"].iloc[-1]
        # Update your Battery object (if you want to keep track in memory)
        bat.current_soc_kWh = final_soc

        # If you want to store it in the DB as well, you can call your save_battery_state(bat).
        # from . import save_battery_state
        # save_battery_state(bat)

    return df_results
