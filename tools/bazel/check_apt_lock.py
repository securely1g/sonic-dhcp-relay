#!/usr/bin/env python3
"""Compare current resolver output with the reviewed canonical package selection.

Run after Bazel resolution. MODULE.bazel.lock is ignored execution evidence;
apt.lock.json is a reviewed acceptance contract, NOT a resolver input.
This low-level comparison alone cannot establish freshness. Use
validate-apt-lock.py as the documented validation/CI entrypoint.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
expected = json.loads((root / "apt.lock.json").read_text())
module = json.loads((root / "MODULE.bazel.lock").read_text())
extension = module["moduleExtensions"]["@@rules_distroless+//apt:extensions.bzl%apt"]["general"]
actual = json.loads(extension["generatedRepoSpecs"]["trixie"]["attributes"]["lock_content"])
for key in ("packages", "dependency_sets", "sources"):
    if actual[key] != expected[key]:
        raise SystemExit("APT selection drift in " + key + "; intentionally refresh canonical apt.lock.json")
print("APT canonical selection matches:", len(expected["packages"]), "packages")
