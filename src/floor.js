// One residential floor built from the architect's plan: room floors, walls and columns,
// windows and glazing, balconies, bathroom fittings from the drawing, and furniture.
// Used for the cut-away floor view and, with a ceiling and lights, for the walk-through.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { PLANS, planFrame, towerByKey } from './config.js';
import { distToPolygon, distToSegment, inside, innerRect, interiorPoint } from './geometry.js';
import { tileTexture, woodTexture } from './textures.js';

const SILL = 0.85;
const HEAD = 0.35;

const C = {
  wall: 0xf1eee8, struct: 0xe2ded6, white: 0xf3f1ec, counter: 0x34363a, wood: 0xa27a54, darkwood: 0x5b4331,
  fabric: 0x6b7b8f, cushion: 0x8696aa, linen: 0xf4f1ea, duvet: 0x93a9bf, black: 0x1b1c1f, steel: 0xcfd2d4,
  rug: 0xd8cab2, pot: 0xb8673f, leaf: 0x4e7d3a, ceramic: 0xfafafa, corridor: 0xd9d6d0, balcony: 0xcfc8bd,
};

const shared = {};
function mats() {
  if (shared.wood) return shared;
  const wood = woodTexture(), tile = tileTexture();
  for (const t of [wood, tile]) t.repeat.set(1 / 1.2, 1 / 1.2);
  shared.wood = new THREE.MeshStandardMaterial({ map: wood, roughness: 0.55 });
  shared.tile = new THREE.MeshStandardMaterial({ map: tile, roughness: 0.35 });
  shared.glass = new THREE.MeshPhysicalMaterial({
    color: 0xbcd6e4, roughness: 0.05, transparent: true, opacity: 0.22, depthWrite: false, side: THREE.DoubleSide,
  });
  // indoor surfaces barely reflect the sky (it has green ground underneath)
  shared.ceiling = new THREE.MeshStandardMaterial({ color: 0xfbfaf7, roughness: 1, side: THREE.DoubleSide, envMapIntensity: 0.15 });
  shared.lamp = new THREE.MeshStandardMaterial({ color: 0xfff6e6, emissive: 0xfff1d6, emissiveIntensity: 1.2 });
  shared.byColor = new Map();
  return shared;
}
const colorMat = (c) => {
  const S = mats();
  if (!S.byColor.has(c)) S.byColor.set(c, new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, envMapIntensity: 0.35 }));
  return S.byColor.get(c);
};

const shape = (poly) => new THREE.Shape(poly.map(([x, y]) => new THREE.Vector2(x, y)));
// plan polygon -> vertical prism in local (x, height, -y)
function prism(poly, y0, y1) {
  const g = new THREE.ExtrudeGeometry(shape(poly), { depth: y1 - y0, bevelEnabled: false, curveSegments: 1 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, y0, 0);
  return g;
}
function flat(poly, y) {
  const g = new THREE.ShapeGeometry(shape(poly));
  g.rotateX(-Math.PI / 2);
  g.translate(0, y, 0);
  return g;
}

// Collects boxes per material and merges them into one mesh each.
class Batch {
  constructor() { this.parts = new Map(); }
  add(mat, geo) {
    if (!this.parts.has(mat)) this.parts.set(mat, []);
    this.parts.get(mat).push(geo);
  }
  box(color, x0, y0, x1, y1, z0, z1) {
    const g = new THREE.BoxGeometry(Math.abs(x1 - x0), z1 - z0, Math.abs(y1 - y0));
    g.translate((x0 + x1) / 2, (z0 + z1) / 2, -(y0 + y1) / 2);
    this.add(typeof color === 'number' ? colorMat(color) : color, g);
  }
  cyl(color, x, y, r, z0, z1, seg = 16) {
    const g = new THREE.CylinderGeometry(r, r, z1 - z0, seg);
    g.translate(x, (z0 + z1) / 2, -y);
    this.add(typeof color === 'number' ? colorMat(color) : color, g);
  }
  ball(color, x, y, r, z) {
    const g = new THREE.IcosahedronGeometry(r, 1);
    g.translate(x, z, -y);
    this.add(colorMat(color), g);
  }
  build(group, own, { cast = true } = {}) {
    for (const [mat, geos] of this.parts) {
      const g = mergeGeometries(geos.map((x) => (x.index ? x.toNonIndexed() : x)), false);
      geos.forEach((x) => x.dispose());
      own.push(g);
      const m = new THREE.Mesh(g, mat);
      m.castShadow = cast && !mat.transparent;
      m.receiveShadow = true;
      group.add(m);
    }
  }
}

// ---------- furniture, placed in the largest free rectangle of each room ----------

function furnish(B, room, H) {
  const r = innerRect(room.poly, 0.12);
  const w = r.x1 - r.x0, d = r.y1 - r.y0;
  if (w < 0.9 || d < 0.9) return;
  const alongX = w >= d; // long axis
  const L = Math.max(w, d), S = Math.min(w, d);
  // local rect helpers: u along the long axis, v across, both from the rect's low corner
  const box = (color, u0, v0, u1, v1, z0, z1) =>
    alongX ? B.box(color, r.x0 + u0, r.y0 + v0, r.x0 + u1, r.y0 + v1, z0, z1) : B.box(color, r.x0 + v0, r.y0 + u0, r.x0 + v1, r.y0 + u1, z0, z1);
  const cyl = (color, u, v, rad, z0, z1) => (alongX ? B.cyl(color, r.x0 + u, r.y0 + v, rad, z0, z1) : B.cyl(color, r.x0 + v, r.y0 + u, rad, z0, z1));
  const ball = (color, u, v, rad, z) => (alongX ? B.ball(color, r.x0 + u, r.y0 + v, rad, z) : B.ball(color, r.x0 + v, r.y0 + u, rad, z));
  const plant = (u, v) => {
    cyl(C.pot, u, v, 0.2, 0, 0.42);
    ball(C.leaf, u, v, 0.38, 0.88);
  };

  switch (room.kind) {
    case 'bedroom': {
      const bw = S >= 2.4 ? 1.6 : 0.95, bl = 2.05;
      if (L < bl + 0.6) break;
      const v0 = (S - bw) / 2;
      box(C.darkwood, 0, v0 - 0.04, bl, v0 + bw + 0.04, 0, 0.3);
      box(C.linen, 0.06, v0, bl - 0.04, v0 + bw, 0.3, 0.5);
      box(C.duvet, 0.7, v0 - 0.02, bl - 0.02, v0 + bw + 0.02, 0.5, 0.56);
      box(C.darkwood, 0, v0 - 0.04, 0.08, v0 + bw + 0.04, 0.3, 1.1);
      box(C.white, 0.15, v0 + 0.1, 0.5, v0 + bw / 2 - 0.05, 0.5, 0.63);
      if (bw > 1) box(C.white, 0.15, v0 + bw / 2 + 0.05, 0.5, v0 + bw - 0.1, 0.5, 0.63);
      box(C.rug, 1.0, v0 - 0.5, bl + 0.4 > L ? L : bl + 0.4, v0 + bw + 0.5, 0, 0.012);
      for (const vv of [v0 - 0.5, v0 + bw + 0.05]) {
        if (vv < 0 || vv + 0.45 > S) continue;
        box(C.wood, 0, vv, 0.42, vv + 0.45, 0, 0.5);
        cyl(0xfff1d0, 0.2, vv + 0.22, 0.09, 0.5, 0.75);
      }
      if (L - bl > 1.3) box(C.white, L - 0.6, 0.1, L, Math.min(S - 0.1, 2.4), 0, 2.2); // wardrobe
      break;
    }
    case 'living': {
      if (S < 2.2) break;
      const sl = Math.min(2.4, L - 1.0), u0 = (L - sl) / 2;
      box(C.fabric, u0, 0, u0 + sl, 0.9, 0, 0.42);
      box(C.fabric, u0, 0, u0 + sl, 0.2, 0.42, 0.85);
      box(C.fabric, u0, 0, u0 + 0.2, 0.9, 0.42, 0.62);
      box(C.fabric, u0 + sl - 0.2, 0, u0 + sl, 0.9, 0.42, 0.62);
      box(C.cushion, u0 + 0.22, 0.22, u0 + sl / 2 - 0.02, 0.85, 0.42, 0.52);
      box(C.cushion, u0 + sl / 2 + 0.02, 0.22, u0 + sl - 0.22, 0.85, 0.42, 0.52);
      box(C.rug, u0 - 0.2, 0.7, u0 + sl + 0.2, Math.min(S - 0.6, 3.0), 0, 0.012);
      const tv = Math.min(S - 0.45, 3.2);
      box(C.wood, L / 2 - 0.3, 1.35, L / 2 + 0.3, 2.0 > tv - 0.5 ? tv - 0.5 : 2.0, 0.36, 0.4);
      if (S >= 3.0) {
        box(0x2c2c2e, L / 2 - 0.8, S - 0.45, L / 2 + 0.8, S, 0, 0.45);
        box(C.black, L / 2 - 0.65, S - 0.08, L / 2 + 0.65, S - 0.04, 0.85, 1.6);
      }
      plant(0.3, S - 0.3);
      if (L > 4.5) plant(L - 0.3, 0.3);
      break;
    }
    case 'kitchen': {
      const kl = Math.min(L - 0.2, 3.6);
      box(C.white, 0, 0, kl, 0.62, 0, 0.86);
      box(C.counter, 0, 0, kl, 0.65, 0.86, 0.9);
      box(C.white, 0, 0, kl, 0.35, 1.45, 2.2);
      box(C.black, kl * 0.55, 0.08, kl * 0.55 + 0.6, 0.55, 0.9, 0.905);
      if (L - kl > 0.7) box(C.steel, kl + 0.05, 0, kl + 0.75, 0.68, 0, 2.0);
      if (S >= 2.6) {
        const cu = L / 2, cv = 0.62 + (S - 0.62) / 2;
        box(C.wood, cu - 0.75, cv - 0.45, cu + 0.75, cv + 0.45, 0.72, 0.76);
        for (const [a, b] of [[-0.68, -0.38], [0.68, -0.38], [-0.68, 0.38], [0.68, 0.38]]) box(C.darkwood, cu + a - 0.03, cv + b - 0.03, cu + a + 0.03, cv + b + 0.03, 0, 0.72);
        for (const du of [-0.4, 0.4]) {
          for (const sgn of [-1, 1]) {
            const vv = cv + sgn * 0.72;
            box(C.darkwood, cu + du - 0.2, vv - 0.2, cu + du + 0.2, vv + 0.2, 0.43, 0.47);
            box(C.darkwood, cu + du - 0.2, vv + sgn * 0.17, cu + du + 0.2, vv + sgn * 0.2, 0.47, 0.9);
          }
        }
        cyl(C.black, cu, cv, 0.006, 1.8, 2.8);
        cyl(0xfff1d0, cu, cv, 0.22, 1.62, 1.8);
      }
      break;
    }
    case 'hall':
      if (L >= 2.2 && S >= 1.3) box(C.white, 0.2, 0, Math.min(L - 0.8, 2.2), 0.55, 0, 2.2);
      if (S >= 1.6) plant(L - 0.3, S - 0.3);
      break;
    case 'storage':
      box(C.white, 0, 0, L, Math.min(0.45, S / 2), 0, 2.1);
      break;
    default:
      break;
  }
}

function balconyFurniture(B, poly) {
  const [x, y] = interiorPoint(poly);
  if (distToPolygon(poly, x, y) > 0) return;
  B.cyl(C.white, x, y, 0.3, 0.7, 0.73);
  B.cyl(C.steel, x, y, 0.03, 0, 0.7);
  for (const dx of [-0.6, 0.6]) {
    if (!inside(poly, x + dx, y)) continue;
    B.box(C.darkwood, x + dx - 0.22, y - 0.22, x + dx + 0.22, y + 0.22, 0.42, 0.46);
    B.box(C.darkwood, x + dx + (dx > 0 ? 0.18 : -0.22), y - 0.22, x + dx + (dx > 0 ? 0.22 : -0.18), y + 0.22, 0.46, 0.85);
  }
}

// ---------- the floor ----------

/**
 * @param towerKey 'V' | 'B'
 * @param floor floor number
 * @param apts apartments of this floor (data.js)
 * @param walk the apartment to walk around in (adds ceiling and lights), or null
 */
export function buildFloor(towerKey, floor, apts, walk = null) {
  const S = mats();
  const tower = towerByKey[towerKey];
  const fl = tower.floors.find((f) => f.floor === floor);
  const plan = PLANS[fl.plan];
  const frame = planFrame(tower);
  const baseY = fl.z + tower.slab;
  const H = fl.h - 0.5; // clear height

  const group = new THREE.Group();
  group.position.set(frame.position.x, baseY, frame.position.z);
  group.rotation.y = frame.rotY;
  const own = [];
  const floorMeshes = [];
  const B = new Batch();

  // room floors (wood, tiles in wet rooms), balconies
  for (const apt of apts) {
    for (const room of apt.data.rooms) {
      const g = flat(room.poly, 0.006);
      own.push(g);
      const m = new THREE.Mesh(g, ['bath', 'storage', 'loggia'].includes(room.kind) ? S.tile : S.wood);
      m.receiveShadow = true;
      m.userData = { apt, room };
      group.add(m);
      floorMeshes.push(m);
    }
    for (const b of apt.data.balconies) {
      B.add(colorMat(C.balcony), flat(b.poly, 0.012));
      balconyFurniture(B, b.poly);
    }
    for (const fx of apt.data.fixtures) B.add(colorMat(C.ceramic), prism(fx, 0, 0.5));
    for (const room of apt.data.rooms) furnish(B, room, H);
  }
  for (const c of plan.common ?? []) B.add(colorMat(C.corridor), flat(c, 0.004));

  // walls and structure, windows (sill, glass, head) and floor-to-ceiling glazing
  for (const w of plan.walls) B.add(colorMat(C.wall), prism(w, 0, H));
  for (const w of plan.struct) B.add(colorMat(C.struct), prism(w, 0, H));
  for (const w of plan.windows) {
    B.add(colorMat(C.wall), prism(w, 0, SILL));
    B.add(S.glass, prism(w, SILL, H - HEAD));
    B.add(colorMat(C.wall), prism(w, H - HEAD, H));
  }
  for (const w of plan.glazing) B.add(S.glass, prism(w, 0, H));
  B.build(group, own);

  // walls and furniture to bump into, in plan coordinates
  const segments = [];
  for (const list of [plan.walls, plan.struct, plan.windows, plan.glazing]) {
    for (const p of list) for (let i = 0, j = p.length - 1; i < p.length; j = i++) segments.push([p[j][0], p[j][1], p[i][0], p[i][1]]);
  }

  let spawn = null, outline = null;
  if (walk) {
    outline = walk.data.outline;
    const ceil = flat(plan.enclosure, H);
    own.push(ceil);
    const c = new THREE.Mesh(ceil, S.ceiling);
    c.receiveShadow = true;
    group.add(c);
    const rooms = [...walk.data.rooms].sort((a, b) => b.area - a.area);
    // a few ceiling lights in the main rooms (each point light costs every pixel on screen)
    for (const room of rooms.filter((r) => r.area > 9 && r.kind !== 'loggia').slice(0, 3)) {
      const [x, y] = interiorPoint(room.poly);
      const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.03, 20), S.lamp);
      own.push(disc.geometry);
      disc.position.set(x, H - 0.02, -y);
      group.add(disc);
      const light = new THREE.PointLight(0xffe4c0, room.area > 15 ? 8 : 5, 10, 2);
      light.position.set(x, H - 0.35, -y);
      group.add(light);
    }
    // start in the hall, looking into the largest room
    // the drawing's entrance hall ("Даҳлез"), else any hall, else the smallest real room
    const hall = walk.data.rooms.find((r) => r.tj === 'Даҳлез') ?? walk.data.rooms.find((r) => r.kind === 'hall') ?? rooms[rooms.length - 1];
    const [sx, sy] = interiorPoint(hall.poly);
    const [tx, ty] = interiorPoint(rooms[0].poly);
    // look the way with the widest clear view (open over the whole field of view, not through a
    // doorway's slot), leaning a little towards the largest room
    const toRoom = Math.atan2(ty - sy, tx - sx);
    const N = 72, dist = [];
    for (let k = 0; k < N; k++) {
      const a = (k / N) * Math.PI * 2, dx = Math.cos(a), dy = Math.sin(a);
      let d = 10;
      for (const [ax, ay, bx, by] of segments) {
        // ray (sx, sy) + t (dx, dy) against segment a-b
        const ex = bx - ax, ey = by - ay, den = dx * ey - dy * ex;
        if (Math.abs(den) < 1e-9) continue;
        const t = ((ax - sx) * ey - (ay - sy) * ex) / den, u = ((ax - sx) * dy - (ay - sy) * dx) / den;
        if (t > 0 && u >= 0 && u <= 1) d = Math.min(d, t);
      }
      dist.push(d);
    }
    let best = toRoom, bestScore = -Infinity;
    for (let k = 0; k < N; k++) {
      let open = 0;
      for (let j = -5; j <= 5; j++) open += Math.min(dist[(k + j + N) % N], 8); // +-25 degrees
      const a = (k / N) * Math.PI * 2;
      const score = open * (1 + 0.2 * Math.cos(a - toRoom));
      if (score > bestScore) [bestScore, best] = [score, a];
    }
    const s0 = frame.toScene(sx, sy), t0 = frame.toScene(sx + Math.cos(best), sy + Math.sin(best));
    spawn = { x: s0.x, z: s0.z, yaw: Math.atan2(-(t0.x - s0.x), -(t0.z - s0.z)) };
  }

  const RADIUS = 0.25;
  return {
    apt: walk,
    group,
    floorMeshes,
    baseY,
    spawn,
    frame,
    plan,
    // Move from (x, z) to (nx, nz) in the scene without walking through walls or out of the flat.
    move(x, z, nx, nz) {
      let p = frame.toPlan(nx, nz);
      let px = p.x, py = p.y;
      for (let iter = 0; iter < 3; iter++) {
        for (const [ax, ay, bx, by] of segments) {
          if (Math.min(ax, bx) - RADIUS > px || Math.max(ax, bx) + RADIUS < px) continue;
          if (Math.min(ay, by) - RADIUS > py || Math.max(ay, by) + RADIUS < py) continue;
          const { d, px: qx, py: qy } = distToSegment(px, py, ax, ay, bx, by);
          if (d < RADIUS && d > 1e-6) {
            px = qx + ((px - qx) / d) * RADIUS;
            py = qy + ((py - qy) / d) * RADIUS;
          }
        }
      }
      if (outline && !inside(outline, px, py)) return { x, z };
      const s = frame.toScene(px, py);
      return { x: s.x, z: s.z };
    },
    dispose() {
      group.removeFromParent();
      own.forEach((g) => g.dispose());
    },
  };
}

