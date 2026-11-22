# dependency-blast-radius

Flag lockfile-only PRs whose dependency bumps silently widen the blast radius into unrelated production code.

## Purpose
Coverage-drift / mutation-audit / flaky-triage guard code changes. A PR that edits only a lockfile can ripple through transitive dependencies and break production with zero source diff. This tool walks the dependency graph from each changed direct dependency to its importers, then across importers-to-importers, and reports which code paths become exposed. A configurable fail threshold turns a wide blast radius into a CI gate.

## Design
- Parsers for `requirements.txt`, `pyproject.toml`, `poetry.lock`, and `package-lock.json` produce a normalized map: package name -> set of dependency names (edges point dep -> importer after inversion).
- Graph nodes are canonicalized as `frozenset` of `(kind, name, version)` tuples, so node identity is hashable regardless of lockfile shape (lesson L5).
- `analyze(base, head, graph)` diffs versions between refs, then for each changed node does a BFS over reverse edges to collect all transitive importers.
- A `BlastReport` exposes changed nodes, the impacted set, and `max_depth`. `radius` is the count of distinct importers. A bump is flagged silent when it touches no direct source change but exceeds `threshold`.
- CLI/JSON: `analyze` returns a dataclass; `report_json` gives machine-readable output. No I/O at import time.

## Usage
```python
from dependency_blast_radius import analyze, report_json

report = analyze(
    base={"requests": "2.28.0"},
    head={"requests": "2.31.0"},
    graph={"requests": {"api", "worker"}, "api": {"web"}},
    threshold=1,
)
assert report.flagged and report.radius >= 2
print(report_json(report))
```
