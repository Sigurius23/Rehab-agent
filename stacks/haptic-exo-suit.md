# Stack: Haptic feedback suit + exoskeleton support (two different tracks)

## Track 1 — Haptic posture cueing (buildable now, low risk)
```
SlimeVR trackers (posture sensing) ──► twin (stacks/digital-twin.md)
   ──► rule: joint/posture deviation > clinician-set threshold
   ──► senseshift-firmware vest/sleeves (vibrotactile cue at the deviating segment)
       [LucidVR/lucidgloves only if hand rehab is in scope]
```
Clone: `python scripts/clone.py --only SlimeVR/SlimeVR-Server,SlimeVR/SlimeVR-Tracker-ESP,senseshift/senseshift-firmware`

**Rule engine implemented:** `pipeline/rehabtwin/feedback.py` (`rehabtwin cues`). Clinician-authored
rules map a posture signal (e.g. knee frontal-plane projection angle, trunk inclination vs gravity)
to an actuator, with hysteresis, minimum duration, refractory period and **faded feedback**
(cue share falls over repetitions to avoid dependence on the cue). The same `CueEngine.update()`
runs offline on recorded sessions (`commands.csv`, LSL-ready events) and later live. Cues are
only *sent* for a Tier-A twin on validated joint/planes; everything else is logged as `would_cue`.
Template rules: `pipeline/configs/feedback/squat_posture.json`. Live sensing is wired too:
`rehabtwin vmc-posture` turns SlimeVR's VMC stream into the same posture signals.  The
actuation side exists as well: `rehabtwin suit-bridge` encodes cues as bHaptics-protocol BLE
payloads for SenseShift firmware (X40 vest nibble encoding, 6-motor sleeves), with a dry-run
mode. The physical BLE write (bleak) is the only untested step.

## Track 2 — Powered joint support (research build, safety-gated)
```
naubiomech/OpenExo (modular exo base: hip/ankle/elbow, mechanics+electronics+control)
   + neurobionics/opensourceleg (lower-limb actuator/sensor SDK patterns)
   + mjbots/moteus or simplefoc/Arduino-FOC (actuator controllers)
   + CEINMS / OpenSimRT (person-specific, EMG-informed assistance targets)
```
Clone: `python scripts/clone.py --only naubiomech/OpenExo,neurobionics/opensourceleg,mjbots/moteus,simplefoc/Arduino-FOC,CEINMS/CEINMS,mitkof6/OpenSimRT`

**Sizing a device before building it:** `rehabtwin muscles SESSION --assist knee_angle_r=40:neg`
adds an ideal assistive actuator (capped torque, chosen direction) to the subject's
static-optimisation problem. It shows how much torque, when, and which muscles it offloads.
It is an upper bound for an ideal device and should inform an assist-as-needed controller,
not constant support. `--passive knee_angle_r=60@20:pos` is the realistic counterpart: a
one-sided elastic (band, spring) with stiffness and slack angle, i.e. what a passive suit
panel can do without motors.

For **trunk/posture support** use the physical coordinates `lumbar_total_extension`
(`_bending`, `_rotation`): torque and stiffness between pelvis and thorax, e.g.
`--assist lumbar_total_extension=30:pos` or a back elastic resisting flexion
`--passive lumbar_total_extension=60@0:neg`. Do not put devices on `L5_S1_Flex_Ext` directly:
the model's six lumbar levels are coupled to it, so the thorax turns ~7× the L5/S1 angle and a
"40 N·m" generalized force there is only ~5.6 N·m across the trunk.

⚠️ No turnkey open repo provides powered *spinal* posture support. Track 2 is joint
assistance adapted from OpenExo. Before anything load-bearing touches a person:
hardware e-stop, firmware torque limits, clinician-set range limits, and a written
risk assessment are mandatory — none of that ships in these repos.
