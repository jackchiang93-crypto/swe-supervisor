"""Top-level gate: combine command analysis, path policy, traceability.

Traceability fix: the blueprint hardcoded spec_refs=["SPEC-001"] in the hook,
so the check always passed — a rubber stamp. Here we verify the referenced spec
ID actually exists in the specs/ tree. A ref the agent invented won't resolve.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .models import ErrorCode, GateDecision, GateStatus, ToolEvent, allow
from .policy import Policy
from .sandbox import classify_command


def verify_spec_refs(refs: List[str], specs_dir: str | Path) -> GateDecision:
    """Each ref must resolve to a real spec ID in specs/*.md (e.g. 'SPEC-001')."""
    specs_dir = Path(specs_dir)
    if not refs:
        return GateDecision(
            status=GateStatus.BLOCK,
            codes=[ErrorCode.MISSING_EVIDENCE],
            reasons=["缺少 spec 參照,無法證明變更符合需求"],
            required_actions=["在任務/分支/PR 標明對應 spec ID"],
        )
    known: set[str] = set()
    if specs_dir.exists():
        for f in specs_dir.rglob("*.md"):
            known |= set(re.findall(r"\bSPEC-\d+\b", f.read_text(errors="ignore")))
    missing = [r for r in refs if r not in known]
    if missing:
        return GateDecision(
            status=GateStatus.BLOCK,
            codes=[ErrorCode.SPEC_MISMATCH],
            reasons=[f"spec 參照無法在 specs/ 解析: {missing}"],
            required_actions=["建立對應 spec 條目,或修正 spec ID"],
        )
    return allow(f"spec 參照已驗證: {refs}")


def validate_event(evt: ToolEvent, policy: Policy, specs_dir: str | Path = "specs") -> GateDecision:
    """Fast path: read-only commands with no file writes ALLOW without LLM/spec
    checks — zero latency, zero cost. Friction is the #1 adoption killer."""
    # 1. command risk (tokenized, fail-closed)
    if evt.command:
        verdict, reasons = classify_command(evt.command)
        if verdict == "review":
            return GateDecision(
                status=GateStatus.REVIEW,
                codes=[ErrorCode.DANGEROUS_COMMAND],
                reasons=reasons,
                required_actions=["人工確認後才執行此命令"],
            )
        if verdict == "allow" and not evt.changed_files:
            return allow("唯讀命令,快路徑放行")

    decision = allow("通過初步檢查")

    # 2. path policy (allowlist + hard-protected)
    if evt.changed_files:
        decision = decision.merge(policy.check_paths(evt.changed_files))
        # only require spec traceability for writes, and only if not already blocked
        if policy.require_spec_ref and decision.status != GateStatus.BLOCK:
            decision = decision.merge(verify_spec_refs(evt.spec_refs, specs_dir))

    return decision
