// The ground-level playground in front of the podium (between the car park and block B), fitted out
// in the viewer: the model has only its rubber surfaces, three bare gazebos and a lattice frame
// (Ground_playground, Site_ground_13 and the gazebo roofs in Site_ground_9), which are taken out.
//
// Two zones on the model's rubber: the blue one for older children (a pair of play towers with
// roofs, slides, a rope bridge, a climbing wall and a fireman's pole; swings with a nest swing;
// a roundabout; painted games) and the orange one for small children (a sandpit under a shade
// sail, a play house with a short slide, spring riders, a see-saw). A low fence with two gates
// runs round both, with benches for the parents, bins and a kerb at the edge of the rubber.
//
// Positions are scene metres (x east, z south) taken from the model's surfaces; everything is
// built with the interiors' kit (src/interior/kit.js), so it is a few dozen merged meshes.
import * as THREE from 'three';
import { Kit } from './interior/kit.js';
import { veneer } from './interior/textures.js';

const Y0 = 0.1; // the rubber's level
// outlines of the two rubber zones (scene x, z), from Site_ground_8 and _9
const BLUE = [[-2.99, 17.46], [11.11, 20.75], [11.48, 35.03], [9.65, 43.82], [5.44, 46.75], [-3.9, 41.08]];
const ORANGE = [[-24.59, 17.27], [-2.99, 17.46], [-3.9, 38.88]];
// the fence runs round both
const OUTER = [[-24.59, 17.27], [-2.99, 17.46], [11.11, 20.75], [11.48, 35.03], [9.65, 43.82], [5.44, 46.75], [-3.9, 41.08], [-3.9, 38.88]];

// scene (x, z) -> the kit's plan coordinates (x, -z)
const P = (x, z) => [x, -z];

function canvasTex(w, h, draw, repeat = false) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

function seeded(seed) {
  return () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
}

function materials() {
  const std = (o, boxUV) => {
    const m = new THREE.MeshStandardMaterial(o);
    if (boxUV) m.userData.boxUV = boxUV;
    return m;
  };
  const larch = veneer('oak');
  const sand = canvasTex(256, 256, (g, w, h) => {
    const r = seeded(9);
    g.fillStyle = '#d8c39a';
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 9000; i++) {
      g.globalAlpha = 0.35;
      g.fillStyle = ['#e6d4ad', '#c4ad82', '#b89e74', '#efe2c4'][Math.floor(r() * 4)];
      g.fillRect(r() * w, r() * h, 1 + r() * 1.5, 1 + r() * 1.5);
    }
    // raked and played-in: soft darker swirls
    g.globalAlpha = 0.12;
    g.strokeStyle = '#8f7a55';
    g.lineWidth = 6;
    for (let i = 0; i < 7; i++) {
      g.beginPath();
      g.arc(r() * w, r() * h, 20 + r() * 50, r() * 6, r() * 6 + 2);
      g.stroke();
    }
  }, true);
  sand.repeat.set(1 / 1.5, 1 / 1.5);
  // painted games on the rubber: hopscotch, a target circle and a snail track
  const games = canvasTex(512, 512, (g, w) => {
    g.clearRect(0, 0, w, w);
    g.strokeStyle = 'rgba(250, 248, 240, 0.92)';
    g.fillStyle = 'rgba(250, 248, 240, 0.92)';
    g.lineWidth = 7;
    const s = 56, x0 = 60, y0 = 40;
    const cells = [[0, 0], [0, 1], [-0.5, 2], [0.5, 2], [0, 3], [-0.5, 4], [0.5, 4], [0, 5]];
    g.font = 'bold 34px system-ui, sans-serif';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    cells.forEach(([cx, cy], i) => {
      g.strokeRect(x0 + cx * s, y0 + cy * s, s, s);
      g.fillText(String(i + 1), x0 + cx * s + s / 2, y0 + cy * s + s / 2 + 2);
    });
    g.beginPath();
    g.arc(x0 + s / 2, y0 + 6.5 * s, s * 0.8, Math.PI, 0);
    g.stroke();
    // target circles
    for (const r of [40, 80, 120]) {
      g.beginPath();
      g.arc(360, 150, r, 0, Math.PI * 2);
      g.stroke();
    }
    // a snail spiral
    g.beginPath();
    for (let a = 0; a < Math.PI * 7; a += 0.1) {
      const r = 8 + a * 9;
      const px = 360 + Math.cos(a) * r, py = 390 + Math.sin(a) * r;
      a ? g.lineTo(px, py) : g.moveTo(px, py);
    }
    g.stroke();
  });
  const sail = canvasTex(64, 64, (g, w) => {
    g.fillStyle = '#f0ece2';
    g.fillRect(0, 0, w, w);
    g.globalAlpha = 0.15;
    for (let y = 0; y < w; y += 2) {
      g.fillStyle = y % 4 ? '#ffffff' : '#c9c2b2';
      g.fillRect(0, y, w, 1);
    }
  }, true);
  sail.repeat.set(1 / 0.4, 1 / 0.4);
  return {
    post: std({ color: 0x3f7f3a, roughness: 0.45, metalness: 0.35 }), // powder-coated green
    steel: std({ color: 0xbfc4c7, roughness: 0.3, metalness: 0.9 }),
    stainless: std({ color: 0xe1e4e6, roughness: 0.12, metalness: 1, envMapIntensity: 1.2 }),
    yellow: std({ color: 0xf0bb2b, roughness: 0.4 }),
    orange: std({ color: 0xe46f2b, roughness: 0.4 }),
    red: std({ color: 0xc83a30, roughness: 0.45 }),
    blue: std({ color: 0x2f6fb7, roughness: 0.4 }),
    teal: std({ color: 0x2c9a92, roughness: 0.4 }),
    larch: std({ map: larch.map, roughness: 0.8, color: 0xe6d2b8 }, larch.metres),
    rope: std({ color: 0x3a3f3a, roughness: 0.9 }),
    rubberSeat: std({ color: 0x232527, roughness: 0.8 }),
    sand: std({ map: sand, roughness: 1 }),
    games: std({ map: games, transparent: true, depthWrite: false, roughness: 0.9, polygonOffset: true, polygonOffsetFactor: -2 }),
    sail: std({ map: sail, roughness: 0.95, side: THREE.DoubleSide }, 0.4),
    concrete: std({ color: 0xc9c5bc, roughness: 0.9 }),
    fence: std({ color: 0x2f5f35, roughness: 0.5, metalness: 0.3 }),
    bench: std({ map: larch.map, roughness: 0.7, color: 0xb9895f }, larch.metres),
    bin: std({ color: 0x3b4a3f, roughness: 0.6, metalness: 0.2 }),
    sign: std({ color: 0xf2efe6, roughness: 0.6 }),
  };
}

// ---------- pieces (each in its own frame: x right, y up, z front; origin on the ground) ----------

/** a square play tower: four posts, a deck at height h, a pyramid roof, panels on chosen sides */
function tower(k, M, h, roofMat, panels) {
  const s = 1.3, H = h + 1.25;
  for (const x of [-s / 2, s / 2]) for (const z of [-s / 2, s / 2]) {
    k.cyl(M.post, x, 0, z, 0.055, H, 12);
    k.cyl(M.post, x, H - 0.02, z, 0.07, H + 0.03, 12);
  }
  k.box(M.larch, -s / 2, h - 0.05, -s / 2, s / 2, h, s / 2);
  // roof: a four-sided pyramid with a ball on top
  const cone = new THREE.ConeGeometry(s * 0.95, 0.9, 4, 1);
  cone.rotateY(Math.PI / 4);
  cone.translate(0, H + 0.45, 0);
  k.add(roofMat, cone);
  k.sphere(M.yellow, 0, H + 0.95, 0, 0.09);
  // guard panels and rails on the closed sides
  for (const side of panels) {
    const [x0, z0, x1, z1] = { n: [-s / 2, -s / 2, s / 2, -s / 2 + 0.03], s: [-s / 2, s / 2 - 0.03, s / 2, s / 2], w: [-s / 2, -s / 2, -s / 2 + 0.03, s / 2], e: [s / 2 - 0.03, -s / 2, s / 2, s / 2] }[side];
    k.box(side === 'n' || side === 's' ? M.blue : M.orange, x0, h + 0.12, z0, x1, h + 0.8, z1);
  }
}

/** a slide from the deck edge at height h, going out along +z, w wide */
function slide(k, M, h, len, mat, w = 0.55, wavy = true) {
  const N = 28, pos = [], idx = [], uv = [];
  const pt = (t) => {
    // a run-out at the bottom, a gentle wave on the way down
    const z = t * len;
    const ease = t < 0.85 ? 1 - Math.pow(t / 0.85, 1.15) : 0;
    const y = 0.3 + (h - 0.3) * ease + (wavy && t < 0.8 ? Math.sin(t * Math.PI * 3) * 0.08 * (1 - t) : 0);
    return [z, y];
  };
  // a trough: floor and two side walls, made as one strip across
  const prof = [[-w / 2 - 0.04, 0.22], [-w / 2, 0.02], [-w / 2 + 0.08, 0], [w / 2 - 0.08, 0], [w / 2, 0.02], [w / 2 + 0.04, 0.22]];
  for (let i = 0; i <= N; i++) {
    const [z, y] = pt(i / N);
    for (const [px, py] of prof) {
      pos.push(px, y + py, z);
      uv.push(px, z);
    }
  }
  const P = prof.length;
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < P - 1; j++) {
      const a = i * P + j, b = a + 1, c = a + P, d = c + 1;
      idx.push(a, c, b, b, c, d);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  // both sides visible: add the reverse faces
  const back = g.clone();
  const bi = back.index.array;
  for (let i = 0; i < bi.length; i += 3) [bi[i + 1], bi[i + 2]] = [bi[i + 2], bi[i + 1]];
  back.computeVertexNormals();
  k.add(mat, g);
  k.add(mat, back);
  // legs under the run-out and the middle
  const [zm, ym] = pt(0.5);
  for (const s of [-1, 1]) {
    k.cyl(M.post, s * (w / 2 - 0.05), 0, zm, 0.035, ym, 10);
    k.cyl(M.post, s * (w / 2 - 0.05), 0, len - 0.25, 0.035, 0.3, 10);
  }
  // hand grips at the top
  for (const s of [-1, 1]) k.tube(M.post, [[s * (w / 2 + 0.03), h + 0.05, -0.05], [s * (w / 2 + 0.03), h + 0.7, 0.0], [s * (w / 2 + 0.03), h + 0.6, 0.25], [s * (w / 2 + 0.03), h + 0.25, 0.35]], 0.025, 16);
}

/** a rope-and-plank bridge between two decks at height h, from z = 0 to z = len */
function bridge(k, M, h, len, w = 0.75) {
  const n = Math.round(len / 0.16), sag = 0.12;
  const y = (t) => h - 0.04 - Math.sin(t * Math.PI) * sag;
  for (let i = 0; i < n; i++) {
    const t = (i + 0.5) / n;
    k.box(M.larch, -w / 2, y(t) - 0.03, t * len - 0.06, w / 2, y(t), t * len + 0.06);
  }
  for (const s of [-1, 1]) {
    const pts = [], low = [];
    for (let i = 0; i <= 8; i++) {
      const t = i / 8;
      pts.push([s * w / 2, y(t) + 0.75 + Math.sin(t * Math.PI) * 0.05, t * len]);
      low.push([s * w / 2, y(t) + 0.02, t * len]);
    }
    k.tube(M.rope, pts, 0.018, 24);
    k.tube(M.rope, low, 0.014, 24);
    // net between the rails
    for (let i = 1; i < 8; i++) {
      const t = i / 8;
      k.cyl(M.rope, s * w / 2, y(t), t * len, 0.008, y(t) + 0.75, 4);
    }
  }
}

/** a sloping climbing wall: foot at the origin, leaning forward (+z) up to a deck at height h */
function climbingWall(k, M, h, w = 1.2, lean = 0.55) {
  const L = Math.hypot(h, lean), a = Math.atan2(lean, h);
  const g = new THREE.BoxGeometry(w, L, 0.05);
  g.translate(0, L / 2, 0);
  g.rotateX(a);
  k.add(M.teal, g);
  // holds on the climbing face (the underside of the lean faces back, -z)
  const R = seeded(31), cols = [M.yellow, M.red, M.orange, M.blue];
  for (let i = 0; i < 14; i++) {
    const t = 0.08 + R() * 0.84, x = (R() - 0.5) * (w - 0.2);
    k.sphere(cols[i % 4], x, Math.cos(a) * t * L - 0.03, Math.sin(a) * t * L - 0.04, 0.05, 1.2, 0.8, 0.7, 1);
  }
}

function swings(k, M, w = 5.4, h = 2.4) {
  // A-frames at both ends, a beam, two flat seats and a nest swing
  for (const x of [-w / 2, w / 2]) {
    for (const s of [-1, 1]) k.tube(M.post, [[x, 0, s * 1.1], [x, h / 2, s * 0.55], [x, h, 0]], 0.06, 8);
    k.cyl(M.post, x, h - 0.05, 0, 0.09, h + 0.1, 12);
  }
  const beam = new THREE.CylinderGeometry(0.065, 0.065, w, 16);
  beam.rotateZ(Math.PI / 2);
  beam.translate(0, h + 0.02, 0);
  k.add(M.post, beam);
  const seatY = 0.45;
  for (const x of [-w / 2 + 0.85, -w / 2 + 1.75]) {
    for (const s of [-1, 1]) k.cyl(M.steel, x + s * 0.2, seatY + 0.02, 0, 0.008, h, 4);
    k.rbox(M.rubberSeat, x, seatY, 0, 0.45, 0.04, 0.17, 0.015, 1);
  }
  // nest swing: a ring with a net, on four chains
  const nx = w / 2 - 1.35, ny = 0.55;
  const ring = new THREE.TorusGeometry(0.5, 0.045, 10, 40);
  ring.rotateX(Math.PI / 2);
  ring.translate(nx, ny, 0);
  k.add(M.orange, ring);
  const net = new THREE.CircleGeometry(0.48, 32);
  net.rotateX(-Math.PI / 2);
  net.translate(nx, ny - 0.03, 0);
  k.add(M.rope, net);
  for (const [dx, dz] of [[0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]]) k.tube(M.steel, [[nx + dx, ny, dz], [nx + dx * 0.4, h, dz * 0.4]], 0.008, 4);
}

function roundabout(k, M) {
  k.cyl(M.steel, 0, 0, 0, 0.12, 0.25, 16);
  k.cyl(M.yellow, 0, 0.18, 0, 1.0, 0.24, 40);
  k.cyl(M.blue, 0, 0.24, 0, 0.98, 0.26, 40);
  k.cyl(M.steel, 0, 0.24, 0, 0.05, 1.0, 12);
  const ring = new THREE.TorusGeometry(0.55, 0.025, 8, 40);
  ring.rotateX(Math.PI / 2);
  ring.translate(0, 0.95, 0);
  k.add(M.red, ring);
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI * 2, x = Math.cos(a), z = Math.sin(a);
    k.tube(M.red, [[x * 0.05, 0.95, z * 0.05], [x * 0.55, 0.95, z * 0.55], [x * 0.85, 0.7, z * 0.85], [x * 0.85, 0.26, z * 0.85]], 0.022, 12);
  }
}

function springRider(k, M, body) {
  // a steel spring on a base, a body on top with handles and foot rests
  const pts = [];
  for (let t = 0; t <= 1; t += 0.02) pts.push([Math.cos(t * Math.PI * 12) * 0.11, 0.05 + t * 0.4, Math.sin(t * Math.PI * 12) * 0.11]);
  k.tube(M.stainless, pts, 0.018, 120);
  k.cyl(M.steel, 0, 0, 0, 0.18, 0.05, 20);
  k.rbox(body, 0, 0.62, 0, 0.26, 0.26, 0.7, 0.1);
  k.sphere(body, 0, 0.88, 0.32, 0.17, 1, 1, 1.1);
  k.sphere(M.rubberSeat, 0.07, 0.93, 0.47, 0.025, 1, 1, 1, 1);
  k.sphere(M.rubberSeat, -0.07, 0.93, 0.47, 0.025, 1, 1, 1, 1);
  const bar = new THREE.CylinderGeometry(0.018, 0.018, 0.4, 8);
  bar.rotateZ(Math.PI / 2);
  bar.translate(0, 0.86, 0.18);
  k.add(M.yellow, bar);
  k.rbox(M.yellow, 0, 0.77, -0.05, 0.3, 0.05, 0.28, 0.02, 1);
}

function seesaw(k, M) {
  k.box(M.post, -0.12, 0, -0.15, 0.12, 0.45, 0.15);
  const beam = new THREE.BoxGeometry(3.0, 0.08, 0.22);
  beam.rotateZ(0.12);
  beam.translate(0, 0.5, 0);
  k.add(M.orange, beam);
  for (const s of [-1, 1]) {
    const x = s * 1.3, y = 0.5 + s * 0.16;
    k.rbox(M.rubberSeat, x, y + 0.06, 0, 0.32, 0.05, 0.3, 0.015, 1);
    k.tube(M.yellow, [[x - s * 0.22, y + 0.04, -0.12], [x - s * 0.25, y + 0.4, -0.1], [x - s * 0.25, y + 0.4, 0.1], [x - s * 0.22, y + 0.04, 0.12]], 0.02, 12);
    k.cyl(M.rubberSeat, s * 1.35, 0, 0, 0.12, 0.12, 16);
  }
}

function sandpit(k, M, w) {
  const t = 0.25, h = 0.35;
  k.box(M.larch, -w / 2, 0, -w / 2, w / 2, h, -w / 2 + t);
  k.box(M.larch, -w / 2, 0, w / 2 - t, w / 2, h, w / 2);
  k.box(M.larch, -w / 2, 0, -w / 2 + t, -w / 2 + t, h, w / 2 - t);
  k.box(M.larch, w / 2 - t, 0, -w / 2 + t, w / 2, h, w / 2 - t);
  k.box(M.sand, -w / 2 + t, 0, -w / 2 + t, w / 2 - t, 0.22, w / 2 - t);
  // a sand mound, bucket and spade, a castle
  k.sphere(M.sand, 0.5, 0.18, 0.3, 0.55, 1, 0.25, 1, 2);
  k.lathe(M.red, [[0, 0], [0.07, 0], [0.09, 0.14], [0.085, 0.14], [0.065, 0.01], [0, 0.01]], -0.6, 0.22, -0.4, 16);
  k.box(M.blue, -0.3, 0.22, 0.6, -0.12, 0.24, 0.66);
  k.box(M.sand, 0.9, 0.22, -0.7, 1.1, 0.34, -0.5);
  k.cyl(M.sand, 1.0, 0.34, -0.6, 0.06, 0.42, 8, 0.03);
}

function playHouse(k, M) {
  const w = 1.6, d = 1.4, h = 1.3;
  for (const x of [-w / 2, w / 2]) for (const z of [-d / 2, d / 2]) k.box(M.larch, x - 0.05, 0, z - 0.05, x + 0.05, h, z + 0.05);
  k.box(M.larch, -w / 2, 0, -d / 2, w / 2, 0.06, d / 2);
  // walls: back full, sides with a window, front with a counter (a shop window)
  k.box(M.larch, -w / 2, 0, -d / 2, w / 2, h, -d / 2 + 0.03);
  for (const s of [-1, 1]) {
    k.box(M.larch, s * w / 2 - 0.015, 0, -d / 2, s * w / 2 + 0.015, 0.6, d / 2);
    k.box(M.larch, s * w / 2 - 0.015, 1.05, -d / 2, s * w / 2 + 0.015, h, d / 2);
  }
  k.box(M.larch, -w / 2, 0, d / 2 - 0.03, w / 2, 0.7, d / 2);
  k.box(M.yellow, -w / 2 - 0.02, 0.7, d / 2 - 0.05, w / 2 + 0.02, 0.74, d / 2 + 0.15);
  // gable roof in red
  for (const s of [-1, 1]) {
    const r = new THREE.BoxGeometry(w + 0.3, 0.04, d * 0.62);
    r.rotateX(s * 0.62);
    r.translate(0, h + 0.27, s * d * 0.25);
    k.add(M.red, r);
  }
  // a short slide off one side
  k.save().offset(w / 2 + 0.02, 0, Math.PI / 2);
  slide(k, M, 0.6, 1.3, M.yellow, 0.45, false);
  k.restore();
}

function shadeSail(k, M, corners) {
  // corners: three [x, z, postHeight] in the frame; the sail sags a little in the middle
  const pts = corners.map(([x, z, hh]) => new THREE.Vector3(x, hh, z));
  for (const [x, z, hh] of corners) {
    k.cyl(M.steel, x, 0, z, 0.06, hh + 0.15, 12);
    k.sphere(M.steel, x, hh + 0.17, z, 0.07, 1, 1, 1, 1);
  }
  const n = 8, pos = [], idx = [], uv = [];
  const c = pts[0].clone().add(pts[1]).add(pts[2]).multiplyScalar(1 / 3);
  const rows = [];
  for (let i = 0; i <= n; i++) {
    const row = [];
    for (let j = 0; j <= n - i; j++) {
      const a = i / n, b = j / n, cc = 1 - a - b;
      const p = pts[0].clone().multiplyScalar(cc).add(pts[1].clone().multiplyScalar(a)).add(pts[2].clone().multiplyScalar(b));
      p.y -= 0.35 * 27 * a * b * cc * 0.6; // sag, largest in the middle
      p.lerp(c, 0.06); // pulled in a little from the posts
      row.push(pos.length / 3);
      pos.push(p.x, p.y, p.z);
      uv.push(p.x, p.z);
    }
    rows.push(row);
  }
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n - i; j++) {
      idx.push(rows[i][j], rows[i + 1][j], rows[i][j + 1]);
      if (j < n - i - 1) idx.push(rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  k.add(M.sail, g);
  // tension wires to the post tops
  for (const p of pts) k.tube(M.steel, [[p.x, p.y, p.z], [p.x, p.y + 0.12, p.z]], 0.006, 2);
}

function bench(k, M) {
  for (const x of [-0.7, 0.7]) {
    k.box(M.concrete, x - 0.05, 0, 0.05, x + 0.05, 0.42, 0.5);
    k.box(M.concrete, x - 0.05, 0.42, 0.02, x + 0.05, 0.85, 0.1);
  }
  for (let i = 0; i < 4; i++) k.box(M.bench, -0.95, 0.42, 0.08 + i * 0.11, 0.95, 0.46, 0.17 + i * 0.11);
  for (let i = 0; i < 3; i++) k.box(M.bench, -0.95, 0.52 + i * 0.12, 0.06, 0.95, 0.61 + i * 0.12, 0.1);
}

function bin(k, M) {
  k.cyl(M.bin, 0, 0, 0, 0.22, 0.85, 20);
  k.cyl(M.steel, 0, 0.85, 0, 0.23, 0.9, 20, 0.18);
}

// ---------- layout ----------

/** fence with posts every 2 m and vertical bars, along a closed outline; `gates`: [edge index, t] */
function fence(k, M, outline, gates) {
  const h = 1.0, inset = 0.3;
  // inward offset of each edge (the outline runs clockwise in scene x/z = anticlockwise in plan)
  const plan = outline.map(([x, z]) => P(x, z));
  let area = 0;
  for (let i = 0, j = plan.length - 1; i < plan.length; j = i++) area += (plan[j][0] - plan[i][0]) * (plan[j][1] + plan[i][1]);
  const ccw = area > 0;
  for (let i = 0; i < plan.length; i++) {
    const a = plan[i], b = plan[(i + 1) % plan.length];
    const L = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const u = [(b[0] - a[0]) / L, (b[1] - a[1]) / L], n = ccw ? [-u[1], u[0]] : [u[1], -u[0]];
    const p = (t) => [a[0] + u[0] * t + n[0] * inset, a[1] + u[1] * t + n[1] * inset];
    const gate = gates.find((g) => g[0] === i);
    const gaps = gate ? [[gate[1] * L - 0.7, gate[1] * L + 0.7]] : [];
    const runs = [];
    let t0 = inset;
    for (const [g0, g1] of gaps) {
      runs.push([t0, g0]);
      t0 = g1;
    }
    runs.push([t0, L - inset]);
    for (const [r0, r1] of runs) {
      if (r1 - r0 < 0.2) continue;
      const q0 = p(r0), q1 = p(r1);
      // rails
      for (const y of [0.12, h - 0.05]) k.world().along(M.fence, q0[0], q0[1], q1[0], q1[1], -0.02, 0.04, Y0 + y, Y0 + y + 0.04);
      // posts every 2 m, bars every 12 cm
      const len = r1 - r0;
      const posts = Math.max(1, Math.round(len / 2));
      for (let s = 0; s <= posts; s++) {
        const q = p(r0 + (len * s) / posts);
        k.world().at(q[0], q[1], 0, Y0);
        k.cyl(M.fence, 0, 0, 0, 0.035, h + 0.05, 8);
      }
      const bars = Math.floor(len / 0.12);
      for (let s = 1; s < bars; s++) {
        const t = r0 + (len * s) / bars;
        const q = p(t), qq = [q[0] + u[0] * 0.022, q[1] + u[1] * 0.022]; // 22 x 12 mm flat bar
        k.world().along(M.fence, q[0], q[1], qq[0], qq[1], -0.006, 0.012, Y0 + 0.12, Y0 + h - 0.01);
      }
    }
    // gate posts a little taller with a cap
    for (const [g0, g1] of gaps) {
      for (const t of [g0, g1]) {
        const q = p(t);
        k.world().at(q[0], q[1], 0, Y0);
        k.box(M.fence, -0.05, 0, -0.05, 0.05, h + 0.25, 0.05);
        k.sphere(M.yellow, 0, h + 0.3, 0, 0.06, 1, 1, 1, 1);
      }
    }
  }
}

/** kerb along the outline of the rubber (outside it, a little proud) */
function kerb(k, M, outline) {
  const plan = outline.map(([x, z]) => P(x, z));
  let area = 0;
  for (let i = 0, j = plan.length - 1; i < plan.length; j = i++) area += (plan[j][0] - plan[i][0]) * (plan[j][1] + plan[i][1]);
  for (let i = 0; i < plan.length; i++) {
    let a = plan[i], b = plan[(i + 1) % plan.length];
    // the kit's slab goes to the left of a -> b, which is inside for an anticlockwise outline
    if (area > 0) [a, b] = [b, a];
    k.world().along(M.concrete, a[0], a[1], b[0], b[1], -0.005, 0.12, 0.02, Y0 + 0.06);
  }
}

/** place a piece at scene (x, z), its front towards scene direction (dx, dz) */
function at(k, x, z, dx, dz) {
  const [px, py] = P(x, z);
  return k.at(px, py, Math.atan2(-dz, dx), Y0);
}

export function addPlayground(scene, root) {
  // take out the old equipment and the gazebo roofs drawn on the orange rubber
  for (const name of ['Ground_playground', 'Site_ground_13']) {
    const o = root.getObjectByName(name);
    if (o) o.visible = false;
  }
  const orange = root.getObjectByName('Site_ground_9');
  if (orange?.geometry) {
    // keep the triangles that lie on the ground (the roofs stand 3-6 m up); heights in metres,
    // through the node's transform (the positions are quantized, in the node's own units)
    root.updateMatrixWorld(true);
    const g = orange.geometry, p = g.attributes.position, v = new THREE.Vector3();
    const y = (i) => v.fromBufferAttribute(p, i).applyMatrix4(orange.matrixWorld).y;
    const tri = g.index ? (i) => g.index.getX(i) : (i) => i;
    const n = g.index ? g.index.count : p.count, keep = [];
    for (let i = 0; i < n; i += 3) {
      const a = tri(i), b = tri(i + 1), c = tri(i + 2);
      if (Math.max(y(a), y(b), y(c)) < 0.5) keep.push(a, b, c);
    }
    const ng = g.clone();
    ng.setIndex(keep);
    ng.computeBoundingBox();
    ng.computeBoundingSphere();
    orange.geometry = ng;
  }

  const M = materials();
  const k = new Kit();
  const group = new THREE.Group();
  group.name = 'Playground';

  // ---- older children (blue) ----
  // two towers joined by a rope bridge, a wavy slide off the north one, a climbing wall and a
  // fireman's pole on the south one; long axis north-south
  at(k, 4.2, 24.6, 0, -1);
  tower(k, M, 1.5, M.red, ['e', 'w']);
  k.save().offset(0, 0.65, 0);
  slide(k, M, 1.5, 3.2, M.stainless);
  k.restore();
  at(k, 4.2, 25.25, 0, 1);
  bridge(k, M, 1.5, 2.7);
  at(k, 4.2, 28.6, 0, 1);
  tower(k, M, 1.5, M.blue, []); // bridge north, slide south, wall east, pole west
  k.save().offset(0, 0.65, 0);
  slide(k, M, 1.5, 2.6, M.yellow, 0.5, false);
  k.restore();
  at(k, 4.2 + 0.65 + 0.55, 28.6, -1, 0); // its foot 55 cm out east, leaning up to the deck
  climbingWall(k, M, 1.5);
  at(k, 4.2 - 0.95, 28.6, -1, 0); // the pole 30 cm off the deck's west edge
  k.cyl(M.stainless, 0, 0, 0, 0.03, 2.9, 12);
  k.tube(M.post, [[0, 2.9, 0], [0, 2.85, -0.15], [0, 1.55, -0.3]], 0.03, 12);
  // swings, the roundabout
  at(k, 3.4, 38.8, 0, 1);
  swings(k, M, 5.4, 2.4);
  at(k, 8.7, 33.6, 0, 1);
  roundabout(k, M);
  // painted games on the open rubber
  {
    const g = new THREE.PlaneGeometry(5, 5);
    g.rotateX(-Math.PI / 2);
    g.translate(-0.4, Y0 + 0.006, 31.5);
    k.world().add(M.games, g);
  }

  // ---- small children (orange) ----
  at(k, -8.2, 21.6, 0, 1);
  sandpit(k, M, 3.6);
  at(k, -8.2, 21.6, 0, 1);
  shadeSail(k, M, [[-2.4, -2.2, 2.9], [2.6, -2.0, 2.5], [0.2, 2.8, 2.2]]);
  at(k, -15.0, 20.0, 0, 1);
  playHouse(k, M);
  at(k, -7.0, 28.2, -1, 0);
  springRider(k, M, M.orange);
  at(k, -8.9, 27.0, -1, 0);
  springRider(k, M, M.teal);
  at(k, -16.6, 23.8, 0, 1);
  seesaw(k, M);

  // ---- fence, kerb, benches, bins, a sign ----
  fence(k, M, OUTER, [[7, 0.45], [5, 0.5]]);
  kerb(k, M, BLUE);
  kerb(k, M, ORANGE);
  // benches along the edges, facing in
  const benches = [[-12.6, 27.6, 0.72, -0.69], [-17.4, 22.6, 0.72, -0.69], [-1.2, 41.2, 0.52, -0.85], [9.2, 27.2, -1, 0], [-1.8, 24.0, 1, 0]];
  for (const [x, z, dx, dz] of benches) {
    at(k, x, z, dx, dz);
    bench(k, M);
  }
  for (const [x, z] of [[-13.6, 28.9], [-0.2, 42.4]]) {
    at(k, x, z, 1, 0);
    bin(k, M);
  }
  // rules sign beside the south gate, facing the way in
  at(k, 2.6, 44.0, -0.52, 0.85);
  k.cyl(M.steel, -0.3, 0, 0, 0.03, 1.6, 8);
  k.cyl(M.steel, 0.3, 0, 0, 0.03, 1.6, 8);
  k.box(M.sign, -0.42, 1.0, 0.03, 0.42, 1.55, 0.05);
  k.box(M.blue, -0.42, 1.45, 0.051, 0.42, 1.55, 0.055);

  const own = [];
  k.build(group, own);
  group.traverse((o) => {
    if (o.isMesh && o.material === M.games) o.receiveShadow = true;
  });
  scene.add(group);
  return group;
}
