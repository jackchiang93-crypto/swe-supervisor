#!/usr/bin/env python3
"""Claude Code PreToolUse hook → supervisor.validate_event.

Reads hook JSON from stdin, builds a ToolEvent, runs the gate.
exit 2 => Claude blocks the tool call and shows stderr to the agent.

Spec refs are extracted from the branch name (e.g. feat/SPEC-001-foo) so they
are NOT hardcoded — the blueprint's rubber-stamp bug. No ref on branch => the
write will be blocked for missing evidence, which is the point.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supervisor.core import validate_event
from supervisor.models import ToolEvent
from supervisor.policy import Policy


def branch_spec_refs() -> list[str]:
    try:
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True).stdout
        return re.findall(r"SPEC-\d+", b)
    except Exception:
        return []


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    ti = payload.get("tool_input", {})
    files = [p for p in (ti.get("file_path"), ti.get("path")) if p]
    evt = ToolEvent(
        event=payload.get("event_name", "PreToolUse"),
        tool_name=payload.get("tool_name", "unknown"),
        command=ti.get("command"),
        changed_files=files,
        spec_refs=branch_spec_refs(),
    )
    policy_path = Path("policies/default.yaml")
    policy = Policy.load(policy_path) if policy_path.exists() else Policy()
    decision = validate_event(evt, policy)
    if decision.status.value != "allow":
        print(f"[{decision.status.value.upper()}] " + "; ".join(decision.reasons),
              file=sys.stderr)
        if decision.required_actions:
            print("→ " + "; ".join(decision.required_actions), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
