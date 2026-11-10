<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: MIT -->
# Video-benchmark pilot: OpenCap LabValidation subject 2, `squats1` (2026-11-10)

The run scripts behind `validation/results/kin_pilot_opencap_subject2_squats1.json` and `plan/nodes/t-kin-pilot.md`.
They run on a machine with the data under `~/rehab-agent-data` (nothing downloaded is in the repository):

1. `pilot_stage_a.sh`: the four routes of `examples/opencap_agreement.sh` (a copy), processed without a reference.
2. `lag_check.py`: the alignment check, before any error is computed.
3. `pilot_stage_b.sh`: each route against the marker motion capture and against OpenCap's result.
4. `pilot_sharedlag.sh`: the one-camera routes at one shared lag (the owner's sensitivity analysis).
5. `pilot_report_v2.py`: the table and the check of the expected result. `provenance.py` records the inputs.

Inputs: the fixture at opencap-test-data commit 63546b7, the laptop's LabValidation copy (marker motion capture),
Pose2Sim c6db0ca, MediaPipe 1.2.2 with `pose_landmarker_heavy.task`; every file's sha256 is in the results file.
