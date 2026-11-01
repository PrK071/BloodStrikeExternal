# Python | tools/run_tests.py | Python 3.12+ | project test runner with JSON and JUnit reports.
"""No installation/game dependency; native tests select only a child they create."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []

    def startTest(self, test):
        self._started = time.perf_counter()
        super().startTest(test)

    def _event(self, test, status, detail=""):
        self.events.append({"id": test.id(), "status": status, "detail": detail,
                            "seconds": time.perf_counter() - getattr(self, "_started", time.perf_counter())})

    def addSuccess(self, test):
        super().addSuccess(test)
        self._event(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._event(test, "failed", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._event(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._event(test, "skipped", reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            status = "failed" if issubclass(err[0], test.failureException) else "error"
            self._event(subtest, status, self._exc_info_to_string(err, test))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._event(test, "skipped", "expected failure: " + self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._event(test, "failed", "unexpected success")


def write_junit(path, events, elapsed):
    # Subtest failures are explicit cases; JUnit counts must match its elements.
    xml = ET.Element("testsuite", name="BloodStrikeExternal", tests=str(len(events)),
                     failures=str(sum(e["status"] == "failed" for e in events)),
                     errors=str(sum(e["status"] == "error" for e in events)),
                     skipped=str(sum(e["status"] == "skipped" for e in events)), time=f"{elapsed:.6f}")
    for event in events:
        testcase = ET.SubElement(xml, "testcase", name=event["id"], time=f'{event["seconds"]:.6f}')
        if event["status"] != "passed":
            tag = {"failed": "failure", "error": "error", "skipped": "skipped"}[event["status"]]
            ET.SubElement(testcase, tag).text = event["detail"]
    ET.ElementTree(xml).write(path, encoding="utf-8", xml_declaration=True)


def initialize_reports(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text('{"status":"RUNNING"}\n', encoding="utf-8")
    write_junit(output_dir / "junit.xml", [{"id": "run_incomplete", "status": "error",
                "detail": "run has not completed", "seconds": 0.0}], 0.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "tests")
    args = parser.parse_args()
    # Invalidate both reports before discovery; interruption cannot retain PASS.
    initialize_reports(args.output_dir)
    summary_path = args.output_dir / "summary.json"
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    elapsed = time.perf_counter() - started
    sources = sorted([*ROOT.glob("ExternalCore/*.py"), *ROOT.glob("tests/*.py"), Path(__file__)])
    required_native = {"test_win32_integration.": 4, "test_overlay_native.": 4, "test_pipeline_native.": 1}
    native_required_ok = os.name != "nt" or all(
        len(events := [event for event in result.events if event["id"].startswith(prefix)]) >= minimum
        and all(event["status"] == "passed" for event in events)
        for prefix, minimum in required_native.items())
    ok = result.wasSuccessful() and result.testsRun > 0 and native_required_ok
    report = {"status": "PASS" if ok else "FAIL", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "platform": platform.platform(),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "junit_cases": len(result.events), "unexpected_successes": len(result.unexpectedSuccesses),
              "skipped": len(result.skipped), "seconds": elapsed,
              "native_integration": "owned_child_process_and_owned_hidden_GDI_only", "protected_game_access": False,
              "native_required_groups": required_native, "system_input_events_sent": False,
              "bloodstrike_gameplay_validated": False, "publisher_certification": False,
              "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"):
                                  hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
              "tests": result.events}
    summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_junit(args.output_dir / "junit.xml", result.events, elapsed)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
