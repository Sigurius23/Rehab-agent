# Provenance of the video-benchmark pilot's downloads and environments. Args: kin_root out_json
import hashlib, json, subprocess, sys, datetime
from pathlib import Path
K, out = Path(sys.argv[1]), Path(sys.argv[2])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
D = K / "pilot" / "data"
fix = "63546b73ab2a3c6dd6c95a05d66e0527bab873c7"
rec = dict(written=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
  fixture=dict(source=f"https://raw.githubusercontent.com/stanfordnmbl/opencap-test-data/{fix}/Data/labvalidation-fixtures/subject2_session0_5-cameras",
               commit=fix, files={str(p.relative_to(D)): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(D.rglob("*")) if p.is_file()}),
  mediapipe_model=dict(source="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
                       etag="453dec4d02ccc4d3ce812b6de84fa516", generation="1682642785588631", last_modified="Fri, 28 Apr 2023 00:46:25 GMT",
                       bytes=(K/"models/mediapipe/pose_landmarker_heavy.task").stat().st_size, sha256=sha(K/"models/mediapipe/pose_landmarker_heavy.task")),
  pose2sim=dict(source="https://github.com/perfanalytics/pose2sim", depth=1,
                commit=subprocess.check_output(["git", "-C", str(K/"upstream/perfanalytics/pose2sim"), "rev-parse", "HEAD"], text=True).strip(),
                lstm=dict((str(p.relative_to(K/"upstream/perfanalytics/pose2sim")), sha(p)) for p in sorted((K/"upstream/perfanalytics/pose2sim/Pose2Sim/MarkerAugmenter").rglob("*")) if p.is_file())),
  repo_commit=subprocess.check_output(["git", "-C", str(Path.home()/"rehab-agent"), "rev-parse", "HEAD"], text=True).strip(),
  environments={n: subprocess.check_output(["uv", "pip", "freeze", "--python", str(K/f"envs/{n}/bin/python")], text=True).split()
                for n in ("pipeline", "mediapipe")})
rec["environments"]["python"] = {n: subprocess.check_output([str(K/f"envs/{n}/bin/python"), "-I", "-c", "import sys; print(sys.version.split()[0])"], text=True).strip() for n in ("pipeline", "mediapipe")}
out.write_text(json.dumps(rec, indent=1))
print(json.dumps({k: (v if k != "fixture" else {kk: (vv if kk != "files" else len(vv)) for kk, vv in v.items()}) for k, v in rec.items() if k not in ("environments",)}, indent=1)[:1500])
print({n: len(v) for n, v in rec["environments"].items()})
