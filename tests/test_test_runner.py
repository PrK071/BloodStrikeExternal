# Python | tests/test_test_runner.py | Python 3.12+ unittest | fault injection in test reporting.
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location("project_test_runner", Path(__file__).resolve().parents[1] / "tools/run_tests.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def test_multiple_failing_subtests_produce_consistent_junit_counts(self):
        class InjectedFailure(unittest.TestCase):
            def runTest(self):
                for value in (1, 2):
                    with self.subTest(value=value):
                        self.fail("intentional reporting fixture")
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=runner.RecordedResult).run(InjectedFailure())
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(result.testsRun, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "junit.xml"
            runner.write_junit(path, result.events, 0)
            xml = ET.parse(path).getroot()
        self.assertEqual(int(xml.attrib["tests"]), len(xml.findall("testcase")))
        self.assertEqual(int(xml.attrib["failures"]), 2)
        self.assertEqual(len(xml.findall("testcase/failure")), 2)

    def test_run_start_invalidates_both_old_success_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "summary.json").write_text('{"status":"PASS"}', encoding="utf-8")
            (path / "junit.xml").write_text('<testsuite failures="0"/>', encoding="utf-8")
            runner.initialize_reports(path)
            self.assertEqual(json.loads((path / "summary.json").read_text())["status"], "RUNNING")
            xml = ET.parse(path / "junit.xml").getroot()
            self.assertEqual(xml.attrib["errors"], "1")
            self.assertIsNotNone(xml.find("testcase/error"))

    def test_subtest_errors_and_class_setup_errors_are_reported_as_errors(self):
        class InjectedError(unittest.TestCase):
            def runTest(self):
                with self.subTest(kind="error"):
                    raise RuntimeError("intentional subtest error")
        class SetupError(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError("intentional class setup error")
            def runTest(self):
                pass
        for suite in (InjectedError(), unittest.TestSuite([SetupError()])):
            with self.subTest(suite=type(suite).__name__):
                result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=runner.RecordedResult).run(suite)
                self.assertFalse(result.wasSuccessful())
                self.assertEqual(result.events[0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
