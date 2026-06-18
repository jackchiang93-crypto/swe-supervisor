#!/usr/bin/env python3
"""Claude Code PreToolUse hook → supervisor gate.

Emits Claude's native PreToolUse JSON so the three gate states map cleanly:
  ALLOW  -> exit 0 silently (stay out of the way; let normal flow continue)
  REVIEW -> permissionDecision "ask"  (Claude prompts the human — HITL)
  BLOCK  -> permissionDecision "deny" (blocked; reason + fix shown to the agent
            so it can self-correct instead of guessing)

Spec refs come from the branch name (feat/SPEC-001-x), never hardcoded.
Finds policies/ relative to the project the hook runs in (cwd), so one install
serves any repo.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supervisor.core import validate_event
from supervisor.models import GateStatus, ToolEvent
from supervisor.policy import Policy


def branch_spec_refs() -> list[str]:
    try:
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=3).stdout
        return re.findall(r"SPEC-\d+", b)
    except Exception:
        return []


def emit(decision, cwd: Path) -> int:
    if decision.status == GateStatus.ALLOW:
        return 0  # silent, don't interrupt

    pd = "deny" if decision.status == GateStatus.BLOCK else "ask"
    reason = "; ".join(decision.reasons)
    if decision.required_actions:
        reason += " | 修正建議: " + "; ".join(decision.required_actions)
    if decision.codes:
        reason += " | codes: " + ",".join(c.value for c in decision.codes)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": pd,
            "permissionDecisionReason": reason,
        }
    }))
    return 0


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    ti = payload.get("tool_input", {})
    files = [p for p in (ti.get("file_path"), ti.get("path")) if p]
    evt = ToolEvent(
        event=payload.get("hook_event_name", "PreToolUse"),
        tool_name=payload.get("tool_name", "unknown"),
        command=ti.get("command"),
        changed_files=files,
        spec_refs=branch_spec_refs(),
    )
    cwd = Path(payload.get("cwd", "."))
    policy_path = cwd / "policies" / "default.yaml"
    policy = Policy.load(policy_path) if policy_path.exists() else Policy()
    decision = validate_event(evt, policy, cwd / "specs")
    return emit(decision, cwd)


if __name__ == "__main__":
    raise SystemExit(main())
