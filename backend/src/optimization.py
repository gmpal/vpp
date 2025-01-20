import pulp
import numpy as np
import pandas as pd
from battery import Battery

# -------------------------
# 1. Data Setup
# -------------------------

# Define time horizon (24 hours)
time_steps = list(range(24))

np.random.seed(42)  # for reproducibility
root = "./data/"
wind = pd.read_csv(root + "wind_turbine_power_output.csv", index_col=0).values
solar = pd.read_csv(root + "solar_panel_generation.csv", index_col=0).values
load = pd.read_csv(root + "synthetic_load_data.csv", index_col=0).values
price = pd.read_csv(root + "synthetic_market_price.csv", index_col=0).values

data = pd.concat(
    [
        pd.DataFrame(wind, columns=["wind"]),
        pd.DataFrame(solar, columns=["solar"]),
        pd.DataFrame(load, columns=["load"]),
        pd.DataFrame(price, columns=["price"]),
    ],
    axis=1,
)

print(data)
# -------------------------
# 2. Battery Parameters
# -------------------------
battery = Battery(
    capacity_kWh=10.0,
    current_soc_kWh=5.0,
    max_charge_kW=2.0,
    max_discharge_kW=2.0,
    round_trip_efficiency=0.95,
)

# -------------------------
# 3. Initialize Optimization Problem
# -------------------------
problem = pulp.LpProblem("VPP_Optimization", pulp.LpMinimize)

# -------------------------
# 4. Decision Variables
# -------------------------
battery_charge = pulp.LpVariable.dicts("Charge", time_steps, lowBound=0)
battery_discharge = pulp.LpVariable.dicts("Discharge", time_steps, lowBound=0)
battery_soc = pulp.LpVariable.dicts(
    "SOC", time_steps, lowBound=0, upBound=battery.capacity_kWh
)
grid_buy = pulp.LpVariable.dicts("GridBuy", time_steps, lowBound=0)
grid_sell = pulp.LpVariable.dicts("GridSell", time_steps, lowBound=0)
delta = pulp.LpVariable.dicts("Delta", time_steps, cat="Binary")

# Set initial SOC constraint
problem += battery_soc[0] == battery.soc_kWh

# -------------------------
# 5. Constraints
# -------------------------
M = 1000  # Big-M method for linearizing piecewise constraints

for t in time_steps:
    # Charge/Discharge limits
    problem += battery_charge[t] <= battery.max_charge_kW
    problem += battery_discharge[t] <= battery.max_discharge_kW

    # Battery capacity constraint
    problem += battery_soc[t] <= battery.capacity_kWh

    # SOC update constraint for t > 0
    if t > 0:
        # SOC(t) = SOC(t-1) + η*Charge(t) - Discharge(t)
        problem += (
            battery_soc[t]
            == battery_soc[t - 1]
            + battery.eta * battery_charge[t]
            - battery_discharge[t]
        )

    # Net excess energy calculation at time t
    net_excess = solar[t] + wind[t] - load[t] + battery_charge[t] - battery_discharge[t]

    # Constraints to set grid_buy and grid_sell based on net_excess
    # grid_sell[t] captures surplus energy available to sell
    problem += grid_sell[t] >= net_excess
    problem += grid_sell[t] >= 0

    # Upper bounds when net_excess positive
    problem += grid_sell[t] <= net_excess + M * (1 - delta[t])
    problem += grid_sell[t] <= M * delta[t]

    # grid_buy[t] captures energy needed from grid if deficit
    problem += grid_buy[t] >= -net_excess
    problem += grid_buy[t] >= 0

    # Upper bounds when net_excess negative
    problem += grid_buy[t] <= -net_excess + M * delta[t]
    problem += grid_buy[t] <= M * (1 - delta[t])

# -------------------------
# 6. Objective Function
# -------------------------
# Minimize total cost: cost of buying minus revenue from selling
total_cost = pulp.lpSum([price[t] * (grid_buy[t] - grid_sell[t]) for t in time_steps])
problem += total_cost

# -------------------------
# 7. Solve the Optimization Problem
# -------------------------
problem.solve()
print("Status:", pulp.LpStatus[problem.status])

# -------------------------
# 8. Extract and Display Results
# -------------------------
for t in time_steps:
    print(
        f"Time {t}: "
        f"Charge = {battery_charge[t].varValue:.2f} kW, "
        f"Discharge = {battery_discharge[t].varValue:.2f} kW, "
        f"SOC = {battery_soc[t].varValue:.2f} kWh, "
        f"GridBuy = {grid_buy[t].varValue:.2f} kW, "
        f"GridSell = {grid_sell[t].varValue:.2f} kW"
    )

print("Total Cost:", pulp.value(total_cost))

"""
Charge/Discharge Strategy: The battery is charged/discharged at various time steps to minimize total cost, taking advantage of times when electricity prices are low to charge and discharging when prices are high (or based on availability of renewable energy).
SOC Evolution: The state of charge (SOC) evolves over time according to the charging/discharging decisions while respecting battery constraints.
Grid Interaction: The grid buy/sell values show how much energy is drawn from or supplied to the grid at each time step to balance supply and demand, given the renewable generation, load, and battery operations.
Objective Value: The total cost indicates the minimized net cost of purchasing energy from the grid minus the revenue from selling energy to the grid over the 24-hour horizon.
"""
