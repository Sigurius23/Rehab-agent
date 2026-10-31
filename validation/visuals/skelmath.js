/* SKEL in its rest pose for given shape parameters: skin, joint centres and bone mesh.
   A port of SKEL's forward pass with zero pose (skel_model.py: compute_bone_orientation 'learn_adjust',
   compute_bone_scale), plus arms lowered at the shoulder for display. Also runs in node for the check. */
(function (root) {
  "use strict";

  // Read the packed arrays: {name: {dtype, shape, offset, scale?}} over one ArrayBuffer.
  function unpack(index, buf) {
    const T = { int16: Int16Array, uint16: Uint16Array, uint8: Uint8Array, uint32: Uint32Array, float32: Float32Array };
    const out = {};
    for (const [name, a] of Object.entries(index)) {
      const n = a.shape.reduce((x, y) => x * y, 1);
      const raw = new T[a.dtype](buf, a.offset, n);
      if (a.scale) {
        const f = new Float32Array(n);
        for (let i = 0; i < n; i++) f[i] = raw[i] * a.scale;
        out[name] = f;
      } else out[name] = raw;
      out[name].shape = a.shape;
    }
    return out;
  }

  function sexModel(meta, arr, sex) {
    const m = meta.sexes[sex], g = (k) => arr[`${sex}.${k}`];
    return { sex, ...m, v0: g("v0"), sd: g("sd"), J0: g("J0"), Jd: g("Jd"), osim: g("osim"), pjr: g("pjr"),
             boneV: g("bone_v"), boneB: g("bone_b"), boneF: g("bone_f"), arm: g("arm"), grid: g("grid"),
             faces: arr.faces, nv: g("v0").length / 3, nb: g("sd").shape[2] };
  }

  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const norm = (a) => Math.hypot(a[0], a[1], a[2]);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const mv = (M, v) => [M[0] * v[0] + M[1] * v[1] + M[2] * v[2], M[3] * v[0] + M[4] * v[1] + M[5] * v[2],
                        M[6] * v[0] + M[7] * v[1] + M[8] * v[2]];
  function mm(A, B) {
    const C = new Array(9).fill(0);
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let k = 0; k < 3; k++) C[i * 3 + j] += A[i * 3 + k] * B[k * 3 + j];
    return C;
  }
  function rotFromVectors(a, b) {            // as skel/utils.py rotation_matrix_from_vectors
    const na = norm(a), nb = norm(b);
    a = a.map((x) => x / na); b = b.map((x) => x / nb);
    const v = cross(a, b), c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    const s = norm(v) + 2.220446049250313e-16;
    const K = [0, -v[2], v[1], v[2], 0, -v[0], -v[1], v[0], 0];
    const KK = mm(K, K), f = (1 - c) / (s * s);
    const I = [1, 0, 0, 0, 1, 0, 0, 0, 1];
    return I.map((x, i) => x + K[i] + KK[i] * f);
  }

  // Skin vertices and joint centres for shape parameters (up to M.nb; the depth fits use 16, SKEL itself 10).
  function shape(M, betas) {
    const nv = M.nv, vs = new Float32Array(nv * 3), nb = M.nb, n = Math.min(betas.length, nb);
    if (betas.length > nb) throw new Error(`${betas.length} shape parameters, the model has ${nb}`);
    for (let i = 0; i < nv * 3; i++) {
      let x = M.v0[i];
      for (let b = 0; b < n; b++) x += M.sd[i * nb + b] * betas[b];
      vs[i] = x;
    }
    const J = [];
    for (let j = 0; j < 24; j++) {
      const p = [0, 0, 0];
      for (let c = 0; c < 3; c++) {
        let x = M.J0[j * 3 + c];
        for (let b = 0; b < n; b++) x += M.Jd[(j * 3 + c) * nb + b] * betas[b];
        p[c] = x;
      }
      J.push(p);
    }
    return { vs, J };
  }

  // Per bone: rotation Gk (3x3, row-major), scale S (3) and the joint centre placing the template bone mesh.
  function bones(M, vs, J) {
    const P = M.parent, C = M.child, osim = [], Jl = [];
    for (let j = 0; j < 24; j++) {
      osim.push([M.osim[j * 3], M.osim[j * 3 + 1], M.osim[j * 3 + 2]]);
      Jl.push(j === 0 ? J[0].slice() : sub(J[j], J[P[j]]));
    }
    const bv = C.map((c) => Jl[c].slice()), ov = C.map((c) => osim[c].slice());
    for (const [a, b] of [[16, 17], [21, 22]]) {
      bv[a] = bv[a].map((x, i) => x + bv[b][i]);
      ov[a] = ov[a].map((x, i) => x + ov[b][i]);
    }
    bv[12] = bv[11].slice();
    const Gk = [];
    for (let j = 0; j < 24; j++) {
      const Gl = Array.from(M.pjr.subarray(j * 9, j * 9 + 9));
      let R = M.fixed.includes(j) ? [1, 0, 0, 0, 1, 0, 0, 0, 1] : rotFromVectors(mv(Gl, ov[j]), bv[j]);
      R = R.map((x) => (Number.isNaN(x) ? 0 : x));
      Gk.push(mm(R, Gl));
    }
    const bsp = Jl.map((l, j) => norm(l) / norm(osim[j]));
    const bs = new Array(24).fill(1);
    for (let j = 0; j < 24; j++) if (C[j] !== 0) bs[j] = bsp[C[j]];
    bs[16] = bs[17]; bs[21] = bs[22];
    bs[12] = bs[11];
    bs[11] = Math.abs(Jl[11][1]) / Math.abs(osim[11][1]);
    const S = bs.map((x) => [x, x, x]);
    const v = (i) => [vs[i * 3], vs[i * 3 + 1], vs[i * 3 + 2]], v0 = (i) => [M.v0[i * 3], M.v0[i * 3 + 1], M.v0[i * 3 + 2]];
    const ratio = (a, b, d) => (v(a)[d] - v(b)[d]) / (v0(a)[d] - v0(b)[d]);
    for (const [j, d, ds, a, b] of M.keypoints) S[j][d] = ratio(a, b, ds);
    const [back, front, sternum] = M.thorax;
    S[12][0] = Math.min(ratio(back, front, 2), ratio(back, sternum, 2));
    S[11][0] = S[12][0];
    return { Gk, S };
  }

  // The whole body: skin (Float32Array), bone mesh vertices, joint centres; arms lowered by armDeg at the shoulders.
  function body(M, betas, armDeg = 0) {
    const { vs, J } = shape(M, betas);
    const { Gk, S } = bones(M, vs, J);
    const nb = M.boneB.length, bv = new Float32Array(nb * 3);
    for (let i = 0; i < nb; i++) {
      const b = M.boneB[i], G = Gk[b], s = S[b];
      const p = mv(G, [M.boneV[i * 3] * s[0], M.boneV[i * 3 + 1] * s[1], M.boneV[i * 3 + 2] * s[2]]);
      bv[i * 3] = p[0] + J[b][0]; bv[i * 3 + 1] = p[1] + J[b][1]; bv[i * 3 + 2] = p[2] + J[b][2];
    }
    const out = { skin: vs.slice(), bones: bv, J: J.map((p) => p.slice()), Jrest: J, restSkin: vs };
    if (armDeg) lowerArms(M, out, armDeg);
    return out;
  }

  // Rotate each arm about the forward axis (SMPL z) at the shoulder joint: bones rigidly, skin by its weights.
  const ARMS = [{ shoulder: 15, hand: 18, bones: [15, 16, 17, 18], w: 0 }, { shoulder: 20, hand: 23, bones: [20, 21, 22, 23], w: 1 }];
  function lowerArms(M, out, deg) {
    const J = out.Jrest;
    for (const arm of ARMS) {
      const o = J[arm.shoulder], side = Math.sign(J[arm.hand][0] - o[0]);
      const a = -side * deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
      const rot = (x, y) => [o[0] + (x - o[0]) * c - (y - o[1]) * s, o[1] + (x - o[0]) * s + (y - o[1]) * c];
      for (let i = 0; i < M.boneB.length; i++) {
        if (!arm.bones.includes(M.boneB[i])) continue;
        const [x, y] = rot(out.bones[i * 3], out.bones[i * 3 + 1]);
        out.bones[i * 3] = x; out.bones[i * 3 + 1] = y;
      }
      for (let i = 0; i < M.nv; i++) {
        const w = M.arm[i * 2 + arm.w];
        if (!w) continue;
        const X = out.skin[i * 3], Y = out.skin[i * 3 + 1], [x, y] = rot(X, Y);
        out.skin[i * 3] = X + w * (x - X); out.skin[i * 3 + 1] = Y + w * (y - Y);
      }
      for (const b of arm.bones) { const [x, y] = rot(out.J[b][0], out.J[b][1]); out.J[b][0] = x; out.J[b][1] = y; }
    }
  }

  // Height (vertical extent) and mass from the closed mesh's volume at 1000 kg/m^3, as rehabtwin.skel_bones.
  function measures(M, vs) {
    let lo = Infinity, hi = -Infinity, vol = 0;
    for (let i = 0; i < M.nv; i++) { lo = Math.min(lo, vs[i * 3 + 1]); hi = Math.max(hi, vs[i * 3 + 1]); }
    const F = M.faces;
    for (let f = 0; f < F.length; f += 3) {
      const a = F[f] * 3, b = F[f + 1] * 3, c = F[f + 2] * 3;
      vol += vs[a] * (vs[b + 1] * vs[c + 2] - vs[b + 2] * vs[c + 1]) - vs[a + 1] * (vs[b] * vs[c + 2] - vs[b + 2] * vs[c])
           + vs[a + 2] * (vs[b] * vs[c + 1] - vs[b + 1] * vs[c]);
    }
    return { height: hi - lo, mass: Math.abs(vol) / 6 * 1000 };
  }

  // Segment lengths between SKEL joint centres (rehabtwin.skel_bones.SEGMENTS), right side.
  const SEGMENTS = { thigh: [1, 2], shank: [2, 3], upper_arm: [15, 16], forearm: [16, 18], hip_width: [1, 6] };
  function segments(J) {
    const out = {};
    for (const [k, [a, b]] of Object.entries(SEGMENTS)) out[k] = norm(sub(J[a], J[b]));
    return out;
  }

  // Shape parameters for a height and BMI: bilinear in the grid of nearest-to-mean bodies (grid value 999 = none).
  function betasFor(M, height, bmi) {
    const H = M.grid_height_m, B = M.grid_bmi, g = M.grid;
    const at = (x, xs) => {
      const t = Math.min(Math.max((x - xs[0]) / (xs[1] - xs[0]), 0), xs.length - 1.000001);
      return [Math.floor(t), t - Math.floor(t)];
    };
    const [i, fi] = at(height, H), [j, fj] = at(bmi, B), nb = B.length, out = new Array(10).fill(0);
    const cell = (a, b, k) => g[((a * nb) + b) * 10 + k];
    if ([cell(i, j, 0), cell(i + 1, j, 0), cell(i, j + 1, 0), cell(i + 1, j + 1, 0)].some((x) => x > 900)) return null;
    for (let k = 0; k < 10; k++)
      out[k] = (1 - fi) * (1 - fj) * cell(i, j, k) + fi * (1 - fj) * cell(i + 1, j, k) + (1 - fi) * fj * cell(i, j + 1, k) + fi * fj * cell(i + 1, j + 1, k);
    return out;
  }

  const api = { unpack, sexModel, shape, bones, body, measures, segments, betasFor };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.SkelMath = api;
})(this);
