#!/usr/bin/env python3
"""Read one local regular file and compare only supplied expected values."""
import argparse
import hashlib
import json
import os
import re
import stat


def snapshot(info):
    return (info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def verify(local_file, expected_bytes=None, expected_sha256=None):
    report = {"status": "failed", "bytes_read": None, "sha256": None,
              "metadata_stable": None,
              "checks": {"expected_bytes": None, "expected_sha256": None},
              "reasons": []}
    try:
        before = os.lstat(local_file)
        if stat.S_ISLNK(before.st_mode):
            report["reasons"] = ["symlink_not_allowed"]
            return report, 1
        if not stat.S_ISREG(before.st_mode):
            report["reasons"] = ["not_regular_file"]
            return report, 1
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        with os.fdopen(os.open(local_file, flags), "rb") as stream:
            start = os.fstat(stream.fileno())
            if not stat.S_ISREG(start.st_mode):
                report["reasons"] = ["not_regular_file"]
                return report, 1
            digest, count, remaining = hashlib.sha256(), 0, start.st_size
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                digest.update(chunk)
                count += len(chunk)
                remaining -= len(chunk)
            extra = stream.read(1)
            end = os.fstat(stream.fileno())
        after = os.lstat(local_file)
        stable = (snapshot(before) == snapshot(start) == snapshot(end)
                  == snapshot(after) and count == start.st_size and not extra)
        report.update(bytes_read=count, metadata_stable=stable)
        if not stable:
            report.update(status="inconclusive", reasons=["file_changed_during_read"])
            return report, 2
        report["sha256"] = digest.hexdigest()
        if expected_bytes is not None:
            report["checks"]["expected_bytes"] = count == expected_bytes
        if expected_sha256 is not None:
            report["checks"]["expected_sha256"] = report["sha256"] == expected_sha256.lower()
        if count == 0:
            report.update(status="empty", reasons=["empty_file"])
            return report, 2
        checks = [value for value in report["checks"].values() if value is not None]
        if not checks:
            report.update(status="observed", reasons=["no_expected_values"])
            return report, 2
        if not all(checks):
            report.update(status="mismatch", reasons=["expected_value_mismatch"])
            return report, 2
        report["status"] = "matched"
        return report, 0
    except OSError:
        report["reasons"] = ["file_unavailable"]
        return report, 1


def nonnegative_integer(value):
    if not re.fullmatch(r"[0-9]{1,30}", value):
        raise argparse.ArgumentTypeError("expected bytes must be a nonnegative integer")
    return int(value)


def sha256_value(value):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise argparse.ArgumentTypeError("expected SHA-256 must be 64 hexadecimal characters")
    return value.lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_file", help="Exact file explicitly selected by the user")
    parser.add_argument("--expected-bytes", type=nonnegative_integer)
    parser.add_argument("--expected-sha256", type=sha256_value)
    args = parser.parse_args()
    report, code = verify(args.local_file, args.expected_bytes, args.expected_sha256)
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
