"""Person model (rehabtwin/person.py) without OpenSim: versions, history and refusals.

The round trip through OpenSim (build from a session, re-process with the person's bones) is in
test_pipeline.py.
"""
import json

import pytest

from rehabtwin import person, records, tiers


def _with_model(d, **model):
    """A person folder whose person.json points at a stand-in model file."""
    (d / "model.osim").write_text("<OpenSimDocument/>")
    rec = person.load(d)
    rec["model"] = {"kind": "scaled-generic", "file": "model.osim", "sha256": tiers.sha256(d / "model.osim"),
                    "generic_model": "g.osim", "generic_model_sha256": "0" * 64, "scale_set": {"femur_r": [1, 1, 1]},
                    "config": "skel105_pose2sim.json", "built_from": {"session_id": "s1"}, **model}
    rec["keypoint_segments"] = {"LHip-LKnee": {"length_m": 0.41}, "RHip-RKnee": {"length_m": 0.42}}
    return person.save(d, rec, "test model")


def _session(d, person_ref="P1", mass_source="measured", synthetic=False, pid="p0", scaling=None):
    d.mkdir(parents=True, exist_ok=True)
    pipeline = {"front_end": "test", "config": "skel105_pose2sim.json",
                "outputs": {"model": "opensim/model_scaled.osim", "motion": "opensim/ik.mot"}}
    if pid:
        pipeline["processing_id"] = pid
    else:
        pipeline["reprocessing_started_at"] = "2026-01-01T00:00:00+00:00"
    (d / "session.json").write_text(json.dumps({"session_id": "s1", "person_ref": person_ref, "synthetic": synthetic,
                                                "pipeline": pipeline}))
    qc = {"subject": {"mass_kg": 80.0, "mass_source": mass_source, "height_m": 1.8},
          "scale_factors": {"femur_r": [1.1, 1.1, 1.1]}}
    if scaling:
        qc["scaling"] = scaling
    (d / "qc.json").write_text(json.dumps(qc))
    return d


def test_init_versions_and_history(tmp_path):
    d = tmp_path / "P1"
    rec = person.init(d, "P1", height_m=1.8, mass_kg=80)
    assert rec["version"] == 1 and rec["format"] == person.FORMAT
    assert rec["anthropometrics"]["mass_kg"]["measured"] is True
    assert set(rec["layers"]) == set(person.LAYERS) and rec["layers"]["bone_geometry"]["status"] == "not modelled"
    with pytest.raises(person.PersonRefused, match="already holds"):
        person.init(d, "P1")
    rec = person.set_measurement(d, mass_kg=78.5)
    assert rec["version"] == 2 and rec["anthropometrics"]["mass_kg"]["value"] == 78.5
    assert rec["anthropometrics"]["height_m"]["value"] == 1.8                   # kept
    old = json.loads((d / "history" / "person_v001.json").read_text())
    assert old["anthropometrics"]["mass_kg"]["value"] == 80
    assert [h["version"] for h in rec["history"]] == [1, 2]
    assert "P1" in person.summary(rec) and "not modelled" in person.summary(rec)


def test_assumed_mass_is_not_used_as_measured(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1", height_m=1.8, mass_kg=80, mass_source="assumed")
    _with_model(d)
    info = person.for_session(d, "P1")
    assert info["mass_kg"] is None and info["height_m"] == 1.8
    assert "NOT measured" in person.summary(person.load(d))


def test_load_refuses_a_changed_model_or_format(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1")
    _with_model(d)
    assert person.load(d)["model"]["kind"] == "scaled-generic"
    (d / "model.osim").write_text("<OpenSimDocument>edited</OpenSimDocument>")
    with pytest.raises(person.PersonRefused, match="changed since"):
        person.load(d)
    rec = json.loads((d / "person.json").read_text())
    rec["format"] = "something-else/9"
    (d / "person.json").write_text(json.dumps(rec))
    with pytest.raises(person.PersonRefused, match="format"):
        person.load(d)
    with pytest.raises(person.PersonRefused, match="no person.json"):
        person.load(tmp_path / "nobody")


def test_for_session_refusals_and_contents(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1", height_m=1.8, mass_kg=80)
    with pytest.raises(person.PersonRefused, match="no model yet"):
        person.for_session(d, "P1")
    _with_model(d)
    with pytest.raises(person.PersonRefused, match="session is of 'P2'"):
        person.for_session(d, "P2")
    with pytest.raises(person.PersonRefused, match="the sequence is synthetic"):
        person.for_session(d, "P1", synthetic=True)
    info = person.for_session(d, None)                                        # the sequence names nobody
    assert info["person_ref"] == "P1" and info["mass_kg"] == 80 and info["version"] == 2
    assert info["keypoint_segments"] == {"LHip-LKnee": 0.41, "RHip-RKnee": 0.42}
    assert info["model"]["path"].endswith("model.osim") and info["sha256"] == tiers.sha256(d / "person.json")


def test_build_refusals(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1")
    with pytest.raises(person.PersonRefused, match="of 'P2'"):
        person.build_from_session(d, _session(tmp_path / "a", person_ref="P2"))
    with pytest.raises(person.PersonRefused, match="synthetic session is not a person"):
        person.build_from_session(d, _session(tmp_path / "b", synthetic=True))
    with pytest.raises(person.PersonRefused, match="needs a measured mass"):
        person.build_from_session(d, _session(tmp_path / "c", mass_source="assumed default"))
    with pytest.raises(person.PersonRefused, match="itself processed with a person model"):
        person.build_from_session(d, _session(tmp_path / "d", scaling={"person_model": {"version": 1}}))
    with pytest.raises(records.StaleResult):
        person.build_from_session(d, _session(tmp_path / "e", pid=None))
    assert person.load(d)["version"] == 1 and not (d / "model.osim").exists()   # nothing changed


def test_attach_refuses_records_that_do_not_bind(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1")
    model = tmp_path / "P1_msk.osim"
    model.write_text("<OpenSimDocument/>")
    prov = {"tier": "A", "person_ref": "P1", "model": "P1_msk.osim", "model_sha256": tiers.sha256(model),
            "evidence": "MRI", "approved_by": "clinician"}

    def attach(**over):
        p = tmp_path / "prov.json"
        p.write_text(json.dumps({**prov, **over}))
        return person.attach_personalised_model(d, model, p)
    with pytest.raises(person.PersonRefused, match="lacks"):
        attach(approved_by="")
    with pytest.raises(person.PersonRefused, match="provenance is for 'P2'"):
        attach(person_ref="P2")
    with pytest.raises(person.PersonRefused, match="sha256 differs"):
        attach(model_sha256="0" * 64)
    assert not (d / "model.osim").exists()


def test_cli_person_init_set_show(tmp_path, capsys):
    from rehabtwin import cli
    d = tmp_path / "P1"
    assert cli.main(["person", "init", str(d), "--person-ref", "P1", "--height-m", "1.75", "--mass-kg", "70"]) == 0
    assert cli.main(["person", "set", str(d), "--mass-kg", "71"]) == 0
    assert cli.main(["person", "show", str(d)]) == 0
    out = capsys.readouterr().out
    assert "person model v2" in out and "71" in out
    assert cli.main(["person", "init", str(d), "--person-ref", "P1"]) == 2
    assert "already holds" in capsys.readouterr().err
    assert cli.main(["person", "build", str(d), str(_session(tmp_path / "s", person_ref="P9"))]) == 2
