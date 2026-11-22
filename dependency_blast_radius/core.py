"""Compute transitive dependent blast radius for changed dependencies."""

from __future__ import annotations

import json
import re
import tomllib
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, Set

Node = frozenset


def _node(kind: str, name: str, version: str) -> Node:
    """Canonical, hashable node key: a frozenset of one typed tuple."""
    return frozenset({(kind, name, version)})


def parse_lockfile(text: str, fmt: str) -> Dict[str, Set[str]]:
    """Parse a lockfile into {dependency_name: {importer_name}} edges."""
    if fmt in ("requirements.txt", "requirements"):
        deps: Set[str] = set()
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                deps.add(re.split(r"[<>=!~;\[]", line, 1)[0].strip())
        return {d: set() for d in deps}
    if fmt == "pyproject.toml":
        data = tomllib.loads(text)
        names: Set[str] = set()
        for group in ("dependencies", "dev-dependencies", "group"):
            sec = data.get("project", {}).get(group, data.get("tool", {}).get("poetry", {}).get(group, {}))
            if isinstance(sec, dict):
                names.update(sec.keys())
        return {n: set() for n in names}
    if fmt == "poetry.lock":
        data = tomllib.loads(text)
        pkgs = data.get("package", [])
        names = {p.get("name") for p in pkgs if p.get("name")}
        edges: Dict[str, Set[str]] = {n: set() for n in names}
        for p in pkgs:
            owner = p.get("name")
            for dep in p.get("dependencies", {}):
                if owner:
                    edges.setdefault(dep, set()).add(owner)
        return edges
    if fmt == "package-lock.json":
        data = json.loads(text)
        edges = {}
        for path, meta in data.get("packages", {}).items():
            if not path:
                continue
            owner = path.rstrip("/").split("/")[-1]
            for dep in list(meta.get("dependencies", {})) + list(meta.get("devDependencies", {})):
                edges.setdefault(dep, set()).add(owner)
        return edges
    raise ValueError(f"unsupported lockfile format: {fmt}")


@dataclass
class BlastReport:
    changed: Set[Node] = field(default_factory=set)
    impacted: Set[Node] = field(default_factory=set)
    max_depth: int = 0
    threshold: int = 1

    @property
    def radius(self) -> int:
        return len(self.impacted)

    @property
    def flagged(self) -> bool:
        return bool(self.changed) and self.radius >= self.threshold


def analyze(
    base: Dict[str, str],
    head: Dict[str, str],
    graph: Dict[str, Iterable[str]],
    threshold: int = 1,
) -> BlastReport:
    """Diff versions and BFS reverse edges from each changed node to importers."""
    all_names = set(base) | set(head) | set(graph)
    for children in graph.values():
        all_names.update(children)
    changed_names = {n for n in all_names if base.get(n) != head.get(n)}

    reverse: Dict[str, Set[str]] = {n: set() for n in all_names}
    for dep, importers in graph.items():
        for importer in importers:
            reverse.setdefault(dep, set()).add(importer)

    report = BlastReport(threshold=threshold)
    for name in changed_names:
        report.changed.add(_node("dep", name, head.get(name, "")))
        queue = deque([(name, 0)])
        seen = {name}
        while queue:
            current, depth = queue.popleft()
            for parent in reverse.get(current, ()):
                if parent in seen:
                    continue
                seen.add(parent)
                report.max_depth = max(report.max_depth, depth + 1)
                report.impacted.add(_node("code", parent, head.get(parent, "")))
                queue.append((parent, depth + 1))
    return report


def report_json(report: BlastReport) -> str:
    """Machine-readable JSON report."""
    flat = lambda ns: sorted(next(iter(n))[1] for n in ns)
    return json.dumps(
        {
            "changed": flat(report.changed),
            "impacted": flat(report.impacted),
            "radius": report.radius,
            "max_depth": report.max_depth,
            "threshold": report.threshold,
            "flagged": report.flagged,
        },
        sort_keys=True,
    )
