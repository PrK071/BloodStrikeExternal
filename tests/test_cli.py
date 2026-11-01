# Python | tests/test_cli.py | Python 3.12+ unittest | CLI success/failure and output provenance.
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ExternalCore.snapshot import FORMAT, json_value, load_snapshot, write_json
from registry_fixture import fixture_segments

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.input = Path(self.temp.name) / "memory.json"
        self.output = Path(self.temp.name) / "frame.json"
        segments, module, _ = fixture_segments()
        self.payload = {"format": FORMAT, "provenance": "synthetic_unit_fixture_not_game_capture",
                        "module": asdict(module),
                        "segments": [{"address": s.address, "hex": s.data.hex()} for s in segments]}

    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "ExternalCore", *args, "--output", str(self.output)],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)

    def test_snapshot_cli_runs_whole_pipeline_and_preserves_provenance(self):
        write_json(self.input, self.payload)
        result = self.run_cli("snapshot", str(self.input))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(output["source"]["kind"], "recorded_memory")
        self.assertEqual(output["source"]["provenance"], self.payload["provenance"])
        self.assertFalse(output["gameplay_validated"])
        self.assertEqual(output["frame"]["records"][0]["position"]["position"], [101.25, -202.5, 303.75])

    def test_scene_cli_adds_camera_projection_and_svg_without_input_dispatch(self):
        write_json(self.input, self.payload)
        svg = self.output.with_suffix(".svg")
        result = self.run_cli("scene", str(self.input), "--svg", str(svg))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(output["frame"]["scene"]["actors"][0]["point"]["x"], 1027.5)
        self.assertEqual(output["frame"]["aim"]["reason"], "inactive")
        self.assertFalse(output["input_dispatched"])
        self.assertIn("unknown #12345678", svg.read_text(encoding="utf-8"))

    def test_predicate_cli_reports_body_identity_with_unresolved_dispatch(self):
        from test_predicate import PredicateFixture
        fixture=PredicateFixture().predicate()
        payload={"format":FORMAT,"provenance":"synthetic_predicate_fixture_not_game_capture",
            "module":asdict(fixture.module),
            "segments":[{"address":s.address,"hex":s.data.hex()} for s in fixture.segments]}
        write_json(self.input,payload)
        result=self.run_cli('predicate',str(self.input),'--function',hex(fixture.function))
        self.assertEqual(result.returncode,0,result.stderr)
        output=json.loads(self.output.read_text(encoding='utf-8'))
        self.assertEqual(output['format'],'bloodstrike-predicate-body-v1')
        self.assertFalse(output['body']['active_dispatch_verified'])
        self.assertFalse(output['body']['operand_semantics_verified'])
        self.assertFalse(output['target_code_executed'])
        self.assertEqual(output['provenance'],payload['provenance'])

    def test_predicate_failure_replaces_old_match_with_error(self):
        write_json(self.input,self.payload)
        self.output.write_text('{"body":"old match"}',encoding='utf-8')
        result=self.run_cli('predicate',str(self.input),'--function','0x200001000')
        self.assertEqual(result.returncode,2)
        output=json.loads(self.output.read_text(encoding='utf-8'))
        self.assertEqual(output['status'],'error')
        self.assertNotIn('body',output)

    def test_output_alias_cannot_overwrite_input_or_sample(self):
        write_json(self.input, self.payload)
        original = self.input.read_bytes()
        for command in [("snapshot", str(self.input)),
                        ("capture", "--pid", "0", "--sample", str(self.input))]:
            result = subprocess.run([sys.executable, "-m", "ExternalCore", *command,
                                     "--output", str(self.input)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(self.input.read_bytes(), original)
            self.assertIn("must not overwrite", result.stderr)

    def test_failure_replaces_a_previous_success_output(self):
        self.output.write_text('{"status":"PASS"}', encoding="utf-8")
        self.payload["module"]["sha256"] = "0" * 64
        write_json(self.input, self.payload)
        result = self.run_cli("snapshot", str(self.input))
        self.assertEqual(result.returncode, 2)
        output = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(output["status"], "error")
        self.assertEqual(output["error_type"], "BuildMismatchError")

    def test_capture_rejects_wrong_sample_before_any_process_access(self):
        self.input.write_bytes(b"not the audited executable")
        result = self.run_cli("capture", "--pid", "0", "--sample", str(self.input))
        self.assertEqual(result.returncode, 2)
        output = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(output["error_type"], "BuildMismatchError")

    def test_nonfinite_numbers_have_explicit_portable_json_spelling(self):
        self.assertEqual(json_value([float("nan"), float("inf"), -float("inf")]),
                         ["NaN", "+Infinity", "-Infinity"])

    def test_overlapping_segments_and_missing_provenance_are_rejected(self):
        self.payload["segments"].append(self.payload["segments"][0])
        write_json(self.input, self.payload)
        with self.assertRaisesRegex(ValueError, "overlapping"):
            load_snapshot(self.input)
        self.payload["provenance"] = ""
        write_json(self.input, self.payload)
        with self.assertRaisesRegex(ValueError, "provenance"):
            load_snapshot(self.input)


if __name__ == "__main__":
    unittest.main()
