"""
P2P community surplus allocation engine.

Distributes surplus energy from producing households to consuming
households according to the community's active participation policy.

Supported policies
------------------
equal_share    – surplus is split equally among all consumers
proportional   – surplus shared proportionally to each consumer's shortfall
priority       – consumers served in the explicit priority_order list first
"""

from typing import Any, Dict, List, Optional


def allocate_surplus(
    surplus_by_household: Dict[str, float],
    demand_by_household: Dict[str, float],
    policy: str,
    community_id: str,
    interval_start: str,
    priority_order: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Compute allocation transfers for one time interval.

    Parameters
    ----------
    surplus_by_household : dict
        {household_id: net_kwh} for households with net > 0 (producers).
    demand_by_household : dict
        {household_id: abs_shortfall_kwh} for households with net < 0 (consumers).
    policy : str
        'equal_share' | 'proportional' | 'priority'
    community_id : str
        ID of the community (stamped on ledger entries).
    interval_start : str
        ISO timestamp for the interval (stamped on ledger entries).
    priority_order : list[str] | None
        Ordered list of household IDs (used only for 'priority' policy).

    Returns
    -------
    list of dicts with keys:
        community_id, interval_start, from_household_id,
        to_household_id, amount_kwh, policy
    """
    import uuid

    producers = {h: v for h, v in surplus_by_household.items() if v > 0}
    consumers = {h: v for h, v in demand_by_household.items() if v > 0}

    if not producers or not consumers:
        return []

    total_surplus = sum(producers.values())
    total_demand = sum(consumers.values())
    available = min(total_surplus, total_demand)

    entries = []

    if policy == "equal_share":
        share = available / len(consumers)
        for consumer_id, shortfall in consumers.items():
            amount = min(share, shortfall)
            if amount <= 0:
                continue
            for producer_id, prod_surplus in producers.items():
                transfer = min(amount, prod_surplus)
                if transfer > 0:
                    entries.append(_make_entry(
                        community_id, interval_start,
                        producer_id, consumer_id, transfer, policy,
                    ))
                    producers[producer_id] -= transfer
                    amount -= transfer
                if amount <= 0:
                    break

    elif policy == "proportional":
        for consumer_id, shortfall in consumers.items():
            share = available * (shortfall / total_demand)
            amount = min(share, shortfall)
            if amount <= 0:
                continue
            for producer_id in list(producers.keys()):
                prod_surplus = producers[producer_id]
                transfer = min(amount, prod_surplus)
                if transfer > 0:
                    entries.append(_make_entry(
                        community_id, interval_start,
                        producer_id, consumer_id, transfer, policy,
                    ))
                    producers[producer_id] -= transfer
                    amount -= transfer
                if amount <= 0:
                    break

    elif policy == "priority":
        ordered_consumers: List[str] = list(priority_order or [])
        # append any consumers not in priority list at the end
        for c in consumers:
            if c not in ordered_consumers:
                ordered_consumers.append(c)

        for consumer_id in ordered_consumers:
            shortfall = consumers.get(consumer_id, 0)
            if shortfall <= 0:
                continue
            amount = shortfall
            for producer_id in list(producers.keys()):
                prod_surplus = producers[producer_id]
                transfer = min(amount, prod_surplus)
                if transfer > 0:
                    entries.append(_make_entry(
                        community_id, interval_start,
                        producer_id, consumer_id, transfer, policy,
                    ))
                    producers[producer_id] -= transfer
                    amount -= transfer
                if amount <= 0:
                    break

    return entries


def _make_entry(
    community_id: str,
    interval_start: str,
    from_household_id: str,
    to_household_id: str,
    amount_kwh: float,
    policy: str,
) -> Dict[str, Any]:
    import uuid
    return {
        "ledger_id": f"led_{uuid.uuid4().hex[:12]}",
        "community_id": community_id,
        "interval_start": interval_start,
        "from_household_id": from_household_id,
        "to_household_id": to_household_id,
        "amount_kwh": round(amount_kwh, 6),
        "policy": policy,
    }
