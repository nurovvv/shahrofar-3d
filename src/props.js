// Trees, cars and people around the complex, drawn as instanced meshes from the positions the
// Blender build exports (model/complex.json). Geometry is generated here, so nothing else to load.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// deterministic noise so every visit looks the same
function rng(seed) {
  return () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

function colorize(geo, fn) {
  geo = geo.index ? geo.toNonIndexed() : geo;
  const pos = geo.attributes.position, n = pos.count;
  const col = new Float32Array(n * 3), c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    fn(c, pos.getX(i), pos.getY(i), pos.getZ(i));
    col.set([c.r, c.g, c.b], i * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return geo;
}

// a lumpy foliage cluster: icosphere pushed in and out by smooth noise
function clump(r, rnd, detail = 2, squash = 0.85) {
  const g = new THREE.IcosahedronGeometry(r, detail);
  const p = g.attributes.position;
  const k = [rnd() * 6, rnd() * 6, rnd() * 6];
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const nz = 1 + 0.16 * Math.sin(x * 3.1 + k[0]) * Math.cos(y * 2.7 + k[1]) + 0.1 * Math.sin(z * 4.3 + k[2]);
    p.setXYZ(i, x * nz, y * nz * squash, z * nz);
  }
  g.computeVertexNormals();
  return g;
}

const BARK = new THREE.Color(0x5b4334);
function trunk(h, r0, r1, branches, rnd) {
  const parts = [new THREE.CylinderGeometry(r1, r0, h, 7).translate(0, h / 2, 0)];
  for (let i = 0; i < branches; i++) {
    const len = h * (0.35 + rnd() * 0.25);
    const b = new THREE.CylinderGeometry(r1 * 0.35, r1 * 0.6, len, 5).translate(0, len / 2, 0);
    b.rotateZ(0.6 + rnd() * 0.4);
    b.rotateY((i / branches) * Math.PI * 2 + rnd());
    b.translate(0, h * (0.6 + rnd() * 0.3), 0);
    parts.push(b);
  }
  return colorize(mergeGeometries(parts.map((g) => g.toNonIndexed())), (c) => c.copy(BARK));
}

// leaf colour: darker underneath and inside, lighter where the sun hits
function leafShade(base, cy, top) {
  return (c, x, y, z) => {
    const t = THREE.MathUtils.clamp((y - cy) / top, -1, 1);
    c.copy(base).offsetHSL(0, 0, 0.07 * t - 0.02 + 0.02 * Math.sin(x * 5 + z * 3));
  };
}

// Tree species: { wood, leaves } geometries (unit size; instances scale them)
function species(rnd) {
  const out = [];
  // 1. broadleaf (plane / elm): wide round crown of several clumps
  {
    const h = 3.2;
    const leaves = [];
    for (const [x, y, z, r] of [[0, 5.2, 0, 2.3], [1.3, 4.6, 0.5, 1.6], [-1.2, 4.7, -0.4, 1.7], [0.3, 4.4, -1.3, 1.5], [-0.4, 4.5, 1.3, 1.5], [0.2, 6.3, 0.2, 1.4]]) {
      leaves.push(clump(r, rnd).translate(x, y, z));
    }
    const g = mergeGeometries(leaves.map((x) => x.toNonIndexed()));
    out.push({ wood: trunk(h + 1.2, 0.26, 0.18, 4, rnd), leaves: colorize(g, leafShade(new THREE.Color(0x4b6b25), 5.0, 2.2)) });
  }
  // 2. conifer: stacked drooping cones
  {
    const cones = [];
    for (let i = 0; i < 5; i++) {
      const r = 2.0 - i * 0.36, y = 2.0 + i * 1.35;
      const c = new THREE.ConeGeometry(r, 2.4, 9, 1, true).translate(0, y + 1.2, 0);
      cones.push(c);
    }
    const g = mergeGeometries(cones.map((x) => x.toNonIndexed()));
    out.push({ wood: trunk(2.6, 0.2, 0.14, 0, rnd), leaves: colorize(g, leafShade(new THREE.Color(0x2f4a2a), 5, 4)) });
  }
  // 3. poplar / cypress: tall narrow crown
  {
    const leaves = [];
    for (const [y, r] of [[3.4, 1.2], [5.0, 1.15], [6.6, 0.95], [8.0, 0.65]]) leaves.push(clump(r, rnd, 2, 1.5).translate(0, y, 0));
    const g = mergeGeometries(leaves.map((x) => x.toNonIndexed()));
    out.push({ wood: trunk(3.0, 0.2, 0.14, 0, rnd), leaves: colorize(g, leafShade(new THREE.Color(0x3e6125), 5.5, 3)) });
  }
  // 4. young ornamental tree: small light crown
  {
    const leaves = [];
    for (const [x, y, z, r] of [[0, 3.2, 0, 1.3], [0.7, 2.9, 0.3, 0.9], [-0.6, 3.0, -0.3, 0.9]]) leaves.push(clump(r, rnd).translate(x, y, z));
    const g = mergeGeometries(leaves.map((x) => x.toNonIndexed()));
    out.push({ wood: trunk(2.2, 0.12, 0.08, 3, rnd), leaves: colorize(g, leafShade(new THREE.Color(0x6a8a2c), 3.1, 1.3)) });
  }
  return out;
}

export function addTrees(scene, protos, list, toScene) {
  const rnd = rng(11);
  const kinds = species(rnd);
  // proto from the Blender build (height, radius, light) -> species
  const pick = (p, i) => {
    if (p.light && p.h <= 6) return 3;
    if (p.h >= 9 && (i % 3 === 0)) return 1;
    if (p.r < 2.4 && (i % 4 === 1)) return 2;
    return 0;
  };
  const groups = kinds.map(() => []);
  list.forEach(([x, y, sc, sz, rot, k], i) => groups[pick(protos[k], i)].push({ x, y, sc, sz, rot, p: protos[k] }));
  const wood = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 });
  const leaf = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.85, envMapIntensity: 0.3 });
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3(), e = new THREE.Euler();
  const tint = new THREE.Color();
  kinds.forEach((kind, si) => {
    const items = groups[si];
    if (!items.length) return;
    const wm = new THREE.InstancedMesh(kind.wood, wood, items.length);
    const lm = new THREE.InstancedMesh(kind.leaves, leaf, items.length);
    items.forEach((t, i) => {
      const w = toScene(t.x, t.y);
      const k = (t.p.h / 7) * t.sc; // the build's tree height relative to the 7 m reference
      q.setFromEuler(e.set(0, t.rot, 0));
      m4.compose(p.set(w.x, 0, w.z), q, s.set(k, k * t.sz, k));
      wm.setMatrixAt(i, m4);
      lm.setMatrixAt(i, m4);
      tint.setHSL(0, 0, 1).offsetHSL(((i * 37) % 11) * 0.004 - 0.02, 0, ((i * 53) % 9) * 0.012 - 0.05);
      lm.setColorAt(i, tint);
    });
    for (const m of [wm, lm]) {
      m.castShadow = true;
      m.receiveShadow = true;
      scene.add(m);
    }
  });
}

// ---------- cars ----------
const CAR_PAINT = [0xd9dde2, 0xc9ccd0, 0x23272d, 0xa82a2a, 0xece8df, 0x5b6b7c, 0x1d2a44];

function carGeometries() {
  // side profile of a saloon, x along the car, extruded across (z), 4.5 m long
  const body = new THREE.Shape([
    [-2.25, 0.32], [2.2, 0.32], [2.3, 0.55], [2.22, 0.8], [1.15, 0.92], [0.55, 1.36], [-0.85, 1.4],
    [-1.55, 0.98], [-2.2, 0.92], [-2.3, 0.6],
  ].map(([x, y]) => new THREE.Vector2(x, y)));
  const bodyG = new THREE.ExtrudeGeometry(body, { depth: 1.62, bevelEnabled: true, bevelSize: 0.08, bevelThickness: 0.08, bevelSegments: 2 });
  bodyG.translate(0, 0, -0.81);
  const glass = new THREE.Shape([[1.08, 0.95], [0.53, 1.33], [-0.83, 1.37], [-1.47, 0.99]].map(([x, y]) => new THREE.Vector2(x, y)));
  const glassG = new THREE.ExtrudeGeometry(glass, { depth: 1.74, bevelEnabled: false }).translate(0, 0, -0.87);
  const wheels = [];
  for (const x of [-1.42, 1.42]) {
    for (const z of [-0.78, 0.78]) {
      wheels.push(new THREE.CylinderGeometry(0.33, 0.33, 0.24, 16).rotateX(Math.PI / 2).translate(x, 0.33, z).toNonIndexed());
    }
  }
  const lights = [];
  for (const z of [-0.6, 0.6]) {
    lights.push(new THREE.BoxGeometry(0.06, 0.12, 0.34).translate(2.34, 0.66, z).toNonIndexed());
  }
  const rear = [];
  for (const z of [-0.62, 0.62]) rear.push(new THREE.BoxGeometry(0.06, 0.12, 0.34).translate(-2.36, 0.72, z).toNonIndexed());
  return {
    body: bodyG,
    glass: glassG,
    wheels: mergeGeometries(wheels),
    front: mergeGeometries(lights),
    rear: mergeGeometries(rear),
  };
}

export function addCars(scene, list, toScene) {
  const G = carGeometries();
  const n = list.length;
  const paint = new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.32, metalness: 0.55, clearcoat: 1, clearcoatRoughness: 0.15 });
  const meshes = [
    new THREE.InstancedMesh(G.body, paint, n),
    new THREE.InstancedMesh(G.glass, new THREE.MeshStandardMaterial({ color: 0x1a2129, roughness: 0.08, metalness: 0.6 }), n),
    new THREE.InstancedMesh(G.wheels, new THREE.MeshStandardMaterial({ color: 0x1b1c1f, roughness: 0.8 }), n),
    new THREE.InstancedMesh(G.front, new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff3d8, emissiveIntensity: 0.6 }), n),
    new THREE.InstancedMesh(G.rear, new THREE.MeshStandardMaterial({ color: 0x8a1010, emissive: 0x6a0000, emissiveIntensity: 0.6 }), n),
  ];
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), one = new THREE.Vector3(1, 1, 1), c = new THREE.Color();
  list.forEach(([x, y, z, r, k], i) => {
    const w = toScene(x, y);
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), r);
    m4.compose(p.set(w.x, z, w.z), q, one);
    meshes.forEach((m) => m.setMatrixAt(i, m4));
    meshes[0].setColorAt(i, c.setHex(CAR_PAINT[(k + i) % CAR_PAINT.length]));
  });
  for (const m of meshes) {
    m.castShadow = true;
    m.receiveShadow = true;
    scene.add(m);
  }
}

// ---------- people ----------
const CLOTHES = [0x2f3b52, 0xb33a3a, 0xe8e2d6, 0x3d6b4f, 0x7a5c99, 0xd4a03a, 0x22252a];
const SKIN = [0xe0b48f, 0xc69472, 0x9c6b4a];

export function addPeople(scene, list, toScene) {
  const rnd = rng(5);
  const legs = new THREE.CapsuleGeometry(0.11, 0.7, 3, 6).translate(0, 0.46, 0);
  const torso = new THREE.CapsuleGeometry(0.17, 0.42, 3, 8).translate(0, 1.18, 0);
  const head = new THREE.SphereGeometry(0.12, 10, 8).translate(0, 1.66, 0);
  const n = list.length;
  const mk = (g, color) => new THREE.InstancedMesh(g, new THREE.MeshStandardMaterial({ color, roughness: 0.85 }), n);
  const L = mk(legs, 0xffffff), T = mk(torso, 0xffffff), H = mk(head, 0xffffff);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3(), c = new THREE.Color();
  list.forEach(([x, y, z], i) => {
    const w = toScene(x, y);
    const h = 0.92 + rnd() * 0.16;
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd() * Math.PI * 2);
    m4.compose(p.set(w.x, z, w.z), q, s.set(1, h, 1));
    for (const m of [L, T, H]) m.setMatrixAt(i, m4);
    L.setColorAt(i, c.setHex([0x2a2f3a, 0x3b4a63, 0x4a3f35, 0x1e1f22][Math.floor(rnd() * 4)]));
    T.setColorAt(i, c.setHex(CLOTHES[Math.floor(rnd() * CLOTHES.length)]));
    H.setColorAt(i, c.setHex(SKIN[Math.floor(rnd() * SKIN.length)]));
  });
  for (const m of [L, T, H]) {
    m.castShadow = true;
    scene.add(m);
  }
}
