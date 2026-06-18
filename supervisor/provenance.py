"""Provenance — traceable record of what produced a change.

For an AI-generated change you want more than 'who merged it': which commit,
which files, which SPEC, which ADR, what the tests said. This builds a plain
JSON attestation (no crypto signing — SLSA/in-toto is future work needing CI +
OIDC). Tamper-evident enough for local single-dev traceability.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .progress import load_status


def _git(args: List[str], root: Path) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def build_attestation(base: str = "origin/main", root: str | Path = ".") -> dict:
    root = Path(root)
    head = _git(["rev-parse", "HEAD"], root)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    diff = _git(["diff", "--name-only", f"{base}...HEAD"], root)
    files = [f for f in diff.splitlines() if f.strip()]
    progress = [
        {"id": ts.id, "spec": ts.spec, "state": ts.state}
        for ts in (load_status(root / "tasks.yaml", root) if (root / "tasks.yaml").exists() else [])
    ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": head or None,
        "branch": branch or None,
        "base": base,
        "changed_files": files,
        "spec_refs": re.findall(r"SPEC-\d+", branch),
        "design_refs": re.findall(r"ADR-\d+", branch),
        "progress": progress,
        "note": "純記錄,未加密簽章(SLSA/in-toto 列未來)" if head else "無 git,記錄不完整",
    }
