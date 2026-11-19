#!/usr/bin/env python3
"""Compare current resolver output with the reviewed canonical package selection.

Run after Bazel resolution. MODULE.bazel.lock is ignored execution evidence;
apt.lock.json is the reviewed SDK lock. The audit resolver uses only the dated
sources and package requests.
This low-level comparison alone cannot establish freshness. Use
validate-apt-lock.py as the documented validation/CI entrypoint.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
expected = json.loads((root / "apt.lock.json").read_text())
module = json.loads((root / "MODULE.bazel.lock").read_text())
from relay_apt_audit import compare, resolved_graph

actual = resolved_graph(module)
compare(expected, actual)
print('APT selection matches:', len(actual['packages']), 'packages')
