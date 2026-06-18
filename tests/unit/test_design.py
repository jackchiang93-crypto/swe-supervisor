"""Deterministic design-conformance tests. This is the trustworthy 'follows
design' check — no LLM, so the result is reproducible ground truth."""
from pathlib import Path

from supervisor.design_rules import DesignRules, check_design
from supervisor.models import GateStatus

RULES_YAML = """
layers:
  - name: domain
    paths: ["**/domain/**"]
    module: "myapp.domain"
  - name: infra
    paths: ["**/infra/**"]
    module: "myapp.infra"
forbidden:
  - from: domain
    to: infra
"""


def _rules(tmp_path):
    p = tmp_path / "rules.yaml"
    p.write_text(RULES_YAML)
    return DesignRules.load(p)


def test_domain_importing_infra_is_blocked(tmp_path):
    (tmp_path / "src" / "domain").mkdir(parents=True)
    f = "src/domain/order.py"
    (tmp_path / f).write_text("from myapp.infra import db\n\ndef place(): ...")
    d = check_design([f], _rules(tmp_path), root=tmp_path)
    assert d.status == GateStatus.BLOCK
    assert any("設計漂移" in r for r in d.reasons)


def test_domain_clean_is_allowed(tmp_path):
    (tmp_path / "src" / "domain").mkdir(parents=True)
    f = "src/domain/order.py"
    (tmp_path / f).write_text("from myapp.domain import money\n\ndef place(): ...")
    d = check_design([f], _rules(tmp_path), root=tmp_path)
    assert d.status == GateStatus.ALLOW


def test_infra_importing_domain_is_fine(tmp_path):
    # only domain→infra is forbidden; the reverse is allowed
    (tmp_path / "src" / "infra").mkdir(parents=True)
    f = "src/infra/db.py"
    (tmp_path / f).write_text("from myapp.domain import order")
    d = check_design([f], _rules(tmp_path), root=tmp_path)
    assert d.status == GateStatus.ALLOW
