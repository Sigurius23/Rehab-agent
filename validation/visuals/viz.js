/* The audit page's 3D views: bodies and their SKEL bones, one depth frame to bones, and the tracked squat.
   Needs three.js r128 (+ OrbitControls) and skelmath.js. Data: viz/bodies.{json,b64.txt}, viz/squat.{json,b64.txt}
   (the packed arrays as base64),
   viz/squat_cam2.mp4. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const ARM_DEG = 68;                                // arms lowered from SKEL's T pose, for the line-up

  async function load(name) {
    const [meta, buf] = await Promise.all([
      fetch(`viz/${name}.json`).then((r) => { if (!r.ok) throw new Error(`viz/${name}.json: ${r.status}`); return r.json(); }),
      fetch(`viz/${name}.b64.txt`).then((r) => { if (!r.ok) throw new Error(`viz/${name}.b64.txt: ${r.status}`); return r.text(); })
        .then((t) => { const b = atob(t.trim()), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u.buffer; })]);
    return { meta, arr: SkelMath.unpack(meta.arrays, buf) };
  }

  // ---------- a small viewer: renderer, camera, orbit controls, lights, floor, HTML labels, theme ----------
  const viewers = [];
  class Viewer {
    constructor(box, { target = [0, 0.9, 0], position = [0, 1.4, 5], fov = 35, floorY = 0, grid = 8, fit = null } = {}) {
      this.box = box;
      this.fit = fit;                               // [width, height] in metres to keep in view
      this.dir = new THREE.Vector3(...position).sub(new THREE.Vector3(...target)).normalize();
      this.renderer = new THREE.WebGLRenderer({ antialias: true });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      box.appendChild(this.renderer.domElement);
      this.labels = document.createElement("div");
      this.labels.className = "v-labels";
      box.appendChild(this.labels);
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(fov, 1, 0.05, 100);
      this.camera.position.set(...position);
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.target.set(...target);
      this.controls.enableDamping = false;
      this.controls.addEventListener("change", () => this.render());
      this.controls.addEventListener("start", () => { this.moved = true; });
      this.controls.update();
      this.hemi = new THREE.HemisphereLight(0xffffff, 0x8a8f96, 0.75);
      const sun = new THREE.DirectionalLight(0xffffff, 0.75);
      sun.position.set(2, 4, 3);
      const fill = new THREE.DirectionalLight(0xffffff, 0.3);
      fill.position.set(-3, 2, -2);
      this.scene.add(this.hemi, sun, fill);
      this.grid = new THREE.GridHelper(grid, grid * 4);
      this.grid.position.y = floorY;
      this.scene.add(this.grid);
      this.items = [];                              // {el, p: Vector3}
      new ResizeObserver(() => this.resize()).observe(box);
      viewers.push(this);
      this.theme();
      this.resize();
    }
    label(text, p, cls = "") {
      const el = document.createElement("div");
      el.className = "v-label " + cls;
      el.textContent = text;
      this.labels.appendChild(el);
      const item = { el, p: new THREE.Vector3(...p) };
      this.items.push(item);
      return item;
    }
    resize() {
      const w = this.box.clientWidth, h = this.box.clientHeight;
      if (!w || !h) return;
      this.renderer.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.refit();
      this.render();
    }
    refit() {
      if (!this.fit || this.moved) return;
      const v = THREE.MathUtils.degToRad(this.camera.fov) / 2, hz = Math.atan(Math.tan(v) * this.camera.aspect);
      const d = 1.06 * Math.max(this.fit[1] / 2 / Math.tan(v), this.fit[0] / 2 / Math.tan(hz));
      this.camera.position.copy(this.controls.target).addScaledVector(this.dir, d);
      this.controls.update();
    }
    theme() {
      this.scene.background = new THREE.Color(token("--viz-bg"));
      this.grid.material.vertexColors = false;
      this.grid.material.color = new THREE.Color(token("--viz-grid"));
      this.grid.material.needsUpdate = true;
      if (this.onTheme) this.onTheme();
      this.render();
    }
    render() {
      if (this.pending) return;
      this.pending = true;
      requestAnimationFrame(() => {
        this.pending = false;
        this.renderer.render(this.scene, this.camera);
        const w = this.box.clientWidth, h = this.box.clientHeight, v = new THREE.Vector3();
        for (const it of this.items) {
          if (it.el.hidden) continue;
          v.copy(it.p).project(this.camera);
          const off = v.z > 1 || Math.abs(v.x) > 1.05 || Math.abs(v.y) > 1.05;
          it.el.style.visibility = off ? "hidden" : "visible";
          it.el.style.transform = `translate(${((v.x + 1) / 2) * w}px, ${((1 - v.y) / 2) * h}px) translate(-50%, -100%)`;
        }
      });
    }
  }
  const retheme = () => viewers.forEach((v) => v.theme());
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", retheme);
  new MutationObserver(retheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  function meshGeometry(positions, index) {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    g.setIndex(new THREE.BufferAttribute(index, 1));
    g.computeVertexNormals();
    return g;
  }
  const boneMaterial = () => new THREE.MeshStandardMaterial({ color: token("--bone"), roughness: 0.65, metalness: 0 });
  const skinMaterial = () => new THREE.MeshStandardMaterial({ color: token("--skin"), roughness: 0.85, transparent: true,
                                                              opacity: 0.3, depthWrite: false });
  function sphereSet(n, r, color) {
    const m = new THREE.InstancedMesh(new THREE.SphereGeometry(r, 12, 8), new THREE.MeshStandardMaterial({ color, roughness: 0.5 }), n);
    m.frustumCulled = false;
    return m;
  }
  function placeSpheres(mesh, pts) {
    const M = new THREE.Matrix4();
    pts.forEach((p, i) => { M.makeTranslation(p[0], p[1], p[2]); mesh.setMatrixAt(i, M); });
    mesh.instanceMatrix.needsUpdate = true;
  }
  const fmt = (x, d = 1) => x.toFixed(d);
  function failed(box, e) {
    box.classList.add("v-failed");
    box.textContent = `This view could not load: ${e.message}`;
  }

  // ---------- 1. bodies and their bones ----------
  function bodiesView(D) {
    const box = $("v-bodies");
    const models = { female: SkelMath.sexModel(D.meta, D.arr, "female"), male: SkelMath.sexModel(D.meta, D.arr, "male") };
    const presets = D.meta.presets.slice().sort((a, b) => a.mass_kg / a.height_m ** 2 - b.mass_kg / b.height_m ** 2);
    const slots = [{ name: "Your numbers", custom: true }, ...presets];
    const gap = 0.82, x0 = -gap * (slots.length - 1) / 2;
    const V = new Viewer(box, { target: [0, 0.98, 0], position: [0, 1.25, 7.4], fov: 30, grid: 8, fit: [gap * slots.length + 0.1, 2.25] });
    const skinMat = skinMaterial(), boneMat = boneMaterial();
    const jointMesh = [];
    const rows = $("bodies-rows");
    slots.forEach((s, k) => {
      s.group = new THREE.Group();
      s.group.position.x = x0 + k * gap;
      V.scene.add(s.group);
      s.label = V.label("", [s.group.position.x, 0, 0], s.custom ? "accent" : "");
      s.tr = document.createElement("tr");
      rows.appendChild(s.tr);
    });
    V.onTheme = () => {
      skinMat.color.set(token("--skin"));
      boneMat.color.set(token("--bone"));
      jointMesh.forEach((m) => m.material.color.set(token("--accent")));
    };
    function build(s, sex, betas) {
      const M = models[sex], b = SkelMath.body(M, betas, ARM_DEG);
      let lo = Infinity;
      for (let i = 1; i < b.skin.length; i += 3) lo = Math.min(lo, b.skin[i]);
      if (s.joints) {
        jointMesh.splice(jointMesh.indexOf(s.joints), 1);
        [s.skin, s.bones, s.joints].forEach((o) => o.geometry.dispose());
      }
      s.group.clear();
      s.group.position.y = -lo;
      s.skin = new THREE.Mesh(meshGeometry(b.skin, M.faces), skinMat);
      s.skin.renderOrder = 2;
      s.skin.visible = $("b-skin").checked;
      s.bones = new THREE.Mesh(meshGeometry(b.bones, M.boneF), boneMat);
      const jm = sphereSet(24, 0.016, token("--accent"));
      placeSpheres(jm, b.J);
      jm.visible = $("b-joints").checked;
      jointMesh.push(jm);
      s.joints = jm;
      s.group.add(s.bones, s.skin, jm);
      const top = Math.max(...b.J.map((p) => p[1])) - lo + 0.36;
      s.label.p.set(s.group.position.x, top, 0);
      const m = SkelMath.measures(M, b.restSkin), seg = SkelMath.segments(b.Jrest);
      s.measured = m;
      const bmi = m.mass / m.height ** 2;
      const full = s.custom ? "Your numbers" : s.name === "OpenCap subject 2" ? "OpenCap subject 2" : `Test body ${s.id.split("_").pop()}`;
      s.label.el.textContent = s.custom ? "Yours" : s.name === "OpenCap subject 2" ? "Subject 2" : s.id.split("_").pop();
      const cm = (x) => fmt(100 * x);
      s.tr.innerHTML = `<td>${full}${s.custom ? "" : `<div class="note">${s.note || "synthetic, from the SKEL test set"}</div>`}</td>` +
        `<td>${sex}</td><td class="num">${fmt(m.height, 2)}</td><td class="num">${fmt(m.mass)}</td><td class="num">${fmt(bmi)}</td>` +
        `<td class="num">${cm(seg.thigh)}</td><td class="num">${cm(seg.shank)}</td><td class="num">${cm(seg.upper_arm)}</td>` +
        `<td class="num">${cm(seg.forearm)}</td><td class="num">${cm(seg.hip_width)}</td>`;
      if (s.custom) s.tr.className = "mine";
      V.render();
    }
    presets.forEach((p, k) => build(slots[k + 1], p.sex, p.betas));
    const custom = slots[0];
    function updateCustom() {
      const sex = $("b-sex-m").checked ? "male" : "female";
      const h = +$("b-height").value, kg = +$("b-mass").value, bmi = kg / h ** 2;
      const M = models[sex], B = M.grid_bmi;
      const clamped = Math.min(Math.max(bmi, B[0]), B[B.length - 1]);
      $("b-height-out").textContent = `${fmt(h, 2)} m`;
      $("b-mass-out").textContent = `${fmt(kg)} kg`;
      const betas = SkelMath.betasFor(M, h, clamped);
      build(custom, sex, betas);
      const m = custom.measured;
      $("b-built").textContent = clamped !== bmi
        ? `BMI ${fmt(bmi)} is outside the range the grid covers (${B[0]}–${B[B.length - 1]}); built at BMI ${fmt(clamped)}: ${fmt(m.height, 2)} m, ${fmt(m.mass)} kg.`
        : `Built body: ${fmt(m.height, 2)} m, ${fmt(m.mass)} kg (BMI ${fmt(m.mass / m.height ** 2)}).`;
    }
    ["b-height", "b-mass", "b-sex-f", "b-sex-m"].forEach((id) => $(id).addEventListener("input", updateCustom));
    $("b-skin").addEventListener("change", () => { slots.forEach((s) => { s.skin.visible = $("b-skin").checked; }); V.render(); });
    $("b-joints").addEventListener("change", () => { slots.forEach((s) => { s.joints.visible = $("b-joints").checked; }); V.render(); });
    updateCustom();
  }

  // ---------- 2. one depth frame to bones ----------
  function depthView(D) {
    const box = $("v-depth");
    const V = new Viewer(box, { target: [0.45, -0.1, -2.75], position: [1.9, 0.55, 0.6], fov: 34, floorY: -1, grid: 6, fit: [2.3, 2.3] });
    const flip = (a) => { const o = new Float32Array(a.length); for (let i = 0; i < a.length; i += 3) { o[i] = a[i]; o[i + 1] = -a[i + 1]; o[i + 2] = -a[i + 2]; } return o; };
    const fitMat = skinMaterial();
    const truthMat = new THREE.MeshBasicMaterial({ color: token("--s2"), wireframe: true, transparent: true, opacity: 0.35 });
    const ptsMat = new THREE.PointsMaterial({ color: token("--pts"), size: 0.0045 });
    const boneMat = boneMaterial();
    const sensor = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.07, 0.07), new THREE.MeshStandardMaterial({ color: token("--muted-3d") }));
    V.scene.add(sensor);
    V.label("Kinect v1", [0, 0.12, 0], "small");
    const frust = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: token("--muted-3d"), transparent: true, opacity: 0.5 }));
    V.scene.add(frust);
    const lblBody = V.label("", [0, 0, 0]), lblBones = V.label("", [0, 0, 0]);
    let cur = null;
    V.onTheme = () => {
      fitMat.color.set(token("--skin")); truthMat.color.set(token("--s2")); ptsMat.color.set(token("--pts"));
      boneMat.color.set(token("--bone")); sensor.material.color.set(token("--muted-3d")); frust.material.color.set(token("--muted-3d"));
      if (cur) { cur.jf.material.color.set(token("--s1")); cur.jt.material.color.set(token("--s2")); }
    };
    function show(k) {
      const d = D.meta.depth[k], M = SkelMath.sexModel(D.meta, D.arr, d.sex);
      if (cur) cur.groups.forEach((g) => V.scene.remove(g));
      const posed = new THREE.Group(), rest = new THREE.Group();
      const pts = flip(D.arr[`depth${k}.points`]);
      const cloud = new THREE.Points(new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(pts, 3)), ptsMat);
      const fit = new THREE.Mesh(meshGeometry(flip(D.arr[`depth${k}.fit`]), M.faces), fitMat);
      fit.renderOrder = 2;
      const truth = new THREE.Mesh(meshGeometry(flip(D.arr[`depth${k}.truth`]), M.faces), truthMat);
      fit.visible = $("d-fit").checked; truth.visible = $("d-truth").checked; cloud.visible = $("d-points").checked;
      posed.add(cloud, fit, truth);
      // floor: up . p = offset in camera coordinates (the flip keeps the dot product)
      const up = [d.floor_up[0], -d.floor_up[1], -d.floor_up[2]], floorY = d.floor_offset / up[1];
      V.grid.position.y = floorY;
      // the bones of the fitted and the true shape, standing beside the frame
      const bf = SkelMath.body(M, d.betas_fit, ARM_DEG), bt = SkelMath.body(M, d.betas_true, ARM_DEG);
      let lo = Infinity, cz = 0, cx = 0, n = pts.length / 3;
      for (let i = 1; i < bf.skin.length; i += 3) lo = Math.min(lo, bf.skin[i]);
      for (let i = 0; i < pts.length; i += 3) { cx += pts[i]; cz += pts[i + 2]; }
      cx /= n; cz /= n;
      rest.position.set(cx + 0.95, floorY - lo, cz);
      rest.add(new THREE.Mesh(meshGeometry(bf.bones, M.boneF), boneMat));
      const jf = sphereSet(24, 0.017, token("--s1")), jt = sphereSet(24, 0.017, token("--s2"));
      placeSpheres(jf, bf.J); placeSpheres(jt, bt.J);
      rest.add(jf, jt);
      V.scene.add(posed, rest);
      // sensor frustum to the frame's corners at the body's depth
      const K = [531.15, 531.15, 320, 240], z = -cz + 0.4, c = [[0, 0], [640, 0], [640, 480], [0, 480]].map(([u, v]) => [(u - K[2]) / K[0] * z, -(v - K[3]) / K[1] * z, -z]);
      const seg = [];
      c.forEach((p, i) => { seg.push(0, 0, 0, ...p, ...p, ...c[(i + 1) % 4]); });
      frust.geometry.dispose();
      frust.geometry = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(seg, 3));
      let top = -Infinity;
      for (let i = 1; i < pts.length; i += 3) top = Math.max(top, pts[i]);
      lblBody.p.set(cx, top + 0.12, cz);
      lblBody.el.textContent = `${n.toLocaleString("en")} depth points`;
      lblBones.p.set(rest.position.x, floorY + Math.max(...bf.J.map((p) => p[1])) - lo + 0.32, cz);
      lblBones.el.textContent = "bones from the fit";
      V.controls.target.set(cx + 0.45, floorY + 0.95, cz);
      V.controls.update();
      V.refit();
      cur = { groups: [posed, rest], fit, truth, cloud, jf, jt };
      // numbers: fitted against true
      const sf = SkelMath.segments(bf.Jrest), st = SkelMath.segments(bt.Jrest);
      const names = { thigh: "Thigh", shank: "Shank", upper_arm: "Upper arm", forearm: "Forearm", hip_width: "Hip width" };
      $("depth-rows").innerHTML = Object.entries(names).map(([key, lab]) =>
        `<tr><td>${lab}</td><td class="num">${fmt(100 * st[key])}</td><td class="num">${fmt(100 * sf[key])}</td><td class="num">${(100 * (sf[key] - st[key]) >= 0 ? "+" : "") + fmt(100 * (sf[key] - st[key]))}</td></tr>`).join("") +
        `<tr><td>Height (m)</td><td class="num">${fmt(d.height_m, 3)}</td><td class="num">${fmt(d.fit_height_m, 3)}</td><td class="num">${(100 * (d.fit_height_m - d.height_m) >= 0 ? "+" : "") + fmt(100 * (d.fit_height_m - d.height_m))}</td></tr>` +
        `<tr><td>Mass (kg)</td><td class="num">${fmt(d.mass_kg)}</td><td class="num">${fmt(d.fit_mass_kg)}</td><td class="num">${(d.fit_mass_kg - d.mass_kg >= 0 ? "+" : "") + fmt(d.fit_mass_kg - d.mass_kg)} kg</td></tr>`;
      $("depth-caption").textContent = `${d.sex === "male" ? "Male" : "Female"} test body (size ${d.size}, ${fmt(d.height_m, 2)} m, ${fmt(d.mass_kg)} kg), ` +
        `${n.toLocaleString("en")} depth points from a simulated ${d.sensor}. The fit saw only these points` +
        `${d.warnings.length ? `; fit warnings: ${d.warnings.join(", ")}` : " and gave no warnings"}.`;
      V.render();
    }
    document.querySelectorAll("input[name=d-body]").forEach((el) => el.addEventListener("change", () => show(+el.value)));
    $("d-fit").addEventListener("change", () => { cur.fit.visible = $("d-fit").checked; V.render(); });
    $("d-truth").addEventListener("change", () => { cur.truth.visible = $("d-truth").checked; V.render(); });
    $("d-points").addEventListener("change", () => { cur.cloud.visible = $("d-points").checked; V.render(); });
    D.meta.depth.forEach((d, k) => { $(`d-body-${k}-label`).textContent = `${d.sex === "male" ? "Male" : "Female"}, size ${d.size}, BMI ${fmt(d.mass_kg / d.height_m ** 2)}`; });
    show(0);
  }

  // ---------- 3. the squat ----------
  const STICKS = [["pelvis", "hip_r"], ["pelvis", "hip_l"], ["hip_r", "knee_r"], ["knee_r", "ankle_r"], ["ankle_r", "heel_r"],
                  ["heel_r", "toes_r"], ["ankle_r", "toes_r"], ["hip_l", "knee_l"], ["knee_l", "ankle_l"], ["ankle_l", "heel_l"],
                  ["heel_l", "toes_l"], ["ankle_l", "toes_l"], ["pelvis", "neck"], ["neck", "shoulder_r"], ["neck", "shoulder_l"],
                  ["shoulder_r", "elbow_r"], ["elbow_r", "wrist_r"], ["shoulder_l", "elbow_l"], ["elbow_l", "wrist_l"]];
  const MP_EDGES = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [27, 29],
                    [29, 31], [27, 31], [24, 26], [26, 28], [28, 30], [30, 32], [28, 32], [0, 11], [0, 12]];
  const COORDS = { knee_angle_r: "Right knee flexion", knee_angle_l: "Left knee flexion", hip_flexion_r: "Right hip flexion",
                   hip_flexion_l: "Left hip flexion", ankle_angle_r: "Right ankle dorsiflexion", ankle_angle_l: "Left ankle dorsiflexion",
                   pelvis_tilt: "Pelvis tilt" };

  class Skeleton {
    constructor(scene, names, color, r, opts = {}) {
      this.names = names;
      this.idx = Object.fromEntries(names.map((n, i) => [n, i]));
      const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, ...opts });
      this.sticks = new THREE.InstancedMesh(new THREE.CylinderGeometry(r, r, 1, 8), mat, STICKS.length);
      this.joints = new THREE.InstancedMesh(new THREE.SphereGeometry(r * 1.9, 12, 8), mat, names.length + 1);
      this.sticks.frustumCulled = this.joints.frustumCulled = false;
      this.group = new THREE.Group();
      this.group.add(this.sticks, this.joints);
      scene.add(this.group);
      this.mat = mat;
    }
    set(P) {                                         // P: {name: [x,y,z]}
      const M = new THREE.Matrix4(), q = new THREE.Quaternion(), Y = new THREE.Vector3(0, 1, 0), a = new THREE.Vector3(), b = new THREE.Vector3();
      STICKS.forEach(([n1, n2], i) => {
        a.set(...P[n1]); b.set(...P[n2]);
        const d = b.clone().sub(a), len = d.length();
        q.setFromUnitVectors(Y, d.normalize());
        M.compose(a.clone().add(b).multiplyScalar(0.5), q, new THREE.Vector3(1, len, 1));
        this.sticks.setMatrixAt(i, M);
      });
      Object.values(P).forEach((p, i) => { M.makeTranslation(...p); this.joints.setMatrixAt(i, M); });
      this.sticks.instanceMatrix.needsUpdate = this.joints.instanceMatrix.needsUpdate = true;
    }
  }

  function squatView(D) {
    const S = D.meta, A = D.arr, nP = S.t.length, names = S.points, nJ = names.length;
    const box = $("v-squat");
    const V = new Viewer(box, { target: [0, 0.82, -0.3], position: [2.9, 1.45, 1.6], fov: 32, grid: 6, fit: [2.4, 2.0] });
    const getP = (k, f) => { const P = A[`${k}.P`]; return (n) => { const i = (f * nJ + n) * 3; return [P[i], P[i + 1], P[i + 2]]; }; };
    // alignment: ours at the origin (mean pelvis position), OpenCap turned to our heading, on our feet level
    const mean = (k, n) => { const P = A[`${k}.P`], m = [0, 0, 0]; for (let f = 0; f < nP; f++) for (let c = 0; c < 3; c++) m[c] += P[(f * nJ + n) * 3 + c] / nP; return m; };
    const heading = (k) => { const H = A[`${k}.heading`]; let x = 0, z = 0; for (let f = 0; f < nP; f++) { x += H[f * 2]; z += H[f * 2 + 1]; } return Math.atan2(z, x); };
    const iP = names.indexOf("pelvis"), iAr = names.indexOf("ankle_r"), iAl = names.indexOf("ankle_l");
    const oF = mean("fix", iP), oC = mean("opencap", iP);
    const footY = (k) => (mean(k, iAr)[1] + mean(k, iAl)[1]) / 2;
    const dPsi = heading("fix") - heading("opencap"), cs = Math.cos(dPsi), sn = Math.sin(dPsi), dY = footY("fix") - footY("opencap");
    const place = {
      fix: (p) => [p[0] - oF[0], p[1], p[2] - oF[2]],
      base: (p) => [p[0] - oF[0], p[1], p[2] - oF[2]],
      opencap: (p) => { const x = p[0] - oC[0], z = p[2] - oC[2]; return [x * cs - z * sn, p[1] + dY, x * sn + z * cs]; } };
    const SIDE = { fix: 0, base: 0.95, opencap: -0.95 };
    // bone meshes of our model, one group per mesh frame
    const mv = A["mesh.v"], mf = A["mesh.f"], mframe = A["mesh.frame"], nF = S.mesh_frames.length;
    const meshRoot = new THREE.Group(), frames = [], boneMat = boneMaterial();
    V.scene.add(meshRoot);
    for (let fi = 0; fi < nF; fi++) {
      const map = new Map(), pos = [], idx = [];
      for (let i = 0; i < mframe.length; i++) if (mframe[i] === fi) { map.set(i, pos.length / 3); pos.push(mv[i * 3], mv[i * 3 + 1], mv[i * 3 + 2]); }
      for (let t = 0; t < mf.length; t += 3) if (map.has(mf[t])) idx.push(map.get(mf[t]), map.get(mf[t + 1]), map.get(mf[t + 2]));
      const g = new THREE.Group();
      g.add(new THREE.Mesh(meshGeometry(new Float32Array(pos), new Uint32Array(idx)), boneMat));
      meshRoot.add(g);
      frames.push(g);
    }
    meshRoot.position.set(-oF[0], 0, -oF[2]);
    const sk = { fix: new Skeleton(V.scene, names, token("--s1"), 0.008, { depthTest: false, transparent: true, opacity: 0.9 }),
                 base: new Skeleton(V.scene, names, token("--s2"), 0.009),
                 opencap: new Skeleton(V.scene, names, token("--s3"), 0.009) };
    sk.fix.sticks.renderOrder = sk.fix.joints.renderOrder = 5;
    const lbl = { fix: V.label("Ours", [0, 0, 0], "s1"), base: V.label("Before fix", [0, 0, 0], "s2"),
                  opencap: V.label("OpenCap", [0, 0, 0], "s3") };
    V.onTheme = () => { boneMat.color.set(token("--bone")); sk.fix.mat.color.set(token("--s1")); sk.base.mat.color.set(token("--s2")); sk.opencap.mat.color.set(token("--s3")); drawChart(); };
    const X = A["mesh.X"];
    let pIdx = -1;
    function pose(p) {
      p = Math.max(0, Math.min(nP - 1, p));
      if (p === pIdx) return;
      pIdx = p;
      const side = $("q-side").checked;
      for (let fi = 0; fi < nF; fi++) {
        const o = (p * nF + fi) * 7;
        frames[fi].position.set(X[o], X[o + 1], X[o + 2]);
        frames[fi].quaternion.set(X[o + 3], X[o + 4], X[o + 5], X[o + 6]);
      }
      for (const k of ["fix", "base", "opencap"]) {
        const get = getP(k, p), P = {};
        names.forEach((n, i) => { const q = place[k](get(i)); q[2] += side ? SIDE[k] : 0; P[n] = q; });
        P.neck = [0, 1, 2].map((c) => (P.shoulder_r[c] + P.shoulder_l[c]) / 2);
        sk[k].set(P);
        const top = Math.max(P.neck[1], P.shoulder_r[1]) + 0.36 + (side ? 0 : { fix: 0, base: 0.11, opencap: 0.22 }[k]);
        lbl[k].p.set(P.pelvis[0], top, P.pelvis[2]);
      }
      meshRoot.position.z = -oF[2];
      V.render();
    }
    function visibility() {
      meshRoot.visible = $("q-mesh").checked;
      sk.opencap.group.visible = $("q-opencap").checked; lbl.opencap.el.hidden = !$("q-opencap").checked;
      sk.base.group.visible = $("q-base").checked; lbl.base.el.hidden = !$("q-base").checked;
      const t = pIdx; pIdx = -1; pose(t);
    }
    ["q-mesh", "q-opencap", "q-base", "q-side", "q-over"].forEach((id) => $(id).addEventListener("change", visibility));

    // video and keypoints (camera 2)
    const video = $("q-video"), kpc = $("q-kp"), kctx = kpc.getContext("2d"), kp = A["cam2.kp"], vis = A["cam2.vis"];
    const nV = S.video.frames;
    let frame = 0, playing = false, last = 0;
    function drawKp(f) {
      const w = kpc.clientWidth, h = kpc.clientHeight, dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (kpc.width !== Math.round(w * dpr)) { kpc.width = Math.round(w * dpr); kpc.height = Math.round(h * dpr); }
      kctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      kctx.clearRect(0, 0, w, h);
      if (!$("q-kpshow").checked) return;
      const pt = (j) => [kp[(f * 33 + j) * 2] * w, kp[(f * 33 + j) * 2 + 1] * h];
      kctx.lineCap = "round";
      for (const [lw, col] of [[4, "rgba(0,0,0,0.55)"], [2, "#ffffff"]]) {
        kctx.lineWidth = lw; kctx.strokeStyle = col;
        kctx.beginPath();
        for (const [a, b] of MP_EDGES) {
          if (vis[f * 33 + a] < 0.3 || vis[f * 33 + b] < 0.3) continue;
          kctx.moveTo(...pt(a)); kctx.lineTo(...pt(b));
        }
        kctx.stroke();
      }
      kctx.fillStyle = "#ffffff";
      for (let j = 11; j < 33; j++) { if (vis[f * 33 + j] < 0.3) continue; const [x, y] = pt(j); kctx.beginPath(); kctx.arc(x, y, 2.5, 0, 7); kctx.fill(); }
    }
    function setFrame(f, seek) {
      frame = Math.max(0, Math.min(nV - 1, Math.round(f)));
      $("q-scrub").value = frame;
      $("q-time").textContent = `${(frame / 60).toFixed(2)} s`;
      if (seek && video.readyState >= 1) video.currentTime = (frame + 0.5) / 60;
      drawKp(frame);
      pose(Math.round(frame / 2));
      moveCursor();
    }
    function tick(ts) {
      if (!playing) return;
      if (video.readyState >= 2 && !video.paused) setFrame(video.currentTime * 60, false);
      else { const f = frame + (ts - last) * 0.06; setFrame(f >= nV - 1 ? 0 : f, false); }   // no video: our own clock
      last = ts;
      requestAnimationFrame(tick);
    }
    function play(on) {
      playing = on;
      $("q-play").textContent = on ? "Pause" : "Play";
      $("q-play").setAttribute("aria-pressed", on ? "true" : "false");
      if (on) { video.play().catch(() => {}); last = performance.now(); requestAnimationFrame(tick); } else video.pause();
    }
    $("q-play").addEventListener("click", () => play(!playing));
    $("q-scrub").max = nV - 1;
    $("q-scrub").addEventListener("input", () => { if (playing) play(false); setFrame(+$("q-scrub").value, true); });
    $("q-kpshow").addEventListener("change", () => drawKp(frame));
    new ResizeObserver(() => drawKp(frame)).observe(kpc);
    const file = video.canPlayType('video/mp4; codecs="avc1.640028"') ? S.video.file : S.video.file.replace(".mp4", ".webm");
    fetch(`viz/${file}`).then((r) => { if (!r.ok) throw new Error(r.status); return r.blob(); })
      .then((b) => { video.src = URL.createObjectURL(b); video.addEventListener("loadeddata", () => setFrame(frame, true), { once: true }); })
      .catch(() => { $("q-video-note").hidden = false; });

    // joint angle chart: ours after and before the fix, OpenCap's
    const chart = $("q-chart"), sel = $("q-coord");
    Object.entries(COORDS).forEach(([k, v]) => { if (S.fix_angles[k] && S.opencap_angles[k]) sel.add(new Option(v, k)); });
    const series = [{ k: "fix", name: "Ours, after the fix", short: "after fix", tok: "--s1", dash: "" },
                    { k: "base", name: "Ours, before the fix", short: "before fix", tok: "--s2", dash: "5 4" },
                    { k: "opencap", name: "OpenCap's own result", short: "OpenCap", tok: "--s3", dash: "" }];
    const W = 900, H = 230, m = { l: 44, r: 92, t: 12, b: 28 };
    const tx = (t) => m.l + (t / S.t[nP - 1]) * (W - m.l - m.r);
    let ty = null, cursor = null, hover = null;
    function drawChart() {
      const c = sel.value, ys = series.map((s) => S[`${s.k}_angles`][c]);
      let lo = Math.min(...ys.flat()), hi = Math.max(...ys.flat());
      const step = hi - lo > 60 ? 20 : hi - lo > 25 ? 10 : 5;
      lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
      ty = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
      let svg = "";
      for (let v = lo; v <= hi + 1e-9; v += step) svg += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${ty(v)}" y2="${ty(v)}"/><text class="tick" x="${m.l - 6}" y="${ty(v) + 4}" text-anchor="end">${v}°</text>`;
      for (let t = 0; t <= S.t[nP - 1] + 1e-9; t += 1) svg += `<text class="tick" x="${tx(t)}" y="${H - 8}" text-anchor="middle">${t} s</text>`;
      const ends = [];
      series.forEach((s, i) => {
        const valid = s.k === "opencap" ? S.opencap_valid : null;
        let d = "", pen = false;
        ys[i].forEach((v, f) => { if (valid && !valid[f]) { pen = false; return; } d += `${pen ? "L" : "M"}${tx(S.t[f]).toFixed(1)},${ty(v).toFixed(1)}`; pen = true; });
        svg += `<path d="${d}" fill="none" stroke="var(${s.tok})" stroke-width="2" stroke-dasharray="${s.dash}" stroke-linejoin="round"/>`;
        ends.push({ y: ty(ys[i][nP - 1]), s });
      });
      ends.sort((a, b) => a.y - b.y);
      for (let i = 1; i < ends.length; i++) ends[i].y = Math.max(ends[i].y, ends[i - 1].y + 14);
      ends.forEach(({ y, s }) => { svg += `<text class="endlabel" x="${W - m.r + 8}" y="${y + 4}">${s.short}</text>`; });
      svg += `<line id="q-cursor" class="cursor" y1="${m.t}" y2="${H - m.b}"/><line id="q-hover" class="hoverline" y1="${m.t}" y2="${H - m.b}" visibility="hidden"/>`;
      svg += `<rect id="q-hit" x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}" fill="transparent"/>`;
      chart.innerHTML = svg;
      cursor = $("q-cursor"); hover = $("q-hover");
      const hit = $("q-hit");
      const at = (ev) => { const r = chart.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width * W; return Math.max(0, Math.min(nP - 1, Math.round((x - m.l) / (W - m.l - m.r) * (nP - 1)))); };
      hit.addEventListener("pointermove", (ev) => {
        const f = at(ev), tip = $("q-tip");
        hover.setAttribute("x1", tx(S.t[f])); hover.setAttribute("x2", tx(S.t[f])); hover.setAttribute("visibility", "visible");
        tip.hidden = false;
        tip.innerHTML = `<b>${S.t[f].toFixed(2)} s</b>` + series.map((s, i) => `<div><i style="background:var(${s.tok})"></i>${s.name}<span>${(s.k === "opencap" && !S.opencap_valid[f]) ? "–" : ys[i][f].toFixed(1) + "°"}</span></div>`).join("");
        const r = chart.getBoundingClientRect(), x = (tx(S.t[f]) / W) * r.width;
        tip.style.left = `${Math.min(x + 12, r.width - tip.offsetWidth - 4)}px`;
      });
      hit.addEventListener("pointerleave", () => { hover.setAttribute("visibility", "hidden"); $("q-tip").hidden = true; });
      hit.addEventListener("click", (ev) => { if (playing) play(false); setFrame(at(ev) * 2, true); });
      const r = S.rmse;
      $("q-legend").innerHTML = series.map((s) => {
        const e = s.k === "opencap" ? null : r[s.k][c];
        return `<span class="lg"><i class="${s.dash ? "dash" : ""}" style="--c:var(${s.tok})"></i>${s.name}${e ? ` <span class="muted">· RMSE ${e.rmse_deg.toFixed(1)}°, ${e.rmse_offset_removed_deg.toFixed(1)}° without the constant offset</span>` : " <span class=\"muted\">· the reference</span>"}</span>`;
      }).join("");
      moveCursor();
    }
    function moveCursor() { if (cursor) { const x = tx(Math.min(frame / 60, S.t[nP - 1])); cursor.setAttribute("x1", x); cursor.setAttribute("x2", x); } }
    sel.addEventListener("change", drawChart);
    // the shank, scaled three ways
    $("q-shank").textContent = `Right shank (knee to ankle joint): ours after the fix ${fmt(100 * S.scale.fix.shank_r_m)} cm, ` +
      `before ${fmt(100 * S.scale.base.shank_r_m)} cm, OpenCap ${fmt(100 * S.scale.opencap.shank_r_m)} cm.`;
    drawChart();
    visibility();
    // start at the deepest point of the first squat, paused
    const kr = S.fix_angles.knee_angle_r, firstRep = kr.slice(0, Math.round(nP / 4));
    setFrame(2 * firstRep.indexOf(Math.max(...firstRep)), true);
  }

  // ---------- start each view when it first comes near the screen ----------
  function lazy(id, fn) {
    const el = $(id);
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); fn().catch((e) => failed(el, e)); } }, { rootMargin: "400px" });
    io.observe(el);
  }
  if (!window.THREE || !THREE.OrbitControls || !window.SkelMath) {
    ["v-bodies", "v-depth", "v-squat"].forEach((id) => failed($(id), new Error("the 3D library did not load")));
    return;
  }
  let bodies = null;
  const getBodies = () => (bodies = bodies || load("bodies"));
  lazy("v-bodies", async () => bodiesView(await getBodies()));
  lazy("v-depth", async () => depthView(await getBodies()));
  lazy("v-squat", async () => squatView(await load("squat")));
})();
