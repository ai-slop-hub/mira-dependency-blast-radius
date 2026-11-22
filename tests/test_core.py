import json

from dependency_blast_radius import analyze, parse_lockfile, report_json
from dependency_blast_radius.core import BlastReport


def test_transitive_bfs_and_threshold_flag():
    r = analyze({"requests": "2.28"}, {"requests": "2.31"}, {"requests": {"api"}, "api": {"web"}}, threshold=1)
    assert r.flagged and r.radius == 2 and r.max_depth == 2
    assert {"api", "web"} == {next(iter(n))[1] for n in r.impacted}


def test_no_change_yields_empty_report():
    r = analyze({"a": "1"}, {"a": "1"}, {"a": {"b"}})
    assert not r.changed and not r.impacted and not r.flagged and r.radius == 0


def test_below_threshold_not_flagged():
    r = analyze({}, {"x": "1"}, {}, threshold=5)
    assert r.changed and r.radius == 0 and not r.flagged


def test_node_keys_are_hashable_frozensets():
    r = analyze({}, {"z": "1"}, {"z": {"y"}})
    assert all(isinstance(n, frozenset) for n in (r.changed | r.impacted))
    assert isinstance(hash(next(iter(r.changed))), int)
    assert isinstance(report_json(r), str) and json.loads(report_json(r))["radius"] == 1


def test_parse_requirement_and_package_lock_edges():
    assert parse_lockfile("flask>=2\n# c\n-r other.txt\n", "requirements.txt") == {"flask": set()}
    pl = '{"packages": {"": {}, "node_modules/api": {"dependencies": {"lodash": "^4"}}}}'
    edges = parse_lockfile(pl, "package-lock.json")
    assert edges == {"lodash": {"api"}}


def test_poetry_lock_dependency_edges():
    text = '[[package]]\nname = "api"\n[package.dependencies]\nrequests = "^2"\n'
    assert parse_lockfile(text, "poetry.lock") == {"api": set(), "requests": {"api"}}
