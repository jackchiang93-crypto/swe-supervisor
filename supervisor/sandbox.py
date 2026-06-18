"""Command risk analysis.

The blueprint used `if "rm -rf" in cmd.lower()` — a substring denylist. Trivially
bypassed: `rm  -rf` (double space), `rm -r -f`, `$IFS`, aliases, base64,
`python -c "shutil.rmtree(...)"`. Denylists fail by construction.

Approach here: tokenize with shlex, normalize, then match on the *program* and
its flags. We treat the default posture as REVIEW for anything not on a known
read-only allowlist — fail closed, not open. This is conservative on purpose: a
supervisor that occasionally over-asks is safe; one that under-blocks is theatre.
"""

from __future__ import annotations

import re
import shlex
from typing import List, Optional, Tuple

# Programs that only read / are obviously safe to run unattended.
# Anything not here defaults to REVIEW (fail closed).
READONLY_ALLOWLIST = {
    "ls", "cat", "head", "tail", "grep", "rg", "find", "fd", "wc", "echo",
    "pwd", "which", "file", "stat", "diff", "tree", "sort", "uniq",
    "pytest", "python", "python3", "node", "npm", "pnpm", "yarn", "ruff",
    "mypy", "black", "flake8", "go", "cargo", "make",
    "git",  # git is gated further below
}

# Destructive program/flag signatures. Tokenized match, not substring.
DESTRUCTIVE = [
    ("rm", {"-rf", "-fr", "-r", "-f"}),       # any rm with recursive/force
    ("rmdir", set()),
    ("shred", set()),
    ("mkfs", set()),
    ("dd", set()),
    ("kubectl", {"delete"}),
    ("terraform", {"apply", "destroy"}),
    ("helm", {"delete", "uninstall"}),
    ("docker", {"system", "rmi", "volume"}),
]

# git subcommands that rewrite history / publish — always REVIEW.
GIT_DANGEROUS = {"push", "reset", "clean", "rebase", "filter-branch", "gc"}

# Shell metachars that defeat single-command analysis — chaining, subshells,
# eval, redirection into files. Presence => can't reason about it => REVIEW.
SHELL_EVASION = re.compile(r"(\|\||&&|;|`|\$\(|>\s*/|eval\b|base64\b|curl\b.*\|\s*sh)")


def _tokenize(cmd: str) -> Optional[List[str]]:
    try:
        return shlex.split(cmd)
    except ValueError:
        return None  # unbalanced quotes etc. — treat as opaque


def classify_command(cmd: str) -> Tuple[str, List[str]]:
    """Return (verdict, reasons). verdict in {allow, review, block}."""
    reasons: List[str] = []
    cmd = cmd.strip()
    if not cmd:
        return "allow", []

    if SHELL_EVASION.search(cmd):
        return "review", ["命令含 shell 串接/子shell/管道注入,無法靜態判讀 → 需人工確認"]

    tokens = _tokenize(cmd)
    if tokens is None:
        return "review", ["命令無法 tokenize(引號不對稱),拒絕自動放行"]

    prog = tokens[0].split("/")[-1]  # strip path
    flags = {t for t in tokens[1:] if t.startswith("-")}
    args = [t for t in tokens[1:] if not t.startswith("-")]

    for dprog, dflags in DESTRUCTIVE:
        if prog == dprog and (not dflags or flags & dflags or (dprog == "rm")):
            reasons.append(f"高風險命令 {prog} {' '.join(sorted(flags & dflags)) if dflags else ''}".strip())
            # rm without recursive flag on a single file is still review-worthy
            return "review", reasons

    if prog == "git" and args and args[0] in GIT_DANGEROUS:
        return "review", [f"git {args[0]} 會改寫歷史/發佈 → 需人工確認"]

    if prog in READONLY_ALLOWLIST:
        return "allow", []

    # Fail closed: unknown program => ask.
    return "review", [f"未知程式 '{prog}' 不在唯讀 allowlist → 預設需確認"]
