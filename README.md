# SWE Supervisor

> A governance layer that supervises AI coding agents — not another agent that writes code, but the gate that **stops one from going off the rails**. Integrates with Claude Code / Codex hooks and GitHub CI.
>
> 監督 AI coding agent 的治理層。不是另一個寫 code 的 agent,而是用來**擋它跑歪**的閘門。整合 Claude Code / Codex hooks 與 GitHub CI。

**English** · [繁體中文](#繁體中文)

---

## What it does

The core insight: an AI coding agent **is** the LLM. The supervisor doesn't need a second model to judge — it just feeds machine-readable verdicts back through a hook, and the agent reads them and self-corrects.

So the core enforcement needs **zero LLM API**:

| Nudge | Mechanism | Needs API? |
|---|---|---|
| You didn't reference a spec | spec ref must resolve in `specs/` | ❌ |
| You changed architecture without updating design | ADR ref must resolve in `design/adr/` | ❌ |
| You drifted from the layering | AST import rules | ❌ |
| You skipped QA | `validate-diff` runs tests, blocks on failure | ❌ |
| Dangerous command / protected path | tokenize + allowlist | ❌ |
| Semantic drift in a prose spec | LLM advisor (REVIEW-only) | ✅ optional |

The advisor "brain" for that last row is your choice:
- `supervisor review --backend codex` — uses your local Codex subscription, **no paid API**
- `supervisor review --backend anthropic` — paid API (optional `[llm]` dep)
- neither installed → advisor skipped, deterministic gates still hard-block

## Trust model (why it doesn't lie)

- **Deterministic checks own BLOCK/ALLOW** — tests, design rules, contract gate. Ground truth.
- **LLM is advisory only** — its verdict escalates to REVIEW at most, never auto-allow/block. Confidence is forced to 0 (never trusted as signal). Spec/diff inputs are injection-screened *before* reaching the model.
- **The supervisor can't disarm itself** — the policy file, `.claude/`, `.codex/`, workflows, secrets are hardcoded-protected; an agent edit to them is blocked.
- **Progress checkboxes are evidence, not claims** — `supervisor status` re-runs each verification every time; a box ticked but broken shows `!`.

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q

supervisor validate-event --tool Bash --command "rm -rf build"      # → review
supervisor validate-event --tool Write --file src/a.py --spec-ref SPEC-001  # → allow
supervisor status        # evidence-derived progress board
supervisor overview      # whole-project SWE dossier
```

## The governance loop

```
1. add/change a feature → supervisor new SPEC-NNN   # scaffolds spec + ADR + progress item
                          fill the spec/ADR, THEN code
2. coding              → gate blocks: no spec ref → block; touch architecture w/o ADR → block
3. done                → bind a verify (test/file) in tasks.yaml
                         supervisor status auto-ticks (the tick is a live re-check, can't lie)
4. review progress     → supervisor status  # 5-line board, no re-reading the conversation, no tokens burned
```

## Commands

| Command | When | What |
|---|---|---|
| `new SPEC-NNN` | before work | scaffold spec + ADR stub + progress item (spec-first, one command) |
| `validate-event` | before a tool runs | command risk + path allowlist + spec/design traceability |
| `validate-diff` | before merge | path policy + traceability + run tests |
| `review [--backend codex\|anthropic]` | code review | design-drift hard-block + LLM advisor (REVIEW-only) |
| `contract` | API changes | OpenAPI contract gate (valid + every endpoint has a contract test) |
| `formal` | high-risk modules | TLA+/Alloy gate (runs TLC if toolchain present, else honest degrade) |
| `pre-deploy` | before deploy | rollback/test evidence; production forces manual approval |
| `status` | anytime | evidence-derived progress board |
| `spec list` / `spec show SPEC-NNN` | anytime / before editing | list all specs (incl. ones inside current.md) / pull one spec + its ADR |
| `overview [--full]` | anytime | whole-project dossier: done / left; `--full` appends full text |
| `attest` | after a change | provenance JSON (commit ↔ spec ↔ diff ↔ progress) |
| `dashboard` | anytime | self-contained HTML dashboard |
| `install <repo>` | setup | drop the governance layer into any project |
| `claude-hook` / `codex-hook` | (wired by hooks) | PreToolUse gate for Claude Code / Codex |

## Integration

- **Claude Code** — `.claude/settings.json` wires `PreToolUse` → `supervisor claude-hook`. ALLOW = silent, REVIEW = ask, BLOCK = deny (reason + fix shown to the agent).
- **Codex** — copy `.codex/config.toml.example`; `supervisor codex-hook` (exit 2 = block).
- **GitHub** — `.github/workflows/ai-governor.yml` runs tests + contract gate + provenance as a PR gate.

## License

Apache-2.0

---

# 繁體中文

[English](#swe-supervisor) · **繁體中文**

## 這是什麼

核心認知:coding AI **本身就是** LLM。supervisor 不需要第二顆模型來判斷——它只把機器可讀的判決透過 hook 塞回去,agent 自己讀懂、自己回頭改。

所以核心督促**零 LLM API**:

| 督促 | 機制 | 要 API? |
|---|---|---|
| 你沒對到 spec | spec ref 須在 `specs/` 解析 | ❌ |
| 你改架構沒更新 design | ADR ref 須在 `design/adr/` 解析 | ❌ |
| 你偏離分層 | AST import 規則 | ❌ |
| QA 沒做 | `validate-diff` 跑測試,沒過就擋 | ❌ |
| 危險命令/動禁區 | tokenize + allowlist | ❌ |
| 散文 spec 的語意漂移 | LLM 顧問(REVIEW-only) | ✅ 選配 |

最後一項的「顧問腦」三選一:
- `supervisor review --backend codex` — 用本機 Codex 訂閱,**不付 API 錢**
- `supervisor review --backend anthropic` — 付費 API(`[llm]` 選用依賴)
- 都不裝 → 顧問跳過,確定性閘門照常硬擋

## 信任模型(為何它不騙人)

- **確定性檢查掌管 BLOCK/ALLOW** — 測試、設計規則、契約閘門。Ground truth。
- **LLM 只當顧問** — 判決最多升 REVIEW,絕不自動放行/阻擋。confidence 強制設 0(不當訊號)。spec/diff 輸入在進模型**前**先過注入篩檢。
- **supervisor 不能自我解除武裝** — policy 檔、`.claude/`、`.codex/`、workflow、secrets 硬編碼保護,agent 改不了。
- **進度勾是證據,不是宣稱** — `supervisor status` 每次重跑每項驗證;勾了但壞掉會顯示 `!`。

## 快速開始

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q

supervisor validate-event --tool Bash --command "rm -rf build"      # → review
supervisor status        # 證據推導的進度板
supervisor overview      # 全專案軟工總覽
```

## 治理閉環

```
1. 加/改功能 → supervisor new SPEC-NNN   # 生 spec+ADR+進度項,先填再動工
2. coding   → gate 擋:沒 spec 參照→擋;碰架構沒 ADR→擋
3. 做完     → tasks.yaml 綁 verify(test/file),supervisor status 自動打勾(當場重驗,不會騙人)
4. 看進度   → supervisor status  # 5 行打勾板,不用重讀對話、不燒 token
```

## 命令一覽

| 命令 | 時機 | 作用 |
|---|---|---|
| `new SPEC-NNN` | 開工前 | 生 spec+ADR stub+進度項(spec-first 一鍵) |
| `validate-event` | 工具使用前 | 命令風險 + 路徑 allowlist + spec/design 追溯 |
| `validate-diff` | 合併前 | 路徑政策 + 追溯 + 跑測試 |
| `review [--backend codex\|anthropic]` | code review | 設計漂移硬擋 + LLM 顧問(REVIEW-only) |
| `contract` | API 變更 | OpenAPI 契約閘門(有效 + 每端點有契約測試) |
| `formal` | 高風險模組 | TLA+/Alloy 閘門(有工具鏈跑 TLC,無則誠實降級) |
| `pre-deploy` | 部署前 | rollback/測試證據;production 強制人工批准 |
| `status` | 任何時候 | 證據推導的打勾進度板 |
| `spec list` / `spec show SPEC-NNN` | 任何時候 / 改功能前 | 列出所有 SPEC(含埋在 current.md 的)/ 拉出單一 SPEC + ADR |
| `overview [--full]` | 任何時候 | 全專案總覽:做到哪、剩多少;`--full` 附全文 |
| `attest` | 變更後 | 產生 provenance JSON(commit↔spec↔diff↔進度) |
| `dashboard` | 任何時候 | 產生自包含 HTML 儀表板 |
| `install <repo>` | 安裝 | 把治理層裝進任何專案 |
| `claude-hook` / `codex-hook` | (由 hook 呼叫) | Claude Code / Codex 的 PreToolUse 閘門 |

## 整合

- **Claude Code** — `.claude/settings.json` 設 `PreToolUse` → `supervisor claude-hook`。ALLOW=靜默、REVIEW=ask、BLOCK=deny(理由+修正建議回給 agent)。
- **Codex** — 複製 `.codex/config.toml.example`;`supervisor codex-hook`(exit 2=擋)。
- **GitHub** — `.github/workflows/ai-governor.yml` 跑測試+契約閘門+provenance 當 PR gate。

## 授權

Apache-2.0
