import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import get_current_user
from backend.api.models import (
    BatteryAsset,
    BatteryAssetCreate,
    Community,
    CommunityCreate,
    CommunitySummary,
    GridConnectionLimit,
    GridConnectionLimitCreate,
    Member,
    MemberCreate,
    ParticipationRule,
    ParticipationRuleCreate,
    SettlementRun,
    SettlementRunCreate,
    Tariff,
    TariffCreate,
)
from backend.src.allocation import allocate_surplus
from backend.src.dependencies import get_crud_manager
from backend.src.settlement import run_settlement

router = APIRouter()


# ---------------------------------------------------------------------------
# Existing summary endpoint
# ---------------------------------------------------------------------------

@router.get("/community/summary", response_model=CommunitySummary)
def community_summary(
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return crud.get_community_summary(user_id=current_user["user_id"])


# ---------------------------------------------------------------------------
# Community CRUD
# ---------------------------------------------------------------------------

@router.post("/community", response_model=Community)
def create_community(
    body: CommunityCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community_id = f"com_{uuid.uuid4().hex[:12]}"
    result = crud.create_community(
        community_id=community_id,
        name=body.name,
        export_limit_kw=body.export_limit_kw,
        import_limit_kw=body.import_limit_kw,
        user_id=current_user["user_id"],
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create community")
    return result


@router.get("/community", response_model=List[Community])
def list_communities(
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    return crud.get_all_communities(user_id=current_user["user_id"])


@router.get("/community/{community_id}", response_model=Community)
def get_community(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return community


@router.delete("/community/{community_id}")
def delete_community(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    crud.delete_community(community_id)
    return {"detail": "Community deleted"}


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/members", response_model=Member)
def add_member(
    community_id: str,
    body: MemberCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    member_id = f"mem_{uuid.uuid4().hex[:12]}"
    result = crud.add_member(
        member_id=member_id,
        community_id=community_id,
        household_id=body.household_id,
        role=body.role,
    )
    if not result:
        raise HTTPException(status_code=409, detail="Household already a member")
    return result


@router.get("/community/{community_id}/members", response_model=List[Member])
def list_members(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return crud.get_members(community_id)


@router.delete("/community/{community_id}/members/{member_id}")
def remove_member(
    community_id: str,
    member_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    crud.remove_member(member_id)
    return {"detail": "Member removed"}


# ---------------------------------------------------------------------------
# Participation policy
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/policy", response_model=ParticipationRule)
def set_policy(
    community_id: str,
    body: ParticipationRuleCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    if body.policy not in ("equal_share", "proportional", "priority"):
        raise HTTPException(status_code=400, detail="Invalid policy")
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    return crud.set_participation_rule(
        rule_id=rule_id,
        community_id=community_id,
        policy=body.policy,
        priority_order=body.priority_order,
    )


@router.get("/community/{community_id}/policy", response_model=ParticipationRule)
def get_policy(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    rule = crud.get_active_rule(community_id)
    if not rule:
        raise HTTPException(status_code=404, detail="No policy set for this community")
    return rule


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/allocate")
def allocate(
    community_id: str,
    body: Dict[str, Any],
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    """
    Distribute surplus energy among members for one interval.

    Request body:
        interval_start (str): ISO timestamp for the interval.
        surplus_by_household (dict): {household_id: kwh} for producers (net > 0).
        demand_by_household (dict): {household_id: kwh} for consumers (shortfall, positive).
    """
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    rule = crud.get_active_rule(community_id)
    if not rule:
        raise HTTPException(status_code=400, detail="No participation policy set")

    interval_start = body.get("interval_start")
    surplus = body.get("surplus_by_household", {})
    demand = body.get("demand_by_household", {})

    if not interval_start:
        raise HTTPException(status_code=422, detail="interval_start is required")

    entries = allocate_surplus(
        surplus_by_household=surplus,
        demand_by_household=demand,
        policy=rule["policy"],
        community_id=community_id,
        interval_start=interval_start,
        priority_order=rule.get("priority_order"),
    )
    crud.save_allocation_ledger(entries)
    return {"allocated": len(entries), "entries": entries}


@router.get("/community/{community_id}/allocation-ledger")
def get_allocation_ledger(
    community_id: str,
    limit: int = 100,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return crud.get_allocation_ledger(community_id, limit=limit)


# ---------------------------------------------------------------------------
# Tariffs
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/tariffs", response_model=Tariff)
def create_tariff(
    community_id: str,
    body: TariffCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    tariff_id = f"tar_{uuid.uuid4().hex[:12]}"
    return crud.create_tariff(
        tariff_id=tariff_id,
        community_id=community_id,
        name=body.name,
        import_rate=body.import_rate,
        export_rate=body.export_rate,
        feed_in_rate=body.feed_in_rate,
    )


@router.get("/community/{community_id}/tariffs", response_model=List[Tariff])
def list_tariffs(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return crud.get_tariffs(community_id)


# ---------------------------------------------------------------------------
# Settlement
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/settle", response_model=SettlementRun)
def settle(
    community_id: str,
    body: SettlementRunCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")

    tariffs = crud.get_tariffs(community_id)
    if not tariffs:
        raise HTTPException(status_code=400, detail="No tariff configured for this community")
    tariff = tariffs[-1]  # Use most recently created tariff

    members = crud.get_members(community_id)
    if not members:
        raise HTTPException(status_code=400, detail="No members in community")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    crud.create_settlement_run(
        run_id=run_id,
        community_id=community_id,
        period_start=body.period_start,
        period_end=body.period_end,
    )
    crud.update_settlement_run_status(run_id, "running")

    try:
        net_kwh_by_household = {
            m["household_id"]: crud.get_household_net_kwh(
                m["household_id"], body.period_start, body.period_end
            )
            for m in members
        }
        lines = run_settlement(
            members=members,
            tariff=tariff,
            net_kwh_by_household=net_kwh_by_household,
            run_id=run_id,
        )
        crud.save_settlement_lines(lines)
        crud.update_settlement_run_status(run_id, "completed")
    except Exception as exc:
        crud.update_settlement_run_status(run_id, "failed")
        raise HTTPException(status_code=500, detail=str(exc))

    return crud.get_settlement_run(run_id)


@router.get("/community/{community_id}/settlement")
def list_settlement_runs(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return crud.get_settlement_runs(community_id)


@router.get("/community/{community_id}/settlement/{run_id}/lines")
def get_settlement_lines(
    community_id: str,
    run_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return crud.get_settlement_lines(run_id)


# ---------------------------------------------------------------------------
# Stationary battery assets
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/batteries", response_model=BatteryAsset)
def add_battery_asset(
    community_id: str,
    body: BatteryAssetCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    battery_id = f"bat_{uuid.uuid4().hex[:12]}"
    return crud.create_battery_asset(
        battery_id=battery_id,
        household_id=body.household_id,
        name=body.name,
        capacity_kwh=body.capacity_kwh,
        soc_kwh=body.soc_kwh,
        max_charge_kw=body.max_charge_kw,
        max_discharge_kw=body.max_discharge_kw,
        eta=body.eta,
    )


@router.get("/community/{community_id}/batteries", response_model=List[BatteryAsset])
def list_battery_assets(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    return crud.get_battery_assets_by_community(community_id)


@router.delete("/community/{community_id}/batteries/{battery_id}")
def remove_battery_asset(
    community_id: str,
    battery_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    crud.delete_battery_asset(battery_id)
    return {"detail": "Battery asset removed"}


# ---------------------------------------------------------------------------
# Grid connection limits
# ---------------------------------------------------------------------------

@router.post("/community/{community_id}/grid-limits", response_model=GridConnectionLimit)
def set_grid_limit(
    community_id: str,
    body: GridConnectionLimitCreate,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    limit_id = f"lim_{uuid.uuid4().hex[:12]}"
    return crud.set_grid_limit(
        limit_id=limit_id,
        community_id=community_id,
        export_limit_kw=body.export_limit_kw,
        import_limit_kw=body.import_limit_kw,
    )


@router.get("/community/{community_id}/grid-limits", response_model=GridConnectionLimit)
def get_grid_limit(
    community_id: str,
    crud=Depends(get_crud_manager),
    current_user: dict = Depends(get_current_user),
):
    community = crud.get_community(community_id, user_id=current_user["user_id"])
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    limit = crud.get_active_grid_limit(community_id)
    if not limit:
        raise HTTPException(status_code=404, detail="No grid limit configured")
    return limit
