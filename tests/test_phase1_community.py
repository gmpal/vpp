"""
Phase 1 unit tests: allocation engine, settlement service, and community API endpoints.
All tests use mocks so no real database is required.
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.src.dependencies import get_crud_manager
from backend.src.allocation import allocate_surplus
from backend.src.settlement import run_settlement


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def client(mock_crud):
    app.dependency_overrides[get_crud_manager] = lambda: mock_crud
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Allocation engine — equal_share
# ---------------------------------------------------------------------------

class TestAllocationEqualShare:
    def test_splits_surplus_equally(self):
        entries = allocate_surplus(
            surplus_by_household={"hh_A": 6.0},
            demand_by_household={"hh_B": 3.0, "hh_C": 3.0},
            policy="equal_share",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        to_B = sum(e["amount_kwh"] for e in entries if e["to_household_id"] == "hh_B")
        to_C = sum(e["amount_kwh"] for e in entries if e["to_household_id"] == "hh_C")
        assert abs(to_B - to_C) < 1e-6

    def test_no_entries_when_no_surplus(self):
        entries = allocate_surplus(
            surplus_by_household={},
            demand_by_household={"hh_B": 3.0},
            policy="equal_share",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        assert entries == []

    def test_no_entries_when_no_demand(self):
        entries = allocate_surplus(
            surplus_by_household={"hh_A": 5.0},
            demand_by_household={},
            policy="equal_share",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        assert entries == []

    def test_total_allocated_capped_by_surplus(self):
        entries = allocate_surplus(
            surplus_by_household={"hh_A": 2.0},
            demand_by_household={"hh_B": 5.0, "hh_C": 5.0},
            policy="equal_share",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        total = sum(e["amount_kwh"] for e in entries)
        assert total <= 2.0 + 1e-9

    def test_entry_has_required_fields(self):
        entries = allocate_surplus(
            surplus_by_household={"hh_A": 4.0},
            demand_by_household={"hh_B": 4.0},
            policy="equal_share",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        assert len(entries) > 0
        e = entries[0]
        for field in ("ledger_id", "community_id", "interval_start",
                      "from_household_id", "to_household_id", "amount_kwh", "policy"):
            assert field in e


# ---------------------------------------------------------------------------
# Allocation engine — proportional
# ---------------------------------------------------------------------------

class TestAllocationProportional:
    def test_larger_shortfall_gets_more(self):
        entries = allocate_surplus(
            surplus_by_household={"hh_A": 9.0},
            demand_by_household={"hh_B": 1.0, "hh_C": 3.0},
            policy="proportional",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        to_B = sum(e["amount_kwh"] for e in entries if e["to_household_id"] == "hh_B")
        to_C = sum(e["amount_kwh"] for e in entries if e["to_household_id"] == "hh_C")
        assert to_C > to_B

    def test_total_proportional_equals_min_of_surplus_and_demand(self):
        surplus = {"hh_A": 6.0}
        demand = {"hh_B": 2.0, "hh_C": 4.0}
        entries = allocate_surplus(
            surplus_by_household=surplus,
            demand_by_household=demand,
            policy="proportional",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
        )
        total = sum(e["amount_kwh"] for e in entries)
        expected = min(sum(surplus.values()), sum(demand.values()))
        assert abs(total - expected) < 1e-6


# ---------------------------------------------------------------------------
# Allocation engine — priority
# ---------------------------------------------------------------------------

class TestAllocationPriority:
    def test_first_in_list_served_first(self):
        entries = allocate_surplus(
            surplus_by_household={"hh_A": 3.0},
            demand_by_household={"hh_B": 2.0, "hh_C": 4.0},
            policy="priority",
            community_id="com_1",
            interval_start="2024-01-01T00:00:00Z",
            priority_order=["hh_B", "hh_C"],
        )
        to_B = sum(e["amount_kwh"] for e in entries if e["to_household_id"] == "hh_B")
        to_C = sum(e["amount_kwh"] for e in entries if e["to_household_id"] == "hh_C")
        # hh_B is priority; only 3 kWh available — hh_B gets 2, hh_C gets 1
        assert abs(to_B - 2.0) < 1e-6
        assert abs(to_C - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Settlement service
# ---------------------------------------------------------------------------

class TestSettlementService:
    def _tariff(self):
        return {"import_rate": 0.25, "export_rate": 0.10, "feed_in_rate": 0.05}

    def test_consumer_has_positive_cost(self):
        members = [{"household_id": "hh_A"}]
        lines = run_settlement(
            members=members,
            tariff=self._tariff(),
            net_kwh_by_household={"hh_A": -10.0},  # net consumer
            run_id="run_1",
        )
        assert len(lines) == 1
        assert lines[0]["cost"] == pytest.approx(10.0 * 0.25)
        assert lines[0]["savings"] == 0.0

    def test_producer_has_zero_cost_and_positive_savings(self):
        members = [{"household_id": "hh_A"}]
        lines = run_settlement(
            members=members,
            tariff=self._tariff(),
            net_kwh_by_household={"hh_A": 10.0},  # net producer
            run_id="run_1",
        )
        assert lines[0]["cost"] == 0.0
        assert lines[0]["savings"] > 0.0

    def test_neutral_household(self):
        members = [{"household_id": "hh_A"}]
        lines = run_settlement(
            members=members,
            tariff=self._tariff(),
            net_kwh_by_household={"hh_A": 0.0},
            run_id="run_1",
        )
        assert lines[0]["cost"] == 0.0
        assert lines[0]["savings"] == 0.0

    def test_line_has_required_fields(self):
        members = [{"household_id": "hh_A"}]
        lines = run_settlement(
            members=members,
            tariff=self._tariff(),
            net_kwh_by_household={"hh_A": -5.0},
            run_id="run_1",
        )
        for field in ("line_id", "run_id", "household_id", "net_kwh", "cost", "savings"):
            assert field in lines[0]

    def test_multiple_members(self):
        members = [{"household_id": "hh_A"}, {"household_id": "hh_B"}]
        lines = run_settlement(
            members=members,
            tariff=self._tariff(),
            net_kwh_by_household={"hh_A": -4.0, "hh_B": 8.0},
            run_id="run_1",
        )
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Community API — new CRUD endpoints (mock DB)
# ---------------------------------------------------------------------------

def _mock_community():
    return {
        "community_id": "com_test",
        "name": "Test Community",
        "export_limit_kw": 100.0,
        "import_limit_kw": 100.0,
        "created_at": "2024-01-01T00:00:00+00:00",
    }


def _auth_headers(client):
    """Create a valid JWT for tests."""
    from backend.api.auth import create_access_token
    token = create_access_token("usr_test")
    return {"Authorization": f"Bearer {token}"}


def _patch_auth(mock_crud):
    """Override get_current_user to return a test user without DB."""
    from backend.api import auth as auth_module
    app.dependency_overrides[auth_module.get_current_user] = lambda: {
        "user_id": "usr_test", "username": "testuser"
    }


class TestCommunityEndpoints:
    def test_create_community_returns_200_shape(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.create_community.return_value = _mock_community()
        response = client.post(
            "/api/community",
            json={"name": "Test Community", "export_limit_kw": 100.0, "import_limit_kw": 100.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Community"
        assert "community_id" in data

    def test_list_communities(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_all_communities.return_value = [_mock_community()]
        response = client.get("/api/community")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_community_not_found(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = None
        response = client.get("/api/community/nonexistent")
        assert response.status_code == 404

    def test_delete_community(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        response = client.delete("/api/community/com_test")
        assert response.status_code == 200

    def test_add_member(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.add_member.return_value = {
            "member_id": "mem_1",
            "community_id": "com_test",
            "household_id": "hh_1",
            "role": "member",
            "joined_at": "2024-01-01T00:00:00+00:00",
        }
        response = client.post(
            "/api/community/com_test/members",
            json={"household_id": "hh_1"},
        )
        assert response.status_code == 200

    def test_set_policy(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.set_participation_rule.return_value = {
            "rule_id": "rule_1",
            "community_id": "com_test",
            "policy": "equal_share",
            "priority_order": None,
            "effective_from": "2024-01-01T00:00:00+00:00",
        }
        response = client.post(
            "/api/community/com_test/policy",
            json={"policy": "equal_share"},
        )
        assert response.status_code == 200

    def test_set_invalid_policy(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        response = client.post(
            "/api/community/com_test/policy",
            json={"policy": "invalid_policy"},
        )
        assert response.status_code == 400

    def test_create_tariff(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.create_tariff.return_value = {
            "tariff_id": "tar_1",
            "community_id": "com_test",
            "name": "Standard",
            "import_rate": 0.25,
            "export_rate": 0.10,
            "feed_in_rate": 0.05,
        }
        response = client.post(
            "/api/community/com_test/tariffs",
            json={"name": "Standard", "import_rate": 0.25, "export_rate": 0.10},
        )
        assert response.status_code == 200

    def test_set_grid_limit(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.set_grid_limit.return_value = {
            "limit_id": "lim_1",
            "community_id": "com_test",
            "export_limit_kw": 50.0,
            "import_limit_kw": 80.0,
            "effective_from": "2024-01-01T00:00:00+00:00",
        }
        response = client.post(
            "/api/community/com_test/grid-limits",
            json={"export_limit_kw": 50.0, "import_limit_kw": 80.0},
        )
        assert response.status_code == 200

    def test_get_grid_limit_not_found(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.get_active_grid_limit.return_value = None
        response = client.get("/api/community/com_test/grid-limits")
        assert response.status_code == 404

    def test_add_battery_asset(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.create_battery_asset.return_value = {
            "battery_id": "bat_1",
            "household_id": "hh_1",
            "name": "Home Battery",
            "capacity_kwh": 10.0,
            "soc_kwh": 5.0,
            "max_charge_kw": 3.0,
            "max_discharge_kw": 3.0,
            "eta": 0.95,
        }
        response = client.post(
            "/api/community/com_test/batteries",
            json={
                "household_id": "hh_1",
                "name": "Home Battery",
                "capacity_kwh": 10.0,
                "soc_kwh": 5.0,
                "max_charge_kw": 3.0,
                "max_discharge_kw": 3.0,
            },
        )
        assert response.status_code == 200

    def test_allocate_no_policy(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.get_active_rule.return_value = None
        response = client.post(
            "/api/community/com_test/allocate",
            json={
                "interval_start": "2024-01-01T00:00:00Z",
                "surplus_by_household": {"hh_A": 5.0},
                "demand_by_household": {"hh_B": 3.0},
            },
        )
        assert response.status_code == 400

    def test_allocate_with_policy(self, client, mock_crud):
        _patch_auth(mock_crud)
        mock_crud.get_community.return_value = _mock_community()
        mock_crud.get_active_rule.return_value = {
            "rule_id": "rule_1",
            "community_id": "com_test",
            "policy": "equal_share",
            "priority_order": None,
            "effective_from": "2024-01-01T00:00:00+00:00",
        }
        mock_crud.save_allocation_ledger.return_value = None
        response = client.post(
            "/api/community/com_test/allocate",
            json={
                "interval_start": "2024-01-01T00:00:00Z",
                "surplus_by_household": {"hh_A": 5.0},
                "demand_by_household": {"hh_B": 3.0},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "allocated" in data
        assert "entries" in data
