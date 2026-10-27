"""MarkerSequence -> scaled OpenSim model + inverse kinematics.

Steps (all intermediate files are written to ``out_dir/opensim``):

1. prepare the generic model: attach the configured marker set, apply
   recorded marker-location fixes, add virtual joint-centre markers;
2. transform the sequence into OpenSim ground (gravity up, x = heading);
3. bridge short gaps, split at long ones, leave long per-marker gaps
   empty (NaN in the TRC), do not solve frames where less than half the
   IK marker weight has a target, low-pass each finite stretch (all logged);
4. build a static trial (SKEL q = 0 neutral pose, or the stillest window)
   and rigidly register it onto the model's default pose;
5. ScaleTool (measurement scaling + marker placement) -> subject .osim;
6. InverseKinematicsTool per segment -> .mot (+ marker errors .sto);
7. QC summary (marker RMS, imputed frames + per-marker gaps, up-vector estimates).
"""
from __future__ import annotations

import contextlib
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from . import filtering, frames
from .config import resolve
from .io_formats import read_table, write_table, write_trc
from .sequence import MarkerSequence

JC_PREFIX = "JC_"


def _osim():
    try:
        import opensim  # noqa: F401
    except ImportError as e:  # pragma: no cover - environment guard
        raise ImportError("The OpenSim stage needs the 'opensim' package (pip install opensim, "
                          "see pipeline/README.md)") from e
    import opensim as osim
    osim.Logger.setLevelString("error")
    return osim


@dataclass
class StageResult:
    out_dir: Path
    scaled_model: Path
    motions: list                    # one .mot per solved segment
    marker_errors: list              # matching *_ik_marker_errors.sto
    qc: dict = field(default_factory=dict)

    @property
    def motion(self) -> Path:
        return self.motions[0]


# ------------------------------------------------------------------ model

def prepare_model(cfg, out_dir: Path, data_names):
    """Generic model + configured markers restricted to those present in the data."""
    osim = _osim()
    cfg_dir = Path(cfg["_path"]).parent
    model = osim.Model(str(resolve(cfg["model"], cfg_dir)))
    model.setName("rehabtwin_generic")
    if cfg.get("marker_set"):
        model.updateMarkerSet(osim.MarkerSet(str(resolve(cfg["marker_set"], cfg_dir))))
    state = model.initSystem()
    notes = []

    # Recorded fixes for upstream marker files (see config "marker_fixes").
    for fix in cfg.get("marker_fixes", []):
        src = model.getBodySet().get(fix["expressed_in"]) if fix["expressed_in"] != "ground" else model.getGround()
        for name in fix["markers"]:
            if not model.getMarkerSet().contains(name):
                continue
            mk = model.getMarkerSet().get(name)
            loc = mk.get_location()
            new = src.findStationLocationInAnotherFrame(state, loc, mk.getParentFrame())
            mk.set_location(new)
        notes.append(f"re-expressed {len(fix['markers'])} markers from {fix['expressed_in']} frame: {fix['why']}")

    # Markers placed for another generic model's bones (config "marker_rescale", "marker_to_joint"): moved to the
    # same anatomical place on this model's bones.
    for fix in cfg.get("marker_rescale", []):
        moved = [n for n in fix["markers"] if model.getMarkerSet().contains(n)]
        for name in moved:
            mk = model.getMarkerSet().get(name)
            loc = mk.get_location()
            mk.set_location(osim.Vec3(*(loc.get(i) * float(f) for i, f in enumerate(fix["factors"]))))
        notes.append(f"rescaled {len(moved)} markers on their bodies by {fix['factors']}: {fix['why']}")
    joint_fix = cfg.get("marker_to_joint", {})
    for name, body in joint_fix.get("markers", {}).items():
        if model.getMarkerSet().contains(name):
            mk = model.getMarkerSet().get(name)
            mk.set_location(model.getBodySet().get(body).findStationLocationInAnotherFrame(
                state, osim.Vec3(0.0, 0.0, 0.0), mk.getParentFrame()))
    if joint_fix:
        notes.append(f"placed {sorted(joint_fix['markers'])} on the joint centres they name: {joint_fix['why']}")

    bodies = {model.getBodySet().get(i).getName() for i in range(model.getBodySet().getSize())}
    jc = cfg.get("joint_centre_markers", {})
    for joint_name, spec in jc.items():
        name = JC_PREFIX + joint_name
        if name not in data_names or spec["body"] not in bodies:
            continue
        loc = osim.Vec3(*spec.get("location", [0.0, 0.0, 0.0]))
        mk = osim.Marker(name, model.getBodySet().get(spec["body"]), loc)
        mk.set_fixed(True)
        model.addMarker(mk)

    # Keep only markers the data can drive; drop markers on missing bodies.
    ms = model.updMarkerSet()
    for i in reversed(range(ms.getSize())):
        mk = ms.get(i)
        if mk.getName() not in data_names:
            ms.remove(i)
    fixed_policy = cfg.get("marker_fixed_policy", "keep")
    for i in range(ms.getSize()):
        mk = ms.get(i)
        if mk.getName().startswith(JC_PREFIX):
            continue
        if fixed_policy == "all_free":
            mk.set_fixed(False)
    model.finalizeConnections()
    model.initSystem()
    path = out_dir / "model_generic_with_markers.osim"
    model.printToXML(str(path))
    names = [ms.get(i).getName() for i in range(ms.getSize())]
    return path, names, notes


def model_marker_positions(model_path, names):
    """Marker positions in ground at the model's default pose."""
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    out = np.full((len(names), 3), np.nan)
    for i, n in enumerate(names):
        if model.getMarkerSet().contains(n):
            p = model.getMarkerSet().get(n).getLocationInGround(state)
            out[i] = [p.get(0), p.get(1), p.get(2)]
    return out


# --------------------------------------------------------------- frames

def foot_marker_heights(model_path, foot_names):
    """Height of each foot marker above the lowest one with the model's feet flat (default pose).

    Foot markers sit at different heights above the sole (back of heel vs.
    plantar points); the floor fit subtracts these so contact samples really
    lie on one plane. Only differences matter, so the common offset is irrelevant.
    """
    pos = model_marker_positions(model_path, foot_names)
    y = pos[:, 1]
    return {n: float(v - np.nanmin(y)) for n, v in zip(foot_names, y) if np.isfinite(v)}


def to_ground(seq: MarkerSequence, cfg, marker_heights=None):
    """Return (names, points (T,N,3) in OpenSim ground, qc dict)."""
    names, pts = seq.all_points()
    fcfg = cfg.get("frames", {})
    qc = {"input_frame": seq.frame}
    if seq.frame == "opensim":
        qc["up_source"] = "input already in OpenSim ground"
        return names, pts, qc
    if seq.frame == "opencv_camera":
        world = frames.apply(frames.R_CV_TO_YUP, pts)
    else:
        world = pts.copy()
    camera_up = np.array([0.0, 1.0, 0.0])
    up = camera_up
    mode = fcfg.get("up", "auto")
    qc["up_mode_requested"] = mode
    device_up = seq.meta.get("gravity_up_cv")
    if device_up is not None and seq.frame == "opencv_camera" and mode in ("auto", "device"):
        # Gravity measured by the recording device (phone IMU / calibration) beats any image-based guess.
        up = frames.apply(frames.R_CV_TO_YUP, np.asarray(device_up, float))
        up = up / np.linalg.norm(up)
        qc["up_source"] = f"device gravity ({seq.meta.get('gravity_source', 'unspecified')})"
        qc["device_tilt_vs_camera_level_deg"] = round(frames.angle_deg(up, camera_up), 2)
    elif mode == "device":
        raise ValueError("up=device requested but the sequence has no gravity_up_cv")
    floor = None
    try:
        n, rms, npts = frames.estimate_floor_up(world, names, fcfg.get("foot_markers", []), camera_up,
                                                marker_heights=marker_heights)
        floor = {"normal": n.round(4).tolist(), "rms_m": round(rms, 4), "n_points": npts,
                 "tilt_vs_camera_level_deg": round(frames.angle_deg(n, camera_up), 2)}
    except ValueError as e:
        floor = {"error": str(e)}
    qc["floor_fit"] = floor
    use_floor = False
    if mode == "floor":
        if "error" in floor:
            raise ValueError(f"up=floor requested but floor fit failed: {floor['error']}")
        use_floor = True
    elif mode == "auto" and "error" not in floor:
        use_floor = (floor["rms_m"] <= fcfg.get("floor_max_rms_m", 0.02)
                     and floor["tilt_vs_camera_level_deg"] <= fcfg.get("floor_max_tilt_deg", 20.0))
    if "up_source" in qc:  # device gravity already chosen; the floor fit is kept as a cross-check
        if "error" not in floor:
            floor["angle_to_device_up_deg"] = round(frames.angle_deg(floor["normal"], up), 2)
    else:
        if use_floor:
            up = np.asarray(floor["normal"])
        fallback = "input y axis (calibrated lab frame)" if seq.frame == "yup_world" else "camera-level assumption"
        qc["up_source"] = "floor plane fit" if use_floor else fallback
    R1 = frames.rotation_between(up, [0.0, 1.0, 0.0])
    world = frames.apply(R1, world)
    R2, t2 = frames.to_opensim_ground(world, names, [0.0, 1.0, 0.0],
                                      [tuple(p) for p in fcfg.get("right_left_pairs", [])],
                                      floor_names=fcfg.get("foot_markers"))
    return names, frames.apply(R2, world, t2), qc


# --------------------------------------------------------------- static

def static_points(seq: MarkerSequence, ground_names, ground_pts, valid_mask, cfg):
    """(points (N,3), description) for the scaling trial, in any rigid frame."""
    if seq.static_markers is not None:
        names, pts = seq.all_points(static=True)
        order = [names.index(n) for n in ground_names]
        return pts[order], "neutral pose supplied by front-end (SKEL q = 0)"
    window = int(round(cfg.get("static", {}).get("window_s", 0.5) * seq.fps))
    best, best_i = math.inf, None
    vel = np.linalg.norm(np.diff(ground_pts, axis=0), axis=2)  # (T-1, N)
    for i in range(0, len(ground_pts) - window):
        if not valid_mask[i:i + window].all():
            continue
        v = np.nanmean(vel[i:i + window - 1])
        if v < best:
            best, best_i = v, i
    if best_i is None:
        raise ValueError("no fully valid window for a static trial; record a still neutral stance")
    pts = np.nanmedian(ground_pts[best_i:best_i + window], axis=0)
    return pts, f"stillest {window}-frame window starting at frame {best_i} (mean speed {best * seq.fps:.3f} m/s)"


# ---------------------------------------------------------------- XML

def marker_weight(n, weights, default_w):
    """IK weight of marker ``n``; a virtual joint-centre marker falls back to its joint's weight."""
    return weights.get(n, weights.get(n[len(JC_PREFIX):] if n.startswith(JC_PREFIX) else "", default_w))


def _tasks_xml(names, weights, default_w, coord_tasks=None):
    """IKTaskSet XML. ``coord_tasks``: {coordinate: {"weight": w, "value": v (internal units) | "from_file": True}}."""
    out = []
    for n in names:
        w = marker_weight(n, weights, default_w)
        out.append(f'<IKMarkerTask name="{escape(n)}"><apply>{"true" if w > 0 else "false"}</apply>'
                   f"<weight>{w}</weight></IKMarkerTask>")
    for c, spec in (coord_tasks or {}).items():
        if spec.get("from_file"):
            value = "<value_type>from_file</value_type>"
        else:
            value = f"<value_type>manual_value</value_type><value>{spec.get('value', 0.0)}</value>"
        out.append(f'<IKCoordinateTask name="{escape(c)}"><apply>true</apply>'
                   f"<weight>{spec['weight']}</weight>{value}</IKCoordinateTask>")
    return "<IKTaskSet><objects>" + "".join(out) + "</objects><groups/></IKTaskSet>"


def scale_setup_xml(cfg, generic_model, static_trc, t_range, mass_kg, height_m, marker_names, manual_scales=None):
    """ScaleTool setup (markers are placed by ``place_markers``): measurement scaling from the static trial, or,
    with ``manual_scales`` ({body: [sx, sy, sz]}, a person model's), exactly those factors.

    OpenSim resolves these file names relative to the setup file's folder.
    """
    meas = []
    for m in ([] if manual_scales else cfg["scaling"]["measurements"]):
        pairs = [p for p in m["pairs"] if p[0] in marker_names and p[1] in marker_names]
        if not pairs:
            continue
        pairs_xml = "".join(f"<MarkerPair><markers> {a} {b}</markers></MarkerPair>" for a, b in pairs)
        bodies_xml = "".join(f'<BodyScale name="{b}"><axes> {ax}</axes></BodyScale>' for b, ax in m["bodies"].items())
        meas.append(f'<Measurement name="{m["name"]}"><apply>true</apply>'
                    f"<MarkerPairSet><objects>{pairs_xml}</objects><groups/></MarkerPairSet>"
                    f"<BodyScaleSet><objects>{bodies_xml}</objects><groups/></BodyScaleSet></Measurement>")
    t0, t1 = t_range
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500">
<ScaleTool name="subject">
<mass>{mass_kg}</mass>
<height>{height_m if height_m else -1}</height>
<age>-1</age>
<notes>Generated by rehabtwin</notes>
<GenericModelMaker><model_file>{generic_model}</model_file><marker_set_file>Unassigned</marker_set_file></GenericModelMaker>
<ModelScaler>
<apply>true</apply>
<scaling_order> {"manualScale" if manual_scales else "measurements"}</scaling_order>
<MeasurementSet><objects>{"".join(meas)}</objects><groups/></MeasurementSet>
<ScaleSet><objects>{"".join(f"<Scale><scales> {' '.join(repr(float(v)) for v in f)}</scales><segment>{b}</segment>"
                             f"<apply>true</apply></Scale>" for b, f in (manual_scales or {}).items())}</objects><groups/></ScaleSet>
<marker_file>{static_trc}</marker_file>
<time_range> {t0} {t1}</time_range>
<preserve_mass_distribution>true</preserve_mass_distribution>
<output_model_file>model_scaled_only.osim</output_model_file>
<output_scale_file>scale_factors.xml</output_scale_file>
</ModelScaler>
<MarkerPlacer><apply>false</apply></MarkerPlacer>
</ScaleTool>
</OpenSimDocument>
"""


def place_markers(model_path, static_mot, static_names, static_pts, out_path, max_move_m):
    """Move free (non-fixed) markers onto their static-trial positions at the solved static pose.

    Equivalent to OpenSim's MarkerPlacer but explicit and logged: markers whose
    required move exceeds ``max_move_m`` are left in place and reported.
    """
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    tab = read_table(static_mot)
    cs = model.getCoordinateSet()
    for c in tab.columns:
        if cs.contains(c):
            co = cs.get(c)
            v = tab.col(c)[0]
            if co.getMotionType() == osim.Coordinate.Rotational and tab.in_degrees:
                v = np.radians(v)
            co.setValue(state, v, False)
    model.realizePosition(state)
    moved, refused = {}, {}
    ground = model.getGround()
    for i, n in enumerate(static_names):
        if not model.getMarkerSet().contains(n) or not np.isfinite(static_pts[i]).all():
            continue
        mk = model.updMarkerSet().get(n)
        if mk.get_fixed():
            continue
        cur = mk.getLocationInGround(state)
        d = float(np.linalg.norm(np.array([cur.get(0), cur.get(1), cur.get(2)]) - static_pts[i]))
        if max_move_m is not None and max_move_m > 0 and d > max_move_m:
            refused[n] = round(d, 4)
            continue
        target = osim.Vec3(*map(float, static_pts[i]))
        mk.set_location(ground.findStationLocationInAnotherFrame(state, target, mk.getParentFrame()))
        moved[n] = round(d, 4)
    model.setName("rehabtwin_subject")
    model.finalizeConnections()
    model.printToXML(str(out_path))
    vals = np.array(list(moved.values())) if moved else np.zeros(1)
    return {"moved": len(moved), "mean_move_m": round(float(vals.mean()), 4), "max_move_m": round(float(vals.max()), 4),
            "refused_over_limit": refused}


def ik_setup_xml(cfg, model, trc, t_range, out_dir, name, marker_names, coord_file=None, coord_tasks=None):
    ik = cfg["ik"]
    t0, t1 = t_range
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500">
<InverseKinematicsTool name="{name}">
<results_directory>.</results_directory>
<model_file>{model}</model_file>
<constraint_weight>{ik.get("constraint_weight", "Inf")}</constraint_weight>
<accuracy>{ik.get("accuracy", 1e-5)}</accuracy>
{_tasks_xml(marker_names, ik.get("weights", {}), ik.get("default_weight", 1.0), coord_tasks)}
<marker_file>{trc}</marker_file>
<coordinate_file>{coord_file or "Unassigned"}</coordinate_file>
<time_range> {t0} {t1}</time_range>
<report_errors>true</report_errors>
<output_motion_file>{name}.mot</output_motion_file>
<report_marker_locations>false</report_marker_locations>
</InverseKinematicsTool>
</OpenSimDocument>
"""


# ------------------------------------------------------------ gaps

def condition_markers(names, pts, valid, frame_index, fps, fcfg, upstream_imputed=None, weights=None,
                      min_target_weight=0.5):
    """Gap policy + low-pass for (T, N, 3) points -> (segments, clean points, gap QC).

    Whole-frame gaps <= max_gap_s are bridged, longer ones split segments. Inside a segment
    each marker is bridged only over its own gaps <= max_gap_s; a longer one stays NaN, so IK
    has no target for that marker there. A frame where less than ``min_target_weight`` of the
    IK marker ``weights`` (N,) has a target is not solved: IK would fail to assemble or hold
    the unobserved joints at its warm start (e.g. augmenter outputs masked over a lost knee).
    Such frames split the segment like a long gap; they are never bridged.
    ``upstream_imputed`` (T,) marks frames already built on bridged data (augmenter inputs).
    """
    max_gap_s = fcfg.get("max_gap_s", 0.2)
    segs, _ = filtering.plan_segments(valid, fps, max_gap_s, fcfg.get("min_segment_s", 1.0))
    raw = np.where(np.asarray(valid, bool)[:, None, None], pts, np.nan)  # a rejected frame is a gap for every marker
    clean = np.full_like(raw, np.nan)
    for a, b in segs:
        seg = filtering.interpolate_gaps(raw[a:b], int(round(max_gap_s * fps)))
        clean[a:b] = filtering.lowpass(seg, fps, fcfg.get("cutoff_hz", 6.0), fcfg.get("order", 4))
    w = np.ones(len(names)) if weights is None else np.asarray(weights, float)
    covered = np.isfinite(clean).all(axis=2) @ w >= min_target_weight * w.sum()
    min_len = max(int(round(fcfg.get("min_segment_s", 1.0) * fps)), 2)
    planned = np.zeros(len(raw), bool)
    for a, b in segs:
        planned[a:b] = True
    segs = [(a + s, a + e) for a, b in segs for s, e in filtering.runs(covered[a:b]) if e - s >= min_len]
    solved = np.zeros(len(raw), bool)
    for a, b in segs:
        solved[a:b] = True
    clean[~solved] = np.nan
    qc = gap_qc(names, raw, clean, segs, frame_index, fps, upstream_imputed, w)
    qc["unsolved"] = {"min_target_weight": min_target_weight, "frames": int((planned & ~covered).sum()),
                      "spans": _spans(planned & ~covered, frame_index, fps)}
    return segs, clean, qc


def _spans(mask, frame_index, fps):
    return [{"start_frame": int(frame_index[a]), "stop_frame": int(frame_index[b - 1]) + 1,
             "duration_s": round((b - a) / fps, 3)} for a, b in filtering.runs(mask)]


def gap_qc(names, raw, clean, segs, frame_index, fps, upstream_imputed=None, weights=None):
    """Per-marker imputed (bridged) and missing (no IK target) spans and coverage over solved frames.

    ``imputed_frames`` lists every frame in which any marker was bridged (here or upstream) and
    ``missing_target_frames`` every frame in which a weighted marker had no target, so metrics
    flag reps built on imputed or partly unobserved data even when only one marker was lost.
    """
    solved = np.zeros(len(raw), bool)
    for a, b in segs:
        solved[a:b] = True
    seen = np.isfinite(raw).all(axis=2) & solved[:, None]
    target = np.isfinite(clean).all(axis=2)
    imputed, missing = target & ~seen, solved[:, None] & ~target
    by_marker = {n: {"coverage": round(float(seen[:, j].sum() / max(solved.sum(), 1)), 4),
                     "imputed_s": round(float(imputed[:, j].sum() / fps), 3),
                     "imputed_spans": _spans(imputed[:, j], frame_index, fps),
                     "missing_s": round(float(missing[:, j].sum() / fps), 3),
                     "missing_spans": _spans(missing[:, j], frame_index, fps)}
                 for j, n in enumerate(names)}
    any_imputed = imputed.any(axis=1)
    if upstream_imputed is not None:
        any_imputed |= solved & upstream_imputed
    weighted = np.ones(len(names), bool) if weights is None else np.asarray(weights) > 0
    return {"imputed_frames": [int(frame_index[f]) for f in np.flatnonzero(any_imputed)],
            "missing_target_frames": [int(frame_index[f]) for f in np.flatnonzero(missing[:, weighted].any(axis=1))],
            "imputed_by_marker": by_marker}


# ------------------------------------------------------------- the stage

KNOWN_MASS_SOURCES = ("measured", "synthetic truth")
PERSON_SCALE_TOL = 0.10      # a calibrated recording this far off the person's bones is another body or a fault


def scale_is_measured(meta):
    """Whether the front end measured metric scale (calibrated cameras, depth). One camera only estimates it:
    MediaPipe's world landmarks are sized for an average body, HSMR's from a shape prior at a fixed focal."""
    if "metric_scale" in meta:
        return bool(meta["metric_scale"])
    src = str(meta.get("source", ""))
    return not ("monocular" in src.lower() or src.startswith("HSMR"))


def recording_scale(cfg, names, static, model_static, person_scales):
    """(median, {measurement: ratio}): the static trial's own measurement scale factors (marker-pair distances
    over the generic model's, as ScaleTool computes them) divided by the person's stored ones."""
    idx = {n: i for i, n in enumerate(names)}
    axis = {"X": 0, "Y": 1, "Z": 2}
    per = {}
    for m in cfg["scaling"]["measurements"]:
        pairs = [p for p in m["pairs"] if p[0] in idx and p[1] in idx]
        body, axes = next(iter(m["bodies"].items()))
        if not pairs or body not in person_scales:
            continue
        own = [np.linalg.norm(static[idx[a]] - static[idx[b]]) / np.linalg.norm(model_static[idx[a]] - model_static[idx[b]])
               for a, b in pairs]
        own = [v for v in own if np.isfinite(v)]
        if own:
            per[m["name"]] = round(float(np.mean(own)) / person_scales[body][axis[axes.split()[0]]], 4)
    if not per:
        raise ValueError("no scaling measurement of this config has both markers in the recording: cannot check "
                         "the recording against the person's bones")
    return round(float(np.median(list(per.values()))), 4), per


def subject_mass(meta, cfg, mass_kg=None):
    """(kg, source) the model is scaled to. Ground forces, joint torques and muscle activations all
    scale with it, so only a given mass is 'measured' (a synthetic session's generator mass is its
    truth); the config default is recorded as 'assumed default', never passed off as this person's.
    The mass given to ``augment --mass-kg`` (an LSTM input) carries over with its ``--mass-source``; two
    measured masses must agree."""
    aug = meta.get("augmenter") or {}
    aug_kg, aug_measured = aug.get("mass_kg"), aug.get("mass_source") == "measured"
    if mass_kg is not None and aug_kg is not None and aug_measured and abs(float(mass_kg) - float(aug_kg)) > 0.5:
        raise ValueError(f"--mass-kg {mass_kg} disagrees with the measured {aug_kg} kg the marker augmenter was run with")
    if mass_kg is None and aug_kg is not None:
        if not aug_kg > 0:
            raise ValueError(f"body mass must be positive, got {aug_kg} kg")
        return float(aug_kg), "measured" if aug_measured else "assumed (augment --mass-kg, not measured)"
    if mass_kg is not None:
        if not mass_kg > 0:
            raise ValueError(f"body mass must be positive, got {mass_kg} kg")
        return float(mass_kg), "measured"
    if meta.get("synthetic") and meta.get("mass_kg"):
        return float(meta["mass_kg"]), "synthetic truth"
    return float(cfg.get("default_mass_kg", 70.0)), "assumed default"


def run(seq: MarkerSequence, cfg: dict, out_dir, mass_kg=None, height_m=None, on_commit=None, person=None) -> StageResult:
    """``person``: ``rehabtwin.person.for_session`` of the person model to use. Its scale factors are applied
    to the generic model instead of fitting new ones (or its personalised model is used as it is)."""
    mass, mass_source = subject_mass(seq.meta, cfg, mass_kg)     # refuse a bad mass before any work
    pm = (person or {}).get("model")
    if pm and pm["kind"] == "personalised":
        cfg = {**cfg, "model": pm["path"]}
    elif pm:
        from .tiers import sha256
        if sha256(resolve(cfg["model"])) != pm["generic_model_sha256"]:
            raise ValueError(f"the person model's scale factors belong to another generic model ({pm['generic_model']}) "
                             f"than this config's ({cfg['model']}): use config {pm.get('config')!r}")
    aug_gap, gap = (seq.meta.get("augmenter") or {}).get("max_gap_s"), cfg.get("filter", {}).get("max_gap_s", 0.2)
    if aug_gap is not None and abs(aug_gap - gap) > 1e-9:
        # augmenter outputs are masked over input gaps > aug_gap; this stage bridges marker gaps <= gap
        raise ValueError(f"the augmenter masked input gaps longer than {aug_gap} s but config filter.max_gap_s is "
                         f"{gap} s: re-run augment with --max-gap-s {gap}")
    osim = _osim()
    out_dir = Path(out_dir)
    od = out_dir / "opensim"
    od.mkdir(parents=True, exist_ok=True)
    qc = {"config": Path(cfg["_path"]).name, "n_frames": seq.n_frames, "fps": seq.fps}

    # 1. model (its foot geometry informs the floor fit)
    generic, model_names, notes = prepare_model(cfg, od, set(seq.all_points()[0]))
    qc["model_notes"] = notes
    manual = None                      # per-body factors a person model fixes (its personalised model: unit ones)
    if pm and pm["kind"] == "personalised":
        pmodel = osim.Model(str(generic))       # keep a reference: the body set lives in it
        bodies = pmodel.getBodySet()
        manual = {bodies.get(i).getName(): [1.0, 1.0, 1.0] for i in range(bodies.getSize())}
        if not manual:
            raise RuntimeError(f"{generic}: no bodies to scale")
    elif pm:
        manual = pm["scale_set"]
    foot = [n for n in cfg.get("frames", {}).get("foot_markers", []) if n in model_names]
    heights = foot_marker_heights(generic, foot) if foot else None

    # 2. frames
    names, pts, frame_qc = to_ground(seq, cfg, heights)
    qc["frames"] = frame_qc
    if heights:
        qc["frames"]["foot_marker_heights_m"] = {k: round(v, 4) for k, v in heights.items()}
    missing = sorted(set(names) - set(model_names))
    qc["markers_in_data_not_in_model"] = missing
    use = [names.index(n) for n in model_names]
    names = model_names
    pts = pts[:, use]
    if len(names) < 6:
        raise ValueError(f"only {len(names)} markers overlap between data and model; check config")

    # 3. segments, gaps, filtering
    fcfg = cfg.get("filter", {})
    valid = seq.valid & np.isfinite(pts).any(axis=(1, 2))
    upstream = np.isin(seq.frame_index, seq.meta.get("augmenter", {}).get("imputed_input_frames", []))
    ik = cfg.get("ik", {})
    weights = [marker_weight(n, ik.get("weights", {}), ik.get("default_weight", 1.0)) for n in names]
    segs, clean, gap_qc = condition_markers(names, pts, valid, seq.frame_index, seq.fps, fcfg, upstream, weights,
                                            ik.get("min_target_weight", 0.5))
    if not segs:
        un = gap_qc["unsolved"]
        raise ValueError("no segment long enough to solve (check detection rate / min_segment_s)" + (
            f"; {un['frames']} frames had targets for less than {un['min_target_weight']:.0%} of the IK marker "
            "weight (long per-marker gaps, or augmenter outputs masked over a keypoint lost > max_gap_s; "
            "a keypoint-only config solves from the remaining keypoints)" if un["frames"] else ""))
    qc["segments"] = [{"start_frame": int(seq.frame_index[a]), "stop_frame": int(seq.frame_index[b - 1]) + 1,
                       "duration_s": round((b - a) / seq.fps, 3)} for a, b in segs]
    qc.update(gap_qc)
    qc["detection_rate"] = round(float(seq.valid.mean()), 4)
    qc["filter"] = {"type": "butterworth zero-lag", "cutoff_hz": fcfg.get("cutoff_hz", 6.0), "order": fcfg.get("order", 4),
                    "max_gap_s": fcfg.get("max_gap_s", 0.2)}
    times = seq.times

    # 4. static trial, registered onto the model default pose
    try:  # prefer a window where every marker has a target (long per-marker gaps stay NaN)
        static, static_desc = static_points(seq, names, clean, valid & np.isfinite(clean).all(axis=(1, 2)), cfg)
    except ValueError:
        static, static_desc = static_points(seq, names, clean, valid, cfg)
    model_static = model_marker_positions(generic, names)
    reg_names = [n for n in cfg.get("static", {}).get("registration_markers", names) if n in names]
    reg = [names.index(n) for n in reg_names]
    R, t, _, rms = frames.kabsch(static[reg], model_static[reg])
    static_g = frames.apply(R, static, t)
    person_scale = None
    if manual:
        # the person's bones only fit a recording of the person's size
        ratio, per = recording_scale(cfg, names, static_g, model_static, manual)
        person_scale = {"recording_vs_person": ratio, "per_measurement": per, "scale_measured": scale_is_measured(seq.meta)}
        if person_scale["scale_measured"] and abs(ratio - 1.0) > PERSON_SCALE_TOL:
            raise ValueError(f"this recording measures the body {ratio:.2f} times the person model's size (median of "
                             f"{len(per)} segments): another person's folder, or a calibration fault. Process without "
                             "--person to compare")
        if not person_scale["scale_measured"]:
            # one camera: its size is a guess, the person's bones are measured. A uniform scale about a floor point
            # changes no joint angle.
            centre = np.array([np.nanmean(clean[..., 0]), 0.0, np.nanmean(clean[..., 2])])
            clean = centre + (clean - centre) / ratio
            static = static / ratio
            R, t, _, rms = frames.kabsch(static[reg], model_static[reg])
            static_g = frames.apply(R, static, t)
            person_scale["rescaled_by"] = round(1.0 / ratio, 4)
    qc["static"] = {"source": static_desc, "registration_rms_m": round(rms, 4), "registration_markers": len(reg)}
    if on_commit:      # every refusal is behind us: the folder's model, motion and markers change from here
        on_commit()
    write_trc(od / "markers_dynamic.trc", names, clean, times)
    n_static = 10
    static_times = np.arange(n_static) / 100.0
    write_trc(od / "markers_static.trc", names, np.repeat(static_g[None], n_static, axis=0), static_times)

    # 5. scale (measurements), static IK (soft-pinned known neutral pose), marker placement
    qc["subject"] = {"mass_kg": mass, "mass_source": mass_source, "height_m": height_m}
    scale_xml = od / "scale_setup.xml"
    scale_xml.write_text(scale_setup_xml(cfg, generic.name, "markers_static.trc",
                                         (static_times[0], static_times[-1]), mass, height_m, names))
    (od / "model_scaled_only.osim").unlink(missing_ok=True)
    if manual:        # the person's bones; with a personalised model only the masses follow today's
        scale_xml.write_text(scale_setup_xml(cfg, generic.name, "markers_static.trc", (static_times[0], static_times[-1]),
                                             mass, height_m, names, manual_scales=manual))
    with _cwd(od):
        # run() reports False whenever MarkerPlacer is off, so judge by the output file
        osim.ScaleTool(str(scale_xml)).run()
    if not (od / "model_scaled_only.osim").exists():
        raise RuntimeError(f"OpenSim ScaleTool failed (setup: {scale_xml})")
    qc["scale_factors"] = read_scale_factors(od / "scale_factors.xml")
    qc["scaling"] = {"method": "measurements from the static frames (config scaling.measurements)"}
    if pm:
        qc["scaling"] = {"method": "person model: its personalised model, segment masses scaled to the session's body "
                                   "mass (distribution kept)" if pm["kind"] == "personalised"
                         else "person model: its stored per-body scale factors (manual scaling)",
                         "person_model": {k: person[k] for k in ("person_ref", "version", "sha256")}}
        if person_scale:
            qc["scaling"]["recording_scale"] = person_scale
        diff = max(abs(a - b) for body, f in manual.items() for a, b in zip(f, qc["scale_factors"].get(body, [9, 9, 9])))
        qc["scaling"]["max_scale_factor_difference"] = round(diff, 5)
        if diff > 1e-3:
            raise RuntimeError(f"manual scaling reproduced the person's scale factors only to {diff:.4f}")
    scfg = cfg.get("static", {})
    pins = scfg.get("coordinate_pins", {}) if seq.static_markers is not None else scfg.get("coordinate_pins_measured", {})
    static_xml = od / "static_ik_setup.xml"
    static_xml.write_text(ik_setup_xml(cfg, "model_scaled_only.osim", "markers_static.trc",
                                       (static_times[0], static_times[-1]), od, "static_pose", names,
                                       coord_tasks={c: {"weight": w, "value": 0.0} for c, w in pins.items()}))
    with _cwd(od):
        ok = osim.InverseKinematicsTool(str(static_xml)).run()
    if not ok:
        raise RuntimeError(f"OpenSim static IK failed (setup: {static_xml})")
    scaled = od / "model_scaled.osim"
    if cfg["scaling"].get("marker_placer", True):
        placement = place_markers(od / "model_scaled_only.osim", od / "static_pose.mot", names, static_g,
                                  scaled, cfg["scaling"].get("max_marker_movement_m", 0.05))
    else:
        import shutil
        shutil.copy(od / "model_scaled_only.osim", scaled)
        placement = {"moved": 0, "note": "marker placement disabled"}
    static_err = read_table(od / "static_pose_ik_marker_errors.sto")
    qc["static"].update({"pinned_coordinates": sorted(pins), "marker_placement": placement,
                         "static_marker_rms_m_before_placement": round(float(static_err.col("marker_error_RMS").mean()), 4)})

    # 6. IK per segment
    coord_tasks, coord_file = None, None
    if cfg.get("skel_coordinate_tasks") and seq.skel_poses is not None:
        coord_tasks, coord_file = _skel_coordinate_file(seq, cfg, scaled, od)
    if cfg["ik"].get("coordinate_tasks"):
        # weak priors, e.g. Pose2Sim's L5_S1 task: sparse markers leave the pelvis/lumbar split ill-conditioned
        coord_tasks = {**cfg["ik"]["coordinate_tasks"], **(coord_tasks or {})}
    motions, errors = [], []
    for k, (a, b) in enumerate(segs):
        name = "ik" if len(segs) == 1 else f"ik_seg{k + 1:02d}"
        xml = od / f"{name}_setup.xml"
        xml.write_text(ik_setup_xml(cfg, scaled.name, "markers_dynamic.trc", (times[a], times[b - 1]),
                                    od, name, names, coord_file and Path(coord_file).name, coord_tasks))
        with _cwd(od):
            ok = osim.InverseKinematicsTool(str(xml)).run()
        if not ok:
            raise RuntimeError(f"OpenSim IK failed (setup: {xml})")
        motions.append(od / f"{name}.mot")
        errors.append(od / f"{name}_ik_marker_errors.sto")

    # 7. QC
    qc["ik"] = summarise_marker_errors(errors, cfg.get("qc", {}).get("max_rms_m", 0.04))
    if seq.skel_poses is not None:
        qc["skel_vs_ik"] = compare_skel_q(seq, motions)
    (out_dir / "qc.json").write_text(json.dumps(qc, indent=2))
    return StageResult(out_dir=out_dir, scaled_model=scaled, motions=motions, marker_errors=errors, qc=qc)


@contextlib.contextmanager
def _cwd(path):
    """OpenSim tools resolve some file names against the working directory."""
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def read_scale_factors(path):
    import re
    if not Path(path).exists():
        return {}
    txt = Path(path).read_text()
    out = {}
    for m in re.finditer(r'<Scale(?: name="[^"]*")?>\s*<scales>([^<]+)</scales>\s*<segment>([^<]+)</segment>', txt):
        seg = m.group(2).strip()
        if seg == "ground" or seg.endswith("_offset") or "geom_frame" in seg:
            continue
        out[seg] = [round(float(v), 4) for v in m.group(1).split()]
    return out


def summarise_marker_errors(paths, max_rms):
    rms_all, max_all = [], []
    for p in paths:
        tab = read_table(p)
        rms_all.append(tab.col("marker_error_RMS"))
        max_all.append(tab.col("marker_error_max"))
    rms = np.concatenate(rms_all)
    mx = np.concatenate(max_all)
    return {
        "marker_rms_m": {"mean": round(float(rms.mean()), 4), "p95": round(float(np.percentile(rms, 95)), 4),
                         "max": round(float(rms.max()), 4)},
        "marker_max_m": {"mean": round(float(mx.mean()), 4), "max": round(float(mx.max()), 4)},
        "frames_over_threshold": int((rms > max_rms).sum()),
        "threshold_rms_m": max_rms,
        "pass": bool((rms > max_rms).mean() < 0.05),
    }


def _skel_coordinate_file(seq, cfg, model_path, od):
    """SKEL q for coordinates that share name and convention with the model."""
    from .skel_names import SKEL_POSE_PARAM_NAMES
    osim = _osim()
    model = osim.Model(str(model_path))
    model.initSystem()
    cs = model.getCoordinateSet()
    shared = [n for n in cfg["skel_coordinate_tasks"] if cs.contains(n) and n in SKEL_POSE_PARAM_NAMES]
    cols = [np.degrees(seq.skel_poses[:, SKEL_POSE_PARAM_NAMES.index(n)]) for n in shared]
    path = od / "skel_coordinates.mot"
    write_table(path, shared, np.stack(cols, axis=1), seq.times, in_degrees=True)
    return {n: {"weight": cfg["skel_coordinate_tasks"][n], "from_file": True} for n in shared}, path


def compare_skel_q(seq, motions):
    """RMSE between SKEL's own joint angles and OpenSim IK, for same-named coordinates.

    A naming-level cross-check of the two routes (direct q vs marker IK); a
    large value flags either a convention mismatch or a poor fit.
    """
    from .skel_names import SKEL_POSE_PARAM_NAMES
    out = {}
    for mot in motions:
        tab = read_table(mot)
        idx = np.searchsorted(seq.times, tab.time - 1e-9)
        idx = np.clip(idx, 0, seq.n_frames - 1)
        for n in SKEL_POSE_PARAM_NAMES:
            if not tab.has(n) or n.startswith("pelvis_"):
                continue
            q = np.degrees(seq.skel_poses[idx, SKEL_POSE_PARAM_NAMES.index(n)])
            d = tab.col(n) - q
            d = d[np.isfinite(d)]
            if len(d):
                out.setdefault(n, []).append(d)
    return {n: round(float(np.sqrt(np.mean(np.concatenate(v) ** 2))), 2) for n, v in out.items()}
