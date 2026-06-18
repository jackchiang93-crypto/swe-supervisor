"""CLI entry. Four control points: plan / validate-event / validate-diff / pre-deploy.

Exit codes: 0=allow, 2=block-or-review (so Claude/Codex hooks treat it as a
block and surface stderr to the agent). JSON always printed to stdout.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from .core import validate_event, verify_spec_refs
from .models import ErrorCode, GateDecision, GateStatus, RiskLevel, ToolEvent
from .policy import Policy, screen_injection


def _emit(decision: GateDecision) -> int:
    print(decision.model_dump_json(indent=2))
    return 0 if decision.status == GateStatus.ALLOW else 2


def _load_policy(args) -> Policy:
    p = Path(args.policy)
    return Policy.load(p) if p.exists() else Policy()


def cmd_validate_event(args) -> int:
    evt = ToolEvent(
        event=args.event,
        tool_name=args.tool,
        command=args.command,
        changed_files=args.file or [],
        spec_refs=args.spec_ref or [],
        risk=RiskLevel(args.risk),
    )
    return _emit(validate_event(evt, _load_policy(args), args.specs))


def cmd_validate_diff(args) -> int:
    """Gate a PR diff: changed files must pass path policy; staged changes must
    have spec refs; run the test command and fail on non-zero."""
    diff = subprocess.run(
        ["git", "diff", "--name-only", args.base + "...HEAD"],
        capture_output=True, text=True,
    )
    files = [f for f in diff.stdout.splitlines() if f.strip()]
    policy = _load_policy(args)
    decision = policy.check_paths(files)
    decision = decision.merge(verify_spec_refs(args.spec_ref or [], args.specs))

    if args.test_cmd:
        res = subprocess.run(args.test_cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            decision = decision.merge(GateDecision(
                status=GateStatus.BLOCK,
                codes=[ErrorCode.TEST_FAILURE],
                reasons=[f"測試失敗 (exit {res.returncode})"],
                required_actions=["修正失敗測試後再合併"],
            ))
    return _emit(decision)


def cmd_plan(args) -> int:
    """Screen spec/design inputs for injection before any model use."""
    text = Path(args.spec).read_text() if args.spec and Path(args.spec).exists() else ""
    decision = screen_injection(text, args.spec or "spec")
    print(decision.model_dump_json(indent=2))
    print("\n# plan 階段:輸入已過注入篩檢。接 LLM 時請把此文本當不可信資料,"
          "用 structured output 綁定輸出。", file=sys.stderr)
    return 0 if decision.status == GateStatus.ALLOW else 2


def cmd_pre_deploy(args) -> int:
    """Pre-deploy checklist. Production always requires manual approval."""
    missing = []
    if not args.rollback:
        missing.append("缺 rollback plan")
    if not args.tests_passed:
        missing.append("測試未通過")
    if missing:
        return _emit(GateDecision(
            status=GateStatus.BLOCK,
            codes=[ErrorCode.MISSING_EVIDENCE],
            reasons=missing,
            required_actions=["補齊部署前證據"],
        ))
    return _emit(GateDecision(
        status=GateStatus.REVIEW,
        codes=[ErrorCode.MANUAL_APPROVAL_REQUIRED],
        reasons=["production 部署一律人工批准"],
        required_actions=["人工核准後放行"],
    ))


def _hook_event_from_stdin() -> tuple[ToolEvent, Path, Policy]:
    payload = json.loads(sys.stdin.read() or "{}")
    ti = payload.get("tool_input", {})
    files = [f for f in (ti.get("file_path"), ti.get("path")) if f]
    import re as _re
    refs: list[str] = []
    adr_refs: list[str] = []
    try:
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=3).stdout
        refs = _re.findall(r"SPEC-\d+", b)
        adr_refs = _re.findall(r"ADR-\d+", b)
    except Exception:
        pass
    evt = ToolEvent(
        event=payload.get("hook_event_name", "PreToolUse"),
        tool_name=payload.get("tool_name", "unknown"),
        command=ti.get("command"),
        changed_files=files,
        spec_refs=refs,
        design_refs=adr_refs,
    )
    cwd = Path(payload.get("cwd", "."))
    pp = cwd / "policies" / "default.yaml"
    return evt, cwd, (Policy.load(pp) if pp.exists() else Policy())


def cmd_claude_hook(args) -> int:
    """PreToolUse hook. ALLOW=silent, REVIEW=ask, BLOCK=deny (Claude JSON)."""
    evt, cwd, policy = _hook_event_from_stdin()
    d = validate_event(evt, policy, cwd / "specs")
    if d.status == GateStatus.ALLOW:
        return 0
    reason = "; ".join(d.reasons)
    if d.required_actions:
        reason += " | 修正: " + "; ".join(d.required_actions)
    if d.codes:
        reason += " | codes: " + ",".join(c.value for c in d.codes)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny" if d.status == GateStatus.BLOCK else "ask",
        "permissionDecisionReason": reason,
    }}))
    return 0


def cmd_codex_hook(args) -> int:
    """Codex hook. exit 0=allow, exit 2=block/review (reason to stderr)."""
    evt, cwd, policy = _hook_event_from_stdin()
    d = validate_event(evt, policy, cwd / "specs")
    if d.status == GateStatus.ALLOW:
        return 0
    msg = f"[{d.status.value.upper()}] " + "; ".join(d.reasons)
    if d.required_actions:
        msg += " | 修正: " + "; ".join(d.required_actions)
    print(msg, file=sys.stderr)
    return 2


def cmd_install(args) -> int:
    """Drop governance config into a target repo. Cross-project core feature."""
    target = Path(args.path).resolve()
    if not target.is_dir():
        print(f"目標不存在: {target}", file=sys.stderr)
        return 1
    # .claude/settings.json
    cdir = target / ".claude"
    cdir.mkdir(exist_ok=True)
    settings = cdir / "settings.json"
    existing = json.loads(settings.read_text()) if settings.exists() else {}
    existing.setdefault("hooks", {})["PreToolUse"] = [{
        "matcher": "Bash|Edit|Write",
        "hooks": [{"type": "command", "command": "supervisor claude-hook"}],
    }]
    settings.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
    # policies + specs scaffolding
    pol = target / "policies"
    pol.mkdir(exist_ok=True)
    pf = pol / "default.yaml"
    if not pf.exists():
        src = Path(__file__).resolve().parent.parent / "policies" / "default.yaml"
        pf.write_text(src.read_text() if src.exists() else "default_mode: review\nallowed_paths: [\"src/**\", \"tests/**\"]\n")
    (target / "specs").mkdir(exist_ok=True)
    print(f"已安裝治理層到 {target}")
    print(f"  - {settings.relative_to(target)} (PreToolUse → supervisor claude-hook)")
    print(f"  - {pf.relative_to(target)}")
    print("調整 policies/default.yaml 的 allowed_paths 後即可用。")
    return 0


def cmd_review(args) -> int:
    """Does the code follow spec/design? Combines deterministic design-rule
    checks (own BLOCK) with the LLM advisor (REVIEW at most). Deterministic
    verdict wins on severity."""
    from .design_rules import DesignRules, check_design
    from .review import advisory_review

    diff = subprocess.run(
        ["git", "diff", "--name-only", args.base + "...HEAD"],
        capture_output=True, text=True,
    )
    files = [f for f in diff.stdout.splitlines() if f.strip()]

    from .models import allow as _allow
    decision = _allow("通過審查")

    # 1. deterministic design conformance (trustworthy → can BLOCK)
    rules_path = Path(args.rules)
    if rules_path.exists():
        rules = DesignRules.load(rules_path)
        decision = decision.merge(check_design(files, rules))

    # 2. LLM advisor (fuzzy → REVIEW at most), only if not already blocked
    if decision.status != GateStatus.BLOCK and not args.no_llm:
        spec = Path(args.spec).read_text() if args.spec and Path(args.spec).exists() else ""
        design = Path(args.design).read_text() if args.design and Path(args.design).exists() else ""
        full_diff = subprocess.run(
            ["git", "diff", args.base + "...HEAD"], capture_output=True, text=True
        ).stdout
        decision = decision.merge(advisory_review(spec, design, full_diff, args.backend))

    return _emit(decision)


SPEC_STUB = """# {id} {title}

## 需求
TODO: 這個功能要做什麼?完成定義是什麼?

## 完成定義(可驗證)
- [ ] TODO

## 對應 ADR
{adr}
"""

ADR_STUB = """# {adr}: {title}

狀態: proposed
日期: TODO

## 背景
TODO: 為何需要這個決策?

## 決策
TODO: 採用什麼架構/契約/邊界?

## 影響
TODO: 哪些模組受影響?有何取捨?

## 對應 spec
{id}
"""


def cmd_contract(args) -> int:
    """OpenAPI contract gate — deterministic, can BLOCK."""
    from .openapi_gate import contract_gate
    return _emit(contract_gate(args.spec, args.tests))


def cmd_new(args) -> int:
    """Scaffold a new work item: spec stub + ADR stub + tasks.yaml entry.
    Enforces 'declare spec+design BEFORE you code' as a single command."""
    spec_id = args.id.upper()
    if not spec_id.startswith("SPEC-"):
        print("id 須為 SPEC-NNN 格式,例如 SPEC-006", file=sys.stderr)
        return 1
    num = spec_id.split("-")[1]
    adr_id = f"ADR-{num}"
    title = args.title or "TODO"

    spec_file = Path("specs") / f"{spec_id}.md"
    adr_file = Path("design/adr") / f"{adr_id}.md"
    for f in (spec_file, adr_file):
        f.parent.mkdir(parents=True, exist_ok=True)
    if spec_file.exists() or adr_file.exists():
        print(f"已存在,不覆寫: {spec_file} / {adr_file}", file=sys.stderr)
        return 1
    spec_file.write_text(SPEC_STUB.format(id=spec_id, title=title, adr=adr_id))
    adr_file.write_text(ADR_STUB.format(adr=adr_id, title=title, id=spec_id))

    # append a tasks.yaml entry (unverified until you add a verify)
    tasks = Path(args.tasks)
    data = yaml.safe_load(tasks.read_text()) if tasks.exists() else {"items": []}
    data.setdefault("items", []).append({
        "id": args.task_id or spec_id,
        "title": title,
        "spec": spec_id,
        # no verify yet → shows as [?] until you wire a test/file
    })
    tasks.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))

    print(f"已建立:\n  {spec_file}\n  {adr_file}\n  tasks.yaml += {args.task_id or spec_id}")
    print("先填 spec/ADR,再開始 code。gate 會擋沒對到 spec 的變更。")
    return 0


def cmd_status(args) -> int:
    """Evidence-derived progress board. Re-verifies every item each run, so the
    checkboxes can't lie. Saves re-reading the whole conversation to ask
    'what's done?'."""
    from .progress import load_status, render_board
    rows = load_status(args.tasks, ".")
    if args.json:
        import json as _json
        print(_json.dumps([r.__dict__ for r in rows], ensure_ascii=False, indent=2))
    else:
        print(render_board(rows))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="supervisor")
    p.add_argument("--policy", default="policies/default.yaml")
    p.add_argument("--specs", default="specs")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("validate-event")
    e.add_argument("--event", default="PreToolUse")
    e.add_argument("--tool", default="Bash")
    e.add_argument("--command")
    e.add_argument("--file", action="append")
    e.add_argument("--spec-ref", action="append")
    e.add_argument("--risk", default="low", choices=[r.value for r in RiskLevel])
    e.set_defaults(func=cmd_validate_event)

    d = sub.add_parser("validate-diff")
    d.add_argument("--base", default="origin/main")
    d.add_argument("--spec-ref", action="append")
    d.add_argument("--test-cmd")
    d.set_defaults(func=cmd_validate_diff)

    pl = sub.add_parser("plan")
    pl.add_argument("--spec")
    pl.set_defaults(func=cmd_plan)

    pd = sub.add_parser("pre-deploy")
    pd.add_argument("--rollback", action="store_true")
    pd.add_argument("--tests-passed", action="store_true")
    pd.set_defaults(func=cmd_pre_deploy)

    rv = sub.add_parser("review")
    rv.add_argument("--base", default="origin/main")
    rv.add_argument("--spec")
    rv.add_argument("--design")
    rv.add_argument("--rules", default="design/rules.yaml")
    rv.add_argument("--no-llm", action="store_true", help="只跑確定性設計檢查")
    rv.add_argument("--backend", default="anthropic", choices=["anthropic", "codex"],
                    help="顧問驗證者腦:anthropic API(付費)或 codex(訂閱)")
    rv.set_defaults(func=cmd_review)

    ct = sub.add_parser("contract")
    ct.add_argument("--spec", default="contracts/openapi.yaml")
    ct.add_argument("--tests", default="tests/contract")
    ct.set_defaults(func=cmd_contract)

    nw = sub.add_parser("new")
    nw.add_argument("id", help="SPEC-NNN,例如 SPEC-006")
    nw.add_argument("--title")
    nw.add_argument("--task-id", help="進度板代號,如 P6(預設用 spec id)")
    nw.add_argument("--tasks", default="tasks.yaml")
    nw.set_defaults(func=cmd_new)

    st = sub.add_parser("status")
    st.add_argument("--tasks", default="tasks.yaml")
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_status)

    sub.add_parser("claude-hook").set_defaults(func=cmd_claude_hook)
    sub.add_parser("codex-hook").set_defaults(func=cmd_codex_hook)

    ins = sub.add_parser("install")
    ins.add_argument("path", help="目標 repo 路徑")
    ins.set_defaults(func=cmd_install)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
