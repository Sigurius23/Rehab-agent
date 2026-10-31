// Compare the page's SKEL port with the numpy reference (prep_bodies.skel_rest) on three bodies.
const fs = require("fs"), path = require("path");
const [out, js] = process.argv.slice(2);
const S = require(path.resolve(js));
const meta = JSON.parse(fs.readFileSync(path.join(out, "bodies.json")));
const b = fs.readFileSync(path.join(out, "bodies.bin"));
const arr = S.unpack(meta.arrays, b.buffer.slice(b.byteOffset, b.byteOffset + b.length));
const ref = JSON.parse(fs.readFileSync(path.join(out, "skel_check.json")));
let worst = 0;
for (const r of ref) {
  const M = S.sexModel(meta, arr, r.sex);
  const o = S.body(M, r.betas, 0);
  let dJ = 0, dB = 0, dS = 0, dSc = 0;
  o.J.forEach((p, j) => p.forEach((x, c) => { dJ = Math.max(dJ, Math.abs(x - r.J[j][c])); }));
  for (let i = 0; i < r.bones.length; i++) for (let c = 0; c < 3; c++) dB = Math.max(dB, Math.abs(o.bones[i * 3 + c] - r.bones[i][c]));
  for (let i = 0; i < r.skin.length; i++) for (let c = 0; c < 3; c++) dS = Math.max(dS, Math.abs(o.skin[i * 3 + c] - r.skin[i][c]));
  const { S: Sc } = S.bones(M, S.shape(M, r.betas).vs, S.shape(M, r.betas).J);
  Sc.forEach((s, j) => s.forEach((x, c) => { dSc = Math.max(dSc, Math.abs(x - r.S[j][c])); }));
  const m = S.measures(M, o.skin);
  console.log(`${r.sex} betas[0..1]=${r.betas.slice(0, 2).map((x) => x.toFixed(2))}  max diff mm: joints ${(dJ * 1e3).toFixed(3)}, bone mesh ${(dB * 1e3).toFixed(3)}, skin ${(dS * 1e3).toFixed(3)}; scale ${dSc.toExponential(1)}; height ${m.height.toFixed(3)} m, mass ${m.mass.toFixed(1)} kg`);
  worst = Math.max(worst, dB, dJ, dS);
}
// the height-BMI grid: interpolated bodies against the asked height and mass
for (const sex of ["female", "male"]) {
  const M = S.sexModel(meta, arr, sex);
  let eh = 0, em = 0;
  for (const h of [1.52, 1.67, 1.83, 1.97]) for (const bmi of [18.5, 23, 29, 37]) {
    const m = S.measures(M, S.shape(M, S.betasFor(M, h, bmi)).vs);
    eh = Math.max(eh, Math.abs(m.height - h)); em = Math.max(em, Math.abs(m.mass / (bmi * h * h) - 1));
  }
  console.log(`${sex} grid, off-grid points: height within ${(eh * 100).toFixed(2)} cm, mass within ${(em * 100).toFixed(2)} %`);
}
console.log(worst < 5e-4 ? "PORT MATCHES (all within 0.5 mm)" : "PORT DIFFERS");
// the depth fits (16 shape parameters): segments against the values stored by the validation run
for (const d of meta.depth) {
  const M = S.sexModel(meta, arr, d.sex);
  for (const [src, betas] of [["true", d.betas_true], ["depth fit", d.betas_fit]]) {
    const seg = S.segments(S.body(M, betas, 0).Jrest), run = d.segments_run[src];
    const names = { thigh: "thigh_r", shank: "shank_r", upper_arm: "upper_arm_r", forearm: "forearm_r", hip_width: "hip_width" };
    const diff = Math.max(...Object.entries(names).map(([k, r]) => Math.abs(seg[k] - run[r])));
    console.log(`${d.id} ${src} (${betas.length} parameters): segments within ${(diff * 1e3).toFixed(3)} mm of the run`);
    worst = Math.max(worst, diff);
  }
}
console.log(worst < 5e-4 ? "DEPTH FITS MATCH THE RUN" : "DEPTH FITS DIFFER");
