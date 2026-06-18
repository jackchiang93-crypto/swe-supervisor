"""Static HTML dashboard — one-glance project SWE status, no server.

Reuses dossier.discover_specs; emits a self-contained HTML file (inline CSS, no
CDN) you can open offline or attach to a PR.
"""

from __future__ import annotations

import html
from pathlib import Path

from .dossier import discover_specs

_COLOR = {"done": "#2e7d32", "todo": "#9e9e9e", "unverified": "#f9a825",
          "failing": "#c62828"}

_CSS = """
body{font-family:-apple-system,Segoe UI,sans-serif;margin:2rem;background:#fafafa;color:#222}
h1{font-size:1.4rem} .bar{height:14px;background:#e0e0e0;border-radius:7px;overflow:hidden;margin:.5rem 0}
.fill{height:100%;background:#2e7d32} table{border-collapse:collapse;width:100%;margin-top:1rem}
td,th{padding:.5rem .7rem;border-bottom:1px solid #eee;text-align:left;font-size:.92rem}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
.left{color:#c62828;font-weight:600}
"""


def render_dashboard(root: str | Path = ".") -> str:
    rows = discover_specs(root)
    total = len(rows)
    done = sum(1 for e in rows if e.progress_state == "done")
    pct = round(done / total * 100) if total else 0
    left = [e.id for e in rows if e.progress_state != "done"]

    trs = ""
    for e in rows:
        c = _COLOR.get(e.progress_state, "#9e9e9e")
        trs += (
            f"<tr><td><span class='dot' style='background:{c}'></span>{html.escape(e.id)}</td>"
            f"<td>{html.escape(e.title)}</td>"
            f"<td>{html.escape(e.adr_id or '—')}</td>"
            f"<td>{html.escape(e.progress_state)}</td></tr>"
        )

    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>SWE Supervisor Dashboard</title><style>{_CSS}</style></head><body>
<h1>SWE Supervisor — 專案軟工儀表板</h1>
<p>進度 <b>{done}/{total}</b>({pct}%)</p>
<div class="bar"><div class="fill" style="width:{pct}%"></div></div>
<p>未完成:<span class="left">{html.escape(', '.join(left) or '無')}</span></p>
<table><thead><tr><th>SPEC</th><th>標題</th><th>ADR</th><th>進度</th></tr></thead>
<tbody>{trs}</tbody></table>
<p style="color:#999;font-size:.8rem">由 supervisor dashboard 產生(靜態快照,重跑命令更新)</p>
</body></html>"""
