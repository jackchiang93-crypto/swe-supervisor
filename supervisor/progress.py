"""Progress board — derived from evidence, never hand-written.

The problem this solves: in a long session, asking "what's done?" forces a
re-read of the whole conversation, burning tokens. `supervisor status` answers
it in one compact board instead.

Critical design choice: a checkbox is NOT a human claim. It's the result of
running a verification — a test passes, a file exists, a design rule holds. A
hand-maintained checklist drifts and lies ("marked done, actually broken"). Here
[x] means "the machine just re-verified it", every time you run status.

tasks.yaml maps each work item (P1, P2, ...) to a verification:
  - test:  a command; done if exit 0
  - file/files: path glob(s); done if all exist
A task with no verify is 'unverified' — shown as [?], never silently [x].
"""

from __future__ import annotations

import glob
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class TaskStatus:
    id: str
    title: str
    spec: Optional[str]
    state: str          # done | todo | unverified | failing
    detail: str

    @property
    def mark(self) -> str:
        return {"done": "x", "todo": " ", "unverified": "?", "failing": "!"}[self.state]


def _verify(item: dict, root: Path) -> tuple[str, str]:
    v = item.get("verify")
    if not v:
        return "unverified", "無驗證方式"

    if "file" in v or "files" in v:
        pats = v.get("files") or [v["file"]]
        missing = [p for p in pats if not glob.glob(str(root / p))]
        if missing:
            return "todo", f"缺檔: {', '.join(missing)}"
        return "done", "檔案齊全"

    if "test" in v:
        res = subprocess.run(v["test"], shell=True, cwd=root,
                             capture_output=True, text=True)
        if res.returncode == 0:
            return "done", "測試通過"
        return "failing", f"測試失敗 (exit {res.returncode})"

    return "unverified", "驗證格式不明"


def load_status(tasks_path: str | Path, root: str | Path = ".") -> List[TaskStatus]:
    root = Path(root)
    data = yaml.safe_load(Path(tasks_path).read_text()) or {}
    out: List[TaskStatus] = []
    for item in data.get("items", []):
        state, detail = _verify(item, root)
        out.append(TaskStatus(
            id=item["id"],
            title=item.get("title", ""),
            spec=item.get("spec"),
            state=state,
            detail=detail,
        ))
    return out


def render_board(rows: List[TaskStatus]) -> str:
    lines = ["SWE Supervisor — 進度(每次執行重新驗證)"]
    for r in rows:
        spec = f" ({r.spec})" if r.spec else ""
        lines.append(f"[{r.mark}] {r.id} {r.title}{spec}  — {r.detail}")
    done = sum(1 for r in rows if r.state == "done")
    failing = sum(1 for r in rows if r.state == "failing")
    tail = f"\n{done}/{len(rows)} 已驗證完成"
    if failing:
        tail += f",{failing} 個標記為已做但測試掛了(!)"
    lines.append(tail)
    return "\n".join(lines)
