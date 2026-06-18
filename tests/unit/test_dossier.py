"""SPEC-010: 專案檔案夾。聚合散落 SPEC + ADR + 進度。"""
from supervisor.dossier import discover_specs, spec_list, spec_show, overview


def _project(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / "design" / "adr").mkdir(parents=True)
    # 散落來源1:current.md 內的章節
    (tmp_path / "specs" / "current.md").write_text(
        "# 規格\n\n## SPEC-001 事件閘門\n需求A\n\n## SPEC-002 hook\n需求B\n")
    # 散落來源2:獨立檔
    (tmp_path / "specs" / "SPEC-007.md").write_text("# SPEC-007 Codex後端\n需求C")
    # ADR(只給 001 跟 007)
    (tmp_path / "design" / "adr" / "ADR-001.md").write_text("# ADR-001\n決策A")
    (tmp_path / "design" / "adr" / "ADR-007.md").write_text("# ADR-007\n決策C")
    # 進度
    (tmp_path / "tasks.yaml").write_text(
        "items:\n"
        "- id: P1\n  title: 閘門\n  spec: SPEC-001\n  verify:\n    file: specs/current.md\n"
        "- id: P7\n  title: codex\n  spec: SPEC-007\n  verify:\n    file: nope.txt\n")
    return tmp_path


def test_discovers_both_sources(tmp_path):
    _project(tmp_path)
    ids = {e.id for e in discover_specs(tmp_path)}
    assert {"SPEC-001", "SPEC-002", "SPEC-007"} <= ids  # current.md 章節 + 獨立檔都抓到


def test_adr_and_progress_linked(tmp_path):
    _project(tmp_path)
    by = {e.id: e for e in discover_specs(tmp_path)}
    assert by["SPEC-001"].adr_id == "ADR-001"
    assert by["SPEC-002"].adr_id is None          # 沒 ADR
    assert by["SPEC-001"].progress_state == "done"   # file 存在
    assert by["SPEC-007"].progress_state == "todo"   # nope.txt 不存在


def test_spec_list_renders(tmp_path):
    _project(tmp_path)
    out = spec_list(tmp_path)
    assert "SPEC-001" in out and "SPEC-007" in out and "共 3 個 SPEC" in out


def test_spec_show_includes_adr(tmp_path):
    _project(tmp_path)
    out = spec_show("SPEC-001", tmp_path)
    assert "需求A" in out and "決策A" in out      # spec 全文 + ADR 全文
    assert "SPEC-002" not in out                  # 只該這一條


def test_spec_show_missing(tmp_path):
    _project(tmp_path)
    assert "找不到" in spec_show("SPEC-999", tmp_path)


def test_overview_counts_and_full(tmp_path):
    _project(tmp_path)
    o = overview(full=False, root=tmp_path)
    assert "1/3" in o  # 只有 SPEC-001 done
    full = overview(full=True, root=tmp_path)
    assert "需求A" in full and "決策C" in full  # full 附全文
