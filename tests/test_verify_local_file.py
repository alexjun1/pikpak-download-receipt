"""Offline checks using synthetic files in an isolated temporary directory."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HELPER = (Path(__file__).resolve().parents[1] / "skills" /
          "pikpak-download-receipt" / "scripts" / "verify_local_file.py")
SPEC = importlib.util.spec_from_file_location("local_receipt", HELPER)
receipt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt)
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pikpak-receipt-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.local = self.root / "PRIVATE_FILENAME_$(touch SHOULD_NOT_EXIST).bin"
        self.local.write_bytes(b"abc")

    def invoke(self, *options, local=None):
        return subprocess.run(
            [sys.executable, str(HELPER), *options, "--", str(local or self.local)],
            env={"PYTHONDONTWRITEBYTECODE": "1"}, cwd=self.root,
            capture_output=True, text=True, timeout=5)

    def report(self, *options, local=None):
        result = self.invoke(*options, local=local)
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertNotIn("PRIVATE_FILENAME", result.stdout)
        self.assertNotIn(str(self.root), result.stdout)
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())
        return result.returncode, data

    def test_without_expectations_measures_but_does_not_pass(self):
        code, data = self.report()
        self.assertEqual((code, data["status"]), (2, "observed"))
        self.assertEqual(data["bytes_read"], 3)
        self.assertEqual(data["sha256"], ABC_SHA256)
        self.assertTrue(data["metadata_stable"])
        self.assertEqual(data["checks"], {"expected_bytes": None, "expected_sha256": None})

    def test_nonempty_file_matches_both_expectations_without_mutation(self):
        before = self.local.stat()
        code, data = self.report("--expected-bytes", "3", "--expected-sha256", ABC_SHA256.upper())
        after = self.local.stat()
        self.assertEqual((code, data["status"]), (0, "matched"))
        self.assertEqual(data["checks"], {"expected_bytes": True, "expected_sha256": True})
        self.assertEqual(self.local.read_bytes(), b"abc")
        self.assertEqual((before.st_ino, before.st_size, before.st_mtime_ns),
                         (after.st_ino, after.st_size, after.st_mtime_ns))

    def test_one_expectation_does_not_invent_another(self):
        code, data = self.report("--expected-bytes", "3")
        self.assertEqual((code, data["status"]), (0, "matched"))
        self.assertTrue(data["checks"]["expected_bytes"])
        self.assertIsNone(data["checks"]["expected_sha256"])

    def test_unicode_path_and_multiple_chunks(self):
        local = self.root / "图片 片段.bin"
        content = b"chunk-data\x00" * 220000
        local.write_bytes(content)
        code, data = self.report("--expected-bytes", str(len(content)),
                                 "--expected-sha256", hashlib.sha256(content).hexdigest(),
                                 local=local)
        self.assertEqual((code, data["status"]), (0, "matched"))
        self.assertEqual(data["bytes_read"], len(content))
        self.assertNotIn("图片", json.dumps(data, ensure_ascii=False))

    def test_same_length_wrong_content_is_rejected_by_hash(self):
        self.local.write_bytes(b"xyz")
        code, data = self.report("--expected-bytes", "3", "--expected-sha256", ABC_SHA256)
        self.assertEqual((code, data["status"]), (2, "mismatch"))
        self.assertTrue(data["checks"]["expected_bytes"])
        self.assertFalse(data["checks"]["expected_sha256"])

    def test_size_mismatch_is_explicit(self):
        code, data = self.report("--expected-bytes", "4")
        self.assertEqual((code, data["status"]), (2, "mismatch"))
        self.assertFalse(data["checks"]["expected_bytes"])

    def test_empty_file_never_passes_even_matching_empty_expectations(self):
        self.local.write_bytes(b"")
        code, data = self.report("--expected-bytes", "0", "--expected-sha256",
                                 hashlib.sha256(b"").hexdigest())
        self.assertEqual((code, data["status"]), (2, "empty"))
        self.assertEqual(data["bytes_read"], 0)
        self.assertEqual(data["reasons"], ["empty_file"])

    def test_missing_file_error_does_not_leak_path(self):
        code, data = self.report(local=self.root / "PRIVATE_FILENAME_missing.bin")
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertEqual(data["reasons"], ["file_unavailable"])
        self.assertIsNone(data["sha256"])

    def test_directory_and_symlink_are_rejected(self):
        code, data = self.report(local=self.root)
        self.assertEqual((code, data["reasons"]), (1, ["not_regular_file"]))
        link = self.root / "link"
        link.symlink_to(self.local)
        code, data = self.report(local=link)
        self.assertEqual((code, data["reasons"]), (1, ["symlink_not_allowed"]))
        self.assertIsNone(data["bytes_read"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable on this platform")
    def test_fifo_is_rejected_without_waiting_for_a_writer(self):
        fifo = self.root / "pipe"
        os.mkfifo(fifo)
        code, data = self.report(local=fifo)
        self.assertEqual((code, data["reasons"]), (1, ["not_regular_file"]))

    def test_appending_during_read_is_inconclusive_and_bounded(self):
        original_sha256 = hashlib.sha256
        local = self.local

        class ChangingDigest:
            def __init__(self):
                self.inner = original_sha256()
                self.changed = False

            def update(self, chunk):
                self.inner.update(chunk)
                if not self.changed:
                    with local.open("ab") as target:
                        target.write(b"extra bytes")
                    self.changed = True

            def hexdigest(self):
                return self.inner.hexdigest()

        with patch.object(receipt.hashlib, "sha256", ChangingDigest):
            data, code = receipt.verify(str(local), expected_bytes=3, expected_sha256=ABC_SHA256)
        self.assertEqual((code, data["status"]), (2, "inconclusive"))
        self.assertEqual(data["bytes_read"], 3)
        self.assertFalse(data["metadata_stable"])
        self.assertIsNone(data["sha256"])
        self.assertEqual(data["reasons"], ["file_changed_during_read"])

    def test_open_errors_are_sanitized(self):
        with patch.object(receipt.os, "open", side_effect=OSError("PRIVATE_SECRET_ERROR")):
            data, code = receipt.verify(str(self.local))
        self.assertEqual((code, data["reasons"]), (1, ["file_unavailable"]))
        self.assertNotIn("PRIVATE_SECRET_ERROR", json.dumps(data))

    def test_invalid_expected_values_are_rejected_without_echoing_them(self):
        for flag, value in [("--expected-bytes", "PRIVATE_SECRET"),
                            ("--expected-bytes", "-1"),
                            ("--expected-sha256", "PRIVATE_SECRET")]:
            with self.subTest(flag=flag, value=value):
                result = self.invoke(flag, value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("PRIVATE_SECRET", result.stderr)
                self.assertNotIn(str(self.root), result.stderr)


if __name__ == "__main__":
    unittest.main()
