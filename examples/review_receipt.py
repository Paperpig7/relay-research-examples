"""Run one allowlisted example and its focused tests, without posting anything."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import threading


ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 30
OUTPUT_LIMIT_BYTES = 16384  # Per stream, per command.
BASE = "https://relay-commons.ericx.workers.dev/t/"

# This is data for fixed local commands, never a shell command or downloaded code.
EXAMPLES = {
    "python-datetime-dst": ("dst_elapsed", "test_dst_elapsed.py", "7d6be1d5-8a75-4f73-8a0f-4e67c2357ea1"),
    "gdp-annualization": ("gdp_annualization", "test_gdp_annualization.py", "fce574a8-ac3c-453a-bd06-ac65bcdce4fd"),
    "sql-null-filters": ("sql_null", "test_sql_null.py", "host-open-conversation?reply=f5b3e897-8765-4020-9d7b-ab452bd57307#post-f5b3e897-8765-4020-9d7b-ab452bd57307"),
    "eps-share-count": ("eps_share_count", "test_eps_share_count.py", "ff2e0e80-e191-4c28-97fc-5fc3f274e1b3"),
    "deterministic-ranking": ("deterministic_ranking", "test_deterministic_ranking.py", "8fbae8c8-3ac2-4435-876b-2c283a715599"),
    "sqlite-recovery-check": ("sqlite_recovery_check", "test_sqlite_recovery_check.py", "1d1ecd88-cfe7-4fbf-bb07-6ecdf9af63fd?reply=874211ff-952a-4d9f-930e-dc8e09f26a99#post-874211ff-952a-4d9f-930e-dc8e09f26a99"),
    "javascript-json-string-validation": ("json_amount_gate", "json_amount_gate.test.mjs", "dc09621a-9fb6-405a-a22c-a6ea4c83e606?reply=8df17710-f39c-469c-9cf0-41786d4030bf#post-8df17710-f39c-469c-9cf0-41786d4030bf"),
    "point-in-time-eps": ("point_in_time_eps", "test_point_in_time_eps.py", "welcome-backtest-review"),
    "sqlite-lost-ack-retries": ("sqlite_lost_ack", "test_sqlite_lost_ack.py", "83d6919e-6749-4a6a-b645-566d53ef1e68"),
    "nonresponse-bounds": ("nonresponse_bounds", "test_nonresponse_bounds.py", "733b39db-f826-42c1-a2e8-898adf55aff3"),
}


def run_command(argv, *, timeout_seconds=TIMEOUT_SECONDS,
                output_limit_bytes=OUTPUT_LIMIT_BYTES):
    """Capture bounded output. Only make_receipt's fixed commands reach the CLI."""
    result = {"argv": ["node" if Path(argv[0]).name.lower() in {"node", "node.exe"} else "python"] + argv[1:],
              "status": "not_run", "exit_code": None,
              "stdout": "", "stderr": "", "output_truncated": False}
    try:
        child = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 shell=False)
    except OSError as error:
        # Exception strings can contain local executable paths; report only type.
        result.update(status="launch_failed", error_type=type(error).__name__)
        return result

    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    overflow = threading.Event()
    capture_errors = {}

    def drain(name, stream):
        try:
            while True:
                chunk = stream.read1(4096)
                if not chunk:
                    return
                remaining = output_limit_bytes - len(buffers[name])
                buffers[name].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    child.kill()
                    return
        except OSError as error:
            capture_errors[name] = type(error).__name__
        finally:
            stream.close()

    readers = [threading.Thread(target=drain, args=(name, getattr(child, name)),
                                daemon=True) for name in buffers]
    for reader in readers:
        reader.start()
    timed_out = False
    try:
        child.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        child.wait()
    for reader in readers:
        reader.join(timeout=1)
    result["exit_code"] = child.returncode
    result["output_truncated"] = overflow.is_set()
    for name, buffer in buffers.items():
        result[name] = bytes(buffer).decode("utf-8", errors="replace").replace(str(ROOT), "<repository>")
    if timed_out:
        result["status"] = "timed_out"
    elif overflow.is_set():
        result["status"] = "output_limit_exceeded"
    elif any(reader.is_alive() for reader in readers):
        result["status"] = "output_capture_incomplete"
    elif capture_errors:
        result.update(status="output_capture_failed", capture_errors=capture_errors)
    else:
        result["status"] = "passed" if child.returncode == 0 else "failed"
    return result


def make_receipt(example_id):
    if example_id not in EXAMPLES:
        raise ValueError("Unknown example ID")
    module, test_name, discussion = EXAMPLES[example_id]
    javascript = example_id == "javascript-json-string-validation"
    sources = ["examples/" + module + (".mjs" if javascript else ".py"), "tests/" + test_name]
    receipt = {
        "schema_version": 1,
        "example_id": example_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "not_run",
        "runtime_versions": {"receipt_python": platform.python_version()},
        "local_file_sha256": {},
        "discussion_url": BASE + discussion,
        "limits": {"seconds_per_command": TIMEOUT_SECONDS, "bytes_per_output_stream": OUTPUT_LIMIT_BYTES},
        "command_labels": "python uses this interpreter; node uses the Node executable found on PATH. Absolute executable paths are omitted.",
        "output_note": "Repository paths are replaced with <repository>. Review captured output before sharing; it is not guaranteed to be free of local details.",
        "scope": "Local synthetic example and focused tests only; not an independent review, production validation or full environment attestation. Nothing is posted.",
        "commands": [],
    }
    try:
        receipt["local_file_sha256"] = {
            source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest() for source in sources
        }
    except OSError as error:
        receipt.update(status="source_unavailable", error_type=type(error).__name__)
        return receipt

    if javascript:
        node = shutil.which("node")
        if node is None:
            receipt.update(status="runtime_unavailable", error="Node.js was not found on PATH; no commands ran.")
            return receipt
        probe = run_command([node, "--version"])
        receipt["runtime_probe"] = probe
        if probe["status"] != "passed":
            receipt["status"] = "runtime_probe_failed"
            return receipt
        version = probe["stdout"].strip()
        if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
            receipt.update(status="runtime_probe_failed", error="Node version output was not recognized; examples were not run.")
            return receipt
        receipt["runtime_versions"]["node"] = version
        if int(version[1:].split(".")[0]) < 20:
            receipt.update(status="unsupported_runtime", error="This example requires Node.js 20 or newer; examples were not run.")
            return receipt
        commands = [[node, sources[0]], [node, "--test", sources[1]]]
    else:
        receipt["runtime_versions"]["example_python"] = platform.python_version()
        if module in {"sql_null", "sqlite_recovery_check", "sqlite_lost_ack"}:
            receipt["runtime_versions"]["sqlite"] = sqlite3.sqlite_version
        commands = [[sys.executable, "-B", "-m", "examples." + module],
                    [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", test_name, "-v"]]
    receipt["commands"] = [run_command(command) for command in commands]
    validate_test_summary(receipt["commands"][1], javascript=javascript)
    receipt["status"] = "passed" if all(r["status"] == "passed" for r in receipt["commands"]) else "failed"
    return receipt


def validate_test_summary(result, *, javascript):
    """A successful process with no reported executed tests is not a test pass."""
    if result["status"] != "passed":
        return
    output = result["stdout"] + "\n" + result["stderr"]
    if javascript:
        # Node emits TAP when this fixed command's output is piped.
        counts = re.findall(r"^# tests (\d+)\s*$", output, re.MULTILINE)
        passes = re.findall(r"^# pass (\d+)\s*$", output, re.MULTILINE)
        skips = re.findall(r"^# skipped (\d+)\s*$", output, re.MULTILINE)
        if not counts or not passes:
            result["status"] = "test_count_unverified"
            return
        total, executed = int(counts[-1]), int(passes[-1])
        skipped = int(skips[-1]) if skips else 0
        subtests = re.findall(r"^# Subtest: (.+)$", output, re.MULTILINE)
        # Node treats a file with no node:test cases as a passing file subtest.
        # That proves only that the file completed, not that any checks ran.
        named_tests = [name for name in subtests
                       if name.replace("\\", "/").rsplit("/", 1)[-1] != "json_amount_gate.test.mjs"]
        result["named_tests_reported"] = len(named_tests)
        if total > 0 and executed > 0 and not named_tests:
            result.update(status="no_named_tests_executed" if subtests else "test_count_unverified",
                          tests_reported=total, tests_skipped=skipped, tests_executed=0)
            return
    else:
        counts = re.findall(r"^Ran (\d+) tests? in [^\n]+$", output, re.MULTILINE)
        if not counts:
            result["status"] = "test_count_unverified"
            return
        total = int(counts[-1])
        skips = re.findall(r"^OK \([^\n]*skipped=(\d+)[^\n]*\)$", output, re.MULTILINE)
        skipped = int(skips[-1]) if skips else 0
        executed = total - skipped
    result.update(tests_reported=total, tests_skipped=skipped, tests_executed=executed)
    if total <= 0 or executed <= 0 or executed > total:
        result["status"] = "no_tests_executed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", nargs="?", choices=tuple(EXAMPLES))
    parser.add_argument("--list", action="store_true", help="List fixed example IDs as JSON without running them")
    args = parser.parse_args(argv)
    if args.list:
        if args.example:
            parser.error("Use either --list or one example ID")
        print(json.dumps({"example_ids": list(EXAMPLES)}, indent=2))
        return 0
    if args.example is None:
        parser.error("Choose an example ID or use --list")
    receipt = make_receipt(args.example)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
