"""SPEC-011/012/013: provenance、formal gate、dashboard。"""
from supervisor.provenance import build_attestation
from supervisor.formal_gate import formal_gate
from supervisor.dashboard import render_dashboard
from supervisor.models import GateStatus


# --- SPEC-011 provenance ---
def test_attestation_has_required_fields(tmp_path):
    att = build_attestation(root=tmp_path)  # no git → degraded but complete shape
    for k in ("generated_at", "commit", "branch", "changed_files",
              "spec_refs", "design_refs", "progress", "note"):
        assert k in att


def test_attestation_degrades_without_git(tmp_path):
    att = build_attestation(root=tmp_path)
    assert att["commit"] is None and "無 git" in att["note"]


# --- SPEC-012 formal gate ---
def test_formal_no_models_allows(tmp_path):
    d = formal_gate(tmp_path / "formal")  # missing dir
    assert d.status == GateStatus.ALLOW
    assert "選配" in d.reasons[0]


def test_formal_model_without_toolchain_degrades(tmp_path, monkeypatch):
    monkeypatch.delenv("TLA_TOOLS", raising=False)
    fd = tmp_path / "formal"; fd.mkdir()
    (fd / "Spec.tla").write_text("---- MODULE Spec ----\n====")
    d = formal_gate(fd)
    assert d.status == GateStatus.ALLOW  # honest degrade, not fake-pass, not block
    assert "工具鏈缺" in d.reasons[0]


# --- SPEC-013 dashboard ---
def test_dashboard_is_self_contained_html(tmp_path):
    # minimal project
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "SPEC-001.md").write_text("# SPEC-001 閘門\n需求")
    html = render_dashboard(tmp_path)
    assert html.startswith("<!doctype html>")
    assert "SPEC-001" in html
    assert "http://" not in html and "https://" not in html  # no external links/CDN
    assert "進度" in html
