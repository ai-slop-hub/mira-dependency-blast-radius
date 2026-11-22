# mira-dependency-blast-radius
Coverage-drift, mutation-audit, and flaky-triage all guard *code* changes, but a PR that edits only a lockfile can ripple through transitive dependencies and break production without any source diff — a gap no existing mira tool covers. This tool answers 'which parts of my code are actually exposed by this dependency bump?' by walking the dependenc
