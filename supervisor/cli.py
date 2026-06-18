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
    try:
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=3).stdout
        refs = _re.findall(r"SPEC-\d+", b)
    except Exception:
        pass
    evt = ToolEvent(
        event=payload.get("hook_event_name", "PreToolUse"),
        tool_name=payload.get("tool_name", "unknown"),
        command=ti.get("command"),
        changed_files=files,
        spec_refs=refs,
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
