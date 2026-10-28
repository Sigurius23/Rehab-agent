"""Stdlib-only tests for the meta-repo tooling. Run: python3 -m unittest discover -s tests -v"""
import csv
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "catalog" / "repos.json").read_text())


class TestCatalog(unittest.TestCase):
    def test_count_matches(self):
        self.assertEqual(DATA["count"], len(DATA["repos"]))

    def test_slugs_unique_and_url_matches(self):
        slugs = [r["slug"].lower() for r in DATA["repos"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        for r in DATA["repos"]:
            self.assertEqual(r["url"], f"https://github.com/{r['slug']}")

    def test_categories_tiers_stages_valid(self):
        for r in DATA["repos"]:
            self.assertIn(r["category"], DATA["categories"], r["slug"])
            self.assertIn(r["tier"], DATA["tiers"], r["slug"])
            self.assertTrue(r["description"], r["slug"])
            for s in r["pipeline_stages"]:
                self.assertIn(s, DATA["pipeline_stages"], r["slug"])

    def test_no_needs_review_left(self):
        self.assertEqual([r["slug"] for r in DATA["repos"] if r["tier"] == "needs-review"], [])

    def test_csv_in_sync(self):
        rows = list(csv.reader((ROOT / "catalog" / "repos.csv").open()))
        self.assertEqual(len(rows) - 1, len(DATA["repos"]))

    def test_generated_catalog_mentions_every_repo(self):
        md = (ROOT / "docs" / "catalog.md").read_text()
        for r in DATA["repos"]:
            self.assertIn(r["slug"], md)

    def test_private_repo_never_cloned(self):
        out = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "clone.py"), "--all", "--dry-run"],
            capture_output=True, text=True)
        self.assertNotIn("DAAPT", out.stdout)

    def test_search_imu_is_precise(self):
        out = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "clone.py"), "--search", "imu", "--dry-run"],
            capture_output=True, text=True)
        self.assertIn("TransPose", out.stdout)
        self.assertNotIn("SMPLSim", out.stdout)

    def test_every_repo_fully_documented(self):
        # Documentation standard: see catalog/repos.json `documentation_standard`
        for r in DATA["repos"]:
            self.assertGreaterEqual(len(r["description"]), 40, r["slug"])
            self.assertGreaterEqual(len(r["notes"]), 30, r["slug"])
            self.assertGreaterEqual(len(r["tags"]), 2, r["slug"])
            self.assertTrue(r["pipeline_stages"], r["slug"])
            self.assertTrue(r["license"], r["slug"])
            self.assertTrue(r["license_source"], r["slug"])
            self.assertTrue(r["updated_snapshot"], r["slug"])
            self.assertTrue(r["upstream_path"], r["slug"])
            if not r["private"]:
                self.assertIsNotNone(r["stars_snapshot"], r["slug"])
                self.assertIsNotNone(r["forks_snapshot"], r["slug"])

    def test_generated_catalog_details_every_repo(self):
        md = (ROOT / "docs" / "catalog.md").read_text()
        for r in DATA["repos"]:
            self.assertIn(f"### {r['id']}. [{r['slug']}]", md, r["slug"])
            self.assertIn(r["license"], md, r["slug"])

    def test_schemas_parse_and_audit_blocks_present(self):
        man = json.loads((ROOT / "schemas" / "twin-manifest.schema.json").read_text())
        for block in ["spinopelvic_parameters", "limb_alignment", "muscle_parameters",
                      "bone_quality", "devices_and_prostheses", "safety_flags", "body_state"]:
            self.assertIn(block, man["properties"], block)
        # Safety flags are clinician-set only, by construction
        flag_items = man["properties"]["safety_flags"]["items"]
        self.assertEqual(flag_items["properties"]["set_by"], {"const": "clinician"})
        sess = json.loads((ROOT / "schemas" / "session.schema.json").read_text())
        self.assertIn("breathing", sess["properties"])
        example = json.loads((ROOT / "examples" / "synthetic-session" / "session.json").read_text())
        self.assertIn(example["breathing"]["diaphragm_status"], ["inferred", "ultrasound-measured"])

    def test_example_session_has_required_keys(self):
        s = json.loads((ROOT / "examples" / "synthetic-session" / "session.json").read_text())
        for k in ["session_id", "twin_tier", "hardware", "streams", "calibration", "sync", "accuracy_layers"]:
            self.assertIn(k, s)
        self.assertIn(s["twin_tier"], ["A", "B", "C"])
        # Synthetic example must never claim real patient data
        self.assertTrue(s["synthetic"])


if __name__ == "__main__":
    unittest.main()
