"""Tool-change regression fixtures; no EDA and no licensed input required."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evidence", ROOT / "scripts/evidence.py")
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


def drc(a=0, b=0):
    return (f"RULECHECK R1 ... TOTAL Result Count = {a} ({b})\n"
            "RULECHECK R2 ... TOTAL Result Count = 0 (0)\n"
            "TOTAL DRC RuleChecks Executed: 2\n"
            f"TOTAL DRC Results Generated: {a} ({b})\n")


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def write(self, name, text):
        path = self.root / name
        path.write_text(text)
        return path

    def frozen(self, paths, name="manifest.json"):
        manifest = self.root / name
        evidence.freeze([str(p) for p in paths], manifest)
        return evidence.Frozen(str(manifest))

    def test_drc_positive_and_nonzero(self):
        self.assertEqual(evidence.parse_drc(drc(), 2)["status"], "passed")
        self.assertEqual(evidence.parse_drc(drc(1, 8))["status"], "failed")
        self.assertEqual(evidence.parse_drc(drc(0, 1))["status"], "failed")

    def test_drc_inconsistent_truncated_duplicate_wrongcoverage(self):
        cases = [drc().replace("Generated: 0 (0)", "Generated: 1 (1)"),
                 drc().replace("RULECHECK R2 ... TOTAL Result Count = 0 (0)\n", ""),
                 drc().replace("R2", "R1"),
                 drc().split("TOTAL DRC Results Generated")[0]]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(evidence.EvidenceError):
                evidence.parse_drc(text)
        with self.assertRaises(evidence.EvidenceError):
            evidence.parse_drc(drc(), 3)

    def test_lvs_exact_top_pair_not_substring(self):
        text = ("OVERALL COMPARISON RESULTS\nCELL  SUMMARY\n"
                "CORRECT top source\nNUMBERS OF OBJECTS AFTER TRANSFORMATION\n"
                "Total CPU Time: 0 sec\nTotal Elapsed Time: 0 sec\n")
        self.assertEqual(evidence.parse_lvs(text, "top", "source")["status"], "passed")
        self.assertEqual(evidence.parse_lvs(text.replace("CORRECT", "INCORRECT"),
                                          "top", "source")["status"], "failed")
        for bad in (text.replace("top source", "other source"),
                    text.split("NUMBERS")[0], text + "CORRECT top source\n",
                    text.split("Total CPU")[0],
                    text.replace("RESULTS\n", "RESULTS\nINCORRECT\n")):
            with self.assertRaises(evidence.EvidenceError):
                evidence.parse_lvs(bad, "top", "source")

    def test_dependency_changes_missing_unbound_and_manifest_change(self):
        path = self.write("input", "one")
        frozen = self.frozen([path])
        self.assertEqual(frozen.text(str(path)), "one")
        other = self.write("other", "two")
        with self.assertRaises(evidence.EvidenceError):
            frozen.text(str(other))
        path.write_text("changed")
        with self.assertRaises(evidence.EvidenceError):
            frozen.verify()
        path.unlink()
        with self.assertRaises(OSError):
            frozen.verify()

    def test_manifest_identity_and_no_overwrite(self):
        path = self.write("input", "one")
        frozen = self.frozen([path])
        with self.assertRaises(FileExistsError):
            evidence.freeze([str(path)], frozen.path)
        frozen.path.write_text(frozen.path.read_text() + "\n")
        with self.assertRaises(evidence.EvidenceError):
            frozen.verify()

    def pv_fixture(self):
        gds = self.write("a.gds", "gds fixture bytes")
        source = self.write("a.cdl", ".SUBCKT source\n.ENDS\n")
        original = self.write("original.drc",
                              'LAYOUT PATH "GDS"\nLAYOUT PRIMARY "TOP"\nRULE KEEP\n')
        replacements = [["GDS", str(gds)], ["TOP", "top"]]
        run = self.write("rules.drc", original.read_text().replace("GDS", str(gds))
                         .replace("TOP", "top"))
        record = self.write("inputs.json", json.dumps({
            key: evidence.fingerprint(path)["sha256"] for key, path in (
                ("gds_sha256", gds), ("source_sha256", source),
                ("original_deck_sha256", original), ("run_deck_sha256", run))}))
        report = self.write("DRC.rep", f"Layout Path(s): {gds}\n"
                            "Layout Primary Cell: top\n" + drc())
        spec = dict(kind="drc", gds=str(gds), source=str(source),
                    original_deck=str(original), run_deck=str(run),
                    execution_inputs=str(record), report=str(report), top="top",
                    replacements=replacements, expected_rules=2)
        return spec, [gds, source, original, run, record, report]

    def test_pv_complete_and_binding_negatives(self):
        spec, paths = self.pv_fixture()
        frozen = self.frozen(paths)
        self.assertEqual(evidence.pv(spec, frozen)["status"], "passed")
        record = Path(spec["execution_inputs"])
        record.write_text(record.read_text().replace(
            evidence.fingerprint(paths[0])["sha256"], "0" * 64))
        frozen = self.frozen(paths, "stale.json")
        with self.assertRaises(evidence.EvidenceError):
            evidence.pv(spec, frozen)

    def test_pv_unlisted_deck_change_and_report_top(self):
        spec, paths = self.pv_fixture()
        spec["replacements"] = spec["replacements"][:1]
        with self.assertRaises(evidence.EvidenceError):
            evidence.pv(spec, self.frozen(paths))
        spec, paths = self.pv_fixture()
        Path(spec["report"]).write_text(
            Path(spec["report"]).read_text().replace("Cell: top", "Cell: wrong"))
        with self.assertRaises(evidence.EvidenceError):
            evidence.pv(spec, self.frozen(paths, "wrongtop.json"))

    def test_pv_lvs_full_bindings_and_wrong_source(self):
        spec, paths = self.pv_fixture()
        original, run, report = [Path(spec[k]) for k in
                                 ("original_deck", "run_deck", "report")]
        original.write_text(original.read_text()
                            + 'SOURCE PATH "CDL"\nSOURCE PRIMARY "SOURCE"\n')
        spec.update(kind="lvs", source_top="source")
        spec["replacements"] += [["CDL", spec["source"]], ["SOURCE\"", 'source"']]
        text = original.read_text()
        for a, b in spec["replacements"]:
            text = text.replace(a, b)
        run.write_text(text)
        record = json.loads(Path(spec["execution_inputs"]).read_text())
        record.update(original_deck_sha256=evidence.fingerprint(original)["sha256"],
                      run_deck_sha256=evidence.fingerprint(run)["sha256"])
        Path(spec["execution_inputs"]).write_text(json.dumps(record))
        report.write_text(
            f"SOURCE NAME: {spec['source']} ('source')\n"
            "OVERALL COMPARISON RESULTS\nCELL  SUMMARY\nCORRECT top source\n"
            "NUMBERS OF OBJECTS AFTER TRANSFORMATION\n"
            "Total CPU Time: 0 sec\nTotal Elapsed Time: 0 sec\n")
        self.assertEqual(evidence.pv(spec, self.frozen(paths))["status"], "passed")
        report.write_text(report.read_text().replace("('source')", "('wrong')"))
        with self.assertRaises(evidence.EvidenceError):
            evidence.pv(spec, self.frozen(paths, "wrongsource.json"))

    def test_wave_samples_and_bad_vectors(self):
        spec = {"signals": ["out"], "sample_times_s": [0, .5, 1]}
        data = {"time": [0, 1], "out": [0, .8]}
        result = evidence.sample_vectors(data, lambda d, k: d[k], spec)
        self.assertEqual(result["signals"]["out"], [0, .4, .8])
        for bad in ({"time": [0, 0], "out": [0, 1]},
                    {"time": [0, 1], "out": [0]},
                    {"time": [0, 1], "out": [0, float("nan")]},
                    {"time": [0, 1], "out": [0, 1j]}):
            with self.assertRaises(evidence.EvidenceError):
                evidence.sample_vectors(bad, lambda d, k: d[k], spec)
        with self.assertRaises(KeyError):
            evidence.sample_vectors({"time": [0, 1]}, lambda d, k: d[k], spec)
        spec["sample_times_s"] = [2]
        with self.assertRaises(evidence.EvidenceError):
            evidence.sample_vectors(data, lambda d, k: d[k], spec)

    def test_real_psf_reader(self):
        try:
            from virtuoso_bridge.spectre.psf import read_psf_ascii, vector
        except ImportError:
            self.skipTest("Optional verified virtuoso-bridge not installed")
        path = self.write("tran", 'HEADER\n"PSFversion" "1.00"\nTYPE\n'
                          '"sweep" FLOAT DOUBLE\n"trace" FLOAT DOUBLE\n'
                          'SWEEP\n"time" "sweep"\nTRACE\n"out" "trace"\n'
                          'VALUE\n"time" 0\n"out" 0\n"time" 1\n"out" 0.8\nEND\n')
        parsed = read_psf_ascii(path)
        self.assertEqual(evidence.sample_vectors(
            parsed, vector, {"signals": ["out"], "sample_times_s": [.5]}
        )["signals"]["out"], [.4])

    def test_gds_transform_units_union_xor_and_band(self):
        try:
            import gdspy
            import shapely
        except ImportError:
            self.skipTest("Optional GDS dependencies not installed")
        lib = gdspy.GdsLibrary(unit=1e-9, precision=1e-12)
        child = lib.new_cell("child")
        child.add(gdspy.Rectangle((0, 0), (1000, 2000), layer=1))
        top = lib.new_cell("top")
        top.add(gdspy.CellReference(child, (1000, 0), rotation=90))
        path = self.root / "a.gds"
        lib.write_gds(str(path))
        spec = dict(gds=str(path), top="top", layers=[[1, 0]],
                    compare_gds=str(path), compare_top="top", band_y_um=[0, 1])
        frozen = self.frozen([path])
        result = evidence.geometry(spec, frozen)
        self.assertEqual(result["status"], "passed")
        self.assertAlmostEqual(result["width_um"], 2)
        self.assertAlmostEqual(result["layer_union_um2"]["1/0"], 2)
        self.assertEqual(result["xor_um2"]["1/0"], 0)
        top.add(gdspy.Rectangle((0, 2e3), (1e3, 3e3), layer=1))
        changed = self.root / "changed.gds"
        lib.write_gds(str(changed))
        spec["compare_gds"] = str(changed)
        frozen = self.frozen([path, changed], "compare.json")
        self.assertAlmostEqual(evidence.geometry(spec, frozen)["xor_um2"]["1/0"], 1)
        spec["band_y_um"] = [0, .5]
        self.assertEqual(evidence.geometry(spec, frozen)["status"], "failed")
        spec["top"] = "missing"
        with self.assertRaises(evidence.EvidenceError):
            evidence.geometry(spec, frozen)

    def test_cli_fails_closed_and_binds_spec(self):
        spec, paths = self.pv_fixture()
        config = self.write("spec.json", json.dumps(spec))
        frozen = self.frozen(paths)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = evidence.main(["pv", str(config), "--manifest", str(frozen.path)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "incomplete")
        frozen = self.frozen(paths + [config], "bound.json")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = evidence.main(["pv", str(config), "--manifest", str(frozen.path)])
        self.assertEqual(code, 0)
        self.assertIn("manifest_sha256", json.loads(output.getvalue()))
        malformed = self.write("malformed.json", "[]")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = evidence.main(["check", str(malformed)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "incomplete")

    @unittest.skipUnless(os.environ.get("DCIM_EVIDENCE_RUN"), "Optional historical replay")
    def test_historical_reports(self):
        run = Path(os.environ["DCIM_EVIDENCE_RUN"])
        good = run / "candidates/B016_group_compute/trial_4/route_43"
        bad = run / "candidates/B017_group_compute/trial_4/route_45"
        self.assertEqual(evidence.parse_drc((good / "drc/DRC.rep").read_text())
                         ["status"], "passed")
        self.assertEqual(evidence.parse_drc((bad / "drc/DRC.rep").read_text())
                         ["status"], "failed")
        for path, status in ((good, "passed"), (bad, "failed")):
            self.assertEqual(evidence.parse_lvs(
                (path / "lvs/lvs.rep").read_text(), "B014_routed",
                "B014_group_compute_source")["status"], status)
        pdk = Path("/PDK/TSMC_12NM/PDK/1P11M_2Xa1Xd_h_3Xe_vhv_2Y2R/"
                   "iPDK_CLN12FFCLL_v1.0_2p4a_20190306/Calibre")
        source = run / "candidates/B016_group_compute/source.cdl"
        for kind in ("drc", "lvs"):
            original = pdk / ("drc/calibre_block.drc.15a" if kind == "drc"
                              else "lvs/calibre.lvs")
            spec = dict(kind=kind, gds=str(good / "routed.gds"), source=str(source),
                        top="B014_routed", source_top="B014_group_compute_source",
                        report=str(good / kind / ("DRC.rep" if kind == "drc" else "lvs.rep")),
                        original_deck=str(original), run_deck=str(good / kind / f"rules.{kind}"),
                        execution_inputs=str(good / kind / "inputs.json"))
            if kind == "drc":
                spec["replacements"] = [
                    ['"GDSFILENAME"', f'"{spec["gds"]}"'],
                    ['"TOPCELLNAME"', '"B014_routed"']]
            else:
                spec["replacements"] = [
                    ['LAYOUT PATH "lvs_top.gds"', f'LAYOUT PATH "{spec["gds"]}"'],
                    ['LAYOUT PRIMARY "lvs_top"', 'LAYOUT PRIMARY "B014_routed"'],
                    ['SOURCE PATH "lvs_top.cdl"', f'SOURCE PATH "{source}"'],
                    ['SOURCE PRIMARY "lvs_top"',
                     'SOURCE PRIMARY "B014_group_compute_source"'],
                    ["VIRTUAL CONNECT COLON YES", "VIRTUAL CONNECT COLON NO"]]
            paths = [Path(spec[k]) for k in ("gds", "source", "report",
                                            "original_deck", "run_deck", "execution_inputs")]
            self.assertEqual(evidence.pv(
                spec, self.frozen(paths, kind + ".json"))["status"], "passed")


if __name__ == "__main__":
    unittest.main()
