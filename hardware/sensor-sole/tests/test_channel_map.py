# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""channel_map.resolve: exactly one intact, matching map, or an error. Plain Python (no KiCad).
Run: python3 -m unittest discover -s hardware/sensor-sole/tests -p "test_channel_map.py" -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import channel_map as cm  # noqa: E402

REGIONS = ["heel_post", "mt1", "toe1"]


def package(bid="EU42 R 0123456789", side="R", design="0123456789abcdef" * 4, mp=None, regions=REGIONS):
    mp = mp or {"1": "COM", "2": "heel_post", "3": "mt1", "4": "toe1", "5": "COM"}
    pkg = dict(format=cm.FORMAT, board_id=bid, design_hash=design, side=side, contacts=len(mp), regions=regions,
               map=mp, verified=dict(board_sha256="ab" * 32), provenance={})
    pkg["map_sha256"] = cm.content_hash(pkg)
    return pkg


class Resolve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, pkg, name=None):
        (self.d / (name or cm.file_name(pkg["board_id"]))).write_text(json.dumps(pkg))

    def test_one_matching_map(self):
        self.put(package())
        self.put(package("EU42 L 0123456789", side="L"))
        self.assertEqual(cm.resolve("  EU42   R 0123456789 ", "R", self.d)["map"]["2"], "heel_post")

    def test_missing(self):
        self.put(package())
        with self.assertRaisesRegex(cm.MapError, "no verified map"):
            cm.resolve("EU42 R 9999999999", "R", self.d)

    def test_ambiguous(self):
        self.put(package())
        self.put(package(), name="copy.json")
        with self.assertRaisesRegex(cm.MapError, "ambiguous"):
            cm.resolve("EU42 R 0123456789", "R", self.d)

    def test_wrong_foot(self):
        self.put(package())
        with self.assertRaisesRegex(cm.MapError, "worn on the L foot"):
            cm.resolve("EU42 R 0123456789", "L", self.d)

    def test_package_side_differs_from_id(self):
        self.put(package(side="L"))
        with self.assertRaisesRegex(cm.MapError, "side"):
            cm.resolve("EU42 R 0123456789", "R", self.d)

    def test_edited_map(self):
        pkg = package()
        pkg["map"]["2"], pkg["map"]["3"] = "mt1", "heel_post"          # swapped after verification
        self.put(pkg)
        with self.assertRaisesRegex(cm.MapError, "does not match its hash"):
            cm.resolve("EU42 R 0123456789", "R", self.d)

    def test_id_not_from_design_hash(self):
        self.put(package(design="f" * 64))
        with self.assertRaisesRegex(cm.MapError, "design hash"):
            cm.resolve("EU42 R 0123456789", "R", self.d)

    def test_inconsistent_maps(self):
        bad = {
            "region twice": {"1": "COM", "2": "mt1", "3": "mt1", "4": "toe1", "5": "COM"},
            "COM missing": {"1": "heel_post", "2": "COM", "3": "mt1", "4": "toe1", "5": "COM"},
            "contact missing": {"1": "COM", "2": "heel_post", "4": "toe1", "5": "COM"},
        }
        for why, mp in bad.items():
            with self.subTest(why):
                for f in self.d.glob("*.json"):
                    f.unlink()
                self.put(package(mp=mp))
                with self.assertRaises(cm.MapError):
                    cm.resolve("EU42 R 0123456789", "R", self.d)

    def test_unreadable_file_blocks_resolution(self):
        self.put(package())
        (self.d / "broken.json").write_text("{not json")
        with self.assertRaisesRegex(cm.MapError, "unreadable"):
            cm.resolve("EU42 R 0123456789", "R", self.d)

    def test_malformed_ids(self):
        self.put(package())
        for bad in ("EU42 R", "EU42 R 012345678", "EU42 X 0123456789", "EU42 R 0123456789ab", "", "EU42 R 012345678G"):
            with self.subTest(bad):
                with self.assertRaises(cm.MapError):
                    cm.resolve(bad, "R", self.d)


if __name__ == "__main__":
    unittest.main()
