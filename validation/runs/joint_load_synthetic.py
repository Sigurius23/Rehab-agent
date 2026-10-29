"""Knee joint load on the synthetic selftest squat (docs/joint-load.md): a synthetic person (SYNTHETIC-NOT-A-PATIENT,
72 kg) with an illustrative DXA table, rep 1, fat -5 kg, quadriceps at 120 %, both, GRF band +/-0.10.
    python -I joint_load_synthetic.py REPO OUT      then joint_load_table.py OUT/session/muscles/study.json"""
import json
import shutil
import sys
from pathlib import Path

DXA = {"method": "DXA (illustrative table for a synthetic person, not a scan)", "date": "2026-10-28",
       "regions": {"left_arm": {"lean_kg": 3.0, "fat_kg": 1.0, "bmc_kg": 0.17},
                   "right_arm": {"lean_kg": 3.1, "fat_kg": 1.0, "bmc_kg": 0.18},
                   "left_leg": {"lean_kg": 9.5, "fat_kg": 3.2, "bmc_kg": 0.5},
                   "right_leg": {"lean_kg": 9.6, "fat_kg": 3.2, "bmc_kg": 0.5},
                   "trunk": {"lean_kg": 25.0, "fat_kg": 7.0, "bmc_kg": 0.8},
                   "head": {"lean_kg": 3.3, "fat_kg": 0.9, "bmc_kg": 0.55}}}


def main():
    repo, out = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(repo / "pipeline"))
    from rehabtwin import cli, person
    if not (out / "session" / "session.json").exists():
        cli.selftest(out / "session")
    shutil.rmtree(out / "session" / "muscles", ignore_errors=True)
    sess = json.loads((out / "session" / "session.json").read_text())
    qc = json.loads((out / "session" / "qc.json").read_text())
    shutil.rmtree(out / "person", ignore_errors=True)
    person.init(out / "person", sess["person_ref"], mass_kg=qc["subject"]["mass_kg"])
    (out / "dxa.json").write_text(json.dumps(DXA))
    person.set_dxa(out / "person", out / "dxa.json")
    cli.muscle_study(out / "session", view_3d=False, person=out / "person", joint_load=True, fat_change_kg=-5.0,
                     strengthen=["quadriceps_r=1.2", "quadriceps_l=1.2"], grf_sensitivity=0.10)


if __name__ == "__main__":       # the study's worker processes import this file again
    main()
