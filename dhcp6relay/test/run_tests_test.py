"""Regression tests for private Redis lifecycle and Make test failure handling."""

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SOURCE = Path(__file__).resolve().parent
PROBE = r'''
import json, os, signal, socket, struct, sys, time
from pathlib import Path
config_path = Path(os.environ["DHCP6RELAY_TEST_DATABASE_CONFIG"])
config = json.loads(config_path.read_text())
socket_path = config["INSTANCES"]["redis"]["unix_socket_path"]
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.connect(socket_path)
    redis_pid, _, _ = struct.unpack("3i", client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    client.sendall(b"DBSIZE\r\n")
    assert client.recv(64) == b":0\r\n"
    client.sendall(b"SET private-fixture-test yes\r\n")
    assert client.recv(64) == b"+OK\r\n"
Path(sys.argv[1]).write_text(json.dumps({"directory": str(config_path.parent), "redis_pid": redis_pid, "test_pid": os.getpid()}))
if sys.argv[2] == "wait":
    time.sleep(30)
elif sys.argv[2] == "signal":
    os.kill(os.getpid(), signal.SIGTERM)
else:
    sys.exit(int(sys.argv[2]))
'''


class RedisFixtureTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="dhcp6-fixture-regression-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.receipt = self.root / "probe.json"

    def command(self, result, redis_server=None):
        return [sys.executable, str(SOURCE / "run_tests.py"), "--redis-server",
                redis_server or os.environ.get("REDIS_SERVER", "redis-server"),
                "--", sys.executable, "-c", PROBE, str(self.receipt), result]

    def require_redis(self):
        if not shutil.which(os.environ.get("REDIS_SERVER", "redis-server")):
            self.skipTest("redis-server is required for lifecycle tests")

    def assert_cleaned(self):
        receipt = json.loads(self.receipt.read_text())
        self.assertFalse(Path(receipt["directory"]).exists())
        for name in ("redis_pid", "test_pid"):
            with self.assertRaises(ProcessLookupError):
                os.kill(receipt[name], 0)
        return receipt

    def test_fresh_database_status_and_cleanup(self):
        self.require_redis()
        directories = []
        for status, expected in (("0", 0), ("7", 7), ("signal", 143)):
            with self.subTest(status=status):
                result = subprocess.run(self.command(status), capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                directories.append(self.assert_cleaned()["directory"])
        self.assertEqual(len(set(directories)), 3)

    def test_interruption_cleans_owned_processes(self):
        self.require_redis()
        with subprocess.Popen(self.command("wait"), stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL) as process:
            try:
                deadline = time.monotonic() + 5
                while not self.receipt.exists() and time.monotonic() < deadline:
                    self.assertIsNone(process.poll())
                    time.sleep(0.02)
                self.assertTrue(self.receipt.exists())
            finally:
                process.terminate()
                result = process.wait(timeout=10)
        self.assertEqual(result, 143)
        self.assert_cleaned()

    def test_startup_failure_does_not_run_tests(self):
        exiting_server = self.root / "exiting-redis"
        exiting_server.write_text("#!/bin/sh\nexit 4\n")
        exiting_server.chmod(0o755)
        for server in (self.root / "missing-redis", exiting_server):
            with self.subTest(server=server.name):
                result = subprocess.run(self.command("0", str(server)), capture_output=True,
                                        text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("DHCPv6 test fixture:", result.stderr)
                self.assertFalse(self.receipt.exists())


class MakeTestStatusTest(unittest.TestCase):
    def test_test_and_coverage_failures_reach_make(self):
        for test_status, coverage_status, expected_calls in (
                (0, 0, ["test", "coverage", "coverage"]),
                (7, 0, ["test", "coverage", "coverage"]),
                (0, 9, ["test", "coverage"])):
            with self.subTest(test_status=test_status, coverage_status=coverage_status), \
                    tempfile.TemporaryDirectory(prefix="dhcp6-make-regression-") as directory:
                root = Path(directory)
                (root / "build-test").mkdir()
                (root / "build-test/dhcp6relay-test").touch()
                for name, contents in {
                    "sudo": '#!/bin/sh\nexec env "$@"\n',
                    "python": '#!/bin/sh\necho test >> "$CALLS"\nexit "$TEST_STATUS"\n',
                    "gcovr": '#!/bin/sh\necho coverage >> "$CALLS"\nexit "$COVERAGE_STATUS"\n',
                }.items():
                    path = root / name
                    path.write_text(contents)
                    path.chmod(0o755)
                environment = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"],
                                   CALLS=str(root / "calls"), TEST_STATUS=str(test_status),
                                   COVERAGE_STATUS=str(coverage_status))
                result = subprocess.run([
                    "make", "--no-print-directory", "-f", str(SOURCE.parent / "Makefile"),
                    "-o", "build-test/dhcp6relay-test", "test", f"PYTHON={root / 'python'}",
                    f"GCOVR={root / 'gcovr'}",
                ], cwd=root, env=environment, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode == 0, test_status == coverage_status == 0,
                                 result.stdout + result.stderr)
                self.assertEqual((root / "calls").read_text().splitlines(), expected_calls)


if __name__ == "__main__":
    unittest.main()
