"""OpenAPI contract gate — deterministic 'follows the API spec' check.

The trustworthy way to know code follows the API spec is to make the spec
machine-checkable. OpenAPI is the standard for HTTP APIs. This gate does two
deterministic checks (no LLM):

1. validate_openapi: the contract itself is structurally valid.
2. check_contract_coverage: every documented operationId has a contract test.

A documented endpoint with no contract test means the API surface can drift
unverified — so that's a BLOCK. This is traceability-level assurance (there IS a
test), not runtime conformance (the test PASSES against a live server) — the
latter needs schemathesis + a running app and is deliberately out of scope here.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from .models import ErrorCode, GateDecision, GateStatus, allow

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}


def validate_openapi(path: str | Path) -> GateDecision:
    p = Path(path)
    if not p.exists():
        return GateDecision(
            status=GateStatus.BLOCK,
            codes=[ErrorCode.SPEC_MISMATCH],
            reasons=[f"找不到 OpenAPI 契約: {p}"],
            required_actions=["建立 contracts/openapi.yaml"],
        )
    try:
        doc = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        return GateDecision(
            status=GateStatus.BLOCK, codes=[ErrorCode.SPEC_MISMATCH],
            reasons=[f"OpenAPI YAML 解析失敗: {e}"],
            required_actions=["修正 YAML 語法"],
        )
    missing = [k for k in ("openapi", "info", "paths") if k not in doc]
    if missing:
        return GateDecision(
            status=GateStatus.BLOCK, codes=[ErrorCode.SPEC_MISMATCH],
            reasons=[f"OpenAPI 缺必要鍵: {missing}"],
            required_actions=["補齊 openapi/info/paths"],
        )
    # every operation must carry an operationId (so it's traceable to a test)
    no_id: List[str] = []
    for route, ops in (doc.get("paths") or {}).items():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() in HTTP_METHODS and isinstance(op, dict):
                if not op.get("operationId"):
                    no_id.append(f"{method.upper()} {route}")
    if no_id:
        return GateDecision(
            status=GateStatus.BLOCK, codes=[ErrorCode.SPEC_MISMATCH],
            reasons=[f"端點缺 operationId(無法對應測試): {no_id}"],
            required_actions=["為每個端點加 operationId"],
        )
    return allow("OpenAPI 契約結構有效")


def operation_ids(path: str | Path) -> List[str]:
    doc = yaml.safe_load(Path(path).read_text()) or {}
    ids: List[str] = []
    for ops in (doc.get("paths") or {}).values():
        if not isinstance(ops, dict):
            continue
        for method, op in ops.items():
            if method.lower() in HTTP_METHODS and isinstance(op, dict) and op.get("operationId"):
                ids.append(op["operationId"])
    return ids


def check_contract_coverage(spec: str | Path, test_dir: str | Path) -> GateDecision:
    ids = operation_ids(spec)
    if not ids:
        return allow("契約無端點,無需覆蓋")
    test_dir = Path(test_dir)
    blob = ""
    if test_dir.exists():
        for f in test_dir.rglob("*.py"):
            blob += f.read_text(errors="ignore")
    # substring match: operationId 出現在測試任一處即算覆蓋(含 test_createOrder 這種命名)
    missing = [i for i in ids if i not in blob]
    if missing:
        return GateDecision(
            status=GateStatus.BLOCK, codes=[ErrorCode.MISSING_EVIDENCE],
            reasons=[f"文件化端點缺契約測試: {missing}"],
            required_actions=[f"在 {test_dir} 為這些 operationId 加契約測試"],
        )
    return allow(f"契約覆蓋齊全({len(ids)} 端點)")


def contract_gate(spec: str | Path, test_dir: str | Path) -> GateDecision:
    d = validate_openapi(spec)
    if d.status == GateStatus.BLOCK:
        return d
    return d.merge(check_contract_coverage(spec, test_dir))
