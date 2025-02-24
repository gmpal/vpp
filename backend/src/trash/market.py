import pandas as pd

def simple_bidding_strategy(df: pd.DataFrame, markup: float = 0.05) -> pd.DataFrame:
    """
    Implements a simple bidding strategy:
    
    For each time step (row in the DataFrame):
      - Calculate net energy: net = (solar + wind) - load
      - If net > 0: submit a sell bid for 'net' at bid_price = market_price * (1 + markup)
      - If net < 0: submit a buy bid for '-net' at bid_price = market_price * (1 - markup)
      - If net == 0: no bid is submitted.
    
    The function returns a DataFrame with bid details and a simulated "result" (i.e. revenue or cost)
    assuming the trade clears at the forecasted market price.
    
    Parameters
    ----------
    df : pd.DataFrame
        Forecast data with columns ['solar', 'wind', 'load', 'price'] and a DateTime index.
    markup : float, optional
        The percentage markup (for sell bids) or markdown (for buy bids) to adjust the bid price.
        Default is 0.05 (i.e. 5%).
        
    Returns
    -------
    pd.DataFrame
        DataFrame with bid details for each time step.
        Columns include:
          - bid_type: 'sell', 'buy', or 'none'
          - quantity: Energy quantity to buy or sell (always positive)
          - bid_price: Price at which the bid is submitted
          - market_price: Forecasted market price at that time step
          - net: The net energy (surplus or deficit) computed
          - result: Revenue (if sell) or cost (if buy, expressed as a negative value)
    """
    
    bids = []
    
    for t, row in df.iterrows():
        # Extract the forecast values, defaulting to 0 if missing
        solar = row.get("solar", 0)
        wind = row.get("wind", 0)
        load = row.get("load", 0)
        market_price = row.get("price", 0)
        
        # Compute net production: positive means surplus, negative means deficit
        net = (solar + wind) - load
        
        if net > 0:
            # Surplus: submit a sell bid.
            bid_type = "sell"
            quantity = net  # energy available to sell
            bid_price = market_price * (1 + markup)
            # Revenue computed at the market clearing price (here, assumed equal to forecast)
            revenue = quantity * market_price  
            result = revenue  # positive revenue
        elif net < 0:
            # Deficit: submit a buy bid.
            bid_type = "buy"
            quantity = -net  # take the absolute value of net (energy needed)
            bid_price = market_price * (1 - markup)
            cost = quantity * market_price  
            result = -cost  # cost is negative (cash outflow)
        else:
            # No surplus or deficit: no bid.
            bid_type = "none"
            quantity = 0
            bid_price = market_price  # or could be left as None
            result = 0
        
        bids.append({
            "time": t,
            "bid_type": bid_type,
            "quantity": quantity,
            "bid_price": bid_price,
            "market_price": market_price,
            "net": net,
            "result": result,
        })
    
    df_bids = pd.DataFrame(bids)
    df_bids.set_index("time", inplace=True)
    return df_bids


# Example usage:
if __name__ == '__main__':
    # Assume you already have a function to load your forecast data.
    # For example, you might have a function similar to your load_optimization_data() function:
    #
    #   df = load_optimization_data(start='2024-01-01 00:00:00+00', end='2024-01-01 23:00:00+00')
    #
    # For demonstration purposes, let’s create a dummy DataFrame:
    date_range = pd.date_range(start="2024-01-01", periods=24, freq="H")
    data = {
        "solar": [max(0, 10 * (1 - abs(12 - t.hour) / 12)) for t in date_range],  # a simple bell curve
        "wind": [5] * 24,
        "load": [8] * 24,
        "price": [50 + t.hour for t in date_range]  # a price that increases over the day
    }
    df_forecast = pd.DataFrame(data, index=date_range)
    
    # Compute the bidding strategy:
    df_bids = simple_bidding_strategy(df_forecast, markup=0.05)
    print(df_bids.head(10))
