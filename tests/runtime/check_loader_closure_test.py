"""Bounded controls for the loader-output gate; no Docker or ELF execution."""
from pathlib import Path
import subprocess
import tempfile
import unittest

CHECK = Path(__file__).with_name("check_loader_closure.sh")


class LoaderClosureTest(unittest.TestCase):
    def run_gate(self, output, status=0):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "loader.txt"
            receipt.write_text(output)
            result = subprocess.run(
                ["bash", "-c", '''
set -euo pipefail
source "$1"
receipt="$2"
status="$3"
docker() { cat "$receipt"; return "$status"; }
check_loader_closure /declared/root /declared/test image
''', "test", str(CHECK), str(receipt), str(status)],
                capture_output=True, text=True,
            )
            return result

    def test_declared_transitive_libraries(self):
        self.assertEqual(self.run_gate(
            "linux-vdso.so.1 (0x123)\n"
            "libswsscommon.so.0 => /rootfs/usr/lib/x86_64-linux-gnu/libswsscommon.so.0 (0x456)\n"
            "libnl-3.so.200 => /rootfs/usr/lib/x86_64-linux-gnu/libnl-3.so.200 (0x789)\n"
            "/rootfs/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 (0xabc)\n"
        ).returncode, 0)

    def test_missing_dependency_rejected(self):
        self.assertNotEqual(self.run_gate(
            "error while loading shared libraries: libnl-3.so.200: cannot open shared object file\n", 127
        ).returncode, 0)

    def test_ambient_dependency_rejected_even_when_loader_succeeds(self):
        self.assertNotEqual(self.run_gate(
            "libxxhash.so.0 => /usr/lib/x86_64-linux-gnu/libxxhash.so.0 (0x123)\n"
        ).returncode, 0)

    def test_absolute_dependency_without_arrow_rejected(self):
        declared = "libc.so.6 => /rootfs/usr/lib/x86_64-linux-gnu/libc.so.6 (0x123)\n"
        for record in (
                "/usr/lib/ambient.so (0x456)\n",
                "relative/ambient.so (0x456)\n",
                "unexpected loader output\n"):
            with self.subTest(record=record):
                self.assertNotEqual(self.run_gate(declared + record).returncode, 0)

    def test_declared_absolute_dependency_without_arrow_accepted(self):
        self.assertEqual(self.run_gate(
            "libc.so.6 => /rootfs/usr/lib/x86_64-linux-gnu/libc.so.6 (0x123)\n"
            "/rootfs/usr/lib/absolute.so (0x456)\n"
        ).returncode, 0)

    def test_not_found_and_empty_output_rejected(self):
        for output in ("", "libnl-3.so.200 => not found\n"):
            with self.subTest(output=output):
                self.assertNotEqual(self.run_gate(output).returncode, 0)


if __name__ == "__main__":
    unittest.main()
