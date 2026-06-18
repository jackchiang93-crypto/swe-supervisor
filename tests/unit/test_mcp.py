"""SPEC-009: MCP server。測工具邏輯層(純函式),不啟動 MCP runtime。
驗證:核心不依賴 mcp、複用同一套規則、回合法結構。"""
from supervisor import mcp_server as M


def test_tool_logic_imports_without_mcp():
    # 純函式層不該 import mcp;能 import 本模組即證明(mcp 綁定是延遲的)
    assert callable(M.tool_validate_event)
    assert len(M.TOOLS) >= 4


def test_validate_event_dangerous_command():
    d = M.tool_validate_event("Bash", command="rm -rf build")
    assert d["status"] == "review"
    assert "DANGEROUS_COMMAND" in d["codes"]


def test_validate_diff_paths_protected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no policy file → default Policy
    d = M.tool_validate_diff_paths(["policies/default.yaml"])
    assert d["status"] == "block"
    assert "PROTECTED_PATH" in d["codes"]


def test_contract_tool(tmp_path):
    spec = tmp_path / "o.yaml"
    spec.write_text("""
openapi: 3.0.3
info: {title: X, version: "1.0"}
paths:
  /o: {get: {operationId: getO, responses: {"200": {description: ok}}}}
""")
    td = tmp_path / "c"; td.mkdir()
    (td / "t.py").write_text("def test_getO(): pass")
    d = M.tool_contract(str(spec), str(td))
    assert d["status"] == "allow"


def test_status_tool(tmp_path):
    (tmp_path / "tasks.yaml").write_text(
        "items:\n- id: X\n  title: t\n  verify:\n    file: nope.txt\n")
    d = M.tool_status(str(tmp_path / "tasks.yaml"))
    assert d["total"] == 1 and d["done"] == 0


def test_build_server_registers_tools():
    # binding layer works when mcp is installed
    srv = M.build_server()
    assert srv is not None
