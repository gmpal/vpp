"""
Settlement service for monthly billing of community members.

Computes each member's net energy position over a billing period,
applies the community tariff, and produces per-household settlement lines.
"""

from typing import Any, Dict, List, Optional


def run_settlement(
    members: List[Dict[str, Any]],
    tariff: Dict[str, Any],
    net_kwh_by_household: Dict[str, float],
    run_id: str,
) -> List[Dict[str, Any]]:
    """
    Produce settlement lines for one billing run.

    Parameters
    ----------
    members : list of dicts
        Each dict must have at least 'household_id'.
    tariff : dict
        Must have 'import_rate', 'export_rate', 'feed_in_rate'.
    net_kwh_by_household : dict
        {household_id: net_kwh} where positive = net producer, negative = net consumer.
    run_id : str
        Settlement run ID to stamp on each line.

    Returns
    -------
    list of dicts with keys:
        line_id, run_id, household_id, net_kwh, cost, savings
    """
    import uuid

    import_rate = float(tariff.get("import_rate", 0.0))
    export_rate = float(tariff.get("export_rate", 0.0))
    feed_in_rate = float(tariff.get("feed_in_rate", 0.0))

    lines = []
    for member in members:
        hh_id = member["household_id"]
        net = net_kwh_by_household.get(hh_id, 0.0)

        if net < 0:
            # Net consumer: cost = abs(net) * import_rate; savings = 0
            cost = abs(net) * import_rate
            savings = 0.0
        else:
            # Net producer: cost = 0; savings from avoided import + feed-in
            cost = 0.0
            savings = net * (import_rate - export_rate + feed_in_rate)

        lines.append({
            "line_id": f"sl_{uuid.uuid4().hex[:12]}",
            "run_id": run_id,
            "household_id": hh_id,
            "net_kwh": round(net, 6),
            "cost": round(cost, 4),
            "savings": round(savings, 4),
        })

    return lines
