#!/usr/bin/env python3
"""Force current APT resolution, then compare its output with reviewed selection.

The canonical JSON is an acceptance contract, NOT a resolver input in facts mode.
Use an idle checkout. Pass the configured Bazel launcher and flags after '--'.
Existing generated lock evidence is retained in --evidence-dir before removal.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time


def compare(expected, actual):
    for key in ('packages', 'dependency_sets', 'sources'):
        if actual[key] != expected[key]:
            raise ValueError('APT selection drift in ' + key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('bazel', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.bazel
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        parser.error('pass the configured Bazel launcher after --')
    root = Path(__file__).resolve().parents[2]
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    lock = root / 'MODULE.bazel.lock'
    # Removal of ignored generated state is explicit, backup-first and local.
    # This invalidates cached extension facts, unlike comparing an old lock.
    if lock.exists():
        previous = evidence / ('MODULE.bazel.lock.before-' + str(time.time_ns()))
        previous.write_bytes(lock.read_bytes())
        lock.unlink()
    result = subprocess.run(command + ['mod', 'deps', '--lockfile_mode=update'], cwd=root,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (evidence / 'fresh-resolution.log').write_bytes(result.stdout)
    if result.returncode:
        raise SystemExit(result.returncode)
    if not lock.exists():
        raise SystemExit('fresh resolution did not produce MODULE.bazel.lock')
    (evidence / 'MODULE.bazel.lock.fresh').write_bytes(lock.read_bytes())
    resolved = json.loads(lock.read_text())
    extension = resolved['moduleExtensions']['@@rules_distroless+//apt:extensions.bzl%apt']['general']
    actual = json.loads(extension['generatedRepoSpecs']['trixie']['attributes']['lock_content'])
    (evidence / 'apt.resolved.json').write_text(json.dumps(actual, indent=2) + '\n')
    expected = json.loads((root / 'apt.lock.json').read_text())
    try:
        compare(expected, actual)
    except ValueError as exc:
        raise SystemExit(str(exc) + '; review the fresh receipt before intentionally updating the canonical contract')
    print('Fresh APT resolution matches canonical contract:', len(expected['packages']), 'packages')


if __name__ == '__main__':
    main()
