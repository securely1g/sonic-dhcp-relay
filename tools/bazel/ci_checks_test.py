import copy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from ci_checks import MINIMUM_CASES, audit_actions, audit_tests


class CIGatesTest(unittest.TestCase):
    def test_action_graph(self):
        graph = {'actions': [{'mnemonic': 'CppLink', 'outputIds': [1]}],
                 'artifacts': [{'id': 1, 'pathFragmentId': 1}],
                 'pathFragments': [{'id': 1, 'label': 'relay'}]}
        self.assertEqual(audit_actions(graph), 1)
        forbidden = copy.deepcopy(graph)
        forbidden['pathFragments'][0]['label'] = 'fixture.deb'
        with self.assertRaises(ValueError):
            audit_actions(forbidden)
        with self.assertRaises(ValueError):
            audit_actions({'actions': []})

    def test_complete_and_empty_or_skipped_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, count in MINIMUM_CASES.items():
                path = root / 'tests/runtime' / name / 'test.xml'
                path.parent.mkdir(parents=True)
                suite = ET.Element('testsuite')
                for i in range(count):
                    ET.SubElement(suite, 'testcase', name=str(i), status='run', result='completed')
                ET.ElementTree(suite).write(path)
            self.assertEqual(audit_tests(root), MINIMUM_CASES)
            path = root / 'tests/runtime/sender_test/test.xml'
            tree = ET.parse(path)
            ET.SubElement(tree.getroot()[0], 'skipped')
            tree.write(path)
            with self.assertRaises(ValueError):
                audit_tests(root)
            path.write_text('<testsuite/>')
            with self.assertRaises(ValueError):
                audit_tests(root)


if __name__ == '__main__':
    unittest.main()
