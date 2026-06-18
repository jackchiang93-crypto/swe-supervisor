"""Policy engine: path allowlist, protected paths, injection screening.

Key fixes vs blueprint:
- Path control is allowlist-first (only allowed_paths may be auto-written),
  not denylist-first.
- The policy file and agent config dirs are protected BY DEFAULT and cannot be
  un-protected by an agent edit — the supervisor must not be able to disarm
  itself. (Blueprint's blocked_paths forgot to include the policy itself.)
- Untrusted text (spec/issue/README content) is screened for injection markers
  before it ever reaches an LLM prompt.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

from .models import ErrorCode, GateDecision, GateStatus, ToolEvent, allow

# These are ALWAYS protected regardless of policy file contents. Hardcoded so an
# agent cannot grant itself write access by editing default.yaml.
HARD_PROTECTED = [
    ".claude/**",
    ".codex/**",
    ".github/workflows/**",
    "policies/**",
    "*secret*", "**/*secret*",
    ".env*", "**/.env*",
    "infra/prod/**",
]

INJECTION_PATTERNS = re.compile(
    r"(ignore (all )?(previous|prior|above) instructions"
    r"|disregard .{0,20}instructions"
    r"|you are now"
    r"|system prompt"
    r"|reveal .{0,20}(prompt|key|secret)"
    r"|<\s*/?\s*(system|assistant)\s*>)",
    re.IGNORECASE,
)


@dataclass
class Policy:
    default_mode: GateStatus = GateStatus.REVIEW
    allowed_paths: List[str] = field(default_factory=lambda: ["src/**", "tests/**"])
    blocked_paths: List[str] = field(default_factory=list)
    require_spec_ref: bool = True
    require_design_ref: bool = False
    # changes touching these globs must carry an ADR ref (architecture surface)
    design_ref_paths: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        data = yaml.safe_load(Path(path).read_text()) or {}
        tp = data.get("tool_policy", {})
        w = tp.get("Write", {})
        return cls(
            default_mode=GateStatus(data.get("default_mode", "review")),
            allowed_paths=data.get("allowed_paths", ["src/**", "tests/**"]),
            blocked_paths=data.get("blocked_paths", []),
            require_spec_ref=w.get("require_spec_ref", True),
            require_design_ref=w.get("require_design_ref", False),
            design_ref_paths=w.get("design_ref_paths", []),
        )

    def needs_design_ref(self, files: List[str]) -> bool:
        if not self.require_design_ref:
            return False
        return any(
            fnmatch.fnmatch(f.removeprefix("./"), pat)
            for f in files for pat in self.design_ref_paths
        )

    def _protected(self) -> List[str]:
        return HARD_PROTECTED + self.blocked_paths

    def check_path(self, path: str) -> GateDecision:
        p = path.removeprefix("./")
        for pat in self._protected():
            if fnmatch.fnmatch(p, pat):
                return GateDecision(
                    status=GateStatus.BLOCK,
                    codes=[ErrorCode.PROTECTED_PATH],
                    reasons=[f"受保護路徑不可由 agent 修改: {p} (符合 {pat})"],
                    required_actions=["此變更需人工手動執行"],
                )
        if any(fnmatch.fnmatch(p, pat) for pat in self.allowed_paths):
            return allow(f"{p} 在 allowlist 內")
        return GateDecision(
            status=GateStatus.REVIEW,
            codes=[ErrorCode.POLICY_BLOCK],
            reasons=[f"{p} 不在 allowed_paths,預設需確認"],
            required_actions=["確認此路徑該被 AI 修改,或加入 allowed_paths"],
        )

    def check_paths(self, files: List[str]) -> GateDecision:
        d = allow("所有路徑通過")
        for f in files:
            d = d.merge(self.check_path(f))
        return d


def screen_injection(text: str, source: str) -> GateDecision:
    """Screen untrusted text before it reaches an LLM prompt."""
    if INJECTION_PATTERNS.search(text or ""):
        return GateDecision(
            status=GateStatus.REVIEW,
            codes=[ErrorCode.INJECTION_SUSPECTED],
            reasons=[f"來源 '{source}' 含疑似 prompt injection 指令"],
            required_actions=["人工檢視該內容,確認後才餵給模型"],
        )
    return allow(f"{source} 無注入跡象")
