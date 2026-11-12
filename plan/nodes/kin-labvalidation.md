---
type: "step"
title: "Video kinematics on OpenCap LabValidation against marker motion capture"
status: "open"
area: "pipeline"
parent: "[[goal-measured-kinematics]]"
priority: "1"
stop_rule: "after the pilot and at most two rounds of fixes, the five-camera route gives a complete squat repetition through the pipeline's gates for fewer than 8 of the 10 subjects"
stop_by: "2026-12-07"
stop_owner: "owner"
source: "docs/gaps-and-open-decisions.md G-01, D-04, D-11; docs/roadmap.md Phase 1"
updated: "2026-11-10"
---
# Video kinematics on OpenCap LabValidation against marker motion capture

The video front-ends on OpenCap LabValidation, against its marker-motion-capture inverse kinematics:
- the pipeline's routes (MediaPipe, five cameras or one, with and without the marker augmenter);
- the monocular candidates (HSMR/SKEL, OpenCap Monocular, SAM4Dcap), where their licences and files allow.

The thresholds are those of `docs/accuracy.md`, as a first attempt; their clinical adjustment is [[D-03]]. Feeds
[[D-11]].

**What it needs (2026-11-09, laptop line updated 2026-11-10):**
- **The videos: on the laptop since 2026-11-10.** `LabValidation_withVideos.zip` holds 19.97 GB, 24.6 GB
  uncompressed, in 15,645 entries; its listing reads, but its CRCs have not been tested. From the listing only:
  - **Videos:** 1,628 (1,620 `.avi`, 8 `.mp4`), 17.0 GB. Each trial has five cameras (Cam0–Cam4). The 8 `.mp4` files
    are extra rotated copies of subject 2's `squatsAsym1` and `static1` for Cam1–Cam4.
  - **Sessions:** `Session0` for every subject. `Session1` for 9 subjects holds the walking trials, with its own
    calibration.
  - **Sync:** every trial video comes twice, as recorded (`<trial>.avi`) and as `<trial>_syncdWithMocap.avi`
    (765 of each). Each session also has a `mocapToVideoTransform.yaml`. There is no separate timestamp file. In
    the positive control, OpenCap's results from this dataset lie at zero lag against the motion capture
    ([[t-kin-opencap-control-all]]).
  - **Calibration:** `cameraIntrinsicsExtrinsics.pickle` per camera and session (90), and a checkerboard video
    `extrinsics/extrinsics.avi` per camera and session (90). There is also `sessionMetadata.yaml` per subject.
  - **Also in the zip:** OpenSimData, MarkerData, EMGData and ForceData. They are not extracted or opened.
- **For HSMR:** the SKEL model files. They are licence-gated (an MPI-IS registration by the owner) and
  non-commercial ([[D-09]]). The other front-ends can start without them. Found on the laptop on 2026-11-10: `skel_models_v1.1.zip` (174 MB, with
  `skel_male.pkl` and `skel_female.pkl`), inside the owner's Drive export `Rehab agent -20261106T152938Z-1-002`.
  HSMR's own trained weights are a separate download and have not been checked.
- **On the laptop:** the pipeline's environment and a MediaPipe environment. Both were set up for the pilot, and
  their versions are in the pilot's results file. `workstation/setup.sh` does not install them yet.

**The pilot ran on 2026-11-10** ([[t-kin-pilot]]; `docs/validation-results.md` section 4b). Its expected result
was not met: for five cameras with the augmenter, the error against motion capture differs from the error against
OpenCap by more than 2° in 26 of 36 cells, mostly larger. What it changes for the full run:
- **Alignment.** A lag search per route is fragile on repeated movements: two routes had no clear peak, and two
  routes on one timeline got lags 0.15 s apart. The full run uses one lag per timeline ([[t-kin-labvalidation]]).
- **The bar.** OpenCap's own result has not been compared with the motion capture in this tool. That comparison
  comes first ([[t-kin-opencap-control]]). It needs no videos.
- **Follow-ups:** [[idea-fppa-deep-flexion]], [[idea-one-camera-robust-signals]] and the approval label
  ([[d-feature-release-rule]]).

**Stop rule (approved by the owner 2026-11-10):** stop and report if, after the pilot and at most two
rounds of fixes, the five-camera route gives a complete squat repetition through the pipeline's gates for fewer
than 8 of the 10 subjects. Check by 2026-12-07; owned by the owner.

**Order of the front ends (owner, 2026-11-10):**
1. The pipeline's own routes on all subjects: MediaPipe with five cameras or one, with and without the marker
   augmenter. These need no GPU.
2. Then the monocular candidates on the GPU, installed one at a time.

HSMR needs the SKEL files, which are on the laptop (above), and its own trained weights, which have not been
checked yet.

**First full run, the pipeline's routes (2026-11-10;** [[t-kin-labvalidation]]**):** the expected result is not
met. Only the frontal pelvis passes. Before any fix, the stop rule's count is 7 subjects, under its 8. Subject 6
shared no videos, so the count can reach 9 at most. The rule allows two rounds of fixes before 2026-12-07; whether
to make them, and which, is the owner's decision.

**The monocular candidates' setup (2026-11-12, lab laptop; everything outside the repository).** GPU: an RTX 5090
Laptop (24 GB, compute capability 12.0).
- **HSMR: set up, but blocked on one file.**
  - Code: HSMR at 88486dc, with SKEL c32cf16 as its submodule, and SMPL2AddBiomechanics 47b728a for the
    adapter's marker map.
  - Environment: `envs/hsmr`, Python 3.10, torch 2.11.0+cu128 (CUDA works on the GPU), Detectron2 0.6; the full
    freeze is in `envs/hsmr.freeze.txt`.
  - Files: the checkpoint `HSMR-ViTH-r1d1` (2.5 GB) and three regressors, from HuggingFace
    `IsshikiHugh/HSMR-data_inputs` at revision 7deaf55, with sha256s recorded; SKEL v1.1.1 from the owner's
    download.
  - Every pickle and the checkpoint were scanned before loading: they rebuild only numpy, scipy and torch tensors.
  - **Blocked:** the demo fetches its person detector (ViTDet, `model_final_f05665.pkl`) from
    `dl.fbaipublicfiles.com`, whose TLS certificate expired on 2026-11-11 23:59 UTC. It was not downloaded over the
    broken certificate. It needs either Meta's renewal or a trusted mirror chosen by the owner.
  - **Unblocked the same day (2026-11-12):** Meta renewed the certificate, valid to 2027-04-25. The detector was
    downloaded (2,765,948,277 bytes, sha256 8601bc52…) and scanned: an OrderedDict of numpy arrays only. It sits in
    a cache outside the repository (`FVCORE_CACHE`).
  - **One local patch to the clone** (`upstream/hsmr_local.patch`): `prepare_mesh` builds SKEL meshes 64 frames at
    a time instead of 720, which ran out of the GPU's 24 GB. This changes only how many frames go through at once,
    not the result.
  - **Smoke test, without a reference:** subject 2's `squats1`, Cam2's synced video. This trial has been seen, so
    no error was computed. HSMR's demo took 7 minutes for 480 frames. Then the repository's adapter
    (`hsmr_to_skelseq.py`) and `rehabtwin process` ran. The person was detected in every frame, and the whole
    trial solved as one segment. Five squat repetitions were found, none with imputed frames or missing markers;
    the mean IK marker error was 28.6 mm. The route runs end to end.
- **OpenCap Monocular (PolyForm Noncommercial): cloned at 94b1122, not installed.** Its recipe pins torch 2.1.2+cu118
  and a prebuilt mmcv-full 1.7.2, and neither supports compute capability 12.0. It would need torch ≥ 2.7 and
  mmcv-full compiled from source, and no CUDA compiler is installed. It also needs the SMPL model, which is on the
  laptop (SMPL v1.1.0, in the owner's Drive exports), and WHAM's weights.
- **SAM4Dcap: not set up.** The code is at github.com/wanglihx/SAM4Dcap-core (cloned at b784efa, 952 MB). It has no
  licence file, so it is treated as all rights reserved. Its full code and environments are not public yet ("will
  be uploaded to a cloud drive later"). It was built on a 96 GB GPU and needs at least 24 GB.

