"""MCP server — sediments stable supervisor capabilities into callable tools.

hooks intercept passively; MCP lets the coding AI actively call supervisor
("check the contract before I touch the API", "what's the progress?").

Two layers (ADR-009):
  - tool-logic layer: plain functions returning dicts, reusing core/openapi_gate/
    progress. NO mcp import → unit-testable, importable without mcp installed.
  - binding layer: build_server() lazily imports FastMCP and registers the
    functions; main() runs stdio. Only this needs the mcp package.

Every tool reuses the same core the CLI uses — no rule is reimplemented here.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from .core import validate_event
from .models import RiskLevel, ToolEvent
from .openapi_gate import contract_gate
from .policy import Policy
from .progress import load_status


# ---- tool-logic layer (no mcp dependency) ----

def tool_validate_event(tool_name: str, command: str = "", changed_files: List[str] | None = None,
                        spec_refs: List[str] | None = None, design_refs: List[str] | None = None,
                        policy_path: str = "policies/default.yaml") -> dict:
    """Gate a single tool/command before the AI runs it."""
    pol = Policy.load(policy_path) if Path(policy_path).exists() else Policy()
    evt = ToolEvent(
        event="PreToolUse", tool_name=tool_name, command=command or None,
        changed_files=changed_files or [], spec_refs=spec_refs or [],
        design_refs=design_refs or [], risk=RiskLevel.LOW,
    )
    return validate_event(evt, pol).model_dump(mode="json")


def tool_validate_diff_paths(changed_files: List[str], spec_refs: List[str] | None = None,
                             policy_path: str = "policies/default.yaml") -> dict:
    """Gate a set of changed paths (allowlist + spec/design traceability)."""
    return tool_validate_event("Write", changed_files=changed_files,
                               spec_refs=spec_refs, policy_path=policy_path)


def tool_contract(spec: str = "contracts/openapi.yaml", tests: str = "tests/contract") -> dict:
    """Run the OpenAPI contract gate."""
    return contract_gate(spec, tests).model_dump(mode="json")


def tool_status(tasks: str = "tasks.yaml") -> dict:
    """Evidence-derived progress board (re-verifies each call)."""
    rows = load_status(tasks, ".")
    return {
        "items": [r.__dict__ for r in rows],
        "done": sum(1 for r in rows if r.state == "done"),
        "total": len(rows),
    }


TOOLS = [tool_validate_event, tool_validate_diff_paths, tool_contract, tool_status]


# ---- binding layer (needs mcp) ----

def build_server():
    from mcp.server.fastmcp import FastMCP
    server = FastMCP("swe-supervisor")
    for fn in TOOLS:
        server.tool()(fn)
    return server


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
