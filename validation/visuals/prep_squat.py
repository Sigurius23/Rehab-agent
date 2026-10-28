"""3D page data, part 2: the OpenCap squat (subject 2, squats1) as tracked from five phone videos.

- our model after the marker fix: bone meshes and their poses per frame (OpenSim, from ik.mot);
- joint centres per frame for our model after and before the fix, and for OpenCap's own result;
- joint angles of all three; camera 2's video (trimmed to the tracked frames) with its MediaPipe keypoints.

    python -I prep_squat.py $WORK $REPO/upstream/perfanalytics/pose2sim/Pose2Sim/OpenSim_Setup/Geometry OUT
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import opensim as osim

SP, GEOM, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(Path(__file__).parent))
from vizpack import Pack   # noqa: E402

RUNS = {"fix": SP / "skel_work/oc_fix/multi_aug_fix", "base": SP / "skel_work/oc_fix/multi_aug_base"}
OPENCAP = SP / "oc_verify/data/OpenSimData"
VIDEO = SP / "oc_verify/data/Videos/Cam2/InputMedia/squats1/squats1.mov"
CAM2_FIRST = 51          # sequence frame k is camera 2's frame k + 51 (sync lag 46 + reference start 5)
STEP = 2                 # poses at 30 per second
# joint centres shown as a stick figure: name -> body whose origin it is
POINTS = {"pelvis": "pelvis", "hip_r": "femur_r", "knee_r": "tibia_r", "ankle_r": "talus_r", "heel_r": "calcn_r",
          "toes_r": "toes_r", "hip_l": "femur_l", "knee_l": "tibia_l", "ankle_l": "talus_l", "heel_l": "calcn_l",
          "toes_l": "toes_l", "shoulder_r": "humerus_r", "elbow_r": "ulna_r", "wrist_r": "hand_r",
          "shoulder_l": "humerus_l", "elbow_l": "ulna_l", "wrist_l": "hand_l"}
ANGLES = ["knee_angle_r", "knee_angle_l", "hip_flexion_r", "hip_flexion_l", "ankle_angle_r", "ankle_angle_l",
          "pelvis_tilt", "lumbar_extension"]


def read_mot(path):
    t = osim.TimeSeriesTable(str(path))
    cols = list(t.getColumnLabels())
    data = np.array([[t.getDependentColumn(c)[i] for c in cols] for i in range(t.getNumRows())])
    return np.array(t.getIndependentColumn()), cols, data


def poses(model_path, mot_path, rows, mesh_frames=False):
    """Per frame (rows of the motion): joint-centre positions, the pelvis heading, and optionally the ground
    transform of every frame that carries a mesh."""
    model = osim.Model(str(model_path))
    state = model.initSystem()
    t, cols, data = read_mot(mot_path)
    cs = model.getCoordinateSet()
    coords = [(cs.get(c), j) for j, c in enumerate(cols) if cs.contains(c)]
    meshes = []
    if mesh_frames:
        for c in model.getComponentsList():
            if c.getConcreteClassName() == "Mesh":
                g = osim.Mesh.safeDownCast(c)
                sf = g.get_scale_factors()
                meshes.append((g.getFrame().getAbsolutePathString(), g.get_mesh_file(), [sf.get(i) for i in range(3)]))
    frames = sorted({m[0] for m in meshes})
    bodies = model.getBodySet()
    P, heading, X = [], [], []
    for i in rows:
        for co, j in coords:
            v = data[i, j]
            co.setValue(state, np.radians(v) if co.getMotionType() == osim.Coordinate.Rotational else v, False)
        model.realizePosition(state)
        P.append([[bodies.get(b).getPositionInGround(state).get(k) for k in range(3)] for b in POINTS.values()])
        R = bodies.get("pelvis").getTransformInGround(state).R()
        heading.append([R.get(0, 0), R.get(2, 0)])
        if frames:
            row = []
            for f in frames:
                T = model.getComponent(f)
                T = osim.Frame.safeDownCast(T).getTransformInGround(state)
                q = T.R().convertRotationToQuaternion()
                row.append([T.p().get(0), T.p().get(1), T.p().get(2), q.get(1), q.get(2), q.get(3), q.get(0)])
            X.append(row)
    angles = {c: data[rows, cols.index(c)].tolist() for c in ANGLES if c in cols}
    return {"t": t[rows], "P": np.array(P), "heading": np.array(heading), "X": np.array(X), "frames": frames,
            "meshes": meshes, "angles": angles}


def read_vtp(path):
    s = Path(path).read_text()

    def array(name):
        m = re.search(r'<DataArray[^>]*Name="%s"[^>]*>(.*?)</DataArray>' % name, s, re.S)
        return np.array(m.group(1).split(), float)
    pts = re.search(r"<Points>\s*<DataArray[^>]*>(.*?)</DataArray>", s, re.S)
    v = np.array(pts.group(1).split(), float).reshape(-1, 3)
    polys = re.search(r"<Polys>(.*?)</Polys>", s, re.S).group(1)
    conn = np.array(re.search(r'Name="connectivity"[^>]*>(.*?)</DataArray>', polys, re.S).group(1).split(), int)
    offs = np.array(re.search(r'Name="offsets"[^>]*>(.*?)</DataArray>', polys, re.S).group(1).split(), int)
    tris, a = [], 0
    for b in offs:                               # fan-triangulate each polygon
        p = conn[a:b]
        tris += [(p[0], p[k], p[k + 1]) for k in range(1, len(p) - 1)]
        a = b
    return v, np.array(tris, int)


def main():
    pack, meta = Pack(), {}
    t_ref, cols_ref, _ = read_mot(OPENCAP / "Kinematics/squats1.mot")
    n = len(read_mot(RUNS["fix"] / "opensim/ik.mot")[0])
    rows = np.arange(0, n, STEP)
    lag = json.loads((RUNS["fix"] / "validation-report.json").read_text())["time_lag_applied_s"]
    run = {k: poses(p / "opensim/model_scaled.osim", p / "opensim/ik.mot", rows, mesh_frames=(k == "fix"))
           for k, p in RUNS.items()}
    # OpenCap's result on our time line: reference time + lag (as the validation report plots it)
    t_our = run["fix"]["t"]
    ref_rows = np.abs(t_ref[None, :] - (t_our - lag)[:, None]).argmin(1)
    run["opencap"] = poses(OPENCAP / "Model/LaiUhlrich2022_scaled.osim", OPENCAP / "Kinematics/squats1.mot", ref_rows)
    inside = (t_our - lag >= t_ref[0]) & (t_our - lag <= t_ref[-1])
    meta["opencap_valid"] = inside.astype(int).tolist()

    # bone meshes of our model, baked at its scale factors and merged per frame
    fx = run["fix"]
    verts, faces, frame_of_vert, counts = [], [], [], {}
    nv = 0
    for fi, f in enumerate(fx["frames"]):
        for fr, mesh, sf in fx["meshes"]:
            if fr != f:
                continue
            v, tri = read_vtp(GEOM / mesh)
            verts.append(v * sf)
            faces.append(tri + nv)
            frame_of_vert.append(np.full(len(v), fi))
            nv += len(v)
            counts[mesh] = len(tri)
    V, F, B = np.vstack(verts), np.vstack(faces), np.concatenate(frame_of_vert)
    print("meshes:", len(counts), "triangles:", len(F), "vertices:", len(V), flush=True)
    pack.add("mesh.v", V, np.float32)
    pack.add("mesh.f", F, np.uint32)
    pack.add("mesh.frame", B, np.uint8)
    pack.add("mesh.X", fx["X"], np.float32)
    meta["mesh_frames"] = [f.replace("/bodyset/", "") for f in fx["frames"]]
    for k in ("fix", "base", "opencap"):
        pack.add(f"{k}.P", run[k]["P"], np.float32)
        pack.add(f"{k}.heading", run[k]["heading"], np.float32)
        meta[f"{k}_angles"] = {c: [round(x, 2) for x in v] for c, v in run[k]["angles"].items()}
    meta["points"] = list(POINTS)
    meta["t"] = [round(x, 4) for x in t_our]
    meta["fps"] = 60 / STEP
    meta["lag_s"] = lag
    rep = {k: json.loads((p / "validation-report.json").read_text()) for k, p in RUNS.items()}
    meta["rmse"] = {k: {c: rep[k]["per_coordinate"][c] for c in ANGLES if c in rep[k]["per_coordinate"]} for k in RUNS}
    meta["scale"] = {}
    for k, p in RUNS.items():
        m = osim.Model(str(p / "opensim/model_scaled.osim"))
        s = m.initSystem()
        bs = m.getBodySet()
        d = lambda a, b: np.linalg.norm(np.array([bs.get(a).getPositionInGround(s).get(i) - bs.get(b).getPositionInGround(s).get(i) for i in range(3)]))
        meta["scale"][k] = {"shank_r_m": round(d("tibia_r", "talus_r"), 4), "thigh_r_m": round(d("femur_r", "tibia_r"), 4)}
    m = osim.Model(str(OPENCAP / "Model/LaiUhlrich2022_scaled.osim"))
    s = m.initSystem()
    bs = m.getBodySet()
    meta["scale"]["opencap"] = {"shank_r_m": round(d("tibia_r", "talus_r"), 4), "thigh_r_m": round(d("femur_r", "tibia_r"), 4)}

    # camera 2: the tracked frames as a small H.264 clip, and its MediaPipe keypoints
    cam = np.load(SP / "oc_verify/cam2.npz", allow_pickle=False)
    kp = cam["image_xy"][CAM2_FIRST:CAM2_FIRST + n] / cam["size"]
    vis = cam["visibility"][CAM2_FIRST:CAM2_FIRST + n]
    pack.add("cam2.kp", kp, np.uint16, 1 / 60000)
    pack.add("cam2.vis", np.clip(vis, 0, 1), np.uint8, 1 / 250)
    meta["video"] = {"file": "squat_cam2.mp4", "frames": n, "fps": 60, "first_source_frame": CAM2_FIRST,
                     "size": cam["size"].tolist(), "source": "OpenCap test data, subject 2, squats1, camera 2"}
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VIDEO), "-vf",
                    f"select=between(n\\,{CAM2_FIRST}\\,{CAM2_FIRST + n - 1}),setpts=N/60/TB,scale=360:640",
                    "-r", "60", "-an", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "27",
                    "-g", "30", "-movflags", "+faststart", str(OUT / "squat_cam2.mp4")], check=True)
    got = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(OUT / "squat_cam2.mp4")],
                         capture_output=True, text=True).stdout.strip()
    assert int(got) == n, f"clip has {got} frames, not {n}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "squat_cam2.mp4"), "-c:v", "libvpx-vp9", "-b:v", "0",
                    "-crf", "40", "-row-mt", "1", "-an", str(OUT / "squat_cam2.webm")], check=True)   # for browsers without H.264
    meta["arrays"] = pack.write(OUT / "squat.bin")
    (OUT / "squat.json").write_text(json.dumps(meta))
    print({k: v for k, v in meta["scale"].items()}, "lag", lag, "frames", len(rows))


if __name__ == "__main__":
    main()
