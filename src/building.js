// The exterior of the building, split per floor so floors can be hidden for the cut-away view.
import * as THREE from 'three';
import { FLOORS, FLOOR_H, SLAB, CORR, floorBase } from './config.js';
import { signTexture } from './textures.js';

const BX = 12, BZ = 8; // facade half extents
const IN_X = 11.75, IN_Z = 7.75; // inner face of the facade

export function buildBuilding(apartments) {
  const root = new THREE.Group();
  const M = {
    slab: new THREE.MeshStandardMaterial({ color: 0xf1eee8, roughness: 0.8 }),
    fin: new THREE.MeshStandardMaterial({ color: 0x3a3f46, roughness: 0.5, metalness: 0.3 }),
    glass: new THREE.MeshPhysicalMaterial({
      color: 0x9cc1dc, roughness: 0.04, metalness: 0.1, transparent: true, opacity: 0.32,
      envMapIntensity: 1.6, depthWrite: false, side: THREE.DoubleSide,
    }),
    rail: new THREE.MeshPhysicalMaterial({
      color: 0xcfe3f0, roughness: 0.05, transparent: true, opacity: 0.22, depthWrite: false, side: THREE.DoubleSide,
    }),
    core: new THREE.MeshStandardMaterial({ color: 0x2b323a, roughness: 1 }),
    lobby: new THREE.MeshStandardMaterial({ color: 0xe8d8bd, emissive: 0x6b4c22, emissiveIntensity: 0.55, roughness: 0.9 }),
  };
  const unitBox = new THREE.BoxGeometry(1, 1, 1);
  const h = FLOOR_H - SLAB;

  const boxMesh = (mat, x0, x1, y0, y1, z0, z1, shadow = true) => {
    const m = new THREE.Mesh(unitBox, mat);
    m.scale.set(Math.abs(x1 - x0), Math.abs(y1 - y0), Math.abs(z1 - z0));
    m.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    m.castShadow = shadow;
    m.receiveShadow = true;
    return m;
  };

  // Pier (fin) and glass positions are the same on every floor: [cx, cz, width x, width z]
  const piers = [], panes = [];
  for (const zs of [1, -1]) {
    for (let k = 1; k < 16; k++) piers.push([-BX + k * 1.5, zs * 7.93, 0.22, 0.36]);
    for (let k = 0; k < 16; k++) panes.push([-BX + 0.75 + k * 1.5, zs * 7.9, 1.28, 0.02]);
  }
  for (const xs of [1, -1]) {
    for (let k = 1; k < 10; k++) piers.push([xs * 11.93, -BZ + k * 1.6, 0.36, 0.22]);
    for (let k = 0; k < 10; k++) panes.push([xs * 11.9, -BZ + 0.8 + k * 1.6, 0.02, 1.38]);
    for (const zs of [1, -1]) piers.push([xs * 11.93, zs * 7.93, 0.36, 0.36]);
  }

  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
  const instanced = (list, mat, base, shadow) => {
    const im = new THREE.InstancedMesh(unitBox, mat, list.length);
    list.forEach(([cx, cz, sx, sz], i) => im.setMatrixAt(i, m4.compose(p.set(cx, base + h / 2, cz), q, s.set(sx, h, sz))));
    im.castShadow = shadow;
    im.receiveShadow = true;
    return im;
  };

  // Living-room balconies: [x0, x1, side]
  const balconies = [[-6.5, -2.3, 1], [-1.7, 3.9, 1], [2.3, 6.5, -1], [-3.9, 1.7, -1]];

  const floors = {};
  for (let f = 1; f <= FLOORS; f++) {
    const g = new THREE.Group();
    const base = floorBase(f);
    g.add(boxMesh(M.slab, -BX - 0.3, BX + 0.3, base - SLAB, base, -BZ - 0.3, BZ + 0.3));
    g.add(instanced(piers, M.fin, base, true));
    g.add(instanced(panes, M.glass, base, false));
    const core = boxMesh(f === 1 ? M.lobby : M.core, -IN_X, IN_X, base, base + h, -IN_Z, IN_Z, false);
    g.add(core);
    if (f > 1) {
      for (const [x0, x1, zs] of balconies) {
        g.add(boxMesh(M.slab, x0, x1, base - 0.2, base, zs * 8.3, zs * 9.5));
        g.add(boxMesh(M.rail, x0, x1, base, base + 1.05, zs * 9.46, zs * 9.5, false));
        g.add(boxMesh(M.rail, x0, x0 + 0.04, base, base + 1.05, zs * 8.3, zs * 9.5, false));
        g.add(boxMesh(M.rail, x1 - 0.04, x1, base, base + 1.05, zs * 8.3, zs * 9.5, false));
        g.add(boxMesh(M.fin, x0, x1, base + 1.05, base + 1.09, zs * 9.44, zs * 9.52));
      }
    }
    root.add(g);
    floors[f] = { group: g, core };
  }

  // roof
  const roof = new THREE.Group();
  const top = FLOORS * FLOOR_H;
  roof.add(boxMesh(M.slab, -BX - 0.3, BX + 0.3, top - SLAB, top, -BZ - 0.3, BZ + 0.3));
  roof.add(boxMesh(M.slab, -BX - 0.3, BX + 0.3, top, top + 1.1, BZ + 0.05, BZ + 0.3));
  roof.add(boxMesh(M.slab, -BX - 0.3, BX + 0.3, top, top + 1.1, -BZ - 0.3, -BZ - 0.05));
  roof.add(boxMesh(M.slab, BX + 0.05, BX + 0.3, top, top + 1.1, -BZ, BZ));
  roof.add(boxMesh(M.slab, -BX - 0.3, -BX - 0.05, top, top + 1.1, -BZ, BZ));
  roof.add(boxMesh(M.fin, -7, -1, top, top + 3.2, -4.5, 0.5));
  const panelMat = new THREE.MeshStandardMaterial({ color: 0x1f2c45, roughness: 0.25, metalness: 0.6 });
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 3; j++) {
      const pnl = new THREE.Mesh(unitBox, panelMat);
      pnl.scale.set(1.8, 0.05, 1.1);
      pnl.position.set(2.5 + j * 2.6, top + 0.7, -5.5 + i * 2.8);
      pnl.rotation.x = -0.45;
      pnl.castShadow = true;
      roof.add(pnl);
    }
  }
  root.add(roof);

  // entrance canopy + sign
  root.add(boxMesh(M.fin, -3.6, 3.6, 2.5, 2.9, BZ + 0.1, 11.2));
  for (const x of [-3.2, 3.2]) root.add(boxMesh(M.fin, x - 0.06, x + 0.06, 0, 2.5, 10.9, 11.02));
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(6.8, 0.36), new THREE.MeshBasicMaterial({ map: signTexture('SKYLINE RESIDENCE') }));
  sign.position.set(0, 2.7, 11.205);
  root.add(sign);

  // Clickable / highlightable volume for every apartment
  const units = new Map();
  for (const apt of apartments) {
    const { def } = apt;
    const base = floorBase(apt.floor);
    const xa = def.ox, xb = def.ox + def.sx * (def.W + 0.45);
    const za = def.sz * (CORR - 0.1), zb = def.sz * 8.45;
    const geo = new THREE.BoxGeometry(Math.abs(xb - xa), h - 0.1, Math.abs(zb - za));
    const overlay = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
    overlay.position.set((xa + xb) / 2, base + h / 2, (za + zb) / 2);
    overlay.renderOrder = 10;
    overlay.visible = false;
    overlay.userData.apt = apt;
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geo), new THREE.LineBasicMaterial({ transparent: true, opacity: 0.95 }));
    edges.position.copy(overlay.position);
    edges.visible = false;
    edges.renderOrder = 11;
    root.add(overlay, edges);
    units.set(apt.id, {
      overlay,
      edges,
      center: new THREE.Vector3((xa + xb) / 2, base, (za + zb) / 2),
    });
  }

  return {
    group: root,
    floors,
    roof,
    units,
    pickables: [...units.values()].map((u) => u.overlay),
    // Cut-away: hide everything above `floor` and open up its interior.
    showUpTo(floor) {
      for (const [f, fl] of Object.entries(floors)) {
        fl.group.visible = +f <= floor;
        fl.core.visible = +f !== floor;
      }
      roof.visible = false;
    },
    showAll(openFloor = null) {
      for (const [f, fl] of Object.entries(floors)) {
        fl.group.visible = true;
        fl.core.visible = +f !== openFloor;
      }
      roof.visible = true;
    },
  };
}
