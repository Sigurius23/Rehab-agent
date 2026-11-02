# Environments — one stack, several isolated envs

The catalog deliberately spans ecosystems that must **not** share one Python
environment. Rule: envs communicate only through the auditable files in
`docs/architecture.md` (video, keypoint JSON, SMPL `.npz`, OpenSim
`.trc/.mot/.osim`, XDF). If two tools need the same interpreter, something is
being coupled that should not be.

| Env (suggested name) | Contents | Why separate |
|---|---|---|
| `twin-live` | mediapipe / mmpose / pose front-ends, LSL (pylsl), record3d client, librealsense (pyrealsense2) | Real-time capture; camera SDKs pin their own deps. Headless Linux: MediaPipe needs `libegl1 libgles2` |
| `twin-pose3d` | GVHMR, EasyMocap, Pose2Sim, smplx, SHAPY | Heavy PyTorch research code, conflicting CUDA/versions |
| `biomech` | OpenSim, `pipeline/` (rehabtwin), opencap-processing, CEINMS, STGCN-rehab | OpenSim 4.6 now ships pip wheels (`pip install opensim`, py3.11–3.13); conda remains an option |
| `hsmr` | HSMR + SKEL (PyTorch, CUDA), `pipeline/adapters/hsmr_to_skelseq.py` | GPU research code with gated model files; talks to `biomech` only through `skel_seq.npz` |
| `imaging` | TotalSegmentator, nnU-Net (GPU PyTorch) | GPU segmentation stack; 3D Slicer is a standalone app, not a pip env |
| `muscle-sim` | MyoSuite/myosim (MuJoCo), SCONE (native app), musclemimic | Simulation; SCONE/SCONE Studio are applications |
| `blender` | Blender + MPFB2, MuSkeMo, Z-Anatomy/BodyParts3D assets | Blender ships its own Python — never pip into it |

Install order for Phase 1 (accuracy-first slice): `imaging` (build one
Tier-A twin for a volunteer) → `biomech` (solve/track against it) →
`twin-live` (selected hardware, docs/hardware.md) → others as stacks demand.

Docker is a valid alternative per env; if adopted, add one Dockerfile per env
here and record image digests in the session record. Do not build one mega-image.
