"""Project dossier — one view over all spec + design + progress.

Aggregates three sources (no rules reimplemented; progress reused):
  - standalone specs/SPEC-NNN.md files
  - SPEC-NNN sections inside specs/current.md (headed `# SPEC-NNN ...`)
  - matching ADR design/adr/ADR-NNN.md
  - progress state from tasks.yaml via progress.load_status

Lets you, at any point: see what's done / what's left at a glance, and pull a
single SPEC's full text (plus its ADR) to review before changing it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .progress import load_status

SPEC_HEADING = re.compile(r"^#+\s*(SPEC-\d+)\b(.*)$", re.MULTILINE)


@dataclass
class SpecEntry:
    id: str
    title: str
    body: str
    source: str
    adr_id: Optional[str] = None
    adr_body: Optional[str] = None
    progress_state: str = "—"   # done/todo/unverified/failing/—(無對應任務)
    progress_detail: str = ""

    @property
    def mark(self) -> str:
        return {"done": "x", "todo": " ", "unverified": "?", "failing": "!"}.get(
            self.progress_state, "·")


def _num(spec_id: str) -> str:
    return spec_id.split("-")[1]


def discover_specs(root: str | Path = ".") -> List[SpecEntry]:
    root = Path(root)
    specs_dir = root / "specs"
    found: Dict[str, SpecEntry] = {}

    # 1. standalone SPEC-NNN.md (authoritative)
    for f in sorted(specs_dir.glob("SPEC-*.md")) if specs_dir.exists() else []:
        text = f.read_text(errors="ignore")
        m = SPEC_HEADING.search(text)
        sid = f.stem
        title = (m.group(2).strip() if m else "").strip() or sid
        found[sid] = SpecEntry(id=sid, title=title, body=text.strip(), source=str(f.relative_to(root)))

    # 2. sections inside current.md (only add ids not already standalone)
    cur = specs_dir / "current.md"
    if cur.exists():
        text = cur.read_text(errors="ignore")
        marks = list(SPEC_HEADING.finditer(text))
        for i, m in enumerate(marks):
            sid = m.group(1)
            if sid in found:
                continue
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            body = text[m.start():end].strip()
            found[sid] = SpecEntry(id=sid, title=m.group(2).strip() or sid,
                                   body=body, source="specs/current.md")

    # 3. link ADR + progress
    progress = {ts.spec: ts for ts in load_status(root / "tasks.yaml", root)} \
        if (root / "tasks.yaml").exists() else {}
    for sid, e in found.items():
        adr = root / "design" / "adr" / f"ADR-{_num(sid)}.md"
        if adr.exists():
            e.adr_id = f"ADR-{_num(sid)}"
            e.adr_body = adr.read_text(errors="ignore").strip()
        ts = progress.get(sid)
        if ts:
            e.progress_state = ts.state
            e.progress_detail = ts.detail

    return [found[k] for k in sorted(found, key=lambda s: _num(s))]


def spec_list(root: str | Path = ".") -> str:
    rows = discover_specs(root)
    lines = ["SPEC 一覽(所有規格,含 current.md 內章節)"]
    for e in rows:
        adr = e.adr_id or "無ADR"
        lines.append(f"[{e.mark}] {e.id} {e.title}  | {adr} | {e.progress_state}  ({e.source})")
    done = sum(1 for e in rows if e.progress_state == "done")
    lines.append(f"\n共 {len(rows)} 個 SPEC,{done} 個已驗證完成")
    return "\n".join(lines)


def spec_show(spec_id: str, root: str | Path = ".") -> str:
    spec_id = spec_id.upper()
    for e in discover_specs(root):
        if e.id == spec_id:
            out = [f"=== {e.id} ({e.source}) | 進度: {e.progress_state} {e.progress_detail} ===",
                   e.body]
            if e.adr_body:
                out += [f"\n=== 設計 {e.adr_id} ===", e.adr_body]
            else:
                out.append("\n(無對應 ADR)")
            return "\n".join(out)
    return f"找不到 {spec_id}。用 `supervisor spec list` 看所有。"


def overview(full: bool = False, root: str | Path = ".") -> str:
    rows = discover_specs(root)
    done = sum(1 for e in rows if e.progress_state == "done")
    left = [e for e in rows if e.progress_state != "done"]
    out = ["# 專案軟工總覽",
           f"進度: {done}/{len(rows)} SPEC 已驗證完成",
           f"未完成: {', '.join(e.id for e in left) or '無'}",
           "", "## 逐項狀態"]
    for e in rows:
        out.append(f"[{e.mark}] {e.id} {e.title}  | {e.adr_id or '無ADR'} | {e.progress_state}")
    if full:
        out.append("\n## 完整 spec + design")
        for e in rows:
            out.append(f"\n{'='*60}\n{spec_show(e.id, root)}")
    return "\n".join(out)
