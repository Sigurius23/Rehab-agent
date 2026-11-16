# t-kin-camera-plus-imu-sim-shanks (part 2; plan c12e25c): fuse_trial.py with one more sensor set, pelvis + thighs + shanks
# (tibia_r, tibia_l). Everything else is as in part 1. The pelvis and thigh sensors get the same random draws as in part 1
# (same generator, same order); the shank sensors' draws come from a second generator seeded by the same text + '/shanks'.
# Only the new set is solved (noise-free and assumed noise), plus pelvis+thighs/noisy once more as a check against part 1.
# Part 1's header follows.
# t-kin-camera-plus-imu-sim: one trial, one route. Markers (the one-camera route's own IK targets and weights, round 0)
# plus simulated orientation sensors, solved together with OpenSim's InverseKinematicsSolver.
#  - Sensors: pelvis, femur_r, femur_l. Orientation = the body's orientation in ground from the trial's motion-capture IK
#    on the subject's motion-capture-scaled model (forward kinematics), at the route's own frame times (lag 0), times a
#    fixed mounting rotation per sensor (random, seeded), times noise in the noisy condition.
#  - Noise (ASSUMED, not measured): 3 deg RMS per axis, independent per frame; plus a heading drift about the vertical
#    growing linearly from 0 to 10 deg over the trial, its sign drawn per sensor. Seeded by subject/trial/route.
#  - Calibration as OpenSense: sensor-to-segment offset = (body orientation at the first frame, mocap model)^T x (sensor
#    reading at the first frame); that offset is put on the pipeline model's body of the same name as a "<body>_imu" frame.
#  - Heading: the sensors' world is the motion capture's ground; the route's ground has its own heading. As OpenSense's
#    base-sensor heading correction, all readings are rotated about the vertical so that the pelvis's forward axis at the
#    first frame matches the route's own no-sensor IK at that frame.
#  - Weights: orientation weight 1 per sensor; marker weights from the route's ik_setup.xml; constraint weight Inf;
#    accuracy 1e-5 (the route's). Time range: the route's own (its longest solved segment).
# Conditions: none (no sensors: the script's baseline), pelvis/clean, pelvis/noisy, pelvis+thighs/clean, pelvis+thighs/noisy.
# Args: session_opensim_dir mocap_model mocap_ik_mot out_dir seed_text
import json, re, sys, zlib
from pathlib import Path
import numpy as np
import opensim as osim
from scipy.spatial.transform import Rotation as R
osim.Logger.setLevelString("error")
sdir, mocap_model, mocap_mot, out, seed_text = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5]
out.mkdir(parents=True, exist_ok=True)
SENSORS = ["pelvis", "femur_r", "femur_l"]
SHANKS = ["tibia_r", "tibia_l"]; ALL = SENSORS + SHANKS
setup = sorted(sdir.glob("ik*_setup.xml"), key=lambda p: -len((sdir / p.name.replace("_setup.xml", ".mot")).read_text()) if (sdir / p.name.replace("_setup.xml", ".mot")).exists() else 0)[0]
xml = setup.read_text()
t0, t1 = map(float, re.search(r"<time_range>\s*([-0-9.eE]+)\s+([-0-9.eE]+)", xml).groups())
weights = {n: float(w) for n, a, w in re.findall(r'<IKMarkerTask name="([^"]+)"><apply>(\w+)</apply><weight>([-0-9.eE]+)</weight>', xml) if a == "true"}
trc = sdir / "markers_dynamic.trc"
tl = trc.read_text().splitlines(); names = [x for x in tl[3].split("\t") if x.strip()][2:]
times = np.array([float(l.split("\t")[1]) for l in tl[5:] if l.strip() and l.split("\t")[1].strip()])
times = times[(times >= t0 - 1e-9) & (times <= t1 + 1e-9)]

def body_rotations(model_path, mot, at):
    """(T, 3, 3) per sensor body: orientation in ground from an IK .mot (degrees), by forward kinematics."""
    m = osim.Model(str(model_path)); s = m.initSystem()
    L = Path(mot).read_text().splitlines(); h = next(i for i, l in enumerate(L) if l.strip() == "endheader")
    cols = L[h + 1].split("\t"); data = np.array([[float(x) for x in l.split()] for l in L[h + 2:] if l.strip()])
    cs = m.getCoordinateSet(); use = [c for c in cols[1:] if cs.contains(c) and (c.startswith("pelvis_") or c.startswith("hip_") or c in ("knee_angle_r", "knee_angle_l"))]
    vals = {c: np.interp(at, data[:, 0], data[:, cols.index(c)]) for c in use}
    outr = {b: np.zeros((len(at), 3, 3)) for b in ALL}
    for k in range(len(at)):
        for c in use:
            co = cs.get(c); v = vals[c][k]
            co.setValue(s, np.radians(v) if co.getMotionType() == osim.Coordinate.Rotational else v, False)
        m.realizePosition(s)
        for b in ALL:
            Rm = m.getBodySet().get(b).getTransformInGround(s).R()
            outr[b][k] = [[Rm.get(i, j) for j in range(3)] for i in range(3)]
    return outr

def solve(model, orient=None):
    """orient: {frame name: (T, 3, 3)} or None. Returns (coordinate names, values (T, n) in degrees/metres)."""
    mw = osim.SetMarkerWeights()
    for n in names: mw.cloneAndAppend(osim.MarkerWeight(n, weights.get(n, 0.0)))
    mref = osim.MarkersReference(str(trc), mw, osim.Units("m"))
    cref = osim.SimTKArrayCoordinateReference()
    if orient:
        # quaternions through an OpenSense-format .sto (w,x,y,z per cell), then OpenSim's own conversion to rotations
        sto = out / "_orientations.sto"
        lines = [f"DataRate={1.0 / np.median(np.diff(times)):.6f}", "DataType=Quaternion", "version=3", "OpenSimVersion=4.6", "endheader", "time\t" + "\t".join(orient)]
        Q = {n: R.from_matrix(orient[n]).as_quat() for n in orient}            # x y z w
        for k, t in enumerate(times):
            lines.append(f"{t:.8f}\t" + "\t".join(f"{Q[n][k][3]:.10f},{Q[n][k][0]:.10f},{Q[n][k][1]:.10f},{Q[n][k][2]:.10f}" for n in orient))
        sto.write_text("\n".join(lines) + "\n")
        tab = osim.OpenSenseUtilities.convertQuaternionsToRotations(osim.TimeSeriesTableQuaternion(str(sto)))
        ow = osim.SetOientationWeights() if hasattr(osim, "SetOientationWeights") else osim.SetOrientationWeights()
        for n in orient: ow.cloneAndAppend(osim.OrientationWeight(n, 1.0))
        oref = osim.OrientationsReference(tab, ow)
        solver = osim.InverseKinematicsSolver(model, mref, oref, cref)
    else:
        solver = osim.InverseKinematicsSolver(model, mref, cref)
    solver.setAccuracy(1e-5)
    s = model.initSystem(); s.setTime(float(times[0])); solver.assemble(s)
    cs = model.getCoordinateSet(); cn = [cs.get(i).getName() for i in range(cs.getSize())]
    rot = [cs.get(i).getMotionType() == osim.Coordinate.Rotational for i in range(cs.getSize())]
    vals = np.zeros((len(times), len(cn)))
    for k, t in enumerate(times):
        s.setTime(float(t)); solver.track(s)
        vals[k] = [np.degrees(cs.get(i).getValue(s)) if rot[i] else cs.get(i).getValue(s) for i in range(len(cn))]
    return cn, vals

def write_mot(path, cn, vals):
    head = f"Coordinates\nversion=1\nnRows={len(times)}\nnColumns={len(cn) + 1}\ninDegrees=yes\nendheader\n"
    np.savetxt(path, np.column_stack([times, vals]), delimiter="\t", header=head + "time\t" + "\t".join(cn), comments="", fmt="%.8f")

# 1. baseline, no sensors (and the route's own first-frame pelvis heading)
base = osim.Model(str(sdir / "model_scaled.osim"))
cn, v0 = solve(base)
st = base.initSystem(); cs = base.getCoordinateSet()
for i, c in enumerate(cn):
    co = cs.get(c); co.setValue(st, np.radians(v0[0, i]) if co.getMotionType() == osim.Coordinate.Rotational else v0[0, i], False)
base.realizePosition(st); Rp = base.getBodySet().get("pelvis").getTransformInGround(st).R()
fwd_route = np.array([Rp.get(0, 0), 0.0, Rp.get(2, 0)])
# 2. truth orientations at the route's times, heading-aligned to the route's ground
truth = body_rotations(mocap_model, mocap_mot, times)
fwd_moc = np.array([truth["pelvis"][0][0, 0], 0.0, truth["pelvis"][0][2, 0]])
yaw = np.arctan2(fwd_moc[2], fwd_moc[0]) - np.arctan2(fwd_route[2], fwd_route[0])      # rotation about +y taking mocap heading to the route's
H = R.from_euler("y", yaw).as_matrix()
rng = np.random.default_rng(zlib.crc32(seed_text.replace('#check', '').encode()))
mount = {b: R.random(random_state=rng.integers(1 << 31)).as_matrix() for b in SENSORS}
drift_sign = {b: rng.choice([-1.0, 1.0]) for b in SENSORS}
rng2 = np.random.default_rng(zlib.crc32((seed_text.replace('#check', '') + '/shanks').encode()))
mount.update({b: R.random(random_state=rng2.integers(1 << 31)).as_matrix() for b in SHANKS}); drift_sign.update({b: rng2.choice([-1.0, 1.0]) for b in SHANKS})
frac = (times - times[0]) / max(times[-1] - times[0], 1e-9)
record = dict(seed_text=seed_text, time_range=[t0, t1], frames=len(times), heading_alignment_deg=float(np.degrees(yaw)), drift_sign=drift_sign, conditions={})
for noise in ("clean", "noisy"):
    readings, offsets = {}, {}
    for b in ALL:
        g = rng if b in SENSORS else rng2
        r = np.einsum("ij,tjk,kl->til", H, truth[b], mount[b])                  # sensor reading in the route's ground
        if noise == "noisy":
            n = R.from_rotvec(np.radians(3.0) * g.standard_normal((len(times), 3))).as_matrix()
            d = R.from_rotvec(np.outer(np.radians(10.0 * drift_sign[b] * frac), [0.0, 1.0, 0.0])).as_matrix()
            r = np.einsum("tij,tjk,tkl->til", d, r, n)
        readings[b] = r
        offsets[b] = (H @ truth[b][0]).T @ r[0]                                 # OpenSense-style, from the first frame
    for label, bodies in ((("pelvis_thighs_check", SENSORS),) if noise == "noisy" and seed_text.endswith("#check") else ()) + (("pelvis_thighs_shanks", ALL),):
        model = osim.Model(str(sdir / "model_scaled.osim"))
        for b in bodies:
            q = R.from_matrix(offsets[b]).as_quat()
            tr = osim.Transform(osim.Rotation(osim.Quaternion(float(q[3]), float(q[0]), float(q[1]), float(q[2]))), osim.Vec3(0))
            f = osim.PhysicalOffsetFrame(f"{b}_imu", model.getBodySet().get(b), tr); model.getBodySet().get(b).addComponent(f)
        model.finalizeConnections()
        cn2, v = solve(model, {f"{b}_imu": readings[b] for b in bodies}); write_mot(out / f"{label}_{noise}.mot", cn2, v)
        record["conditions"][f"{label}_{noise}"] = dict(sensors=bodies)
(out / "record_shanks.json").write_text(json.dumps(record, indent=1)); print(json.dumps(dict(frames=len(times), heading_deg=round(float(np.degrees(yaw)), 1))))
