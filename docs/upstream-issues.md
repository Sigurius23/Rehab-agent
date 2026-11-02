# Upstream issues found while building `pipeline/` — ready to file

Drafts for the upstream maintainers. Each was reproduced in this repo, and each has a
workaround in `pipeline/`, so nothing here blocks us. Filing them helps everyone else.
Commit references are the clones used on 2026-10-21.

---

## perfanalytics/pose2sim — head markers in `Markers_SKEL.xml` sit ~0.5 m above the head

**File:** `Pose2Sim/OpenSim_Setup/Markers_SKEL.xml` (commit `084d822`)
**Model:** `Pose2Sim/OpenSim_Setup/Model_Pose2Sim_muscles_flex.osim`

The seven markers attached to `/bodyset/head` (CHIN, LBHD, LFHD, NOSE, RBHD, RFHD, THD) have
locations that put them far above the skull when the marker set is loaded onto the shipped
model in its default pose:

```python
import opensim as osim
m = osim.Model("Model_Pose2Sim_muscles_flex.osim")
m.updateMarkerSet(osim.MarkerSet("Markers_SKEL.xml"))
s = m.initSystem()
for n in ["THD", "NOSE", "CHIN", "C7"]:
    p = m.getMarkerSet().get(n).getLocationInGround(s); print(n, round(p.get(1), 3))
# THD 2.204, NOSE 2.114, CHIN 2.024, C7 1.421   (hip centres at 0.874, head origin at 1.547)
```

The same coordinates read in the **torso** frame give plausible heights (THD 1.69 m, NOSE
1.60 m, CHIN 1.51 m), so they look like torso-frame values attached to the head body. The
head is offset from the torso origin by (0, 0.512, 0) in the default pose.

**Impact:** scaling pairs or IK tasks using these markers pull the head and torso. In this
marker set they are `fixed=true`, so marker placement doesn't correct them.

**Suggested fix:** re-express the seven locations in the head frame (subtract the default
head–torso offset), or attach them to `/bodyset/torso` if that was the intent.
(Our workaround: `marker_fixes` in `pipeline/configs/skel105_pose2sim.json`.)

---

## IsshikiHugh/HSMR — demo resize swaps width and height arguments

**File:** `lib/kits/hsmr_demo.py`, `load_inputs()` (commit `88486dc`)

```python
if frames.shape[1] > MAX_IMG_H:
    frames = flex_resize_video(frames, (MAX_IMG_H, -1), kp_mod=4)
if frames.shape[2] > MAX_IMG_W:
    frames = flex_resize_video(frames, (-1, MAX_IMG_W), kp_mod=4)
```

`flex_resize_video` takes `tgt_wh = (width, height)`. The first call therefore sets the
**width** to 1080 when the **height** exceeds 1080, so a 3840×2160 (4K landscape) video is
processed at 1080×608 instead of 1920×1080. The second call has the mirror problem. The same
pattern appears in the image branch with `flex_resize_img`.

**Impact:** lower input resolution than intended for 4K landscape videos. Anyone mapping
`bbx_cs` back to original pixels must reproduce the quirk.

**Suggested fix:** `flex_resize_video(frames, (-1, MAX_IMG_H), ...)` and
`flex_resize_video(frames, (MAX_IMG_W, -1), ...)`.
(Our workaround: `rehabtwin.hsmr.hsmr_input_size` replicates the current behaviour; the
adapter takes `--image-size` to override.)

---

## MyoSegmenTUM thigh (Schlaeger et al. 2018) — Table2 volumes use 1 mm pixels and double-count overlapping slices

**Data:** OSF project `svwa7` (view-only key in the paper's data availability statement), `Table2.csv`, and the
per-stack masks in each subject zip.

The `*_V [mm3]` columns equal mask voxel counts times the masks' header spacing (`ElementSpacing = 1 1 4` for the
healthy volunteers, `1 1 1` for the patients). The scans' DICOM files give PixelSpacing 0.78125 / 0.9375 mm
(HV001 stacks 1 / 2), 1.0185 mm (HV012) and 0.81875 mm (P001), and SpacingBetweenSlices 4 mm for the patients.
The healthy volunteers' two stacks also overlap by about 16 mm, and both stacks' masks segment the overlap.
HV001's right quadriceps is 2,110 cm³ from the masks with the DICOM geometry, slices counted once; the table
gives 3,105 cm³. HV012's is 1,107 cm³ against 1,067 cm³, and P001's 1,490 cm³ against 556 cm³. The mean
fat fractions are unaffected.

Workaround here: `pipeline/adapters/myosegmentum.py volumes` recomputes every volume from the masks.


---

## perfanalytics/pose2sim — `Markers_LSTM.xml` carries OpenCap's marker locations onto a model with other bones

**Files:** `Pose2Sim/OpenSim_Setup/Markers_LSTM.xml`, `Pose2Sim/OpenSim_Setup/Model_Pose2Sim_muscles_flex.osim`
(commit `084d822`)

All 43 augmenter markers have exactly the body-frame locations of OpenCap's
`LaiUhlrich2022_markers_augmenter.xml` (opencap-core). The bones they sit on are not the same size in the two
models. Joint-centre distances in the default pose, Pose2Sim / LaiUhlrich2022:

| | Pose2Sim | LaiUhlrich2022 |
|---|---|---|
| tibia (knee to ankle) | 0.430 m | 0.400 m |
| femur (hip to knee) | 0.397 m | 0.406 m |
| hip joint in the pelvis frame | (−0.071, −0.066, ±0.0835) | (−0.056, −0.078, ±0.0773) |

So in Pose2Sim's model the malleolus markers sit 4.5 cm above the ankle joint centre (1.5 cm in
LaiUhlrich2022), and the `RHJC_study`/`LHJC_study` markers, which the augmenter predicts as hip joint centres,
sit 2 cm from the model's hip joints. Scaling the tibia by `r_knee_study`–`r_ankle_study` then lengthens it
about 10 %. On OpenCap's LabValidation subject 2 (5 phones, MediaPipe + augmenter) the scaled shank was
0.54 m; OpenCap's own result for the same videos gives 0.49 m.

**Suggested fix:** move each marker to the same place on Pose2Sim's bones. Scale the tibia and femur markers
along the bone by the joint-centre length ratio (×1.075, ×0.979), and put the hip-joint-centre markers on the
hip joints. On that trial this brought the shank to 0.49 m and agreement with OpenCap's IK from 13.9° to 8.2°
(hip flexion), from 9.3° to 7.4° (knee) and from 6.0° to 2.8° (pelvis tilt), with the ankle 0.5–0.7° worse.
(Our workaround: `marker_rescale` and `marker_to_joint` in `pipeline/configs/mediapipe_lstm_pose2sim.json`.)
