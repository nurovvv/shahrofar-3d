// Builds the 3D interior of one apartment from its layout.
// The group is placed (and mirrored) into the right spot inside the building.
import * as THREE from 'three';
import { CEIL, CORR, floorBase } from './config.js';
import { woodTexture, tileTexture } from './textures.js';

const DOOR_H = 2.1;
const TEX_M = 1.2; // meters covered by one texture repeat

const shared = {};
function getShared() {
  if (shared.box) return shared;
  shared.box = new THREE.BoxGeometry(1, 1, 1);
  shared.cyl = new THREE.CylinderGeometry(1, 1, 1, 24);
  shared.sphere = new THREE.IcosahedronGeometry(1, 2);
  const wood = woodTexture(), tile = tileTexture();
  shared.wood = new THREE.MeshStandardMaterial({ map: wood, roughness: 0.55 });
  shared.tile = new THREE.MeshStandardMaterial({ map: tile, roughness: 0.35 });
  shared.wall = new THREE.MeshStandardMaterial({ color: 0xf1eee8, roughness: 0.9 });
  shared.ceiling = new THREE.MeshStandardMaterial({ color: 0xfbfaf7, roughness: 1 });
  shared.door = new THREE.MeshStandardMaterial({ color: 0x4a3828, roughness: 0.6 });
  shared.frame = new THREE.MeshStandardMaterial({ color: 0xe4ded3, roughness: 0.7 });
  shared.mats = new Map();
  return shared;
}

function material(color, extra = {}) {
  const key = `${color}|${extra.emissive ?? ''}|${extra.metal ? 1 : 0}`;
  if (!shared.mats.has(key)) {
    shared.mats.set(key, new THREE.MeshStandardMaterial({
      color,
      roughness: extra.metal ? 0.08 : 0.7,
      metalness: extra.metal ? 0.9 : 0,
      emissive: extra.emissive ?? 0x000000,
      emissiveIntensity: extra.emissive ? 1.2 : 0,
    }));
  }
  return shared.mats.get(key);
}

/**
 * @param apt apartment from data.js
 * @param full true for walk mode (ceiling + lights), false for the cut-away floor view
 */
export function buildInterior(apt, { full = true } = {}) {
  const S = getShared();
  const { def, layout } = apt;
  const baseY = floorBase(apt.floor);
  const group = new THREE.Group();
  group.position.set(def.ox, baseY, def.sz * CORR);
  group.scale.set(def.sx, 1, def.sz);

  const own = []; // geometries to dispose
  const floorMeshes = [];
  const colliders = [];

  const addBox = (mat, u0, u1, y0, y1, v0, v1, cast = true) => {
    const m = new THREE.Mesh(S.box, mat);
    m.scale.set(u1 - u0, y1 - y0, v1 - v0);
    m.position.set((u0 + u1) / 2, (y0 + y1) / 2, (v0 + v1) / 2);
    m.castShadow = cast;
    m.receiveShadow = true;
    group.add(m);
    return m;
  };

  // floors, one per room, with real-world texture scale
  for (const r of layout.rooms) {
    const w = r.u1 - r.u0, d = r.v1 - r.v0;
    const geo = new THREE.PlaneGeometry(w, d);
    const uv = geo.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, (uv.getX(i) * w) / TEX_M, (uv.getY(i) * d) / TEX_M);
    geo.rotateX(-Math.PI / 2);
    own.push(geo);
    const m = new THREE.Mesh(geo, r.floor === 'tile' ? S.tile : S.wood);
    m.position.set((r.u0 + r.u1) / 2, 0.004, (r.v0 + r.v1) / 2);
    m.receiveShadow = true;
    m.userData.room = r;
    group.add(m);
    floorMeshes.push(m);
  }

  // walls
  for (const w of layout.walls) {
    addBox(S.wall, w.u0, w.u1, 0, CEIL, w.v0, w.v1);
    colliders.push(w);
  }

  // doorways: lintel above, a closed leaf for the front door
  for (const d of layout.doors) {
    addBox(S.wall, d.u0, d.u1, DOOR_H, CEIL, d.v0, d.v1);
    const alongU = d.u1 - d.u0 > d.v1 - d.v0;
    if (alongU) {
      addBox(S.frame, d.u0 - 0.04, d.u1 + 0.04, DOOR_H, DOOR_H + 0.06, d.v0 - 0.01, d.v1 + 0.01, false);
    } else {
      addBox(S.frame, d.u0 - 0.01, d.u1 + 0.01, DOOR_H, DOOR_H + 0.06, d.v0 - 0.04, d.v1 + 0.04, false);
    }
    if (d.entry) {
      const leaf = alongU
        ? { u0: d.u0, u1: d.u1, v0: d.v0 + 0.05, v1: d.v0 + 0.11 }
        : { u0: d.u0 + 0.05, u1: d.u0 + 0.11, v0: d.v0, v1: d.v1 };
      addBox(S.door, leaf.u0, leaf.u1, 0, DOOR_H, leaf.v0, leaf.v1);
      const hu = alongU ? d.u1 - 0.12 : (leaf.u0 + leaf.u1) / 2;
      const hv = alongU ? leaf.v1 + 0.03 : d.v1 - 0.12;
      addBox(material(0xcfd2d4, { metal: true }), hu - 0.06, hu + 0.06, 1.0, 1.03, hv - 0.02, hv + 0.02, false);
      colliders.push(leaf);
    }
  }

  // furniture
  for (const it of layout.items) {
    const mat = material(it.color, it);
    let m;
    if (it.kind === 'box') {
      m = addBox(mat, it.u0, it.u1, it.y0, it.y1, it.v0, it.v1, it.y1 - it.y0 > 0.05);
      if (it.collide) colliders.push({ u0: it.u0, u1: it.u1, v0: it.v0, v1: it.v1 });
    } else if (it.kind === 'cyl') {
      m = new THREE.Mesh(S.cyl, mat);
      m.scale.set(it.r, it.y1 - it.y0, it.r);
      m.position.set(it.u, (it.y0 + it.y1) / 2, it.v);
      if (it.collide) colliders.push({ u0: it.u - it.r, u1: it.u + it.r, v0: it.v - it.r, v1: it.v + it.r });
    } else {
      m = new THREE.Mesh(S.sphere, mat);
      m.scale.setScalar(it.r);
      m.position.set(it.u, it.y, it.v);
    }
    m.castShadow = !it.emissive;
    m.receiveShadow = true;
    group.add(m);
  }

  if (full) {
    const ceil = new THREE.PlaneGeometry(layout.W + 0.2, layout.D + 0.2);
    ceil.rotateX(Math.PI / 2);
    own.push(ceil);
    const c = new THREE.Mesh(ceil, S.ceiling);
    c.position.set(layout.W / 2 - 0.1, CEIL - 0.004, layout.D / 2 - 0.1);
    c.receiveShadow = true;
    group.add(c);

    for (const r of layout.rooms) {
      const cu = (r.u0 + r.u1) / 2, cv = (r.v0 + r.v1) / 2;
      const disc = new THREE.Mesh(S.cyl, material(0xfff6e6, { emissive: 0xfff1d6 }));
      disc.scale.set(0.22, 0.03, 0.22);
      disc.position.set(cu, CEIL - 0.02, cv);
      group.add(disc);
      const light = new THREE.PointLight(0xffe4c0, r.area > 15 ? 7 : 4, 9, 2);
      light.position.set(cu, CEIL - 0.35, cv);
      group.add(light);
    }
  }

  const toLocal = (x, z) => ({ u: (x - def.ox) * def.sx, v: z * def.sz - CORR });
  const toWorld = (u, v) => ({ x: def.ox + def.sx * u, z: def.sz * (CORR + v) });

  return {
    apt,
    group,
    floorMeshes,
    colliders,
    baseY,
    toLocal,
    toWorld,
    dispose() {
      group.removeFromParent();
      own.forEach((g) => g.dispose());
    },
  };
}
