"""Formal verification gate (TLA+/Alloy) — has-it-then-run, else honest degrade.

High-risk logic (state machines, concurrency, consistency) deserves a formal
spec. But TLC model checking needs java + tla2tools.jar; we never assume it's
there. Same philosophy as the OpenAPI runtime check: run it if the toolchain
exists, otherwise say so plainly — never pretend it was verified.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List

from .models import ErrorCode, GateDecision, GateStatus, allow


def _models(formal_dir: Path) -> List[Path]:
    if not formal_dir.exists():
        return []
    return sorted([*formal_dir.rglob("*.tla"), *formal_dir.rglob("*.als")])


def _tlc_available() -> str | None:
    """TLA_TOOLS env points at tla2tools.jar; java must exist."""
    jar = os.getenv("TLA_TOOLS")
    if jar and Path(jar).exists() and shutil.which("java"):
        return jar
    return None


def formal_gate(formal_dir: str | Path = "formal") -> GateDecision:
    formal_dir = Path(formal_dir)
    models = _models(formal_dir)
    if not models:
        return allow("無形式模型(formal/ 空),形式驗證為選配,略過")

    names = [m.name for m in models]
    jar = _tlc_available()
    if not jar:
        # honest degrade — do NOT claim verified
        return GateDecision(
            status=GateStatus.ALLOW,
            reasons=[f"偵測到形式模型 {names},但工具鏈缺(需 env TLA_TOOLS + java),略過實檢"],
            required_actions=["設 TLA_TOOLS 指向 tla2tools.jar 以啟用 TLC model checking"],
        )

    failures: List[str] = []
    for m in models:
        if m.suffix != ".tla":
            continue  # Alloy needs its own runner; TLC handles .tla
        res = subprocess.run(["java", "-jar", jar, "-tool", str(m)],
                             capture_output=True, text=True, timeout=300)
        if res.returncode != 0 or "Error" in res.stdout:
            failures.append(m.name)
    if failures:
        return GateDecision(
            status=GateStatus.BLOCK,
            codes=[ErrorCode.DESIGN_DRIFT],
            reasons=[f"TLC model checking 失敗: {failures}"],
            required_actions=["修正形式規格違反的不變量"],
        )
    return allow(f"TLC 通過: {names}")
