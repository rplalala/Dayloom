"""Optional restriction fields preserve historical decision and Repair wire shapes."""

from backend.app.policies.transport import TransportModeDecision
from backend.app.versions.v3.repair_models import RepairScope


def test_historical_mode_decision_does_not_gain_a_null_restriction():
    decision = TransportModeDecision(travel_mode="WALK", reason="default")
    assert decision.model_dump(mode="json") == {
        "travel_mode": "WALK",
        "reason": "default",
        "routing_preference": None,
    }
    restricted = TransportModeDecision(
        travel_mode="WALK", reason="default", allowed_modes=("WALK", "TRANSIT")
    )
    assert restricted.model_dump(mode="json")["allowed_modes"] == ["WALK", "TRANSIT"]


def test_historical_repair_scope_omits_absent_allowed_modes():
    scope = RepairScope(dates=(), permissions=(), target_ids=("target",))
    assert "allowed_transport_modes" not in scope.model_dump(mode="json")
    restricted = scope.model_copy(update={"allowed_transport_modes": ("WALK", "TRANSIT")})
    assert restricted.model_dump(mode="json")["allowed_transport_modes"] == ["WALK", "TRANSIT"]
