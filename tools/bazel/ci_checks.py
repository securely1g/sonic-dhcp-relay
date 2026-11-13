#!/usr/bin/env python3
"""Fail closed on package-producing actions or missing/skipped test coverage."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


MINIMUM_CASES = {
    'sender_test': 3,
    'pcap_patch_test': 2,
    'v4_full_suite_test': 62,
    'v6_full_suite_test': 47,
}


def audit_actions(data):
    actions = data.get('actions', [])
    if not actions:
        raise ValueError('Empty configured action graph')
    fragments = {item['id']: item for item in data['pathFragments']}

    def path(key):
        item = fragments[key]
        prefix = path(item['parentId']) + '/' if item.get('parentId') else ''
        return prefix + item['label']

    artifacts = {item['id']: path(item['pathFragmentId']) for item in data['artifacts']}
    for action in actions:
        mnemonic = action.get('mnemonic', '')
        outputs = [artifacts[key] for key in action.get('outputIds', [])]
        if (any(name.endswith(('.deb', '.udeb')) for name in outputs)
                or ('deb' in mnemonic.lower()
                    and mnemonic not in ('ExtractDeb', 'DebExtract', 'DebianRuntimeMetadata'))):
            raise ValueError(f'Forbidden DEB-producing action: {mnemonic}: {outputs}')
    return len(actions)


def audit_tests(root):
    counts = {}
    for name, minimum in MINIMUM_CASES.items():
        tree = ET.parse(root / 'tests/runtime' / name / 'test.xml')
        cases = tree.findall('.//testcase')
        if len(cases) < minimum:
            raise ValueError(f'{name}: expected at least {minimum} cases, found {len(cases)}')
        for case in cases:
            if (case.find('failure') is not None or case.find('error') is not None
                    or case.find('skipped') is not None or case.get('status') != 'run'
                    or case.get('result') != 'completed'):
                raise ValueError(f'{name}: incomplete/failed case {case.attrib}')
        for suite in tree.iter('testsuite'):
            if any(int(suite.get(key, '0')) for key in ('failures', 'errors', 'disabled', 'skipped')):
                raise ValueError(f'{name}: nonzero suite failures/skips')
        counts[name] = len(cases)
    return counts


if __name__ == '__main__':
    if sys.argv[1] == 'actions':
        print('Non-DEB configured actions:', audit_actions(json.loads(Path(sys.argv[2]).read_text())))
    elif sys.argv[1] == 'tests':
        print('Fresh complete gtest coverage:', audit_tests(Path(sys.argv[2])))
    else:
        raise SystemExit('expected actions or tests')
