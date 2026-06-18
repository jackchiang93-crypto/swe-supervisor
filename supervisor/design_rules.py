"""Deterministic design conformance: architecture import rules from ADRs.

This is the TRUSTWORTHY half of "does the code follow design". It does not ask
an LLM. It parses the AST, maps each changed file to an architecture layer, and
checks its imports against forbidden layer dependencies declared in
design/rules.yaml. A violation is ground truth → hard BLOCK.

Example rule: "domain layer must not import infra layer". If src/domain/x.py
does `from myapp.infra import db`, that's a fact, not an opinion.
"""

from __future__ import annotations

import ast
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml

from .models import ErrorCode, GateDecision, GateStatus, allow


@dataclass
class Layer:
    name: str
    paths: List[str]      # globs identifying files in this layer
    module: str           # import-path prefix owned by this layer, e.g. "myapp.infra"


@dataclass
class DesignRules:
    layers: List[Layer]
    forbidden: List[tuple[str, str]]  # (from_layer, to_layer)

    @classmethod
    def load(cls, path: str | Path) -> "DesignRules":
        data = yaml.safe_load(Path(path).read_text()) or {}
        layers = [Layer(l["name"], l["paths"], l["module"]) for l in data.get("layers", [])]
        forbidden = [(f["from"], f["to"]) for f in data.get("forbidden", [])]
        return cls(layers, forbidden)

    def layer_of_file(self, file: str) -> str | None:
        for layer in self.layers:
            if any(fnmatch.fnmatch(file, p) for p in layer.paths):
                return layer.name
        return None

    def module_prefix(self, layer_name: str) -> str | None:
        for layer in self.layers:
            if layer.name == layer_name:
                return layer.module
        return None


def _imports(src: str) -> List[str]:
    """Extract imported module paths from Python source."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    mods: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    return mods


def check_design(changed_files: List[str], rules: DesignRules, root: str | Path = ".") -> GateDecision:
    root = Path(root)
    decision = allow("無設計漂移")
    for f in changed_files:
        if not f.endswith(".py"):
            continue
        src_layer = rules.layer_of_file(f)
        if not src_layer:
            continue
        path = root / f
        if not path.exists():
            continue
        mods = _imports(path.read_text(errors="ignore"))
        for from_l, to_l in rules.forbidden:
            if from_l != src_layer:
                continue
            prefix = rules.module_prefix(to_l)
            if prefix and any(m == prefix or m.startswith(prefix + ".") for m in mods):
                decision = decision.merge(GateDecision(
                    status=GateStatus.BLOCK,
                    codes=[ErrorCode.DESIGN_DRIFT],
                    reasons=[f"設計漂移: {f} ({src_layer} 層) 不可 import {to_l} 層 ({prefix})"],
                    required_actions=[f"移除對 {to_l} 的依賴,或修訂 ADR 允許此依賴"],
                ))
    return decision
