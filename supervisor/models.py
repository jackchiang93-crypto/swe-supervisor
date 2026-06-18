"""Core decision types. Structured outputs, not free text.

Design note: `confidence` is NEVER an input to a gate decision. The blueprint
self-contradicted on this (said "don't trust model self-reported confidence"
then used it as a gate). Here confidence is observability-only metadata that
rides along for dashboards/metrics. Gate logic uses policy + evidence, period.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class GateStatus(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"  # pause for human; safe work continues elsewhere


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Machine-readable error codes. Blocked decisions MUST carry these so the
# calling agent can self-correct instead of guessing.
class ErrorCode(str, Enum):
    POLICY_BLOCK = "POLICY_BLOCK"
    SPEC_MISMATCH = "SPEC_MISMATCH"
    DESIGN_DRIFT = "DESIGN_DRIFT"
    TEST_FAILURE = "TEST_FAILURE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MANUAL_APPROVAL_REQUIRED = "MANUAL_APPROVAL_REQUIRED"
    DANGEROUS_COMMAND = "DANGEROUS_COMMAND"
    PROTECTED_PATH = "PROTECTED_PATH"
    INJECTION_SUSPECTED = "INJECTION_SUSPECTED"


class ToolEvent(BaseModel):
    event: str
    tool_name: str
    command: Optional[str] = None
    changed_files: List[str] = Field(default_factory=list)
    spec_refs: List[str] = Field(default_factory=list)
    design_refs: List[str] = Field(default_factory=list)
    risk: RiskLevel = RiskLevel.LOW


class GateDecision(BaseModel):
    status: GateStatus
    codes: List[ErrorCode] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)
    # observability ONLY — not used in gate logic
    confidence: float = 1.0

    def merge(self, other: "GateDecision") -> "GateDecision":
        """Most severe status wins: BLOCK > REVIEW > ALLOW."""
        order = {GateStatus.ALLOW: 0, GateStatus.REVIEW: 1, GateStatus.BLOCK: 2}
        worst = self if order[self.status] >= order[other.status] else other
        return GateDecision(
            status=worst.status,
            codes=self.codes + other.codes,
            reasons=self.reasons + other.reasons,
            required_actions=self.required_actions + other.required_actions,
            confidence=min(self.confidence, other.confidence),
        )


def allow(reason: str) -> GateDecision:
    return GateDecision(status=GateStatus.ALLOW, reasons=[reason])
