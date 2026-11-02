"""Bones from body shape (rehabtwin/skel_bones.py) and the body-model file converter, with toy models only.

The licensed SMPL/SKEL files never enter the tests. Through OpenSim (scale factors on the generic model,
``person bones``) see test_pipeline.py.
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest

from rehabtwin import person, skel_bones

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))
import body_model_files

BONES = ("pelvis", "femur_r", "tibia_r", "talus_r", "calcn_r", "toes_r", "femur_l", "tibia_l", "talus_l", "calcn_l",
         "toes_l", "lumbar_body", "thorax", "head", "scapula_r", "humerus_r", "ulna_r", "radius_r", "hand_r",
         "scapula_l", "humerus_l", "ulna_l", "radius_l", "hand_l")


def _box(w=0.3, h=1.7, d=0.2):
    v = np.array([[x, y, z] for x in (-w / 2, w / 2) for y in (0.0, h) for z in (-d / 2, d / 2)])
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return v, f


def _toy_smpl():
    """A box 'body': beta 0 stretches it in height, beta 1 in girth (x and z)."""
    v, f = _box()
    S = np.zeros((8, 3, 2))
    S[:, 1, 0] = v[:, 1] * 0.1                  # +10 % height per unit
    S[:, 0, 1], S[:, 2, 1] = v[:, 0] * 0.1, v[:, 2] * 0.1
    return {"v_template": v, "shapedirs": S, "f": f}


def test_measures_scale_set_and_segments():
    """Joint-centre distances: a skeleton 1.1x the generic one gives 1.1 on every scaled axis."""
    rng = np.random.default_rng(0)
    gen = {b: rng.normal(0, 0.3, 3) for b in BONES}
    gen_os = {b: np.array([p[2], p[1], -p[0]]) for b, p in gen.items()}       # the same body in OpenSim axes
    mine = {b: 1.1 * p for b, p in gen.items()}
    m_gen, m_os = skel_bones.measures(gen, "smpl"), skel_bones.measures(gen_os, "opensim")
    assert m_gen == pytest.approx(m_os)                                    # frame-independent definitions
    factors = skel_bones.scale_set(skel_bones.measures(mine, "smpl"), m_os)
    assert factors["femur_r"] == pytest.approx([1.1, 1.1, 1.1]) and factors["pelvis"] == pytest.approx([1.1] * 3)
    assert set(factors) >= {"torso", "lumbar1", "sacrum", "toes_l", "hand_r", "patella_l"}
    seg = skel_bones.segment_lengths(mine)
    assert seg["thigh_r"] == pytest.approx(1.1 * np.linalg.norm(gen["femur_r"] - gen["tibia_r"]))
    half = dict(mine, femur_l=mine["femur_r"] * 0 + mine["tibia_l"] + (mine["femur_l"] - mine["tibia_l"]) / 1.1)
    f2 = skel_bones.scale_set(skel_bones.measures(half, "smpl"), m_os)
    assert f2["femur_l"] == pytest.approx([1.0] * 3) and f2["femur_r"] == pytest.approx([1.1] * 3)   # per side


def test_joints_need_smpl_topology():
    sm = _toy_smpl()
    skel = {"J_regressor_osim": np.full((len(BONES), 8), 1 / 8), "bone_names": np.array(BONES),
            "skin_template_v": sm["v_template"]}
    P = skel_bones.joints(skel, skel_bones.rest_surface(sm, [1.0, 0.0]))
    assert P["pelvis"] == pytest.approx([0.0, 1.7 * 1.1 / 2, 0.0])
    with pytest.raises(ValueError, match="SMPL topology"):
        skel_bones.joints(skel, np.zeros((5, 3)))


def test_betas_for_height_mass_and_refusal():
    sm = _toy_smpl()
    h0, m0 = skel_bones.body_measures(sm["v_template"], sm["f"])
    assert (h0, m0) == pytest.approx((1.7, 0.3 * 1.7 * 0.2 * 1000))
    b, got = skel_bones.betas_for_height_mass(sm, 1.87, 120.0, n_betas=2)
    assert got["height_m"] == pytest.approx(1.87, abs=0.005) and got["mass_kg"] == pytest.approx(120.0, rel=0.01)
    assert b[0] == pytest.approx(1.0, abs=0.05)                            # +10 % height
    with pytest.raises(ValueError, match="no SMPL body"):
        skel_bones.betas_for_height_mass({**sm, "shapedirs": sm["shapedirs"][:, :, 1:]}, 1.87, 102.0, n_betas=1)


def test_load_refuses_a_file_that_is_not_converted(tmp_path):
    np.savez(tmp_path / "x.npz", v_template=np.zeros((3, 3)))
    with pytest.raises(ValueError, match="body_model_files"):
        skel_bones.load_smpl(tmp_path / "x.npz")


class _Evil:
    def __reduce__(self):
        import os
        return (os.system, ("echo pwned",))


def test_converter_builds_arrays_and_refuses_code(tmp_path):
    import scipy.sparse
    src = tmp_path / "dl"
    (src / "sub").mkdir(parents=True)
    obj = {"v": np.arange(6.0).reshape(2, 3), "J": scipy.sparse.csc_matrix(np.eye(2)), "names": ["a", "b"],
           "ragged": [np.zeros(2), np.zeros(3)], "nothing": None, "nested": {"r": range(3)}}
    (src / "sub" / "model.pkl").write_bytes(pickle.dumps(obj, protocol=2))
    man = body_model_files.convert(src, tmp_path / "out")
    with np.load(tmp_path / "out" / "model.npz", allow_pickle=False) as z:
        assert z["v"].shape == (2, 3) and z["J"].tolist() == [[1, 0], [0, 1]] and z["names"].tolist() == ["a", "b"]
        assert z["ragged/1"].shape == (3,) and z["nested/r"].tolist() == [0, 1, 2] and z["__none__"].tolist() == ["nothing"]
    assert json.loads((tmp_path / "out" / "manifest.json").read_text()) == man
    (src / "sub" / "model.pkl").write_bytes(pickle.dumps({"x": _Evil()}))
    with pytest.raises(pickle.UnpicklingError, match="refused"):
        body_model_files.convert(src, tmp_path / "out2")
    assert not (tmp_path / "out2" / "model.npz").exists()


def test_person_bones_refusals(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1", height_m=1.8, mass_kg=80)
    with pytest.raises(person.PersonRefused, match="sex"):
        person.set_bones(d, tmp_path, tmp_path)
    person.set_measurement(d, sex="female")
    sm = _toy_smpl()
    np.savez(tmp_path / "basicmodel_f_lbs_10_207_0_v1.1.0.npz", **sm)
    np.savez(tmp_path / "skel_female.npz", J_regressor_osim=np.full((len(BONES), 8), 1 / 8), bone_names=np.array(BONES),
             skin_template_v=sm["v_template"], skin_template_f=sm["f"], shapedirs=sm["shapedirs"])
    with pytest.raises(person.PersonRefused, match="person shape --smpl-model"):
        person.set_bones(d, tmp_path, tmp_path, source="shape")
