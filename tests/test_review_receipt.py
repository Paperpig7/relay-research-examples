import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from examples import review_receipt as receipt


def passed(argv):
    if argv[-1] == "--version":
        output = "v24.0.0\n"
    elif "--test" in argv:
        output = "# Subtest: first check\n# Subtest: second check\n# Subtest: third check\n# tests 3\n# pass 3\n# skipped 0\n"
    elif "unittest" in argv:
        output = "Ran 3 tests in 0.001s\n\nOK\n"
    else:
        output = "ok\n"
    return {"argv": ["runtime"] + argv[1:], "status": "passed", "exit_code": 0,
            "stdout": output,
            "stderr": "", "output_truncated": False}


class ReviewReceiptTests(unittest.TestCase):
    def test_nine_selections_have_real_fixed_sources_and_focused_test_commands(self):
        self.assertEqual(len(receipt.EXAMPLES), 9)
        with patch.object(receipt.shutil, "which", return_value="/private/runtime/node"), \
                patch.object(receipt, "run_command", side_effect=passed) as run:
            for example_id in receipt.EXAMPLES:
                with self.subTest(example=example_id):
                    result = receipt.make_receipt(example_id)
                    self.assertEqual(result["status"], "passed")
                    self.assertEqual(len(result["commands"]), 2)
                    self.assertEqual(len(result["local_file_sha256"]), 2)
                    self.assertTrue(all(len(digest) == 64 for digest in result["local_file_sha256"].values()))
                    self.assertTrue(result["discussion_url"].startswith(receipt.BASE))
                    command = result["commands"][1]["argv"]
                    expected_test = "tests/" + receipt.EXAMPLES[example_id][1]
                    if example_id.startswith("javascript"):
                        self.assertEqual(command[1:], ["--test", expected_test])
                    else:
                        self.assertEqual(command[-2:], [receipt.EXAMPLES[example_id][1], "-v"])
        self.assertEqual(run.call_count, 19)

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
            (False, "Ran 0 tests in 0.001s\n\nOK\n", "no_tests_executed"),
            (False, "Ran 3 tests in 0.001s\n\nOK (skipped=3)\n", "no_tests_executed"),
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

    def test_partial_skips_are_counted_as_not_executed(self):
        result = dict(passed(["python", "tests"]), stdout="Ran 5 tests in 0.001s\n\nOK (skipped=2)\n")
        receipt.validate_test_summary(result, javascript=False)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["tests_executed"], 3)
        self.assertEqual(result["tests_skipped"], 2)

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
