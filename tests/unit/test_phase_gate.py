from app.core.phase_gate import GateItem, GateStatus, PhaseGate


def test_gate_blocks_on_one_missing_item():
    gate = PhaseGate("x", (GateItem("a", "a", True, "ok"), GateItem("b", "b", False, "missing")))
    assert gate.status is GateStatus.BLOCKED
    assert [x.code for x in gate.blockers] == ["b"]


def test_gate_passes_only_when_all_pass():
    gate = PhaseGate("x", (GateItem("a", "a", True, "ok"),))
    assert gate.status is GateStatus.PASS
