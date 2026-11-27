import contextlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import textwrap
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from examples import review_receipt as receipt


def passed(argv):
    if argv[-1] == "--version":
        output = "v24.0.0\n"
    elif "--test" in argv:
        output = "# Subtest: first check\n# Subtest: second check\n# Subtest: third check\n# tests 3\n# pass 3\n# skipped 0\n"
    elif "examples._receipt_unittest" in argv:
        output = "receipt-unittest-v1 3 3 0\n"
    else:
        output = "ok\n"
    return {"argv": ["runtime"] + argv[1:], "status": "passed", "exit_code": 0,
            "stdout": output,
            "stderr": "", "output_truncated": False}


class ReviewReceiptTests(unittest.TestCase):
    def test_selections_have_real_fixed_sources_and_focused_test_commands(self):
        self.assertEqual(len(receipt.EXAMPLES), 13)
        with patch.object(receipt.shutil, "which", return_value="/private/runtime/node"), \
                patch.object(receipt, "run_command", side_effect=passed) as run:
            for example_id in receipt.EXAMPLES:
                with self.subTest(example=example_id):
                    result = receipt.make_receipt(example_id)
                    self.assertEqual(result["status"], "passed")
                    self.assertEqual(len(result["commands"]), 2)
                    hashes = result["local_file_sha256"]
                    if example_id == "invoice-line-rounding":
                        self.assertIn("examples/invoice_line_cases.json", hashes)
                        self.assertIn("examples/invoice_subtotal_cases.json", hashes)
                        self.assertEqual(len(hashes), 4)
                    else:
                        self.assertEqual(len(hashes), 2)
                    self.assertTrue(all(len(digest) == 64 for digest in result["local_file_sha256"].values()))
                    self.assertTrue(result["discussion_url"].startswith(receipt.BASE))
                    if example_id == "sql-null-filters" or example_id.startswith("sqlite-"):
                        self.assertEqual(result["runtime_versions"]["sqlite"], sqlite3.sqlite_version)
                    command = result["commands"][1]["argv"]
                    expected_test = "tests/" + receipt.EXAMPLES[example_id][1]
                    if example_id.startswith("javascript"):
                        self.assertEqual(command[1:], ["--test", expected_test])
                    else:
                        self.assertEqual(command[-2:], ["examples._receipt_unittest", example_id])
        self.assertEqual(run.call_count, 2 * len(receipt.EXAMPLES) + 1)  # One extra Node version probe.

    def test_sql_receipt_links_to_the_review_invitation_in_both_languages(self):
        result = receipt.make_receipt("sql-null-filters")
        self.assertEqual(result["status"], "passed")
        guide = (receipt.ROOT / "docs/sql-null-filters.md").read_text(encoding="utf-8")
        for label in ("Continue the SQL exchange", "继续 SQLite 讨论"):
            with self.subTest(label=label):
                self.assertIn(f"[{label}]({result['discussion_url']})", guide)

    def test_unknown_id_never_executes(self):
        with patch.object(receipt, "run_command") as run:
            with self.assertRaises(ValueError):
                receipt.make_receipt("../../arbitrary.py")
        run.assert_not_called()

    def test_missing_node_is_not_a_pass_or_skip(self):
        with patch.object(receipt.shutil, "which", return_value=None), patch.object(receipt, "run_command") as run:
            result = receipt.make_receipt("javascript-json-string-validation")
        self.assertEqual(result["status"], "runtime_unavailable")
        self.assertEqual(result["commands"], [])
        run.assert_not_called()

    def test_node_probe_failure_prevents_examples(self):
        failure = dict(passed(["node", "--version"]), status="timed_out", exit_code=-9)
        with patch.object(receipt.shutil, "which", return_value="node"), \
                patch.object(receipt, "run_command", return_value=failure) as run:
            result = receipt.make_receipt("javascript-json-string-validation")
        self.assertEqual(result["status"], "runtime_probe_failed")
        self.assertEqual(result["commands"], [])
        self.assertEqual(run.call_count, 1)

    def test_old_or_unrecognized_node_never_runs_examples(self):
        for output, expected in [("v18.0.0\n", "unsupported_runtime"), ("unknown\n", "runtime_probe_failed")]:
            with self.subTest(output=output), patch.object(receipt.shutil, "which", return_value="node"), \
                    patch.object(receipt, "run_command", return_value=dict(passed(["node", "--version"]), stdout=output)) as run:
                self.assertEqual(receipt.make_receipt("javascript-json-string-validation")["status"], expected)
                self.assertEqual(run.call_count, 1)

    def test_test_failure_and_timeout_remain_unsuccessful(self):
        for status in ["failed", "timed_out", "output_limit_exceeded", "launch_failed"]:
            results = [passed(["python", "example"]), dict(passed(["python", "tests"]), status=status, exit_code=7)]
            with self.subTest(status=status), patch.object(receipt, "run_command", side_effect=results):
                result = receipt.make_receipt("point-in-time-eps")
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["commands"][1]["exit_code"], 7)

    def test_real_child_exit_output_and_safe_command_label(self):
        result = receipt.run_command([sys.executable, "-B", "-c", "import sys;print('hello');print('error',file=sys.stderr);sys.exit(7)"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["stdout"], "hello\n")
        self.assertEqual(result["stderr"], "error\n")
        self.assertEqual(result["argv"][0], "python")

    def test_real_timeout_keeps_partial_output(self):
        result = receipt.run_command([sys.executable, "-B", "-c", "import time;print('started',flush=True);time.sleep(5)"], timeout_seconds=.2)
        self.assertEqual(result["status"], "timed_out")
        self.assertIsNotNone(result["exit_code"])
        self.assertIn("started", result["stdout"])

    def test_real_output_limit_kills_child_and_bounds_both_streams(self):
        for stream in ["stdout", "stderr"]:
            with self.subTest(stream=stream):
                result = receipt.run_command([sys.executable, "-B", "-c", "import sys,time;sys." + stream + ".write('x'*100000);sys." + stream + ".flush();time.sleep(5)"], output_limit_bytes=1000)
                self.assertEqual(result["status"], "output_limit_exceeded")
                self.assertTrue(result["output_truncated"])
                self.assertEqual(len(result[stream]), 1000)

    def test_launch_failure_does_not_reveal_exception_path(self):
        with patch.object(receipt.subprocess, "Popen", side_effect=FileNotFoundError("/private/user/secret/node")):
            result = receipt.run_command(["/private/user/secret/node", "--version"])
        self.assertEqual(result["status"], "launch_failed")
        self.assertIsNone(result["exit_code"])
        self.assertNotIn("/private", json.dumps(result))

    def test_list_is_json_and_never_runs(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(receipt, "run_command") as run:
            self.assertEqual(receipt.main(["--list"]), 0)
        self.assertEqual(json.loads(output.getvalue())["example_ids"], list(receipt.EXAMPLES))
        run.assert_not_called()

    def test_cli_nonzero_for_unsuccessful_receipt(self):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(receipt, "make_receipt", return_value={"status": "failed"}):
            self.assertEqual(receipt.main(["point-in-time-eps"]), 1)

    def test_cli_rejects_command_injection_as_an_unknown_choice(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(receipt, "make_receipt") as make:
            with self.assertRaises(SystemExit) as error:
                receipt.main(["point-in-time-eps; touch bad"])
        self.assertEqual(error.exception.code, 2)
        make.assert_not_called()

    def test_real_python_receipt_passes_without_recording_local_paths(self):
        result = receipt.make_receipt("gdp-annualization")
        self.assertEqual(result["status"], "passed")
        self.assertEqual([r["exit_code"] for r in result["commands"]], [0, 0])
        self.assertNotIn(str(receipt.ROOT), json.dumps(result))
        if str(Path(sys.executable).parent) != ".":
            self.assertNotIn(str(Path(sys.executable).parent), json.dumps(result))

    def test_successful_process_without_executed_tests_is_not_a_pass(self):
        cases = [
            (False, "done", "test_count_unverified"),
            (True, "# tests 0\n# pass 0\n# skipped 0\n", "no_tests_executed"),
            (True, "# tests 3\n# pass 0\n# skipped 3\n", "no_tests_executed"),
            (True, "# Subtest: /temporary/tests/json_amount_gate.test.mjs\n# tests 1\n# pass 1\n# skipped 0\n", "no_named_tests_executed"),
            (True, "done", "test_count_unverified"),
        ]
        for javascript, output, status in cases:
            with self.subTest(javascript=javascript, output=output):
                result = dict(passed(["runtime", "test"]), stdout=output)
                receipt.validate_test_summary(result, javascript=javascript)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["exit_code"], 0)

    def test_real_python_case_accounting(self):
        fixtures = [
            ("empty", "pass", "no_tests_executed", (0, 0, 0, 0)),
            ("skipped setup", """
                class SkipSetup(T):
                    @classmethod
                    def setUpClass(cls): raise unittest.SkipTest("fixture")
                    def test_a(self): pass
                class Other(T):
                    def test_b(self): pass
            """, "passed", (1, 1, 0, 1)),
            ("skip per case", """
                class Cases(T):
                    @unittest.skip("skipped")
                    def test_a(self): pass
                    def test_b(self): pass
            """, "passed", (2, 1, 1, 1)),
            ("only skipped subtests", """
                class Cases(T):
                    def test_a(self):
                        for i in range(2):
                            with self.subTest(i=i): self.skipTest("skipped")
            """, "no_tests_executed", (1, 2, 1, 0)),
            ("mixed subtests", """
                class Cases(T):
                    def test_a(self):
                        with self.subTest(i=1): self.skipTest("skipped")
                        with self.subTest(i=2): self.assertEqual(2, 2)
            """, "passed", (1, 1, 0, 1)),
            ("expected failure", """
                class Cases(T):
                    @unittest.expectedFailure
                    def test_a(self): self.fail("expected")
            """, "passed", (1, 0, 0, 1)),
            ("failure", """
                class Cases(T):
                    def test_a(self): self.fail("unexpected")
            """, "failed", None),
        ]
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "examples").mkdir()
            (root / "tests").mkdir()
            for name in ["_receipt_unittest.py", "review_receipt.py", "gdp_annualization.py"]:
                shutil.copy(receipt.ROOT / "examples" / name, root / "examples" / name)
            for name, fixture, status, counts in fixtures:
                with self.subTest(name=name), patch.object(receipt, "ROOT", root):
                    (root / "tests/test_gdp_annualization.py").write_text(
                        "import unittest\nT = unittest.TestCase\n" + textwrap.dedent(fixture))
                    result = receipt.make_receipt("gdp-annualization")
                    command = result["commands"][1]
                    self.assertEqual(command["status"], status, command)
                    self.assertEqual(result["status"], "passed" if status == "passed" else "failed")
                    if counts is not None:
                        self.assertEqual(tuple(command[k] for k in
                                               ("tests_reported", "tests_skipped", "test_cases_skipped", "tests_executed")), counts)

    @unittest.skipUnless(shutil.which("node"), "Node unavailable for real empty-file regression")
    def test_real_empty_node_test_file_is_not_a_successful_test_receipt(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "examples").mkdir()
            (root / "tests").mkdir()
            (root / "examples/json_amount_gate.mjs").write_bytes((receipt.ROOT / "examples/json_amount_gate.mjs").read_bytes())
            (root / "tests/json_amount_gate.test.mjs").write_text("")
            with patch.object(receipt, "ROOT", root):
                result = receipt.make_receipt("javascript-json-string-validation")
        if result["status"] == "unsupported_runtime":
            self.skipTest("Optional Node empty-file regression requires Node.js 20 or newer")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["commands"][1]["exit_code"], 0)
        self.assertEqual(result["commands"][1]["status"], "no_named_tests_executed")
        self.assertEqual(result["commands"][1]["tests_executed"], 0)


if __name__ == "__main__":
    unittest.main()
