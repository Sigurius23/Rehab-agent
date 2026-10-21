# Stack: IMU real-time home rehab

```
6×IMU ──► TransPose (pose) ──► PIP/PNP (pose + joint torques + GRF)
   └────► OpenSimLive (live OpenSim IK) ──► opensim-core models
```
Clone it: `python scripts/clone.py --category pose-mocap --search imu`
Then add: `python scripts/clone.py --only jerela/OpenSimLive,opensim-org/opensim-core`
Note: OpenSimLive targets OpenSim 4.1 — budget time for version pinning.

**Implemented live path (posture cues):** SlimeVR trackers → SlimeVR-Server VMC output →
`rehabtwin vmc-posture` (forward kinematics, posture signals) → LSL `rehabtwin_posture` →
`rehabtwin lsl-live` (CueEngine, gated) → LSL `rehabtwin_cues` → suit bridge.
See `pipeline/README.md`. TransPose/PIP remain the research path for 6-IMU full-body motion and torques.
