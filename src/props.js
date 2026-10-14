// Trees, cars and people around the complex, drawn as instanced meshes at the positions the
// Blender build exports (model/complex.json): tree billboards (public/trees), car bodies
// (public/models/cars.glb), people generated here.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { Q } from './quality.js';
import TREES_INFO from '../public/trees/trees.json';

// deterministic noise so every visit looks the same
function rng(seed) {
  return () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

// ---------- trees ----------
// Billboards of photographed CC0 trees (Poly Haven), rendered in Blender (blender/trees): three
// upright quads crossed at 60 degrees, each face showing the tree from its side, plus one quad
// seen from above. Colour, cut-out and normals come from the renders, so the sun and the sky light
// them like the rest of the scene and they cast proper shadows. 14 triangles per tree, one draw
// call per kind; size, turn and tint vary per tree.
const TREE_URL = `${import.meta.env.BASE_URL}trees/`; // + a_ / b_ atlas prefix from trees.json
const SIDES = 6;

function impostorGeometry(v) {
  const pos = [], nor = [], uv = [], idx = [];
  const quad = (p0, p1, p2, p3, n, cell) => {
    const [u0, v0, du, dv] = cell;
    const base = pos.length / 3;
    pos.push(...p0, ...p1, ...p2, ...p3);
    for (let i = 0; i < 4; i++) nor.push(...n);
    uv.push(u0, v0, u0 + du, v0, u0 + du, v0 + dv, u0, v0 + dv);
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  };
  const S = v.side, h = S / 2;
  for (let k = 0; k < SIDES; k++) {
    // view k was rendered from direction (sin a, -cos a) on the Blender ground plane = (sin a, cos a) here
    const a = (2 * Math.PI * k) / SIDES;
    const d = [Math.sin(a), 0, Math.cos(a)], r = [Math.cos(a), 0, -Math.sin(a)];
    quad([-r[0] * h, 0, -r[2] * h], [r[0] * h, 0, r[2] * h], [r[0] * h, S, r[2] * h], [-r[0] * h, S, -r[2] * h], d, v.cells[`side${k}`]);
  }
  // from above, level with the middle of the crown; image up = Blender +y = -z here
  const T = v.top / 2, y = v.height * 0.62;
  quad([-T, y, T], [T, y, T], [T, y, -T], [-T, y, -T], [0, 1, 0], v.cells.top);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

/**
 * @param protos, list  the site plan's trees (model/complex.json: trees, tree_protos)
 * @param placed        trees on the podium decks, terraces and promenade: [x, y, z, height, radius, kind]
 */
// Foliage cut-outs thin out in the smaller mip levels (averaging leaves with sky lowers alpha below the
// cut), so distant trees would look bare. Alpha is scaled up with the mip level actually sampled
// (keeps the crown's coverage), then three.js sharpens it for alpha-to-coverage.
function treeMaterial(atlas, size) {
  const loader = new THREE.TextureLoader();
  const color = loader.load(`${TREE_URL}${atlas}color_${size}.webp`);
  color.colorSpace = THREE.SRGBColorSpace;
  const normal = loader.load(`${TREE_URL}${atlas}normal_${size}.webp`);
  for (const t of [color, normal]) t.anisotropy = 4;
  const mat = new THREE.MeshStandardMaterial({
    map: color,
    normalMap: normal,
    alphaTest: 0.42,
    alphaToCoverage: true,
    roughness: 0.82,
    envMapIntensity: 0.55,
  });
  const px = size === '2k' ? 2048 : 1024;
  mat.onBeforeCompile = (sh) => {
    sh.fragmentShader = sh.fragmentShader.replace('#include <alphatest_fragment>', `
      {
        vec2 t = vMapUv * ${px.toFixed(1)};
        vec2 dx = dFdx(t), dy = dFdy(t);
        float mip = max(0.0, 0.5 * log2(max(dot(dx, dx), dot(dy, dy))));
        diffuseColor.a *= 1.0 + mip * 0.28;
      }
      #include <alphatest_fragment>`);
  };
  mat.customProgramCacheKey = () => `tree${px}`;
  return mat;
}

export function addTrees(scene, protos, list, placed, toScene) {
  const size = Q.level === 'high' ? '2k' : '1k';
  const mats = {};
  const matFor = (atlas) => (mats[atlas] ??= treeMaterial(atlas, size));
  // kinds of tree -> rendered variants (alternating where there are two)
  const kinds = { broad: ['broad_b', 'broad', 'broad_b'], conifer: ['fir_a', 'fir_b'], poplar: ['poplar'], small: ['shrub'], shrub: ['shrub'] };
  // site plan proto (height, radius, light crown) -> kind
  const pick = (p, i) => {
    if (p.light && p.h <= 6) return 'small';
    if (p.h >= 9 && i % 3 === 0) return 'conifer';
    if (p.r < 2.4 && i % 4 === 1) return 'poplar';
    return 'broad';
  };
  const items = [
    ...list.map(([x, y, sc, sz, rot, k], i) => ({ x, y, z: 0, h: protos[k].h * sc * sz, r: protos[k].r * sc, rot, kind: pick(protos[k], i) })),
    ...placed.map(([x, y, z, h, r, kind], i) => ({ x, y, z, h, r, rot: i * 2.39996, kind })),
  ];
  const groups = {};
  items.forEach((t, i) => {
    const vs = kinds[t.kind] ?? kinds.broad;
    (groups[vs[i % vs.length]] ??= []).push(t);
  });
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3(), e = new THREE.Euler();
  const tint = new THREE.Color(), white = new THREE.Color(1, 1, 1);
  const rnd = rng(23);
  for (const [variant, group] of Object.entries(groups)) {
    const v = TREES_INFO[variant] ?? TREES_INFO.broad;
    if (!v) continue;
    const mesh = new THREE.InstancedMesh(impostorGeometry(v), matFor(v.atlas ?? ''), group.length);
    group.forEach((t, i) => {
      const w = toScene(t.x, t.y);
      // the plan's height and crown radius, within the photographed tree's proportions
      const kv = t.h / v.height;
      const kh = THREE.MathUtils.clamp(t.r / v.radius, kv * 0.8, kv * 1.25);
      q.setFromEuler(e.set(0, t.rot + rnd() * Math.PI * 2, 0));
      m4.compose(p.set(w.x, t.z, w.z), q, s.set(kh, kv, kh));
      mesh.setMatrixAt(i, m4);
      // a little more or less green and light from tree to tree
      tint.setHSL(0.27 + (rnd() - 0.5) * 0.05, 0.25 + rnd() * 0.15, 0.5 + (rnd() - 0.5) * 0.12).lerp(white, 0.72);
      mesh.setColorAt(i, tint);
    });
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false; // instances spread over the whole site
    mesh.name = `trees ${variant}`;
    scene.add(mesh);
  }
}

// ---------- cars ----------
// Saloon, SUV and hatchback modelled in Blender (blender/props/build_cars.py): one instanced mesh
// per body type and material, a close-up and a far version (a quarter of the triangles) chosen per
// car by its distance from the camera. Paint is a clearcoat (MeshPhysicalMaterial: the lacquer layer
// is what makes car paint read as car paint); everything else is the standard material.
const CAR_URL = `${import.meta.env.BASE_URL}models/cars.glb`;
const CAR_PAINT = [0xe8e9eb, 0xc4c7cb, 0x24272c, 0x8f1f22, 0xf2efe8, 0x51606e, 0x1c2638, 0x7d8085];
const CAR_TYPES = ['saloon', 'saloon', 'suv', 'saloon', 'hatch', 'suv', 'saloon', 'hatch'];
const CAR_NEAR = Q.level === 'high' ? 120 : 60; // metres: closer than this, the detailed body

const carMats = {
  'Car paint': () => new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.42, metalness: 0.55, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 1.1 }),
  'Car glass': () => new THREE.MeshStandardMaterial({ color: 0x121619, roughness: 0.05, metalness: 0.0, envMapIntensity: 1.3 }),
  'Car tyre': () => new THREE.MeshStandardMaterial({ color: 0x1b1b1d, roughness: 0.92 }),
  'Car rim': () => new THREE.MeshStandardMaterial({ color: 0xb9bdc1, roughness: 0.3, metalness: 0.9 }),
  'Car lamp': () => new THREE.MeshStandardMaterial({ color: 0xf4f4f0, roughness: 0.1, emissive: 0xfff6e2, emissiveIntensity: 0.15 }),
  'Car rear lamp': () => new THREE.MeshStandardMaterial({ color: 0x8c0d10, roughness: 0.2, emissive: 0x5a0000, emissiveIntensity: 0.3 }),
  'Car under': () => new THREE.MeshStandardMaterial({ color: 0x141414, roughness: 0.95 }),
};

let carUpdate = null;
export function updateCars(camera) {
  carUpdate?.(camera);
}

export function addCars(scene, list, toScene) {
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  loader.load(CAR_URL, (gltf) => {
    const mats = {};
    const mat = (name) => (mats[name] ??= (carMats[name] ?? carMats['Car under'])());
    // body type -> { near: [InstancedMesh], far: [InstancedMesh] }
    const byType = {};
    const cars = list.map(([x, y, z, r, k], i) => ({ type: CAR_TYPES[(k + i) % CAR_TYPES.length], x, y, z, r, color: CAR_PAINT[(k * 3 + i) % CAR_PAINT.length] }));
    gltf.scene.updateMatrixWorld(true);
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      const node = o.parent?.isMesh || o.parent === gltf.scene ? o : o.parent;
      const [type, far] = (node.name || o.name).split('_');
      const n = cars.filter((c) => c.type === type).length;
      if (!n) return;
      const slot = (byType[type] ??= { near: [], far: [] })[far ? 'far' : 'near'];
      const g = o.geometry.clone().applyMatrix4(o.matrixWorld);
      const im = new THREE.InstancedMesh(g, mat(o.material.name), n);
      im.castShadow = true;
      im.receiveShadow = true;
      im.frustumCulled = false;
      im.count = 0;
      slot.push(im);
      scene.add(im);
    });
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), one = new THREE.Vector3(1, 1, 1), c = new THREE.Color();
    const up = new THREE.Vector3(0, 1, 0);
    for (const car of cars) {
      const w = toScene(car.x, car.y);
      car.pos = new THREE.Vector3(w.x, car.z, w.z);
      // the build's cars face +x at r = 0 (Blender), the model's nose is +x too
      car.matrix = m4.compose(p.copy(car.pos), q.setFromAxisAngle(up, car.r), one).clone();
    }
    const last = new THREE.Vector3(1e9, 0, 0);
    carUpdate = (camera) => {
      if (camera.position.distanceToSquared(last) < 4) return; // re-sort only when the camera moved
      last.copy(camera.position);
      for (const [type, slots] of Object.entries(byType)) {
        let nn = 0, nf = 0;
        for (const car of cars) {
          if (car.type !== type) continue;
          const near = car.pos.distanceTo(camera.position) < CAR_NEAR;
          const set = near ? slots.near : slots.far;
          const idx = near ? nn++ : nf++;
          for (const im of set) {
            im.setMatrixAt(idx, car.matrix);
            if (im.material === mats['Car paint']) im.setColorAt(idx, c.setHex(car.color));
          }
        }
        for (const im of slots.near) (im.count = nn), (im.instanceMatrix.needsUpdate = true), im.instanceColor && (im.instanceColor.needsUpdate = true);
        for (const im of slots.far) (im.count = nf), (im.instanceMatrix.needsUpdate = true), im.instanceColor && (im.instanceColor.needsUpdate = true);
      }
    };
  });
}

// ---------- people ----------
// Simple figures with real proportions (about 1.6-1.85 m: legs, body, arms, head, hair), standing
// or mid-stride, coloured per person. Four instanced meshes for all of them.
const CLOTHES = [0x2f3b52, 0x9b3a3a, 0xe3ddd0, 0x3d5f4a, 0x6a5a86, 0xc79a3c, 0x22252a, 0x7a8794, 0xb8a58a];
const TROUSERS = [0x262a33, 0x384b66, 0x4a4038, 0x1d1f22, 0x6b6f75, 0xb9ae9a];
const SKIN = [0xe2b896, 0xc89878, 0xa06e4f, 0x7d533b];
const HAIR = [0x1f1a17, 0x3b2b20, 0x5a4330, 0x9a8f86, 0x1a1a1a];

function personParts(stride) {
  const leg = (side) => {
    const g = new THREE.CylinderGeometry(0.075, 0.06, 0.86, 7).translate(0, 0.43, 0);
    g.rotateX(side * stride);
    return g.translate(side * 0.1, 0.02, 0);
  };
  const legs = mergeGeometries([leg(1), leg(-1)].map((g) => g.toNonIndexed()));
  const torso = new THREE.CylinderGeometry(0.17, 0.14, 0.56, 8).scale(1, 1, 0.62).translate(0, 1.15, 0);
  const arm = (side) => new THREE.CylinderGeometry(0.05, 0.042, 0.6, 6).rotateX(-side * stride * 0.8).translate(side * 0.215, 1.14, 0);
  const body = mergeGeometries([torso, arm(1), arm(-1)].map((g) => g.toNonIndexed()));
  const head = mergeGeometries([
    new THREE.SphereGeometry(0.105, 10, 8).scale(0.9, 1.1, 1).translate(0, 1.6, 0.0),
    new THREE.CylinderGeometry(0.045, 0.05, 0.08, 6).translate(0, 1.47, 0),
  ].map((g) => g.toNonIndexed()));
  const hair = new THREE.SphereGeometry(0.108, 10, 6, 0, Math.PI * 2, 0, Math.PI * 0.55).scale(0.92, 1.05, 1.02).translate(0, 1.625, -0.01);
  return { legs, body, head, hair };
}

export function addPeople(scene, list, toScene) {
  const rnd = rng(5);
  const n = list.length;
  const poses = [personParts(0.02), personParts(0.28)]; // standing, walking
  const mk = (geo, rough) => new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: rough }), n);
  const sets = poses.map((p) => ({ legs: mk(p.legs, 0.9), body: mk(p.body, 0.85), head: mk(p.head, 0.6), hair: mk(p.hair, 0.8) }));
  const counts = [0, 0];
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), pp = new THREE.Vector3(), sc = new THREE.Vector3(), c = new THREE.Color();
  const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
  list.forEach(([x, y, z]) => {
    const w = toScene(x, y);
    const pose = rnd() < 0.45 ? 1 : 0;
    const set = sets[pose], i = counts[pose]++;
    const h = 0.93 + rnd() * 0.14; // 1.6 .. 1.85 m
    q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd() * Math.PI * 2);
    m4.compose(pp.set(w.x, z, w.z), q, sc.set(h, h, h));
    for (const m of Object.values(set)) m.setMatrixAt(i, m4);
    set.legs.setColorAt(i, c.setHex(pick(TROUSERS)));
    set.body.setColorAt(i, c.setHex(pick(CLOTHES)));
    set.head.setColorAt(i, c.setHex(pick(SKIN)));
    set.hair.setColorAt(i, c.setHex(pick(HAIR)));
  });
  sets.forEach((set, k) => {
    for (const m of Object.values(set)) {
      m.count = counts[k];
      m.castShadow = true;
      m.receiveShadow = true;
      m.frustumCulled = false;
      scene.add(m);
    }
  });
}
