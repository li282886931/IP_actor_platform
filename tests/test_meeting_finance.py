from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import ShowCalculationIn
from app.services.finance import calculate_show_result
from test_main import make_test_client
import main as app_module


def complete_inputs(**overrides):
    return {
        "project_id": 1, "venue_capacity": 1000, "expected_attendance": 800,
        "avg_ticket_price": 100, "artist_fee": 20000, "venue_cost": 10000,
        "marketing_cost": 5000, "production_cost": 5000,
        "security_cost": 0, "travel_cost": 0, "accommodation_cost": 0,
        "insurance_cost": 0, "approval_cost": 0, "contingency_cost": 0,
        "tax_fee_rate": 0.06, "ticketing_fee_rate": 0.04,
        **overrides,
    }


def test_fee_inputs_must_be_explicit_and_missing_funds_are_unknown():
    payload = ShowCalculationIn(**complete_inputs(tax_fee_rate=None, ticketing_fee_rate=None))
    result = calculate_show_result(SimpleNamespace(available_funds=None), payload)
    assert result["status"] == "pending_input"
    assert set(result["missing_fields"]) == {"tax_fee_rate", "ticketing_fee_rate"}

    result = calculate_show_result(
        SimpleNamespace(available_funds=None), ShowCalculationIn(**complete_inputs()),
    )
    assert result["funding_gap"] is None
    assert result["gross_ticket_revenue"] == 80000
    assert result["tax_amount"] == 4800
    assert result["ticketing_fee_amount"] == 3200
    assert result["roi"] == 0.8
    assert result["expected_occupancy_rate"] == 0.8
    assert result["breakeven_capacity_feasible"] is True


@pytest.mark.parametrize("overrides", [
    {"artist_fee": -1}, {"avg_ticket_price": 0}, {"venue_capacity": 0},
    {"expected_attendance": 1001}, {"tax_fee_rate": -0.01},
    {"tax_fee_rate": 0.6, "ticketing_fee_rate": 0.4},
    {"neutral_occupancy_rate": 101}, {"conservative_occupancy_rate": 90},
    {"tax_fee_rate": float("nan")},
])
def test_invalid_financial_inputs_rejected(overrides):
    with pytest.raises(ValidationError):
        ShowCalculationIn(**complete_inputs(**overrides))


def test_zero_occupancy_and_sponsor_covered_cost_do_not_produce_negative_breakeven():
    result = calculate_show_result(SimpleNamespace(available_funds=0), ShowCalculationIn(
        **complete_inputs(sponsorship_income=50000, conservative_occupancy_rate=0),
    ))
    assert result["scenarios"]["conservative"]["attendance"] == 0
    assert result["scenarios"]["conservative"]["profit"] == 10000
    assert result["breakeven_attendance"] == 0
    assert result["breakeven_occupancy_rate"] == 0
    assert result["recommended_min_ticket_price"] == 0


def test_full_version_snapshot_and_report_reuse_old_version(monkeypatch):
    client, session_factory = make_test_client(monkeypatch)
    try:
        project = client.post("/projects", json={
            "name": "真实参数核验", "available_funds": 30000,
        }).json()["data"]
        inputs = complete_inputs(project_id=project["id"], sponsorship_income=10000)
        calculation = client.post("/finance/show-calculation", json=inputs).json()["data"]
        db = session_factory()
        try:
            version = db.get(app_module.ProjectVersion, calculation["version_id"])
            assert version.input_snapshot["show_calculation"]["security_cost"] == 0
            assert version.input_snapshot["show_calculation"]["tax_fee_rate"] == 0.06
            assert version.input_snapshot["show_calculation"]["sponsorship_income"] == 10000
        finally:
            db.close()

        client.post("/finance/show-calculation", json={**inputs, "artist_fee": 90000})
        response = client.post(f"/projects/{project['id']}/feasibility-report", json={
            "version_id": calculation["version_id"], "use_ai_copy": False,
        })
        assert response.status_code == 200
        report = response.json()["data"]["calculation_result"]
        assert report["total_cost"] == 40000
        assert report["scenarios"]["neutral"]["net_profit"] == calculation["scenarios"]["neutral"]["profit"]
        assert report["scenarios"]["neutral"]["net_ticket_revenue"] == 72000
        assert report["tax_fee_rate"] == 0.06
        assert report["ticketing_fee_rate"] == 0.04
    finally:
        app_module.app.dependency_overrides.clear()


def test_report_without_real_deduction_rate_does_not_invent_default(monkeypatch):
    client, _ = make_test_client(monkeypatch)
    try:
        project = client.post("/projects", json={
            "name": "扣率待确认", **{k: v for k, v in complete_inputs().items()
                              if k in {"expected_attendance", "avg_ticket_price", "artist_fee",
                                       "venue_cost", "marketing_cost", "production_cost"}},
        }).json()["data"]
        response = client.post(f"/projects/{project['id']}/feasibility-report", json={})
        assert response.status_code == 400
        assert "tax_fee_rate" in response.json()["detail"]["missing_fields"]
    finally:
        app_module.app.dependency_overrides.clear()


def test_saved_project_capacity_is_validated_before_version_creation(monkeypatch):
    client, factory = make_test_client(monkeypatch)
    try:
        project = client.post("/projects", json={
            "name": "容量核验", "venue_capacity": 100, "avg_ticket_price": 100,
        }).json()["data"]
        inputs = complete_inputs(project_id=project["id"], expected_attendance=101)
        del inputs["venue_capacity"]
        response = client.post("/finance/show-calculation", json=inputs)
        assert response.status_code == 422
        db = factory()
        try:
            assert db.get(app_module.Project, project["id"]).expected_attendance is None
        finally:
            db.close()
    finally:
        app_module.app.dependency_overrides.clear()


def test_repeated_calculation_reuses_version_and_incomplete_input_clears_calculated_status(monkeypatch):
    client, factory = make_test_client(monkeypatch)
    try:
        project = client.post("/projects", json={"name": "重复测算核验"}).json()["data"]
        inputs = complete_inputs(project_id=project["id"])
        first = client.post("/finance/show-calculation", json=inputs).json()["data"]
        second = client.post("/finance/show-calculation", json=inputs).json()["data"]
        assert second["version_id"] == first["version_id"]
        pending = client.post("/finance/show-calculation", json={**inputs, "tax_fee_rate": None}).json()["data"]
        assert pending["status"] == "pending_input"
        assert pending["project_status"] == "pending_input"
        db = factory()
        try:
            assert db.query(app_module.ProjectVersion).filter_by(project_id=project["id"]).count() == 3
        finally:
            db.close()
    finally:
        app_module.app.dependency_overrides.clear()


def test_currency_deductions_reconcile_to_net_revenue():
    result = calculate_show_result(SimpleNamespace(available_funds=0), ShowCalculationIn(
        **complete_inputs(expected_attendance=3, avg_ticket_price=1, tax_fee_rate=0.25, ticketing_fee_rate=0.25),
    ))
    assert result["net_ticket_revenue"] == result["gross_ticket_revenue"] - result["tax_amount"] - result["ticketing_fee_amount"]
    for scenario in result["scenarios"].values():
        assert scenario["net_ticket_revenue"] == scenario["gross_ticket_revenue"] - scenario["tax_amount"] - scenario["ticketing_fee_amount"]
