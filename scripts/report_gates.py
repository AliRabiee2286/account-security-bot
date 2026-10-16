import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.phase_gate import PHASE_1_GATE, PHASE_2_GATE

for gate in (PHASE_1_GATE, PHASE_2_GATE):
    print(f"Phase {gate.phase}: {gate.status.value}")
    for item in gate.blockers:
        print(f"  BLOCKED {item.code}: {item.description} ({item.evidence})")
