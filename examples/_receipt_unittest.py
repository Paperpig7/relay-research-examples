"""Run the fixed Python suite for a review receipt and report parent-case counts."""

import sys
import unittest

from examples.review_receipt import EXAMPLES


class ReceiptResult(unittest.TextTestResult):
    executed = 0

    def startTest(self, test):
        self.case_executed = False
        super().startTest(test)

    def addSuccess(self, test):
        self.case_executed = True
        super().addSuccess(test)

    def addExpectedFailure(self, test, err):
        self.case_executed = True
        super().addExpectedFailure(test, err)

    def addSubTest(self, test, subtest, err):
        if err is None:
            self.case_executed = True
        super().addSubTest(test, subtest, err)

    def stopTest(self, test):
        self.executed += int(self.case_executed)
        super().stopTest(test)


def main(example_id):
    _, test_name, _ = EXAMPLES[example_id]
    suite = unittest.defaultTestLoader.discover("tests", pattern=test_name)
    result = unittest.TextTestRunner(verbosity=2, resultclass=ReceiptResult).run(suite)
    if not result.wasSuccessful():
        return 1
    print(f"receipt-unittest-v1 {result.testsRun} {result.executed} {len(result.skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
