"""SPEC-008: OpenAPI 契約閘門。確定性,可硬擋。"""
from supervisor.models import GateStatus
from supervisor.openapi_gate import (validate_openapi, check_contract_coverage,
                                      contract_gate)

VALID = """
openapi: 3.0.3
info: {title: X, version: "1.0"}
paths:
  /orders:
    post: {operationId: createOrder, responses: {"201": {description: ok}}}
"""


def _spec(tmp_path, text):
    p = tmp_path / "openapi.yaml"
    p.write_text(text)
    return p


def test_missing_file_blocks(tmp_path):
    assert validate_openapi(tmp_path / "nope.yaml").status == GateStatus.BLOCK


def test_missing_required_keys_blocks(tmp_path):
    p = _spec(tmp_path, "openapi: 3.0.3\ninfo: {title: X, version: '1'}\n")  # no paths
    assert validate_openapi(p).status == GateStatus.BLOCK


def test_endpoint_without_operationid_blocks(tmp_path):
    p = _spec(tmp_path, """
openapi: 3.0.3
info: {title: X, version: "1.0"}
paths:
  /orders:
    post: {responses: {"201": {description: ok}}}
""")
    d = validate_openapi(p)
    assert d.status == GateStatus.BLOCK
    assert any("operationId" in r for r in d.reasons)


def test_valid_contract_allows(tmp_path):
    assert validate_openapi(_spec(tmp_path, VALID)).status == GateStatus.ALLOW


def test_missing_contract_test_blocks(tmp_path):
    spec = _spec(tmp_path, VALID)
    (tmp_path / "contract").mkdir()  # empty — no test for createOrder
    d = check_contract_coverage(spec, tmp_path / "contract")
    assert d.status == GateStatus.BLOCK
    assert any("createOrder" in r for r in d.reasons)


def test_coverage_satisfied_allows(tmp_path):
    spec = _spec(tmp_path, VALID)
    td = tmp_path / "contract"
    td.mkdir()
    (td / "t.py").write_text("def test_createOrder(): assert True")
    assert check_contract_coverage(spec, td).status == GateStatus.ALLOW


def test_gate_end_to_end(tmp_path):
    spec = _spec(tmp_path, VALID)
    td = tmp_path / "contract"
    td.mkdir()
    (td / "t.py").write_text("def test_createOrder(): pass")
    assert contract_gate(spec, td).status == GateStatus.ALLOW
