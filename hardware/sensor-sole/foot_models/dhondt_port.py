#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Port of D'Hondt et al. (2024)'s passive foot laws into their nominal OpenSim models. Experimental.

D'Hondt, De Groote and Afschrift (2024), "A dynamic foot model for predictive simulations of human gait reveals
causal relations between foot structure and whole-body mechanics", PLOS Comput Biol 20(6): e1012219. The models
and code are in https://github.com/Lars-DHondt-KUL/3dpredictsim, branch four-segment_foot_model (commit e963f4a),
MIT License, Copyright (c) 2019 antoinefalisse. The formulas below are transcribed from that code, with that
notice: "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction, including without
limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND."

Why a port is needed. The paper's simulations do not run the .osim in OpenSim: they evaluate the model through
CasADi, and add the foot's passive laws in MATLAB (CasADiFunctions/CreateCasadiFunctions.m,
OCP/f_PredSim_Gait92_FootModel.m). A plain OpenSim run of the nominal .osim therefore differs from the paper:
  - midtarsal joint: the .osim has 12 OpenSim Ligaments across it; the paper instead applies a fitted ligament
    moment (f_getMtjLigamentMoment_exp5, a bspline over -30..30 deg) plus exponential range-of-motion torques
    and 0.1 N m s/rad damping;
  - MTP joint: the .osim has no passive torque; the paper applies -k q - d qdot plus exponential range-of-motion
    torques (4-segment foot: k = 1, d = 0.1; 3-segment: k = 25, d = 2) and 0.1 N m s/rad more damping;
  - plantar fascia (4-segment foot): the .osim's Ligament uses a 17-point spline; the paper uses the Natali (2010)
    law with slack length 0.146 m, on the length of the same path (fitted there as polynomials). Known remaining
    difference: OpenSim's Ligament applies no compression, while the paper's smoothed law dips to -0.69 N within
    0.9 mm below slack.
What this port does, for both sides:
  - 4-segment: switches the 12 midtarsal Ligaments off; gives PlantarFascia the Natali law exactly (a dense
    piecewise-linear curve, pcsa_force 1 N); adds the midtarsal and MTP passive torques as
    ExpressionBasedCoordinateForces. The ligament moment is a piecewise-linear interpolation of the paper's
    bspline at 0.5 deg knots (dhondt2024_mtj_ligament_moment.json), linearly extrapolated outside -30..30 deg,
    where the paper's function is not defined: results there must be flagged (out_of_range()).
  - 3-segment: adds the MTP passive torque.
What it does not port: the passive torques of the other joints (hip, knee, ankle, subtalar, trunk, arms), muscle
settings (Achilles stiffness, triceps strength), the plantar intrinsic muscle, and the contact model; and it does
not reproduce the paper's optimal-control simulations. tests/test_dhondt_port.py verifies the port against the
transcribed equations and the paper's own saved bspline.

  python foot_models/dhondt_port.py DHondt_2024_4-segment_foot_fixed_knee.osim ported_4seg.osim
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
TABLE = HERE / "dhondt2024_mtj_ligament_moment.json"
SOURCE = "https://github.com/Lars-DHondt-KUL/3dpredictsim (branch four-segment_foot_model, commit e963f4a)"
# the nominal models this port is written for, by sha256 (OpenSimModel/Nominal models/ at e963f4a)
NOMINAL = {
    "241eb5dd064f823e619088248e5ac6805762c349dc3ce46d5ee099342050d959": "4-segment",   # DHondt_2024_4-segment_foot_fixed_knee.osim
    "f78df97841b566ad5fbfbf5e50a3b9dce2a82ac9308153579875bd93e9608e4b": "3-segment",   # DHondt_2024_3-segment_foot_fixed_knee.osim
}
MTJ_LIGAMENTS = ["LongPlantar1", "LongPlantar2", "LongPlantar3", "LongPlantar4", "CalcaneoNavicularPlantar1Mus",
                 "CalcaneoNavicularPlantar2Mus", "CalcaneoNavicularPlantar3Mus", "CalcaneoCuboidPlantar1Mus",
                 "CalcaneoCuboidPlantar2Mus", "CalcaneoCuboidDorsalMus", "CalcaneoNavicularBifurcateMus",
                 "CalcaneoCuboidBifurcateMus"]
# CreateCasadiFunctions.m: f_PassiveMoments(K, theta, q, qdot) = K1 exp(K2 (q - theta2)) + K3 exp(K4 (q - theta1))
#   - 0.1 qdot ("theta_pass 1 and 2 are inverted on purpose")
K_PASS = dict(mtj=([-50, 15, 60, -30], [-0.4, 0.5]),
              mtp=([-0.9, 14.87, 0.18, -70.08], [0.0, 65 / 180 * math.pi]))
MTP_LINEAR = {"4-segment": (1.0, 0.1), "3-segment": (25.0, 2.0)}       # S.Foot.kMTP, S.Foot.dMTP
DMT = 0.1                                                               # S.Foot.dMT (total midtarsal damping)
PF = dict(ls=0.146, A0=70.0, nu=0.4, mu=14.449, k=254.02, alpha=10.397)  # Natali2010 branch, PF_slack_length
PF_CURVE_X = (0.95, 1.25, 0.0005)       # l / ls sampled for the port's curve; finer (2e-5) across the toe-in region


def pf_curve_x():
    lo, hi, step = PF_CURVE_X
    fine = np.arange(0.995, 1.01, 2e-5)
    return np.unique(np.round(np.concatenate([np.arange(lo, 0.995, step), fine, np.arange(1.01, hi + 1e-12, step)]), 8))
MTJ_RANGE_RAD = (math.radians(-30), math.radians(30))


def natali2010_force(l, ls=PF["ls"], A0=PF["A0"], nu=PF["nu"]):
    """Plantar fascia tension (N) at length l (m): f_getPlantarFasciaStiffnessModelCasADiFunction('Natali2010')."""
    l = np.asarray(l, float)
    dl = l - ls
    lam = l / ls
    A = A0 * lam ** (-nu * 2)
    sigma = PF["mu"] * (lam ** 2 - 1 / lam) + PF["k"] / (2 * PF["alpha"]) * (np.exp(PF["alpha"] * (lam ** 2 - 1)) - 1) * lam ** 2
    return sigma * A * (np.tanh(dl * 4e3 - 1.1) + 1) / 2


def falisse_passive(q, qdot, K, theta):
    return K[0] * np.exp(K[1] * (q - theta[1])) + K[2] * np.exp(K[3] * (q - theta[0])) - 0.1 * qdot


def _n(x):
    """A number as OpenSim's expression parser reads it (plain float repr, never numpy's)."""
    return repr(float(x))


def _falisse_expr(K, theta):
    return (f"({_n(K[0])})*exp(({_n(K[1])})*(q-({_n(theta[1])}))) + ({_n(K[2])})*exp(({_n(K[3])})*(q-({_n(theta[0])})))"
            f" - 0.1*qdot")


def table():
    return json.loads(TABLE.read_text())


def hinge_expression(q_knots, m_knots):
    """Piecewise-linear interpolation through the knots as an OpenSim (Lepton) expression in q, extrapolated with
    the end slopes: M0 + s0 (q - q0) + sum_i (s_i - s_(i-1)) max(0, q - q_i)."""
    q = np.asarray(q_knots, float); m = np.asarray(m_knots, float)
    s = np.diff(m) / np.diff(q)
    terms = [f"({_n(m[0])})", f"({_n(s[0])})*(q-({_n(q[0])}))"]
    for i in range(1, len(q) - 1):
        ds = s[i] - s[i - 1]
        if ds != 0:
            terms.append(f"({_n(ds)})*max(0,q-({_n(q[i])}))")
    return " + ".join(terms)


def mtj_ligament_moment(q):
    """The port's ligament moment (N m) at midtarsal angle q (rad): the same interpolation as the expression."""
    t = table()
    qk = np.radians(t["knots_deg"]); mk = np.asarray(t["knots_Nm"])
    q = np.asarray(q, float)
    out = np.interp(q, qk, mk)
    lo, hi = q < qk[0], q > qk[-1]
    out = np.where(lo, mk[0] + (q - qk[0]) * (mk[1] - mk[0]) / (qk[1] - qk[0]), out)
    return np.where(hi, mk[-1] + (q - qk[-1]) * (mk[-1] - mk[-2]) / (qk[-1] - qk[-2]), out)


def out_of_range(q_mtj):
    """True where a midtarsal angle lies outside the paper's ligament-moment definition (-30..30 deg)."""
    q = np.asarray(q_mtj, float)
    return (q < MTJ_RANGE_RAD[0] - 1e-9) | (q > MTJ_RANGE_RAD[1] + 1e-9)


def identify(model_path):
    h = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    if h not in NOMINAL:
        raise SystemExit(f"{model_path}: sha256 {h[:16]}... is not one of the nominal models this port is written for "
                         f"({SOURCE}, OpenSimModel/Nominal models/*_fixed_knee.osim)")
    return NOMINAL[h], h


def port(model_in, model_out):
    """Write a copy of a nominal D'Hondt model with the paper's passive foot laws. Returns a description."""
    import opensim as osim
    kind, sha = identify(model_in)
    m = osim.Model(str(model_in))
    t = table()
    lig_expr = hinge_expression(np.radians(t["knots_deg"]), t["knots_Nm"])
    k_lin, d_lin = MTP_LINEAR[kind]
    changed = []
    for s in "rl":
        if kind == "4-segment":
            for n in MTJ_LIGAMENTS:
                f = m.getForceSet().get(f"{n}_{s}")
                f.set_appliesForce(False)
                changed.append(f"{n}_{s}: off")
            pf = osim.Ligament.safeDownCast(m.getForceSet().get(f"PlantarFascia_{s}"))
            x = pf_curve_x()
            curve = osim.PiecewiseLinearFunction()
            for xi, fi in zip(x, natali2010_force(x * PF["ls"])):
                curve.addPoint(float(xi), float(fi))
            pf.set_force_length_curve(curve)
            pf.set_pcsa_force(1.0)
            pf.set_resting_length(PF["ls"])
            changed.append(f"PlantarFascia_{s}: Natali (2010), slack {PF['ls']} m")
            K, th = K_PASS["mtj"]
            expr = f"{lig_expr} + {_falisse_expr(K, th)} - ({_n(DMT - 0.1)})*qdot"
            fo = osim.ExpressionBasedCoordinateForce(f"mtj_angle_{s}", expr)
            fo.setName(f"mtj_passive_{s}")
            m.addForce(fo)
            changed.append(f"mtj_passive_{s}: ligament moment + range-of-motion torques + damping")
        K, th = K_PASS["mtp"]
        expr = f"-({_n(k_lin)})*q - ({_n(d_lin)})*qdot + {_falisse_expr(K, th)}"
        fo = osim.ExpressionBasedCoordinateForce(f"mtp_angle_{s}", expr)
        fo.setName(f"mtp_passive_{s}")
        m.addForce(fo)
        changed.append(f"mtp_passive_{s}: -{k_lin} q - {d_lin} qdot + range-of-motion torques")
    m.finalizeConnections()
    m.initSystem()
    m.printToXML(str(model_out))
    info = dict(status="experimental port; verified by tests/test_dhondt_port.py", source=SOURCE, model=kind,
                input_sha256=sha, changed=changed,
                not_ported=["other joints' passive torques", "muscle settings", "plantar intrinsic muscle",
                            "contact model", "the paper's optimal-control simulations"],
                midtarsal_ligament_moment_defined_deg=[-30, 30])
    Path(model_out).with_suffix(".port.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model_in"); ap.add_argument("model_out")
    a = ap.parse_args()
    print(json.dumps(port(a.model_in, a.model_out), indent=1))


if __name__ == "__main__":
    main()
