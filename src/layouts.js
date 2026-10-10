// Apartment floor plans in local (u, v) coordinates. Everything the interior builder,
// the 2D plan and the collision system need comes from here.
import { UNIT_D } from './config.js';

const T = 0.12; // partition thickness
export const HV = 2.2; // depth of the hall / bathroom strip along the corridor

const C = {
  white: 0xf3f1ec,
  counter: 0x34363a,
  wood: 0xa27a54,
  darkwood: 0x5b4331,
  fabric: 0x6b7b8f,
  cushion: 0x7d8da2,
  linen: 0xf4f1ea,
  duvet: 0x93a9bf,
  black: 0x1b1c1f,
  steel: 0xcfd2d4,
  rug: 0xd8cab2,
  pot: 0xb8673f,
  leaf: 0x4e7d3a,
  ceramic: 0xfafafa,
  mirror: 0xbcd3e0,
  lamp: 0xfff1d0,
};
const glow = { emissive: 0xffd9a0 };

const cache = new Map();
export function getLayout(type, W) {
  const key = `${type}:${W}`;
  if (!cache.has(key)) cache.set(key, build(type, W));
  return cache.get(key);
}

function build(type, W) {
  const D = UNIT_D;
  const L = { type, W, D, rooms: [], walls: [], doors: [], items: [] };

  const box = (u0, v0, u1, v1, y0, y1, color, collide = true, extra = {}) =>
    L.items.push({ kind: 'box', u0, v0, u1, v1, y0, y1, color, collide, ...extra });
  const cyl = (u, v, r, y0, y1, color, collide = true, extra = {}) =>
    L.items.push({ kind: 'cyl', u, v, r, y0, y1, color, collide, ...extra });
  const ball = (u, v, r, y, color) => L.items.push({ kind: 'sphere', u, v, r, y, color, collide: false });
  const room = (name, u0, v0, u1, v1, floor = 'wood') =>
    L.rooms.push({ name, u0, v0, u1, v1, floor, area: (u1 - u0) * (v1 - v0) });

  // Walls with door gaps. A gap is [start, end] or [start, end, 'entry'].
  function wallV(u, v0, v1, gaps = [], t = T) {
    let c = v0;
    for (const [g0, g1, kind] of gaps) {
      if (g0 > c) L.walls.push({ u0: u - t / 2, u1: u + t / 2, v0: c, v1: g0 });
      L.doors.push({ u0: u - t / 2, u1: u + t / 2, v0: g0, v1: g1, entry: kind === 'entry' });
      c = g1;
    }
    if (v1 > c) L.walls.push({ u0: u - t / 2, u1: u + t / 2, v0: c, v1 });
  }
  function wallH(v, u0, u1, gaps = [], t = T) {
    let c = u0;
    for (const [g0, g1, kind] of gaps) {
      if (g0 > c) L.walls.push({ u0: c, u1: g0, v0: v - t / 2, v1: v + t / 2 });
      L.doors.push({ u0: g0, u1: g1, v0: v - t / 2, v1: v + t / 2, entry: kind === 'entry' });
      c = g1;
    }
    if (u1 > c) L.walls.push({ u0: c, u1, v0: v - t / 2, v1: v + t / 2 });
  }

  function kitchen() {
    box(0, 0.25, 0.62, 3.3, 0, 0.86, C.white);
    box(0, 0.25, 0.65, 3.3, 0.86, 0.9, C.counter, false);
    box(0, 0.25, 0.35, 3.3, 1.45, 2.2, C.white, false);
    box(0, 3.3, 0.68, 4.0, 0, 2.05, C.steel);
    box(0.12, 1.2, 0.5, 1.8, 0.9, 0.906, 0x8a8f94, false);
    box(0.1, 2.4, 0.55, 3.0, 0.9, 0.906, C.black, false);
  }

  function chair(u, v, side) {
    box(u - 0.21, v - 0.21, u + 0.21, v + 0.21, 0.43, 0.47, C.darkwood);
    for (const [a, b] of [[-1, -1], [-1, 1], [1, -1], [1, 1]]) {
      box(u + a * 0.18 - 0.02, v + b * 0.18 - 0.02, u + a * 0.18 + 0.02, v + b * 0.18 + 0.02, 0, 0.43, C.darkwood, false);
    }
    const bu = u + side * 0.19;
    box(bu - 0.02, v - 0.21, bu + 0.02, v + 0.21, 0.47, 0.9, C.darkwood, false);
  }

  function dining(cu, cv) {
    box(cu - 0.45, cv - 0.8, cu + 0.45, cv + 0.8, 0.72, 0.76, C.wood);
    for (const [a, b] of [[-1, -1], [-1, 1], [1, -1], [1, 1]]) {
      box(cu + a * 0.38 - 0.03, cv + b * 0.72 - 0.03, cu + a * 0.38 + 0.03, cv + b * 0.72 + 0.03, 0, 0.72, C.darkwood, false);
    }
    for (const side of [-1, 1]) for (const dv of [-0.4, 0.4]) chair(cu + side * 0.78, cv + dv, side);
    // pendant lamp over the table
    cyl(cu, cv, 0.006, 1.8, 2.9, C.black, false);
    cyl(cu, cv, 0.22, 1.62, 1.8, C.lamp, false, glow);
  }

  function living(Lw) {
    // sofa facing the TV wall
    box(1.3, 3.9, 2.2, 6.0, 0, 0.42, C.fabric);
    box(1.3, 3.9, 1.5, 6.0, 0.42, 0.85, C.fabric, false);
    box(1.3, 3.9, 2.2, 4.08, 0.42, 0.62, C.fabric, false);
    box(1.3, 5.82, 2.2, 6.0, 0.42, 0.62, C.fabric, false);
    box(1.5, 4.1, 2.15, 4.93, 0.42, 0.52, C.cushion, false);
    box(1.5, 4.97, 2.15, 5.8, 0.42, 0.52, C.cushion, false);
    // rug + coffee table
    box(2.4, 4.0, Lw - 0.6, 5.9, 0, 0.012, C.rug, false);
    const tc = (2.3 + Lw - 0.5) / 2;
    box(tc - 0.3, 4.45, tc + 0.3, 5.45, 0.36, 0.4, C.wood);
    box(tc - 0.25, 4.5, tc + 0.25, 5.4, 0.012, 0.36, C.darkwood, false);
    // TV
    box(Lw - 0.48, 4.2, Lw - 0.06, 5.7, 0, 0.45, 0x2c2c2e);
    box(Lw - 0.11, 4.35, Lw - 0.07, 5.55, 0.85, 1.55, C.black, false, { emissive: 0x0d1a2a });
    // floor lamp
    cyl(1.75, 6.3, 0.15, 0, 0.03, C.black);
    cyl(1.75, 6.3, 0.015, 0.03, 1.5, C.black, false);
    cyl(1.75, 6.3, 0.2, 1.5, 1.8, C.lamp, false, glow);
  }

  function plant(u, v) {
    cyl(u, v, 0.22, 0, 0.45, C.pot);
    ball(u, v, 0.42, 0.95, C.leaf);
  }

  function bedroom(u0, v0, u1, v1, wardrobe) {
    const c = (v0 + v1) / 2 + 0.2;
    box(u0 + 0.06, c - 0.82, u0 + 2.1, c + 0.82, 0, 0.3, C.darkwood);
    box(u0 + 0.12, c - 0.78, u0 + 2.06, c + 0.78, 0.3, 0.5, C.linen, false);
    box(u0 + 0.75, c - 0.8, u0 + 2.08, c + 0.8, 0.5, 0.56, C.duvet, false);
    box(u0 + 0.06, c - 0.82, u0 + 0.14, c + 0.82, 0.3, 1.15, C.darkwood, false);
    box(u0 + 0.2, c - 0.72, u0 + 0.55, c - 0.06, 0.5, 0.63, C.white, false);
    box(u0 + 0.2, c + 0.06, u0 + 0.55, c + 0.72, 0.5, 0.63, C.white, false);
    box(u0 + 1.2, c - 1.2, u0 + 2.8, c + 1.2, 0, 0.012, C.rug, false);
    for (const s of [-1, 1]) {
      const nv = c + s * 1.08;
      box(u0 + 0.06, nv - 0.22, u0 + 0.5, nv + 0.22, 0, 0.5, C.wood);
      cyl(u0 + 0.28, nv, 0.1, 0.5, 0.78, C.lamp, false, glow);
    }
    if (wardrobe) box(...wardrobe, 0, 2.2, C.white);
  }

  function bathroom(hE) {
    box(hE + 0.08, 0.02, W - 0.1, 0.78, 0, 0.55, C.ceramic);
    box(hE + 0.15, 0.09, W - 0.17, 0.71, 0.55, 0.553, 0xbfe0ee, false);
    box(W - 0.3, 1.45, W - 0.1, 1.9, 0, 0.8, C.ceramic);
    box(W - 0.72, 1.5, W - 0.3, 1.85, 0, 0.42, C.ceramic);
    box(hE + 0.45, HV - 0.55, hE + 1.15, HV - 0.06, 0, 0.82, C.wood);
    box(hE + 0.55, HV - 0.5, hE + 1.05, HV - 0.12, 0.82, 0.9, C.ceramic, false);
    box(hE + 0.5, HV - 0.08, hE + 1.1, HV - 0.065, 1.1, 1.8, C.mirror, false, { metal: true });
  }

  if (type === 'large') {
    const Lw = 6.0, S = 9.8, hE = W - 2.1;
    room('Living room & kitchen', 0, 0, Lw, D);
    room('Hall', Lw, 0, hE, HV);
    room('Bathroom', hE, 0, W, HV, 'tile');
    room('Bedroom', Lw, HV, S, D);
    room('Bedroom', S, HV, W, D);
    wallH(-0.1, -0.2, W, [[Lw - 1.4, Lw - 0.4, 'entry']], 0.2);
    wallV(-0.1, -0.2, D, [], 0.2);
    wallV(Lw, 0, D, [[0.6, 1.5]]);
    wallH(HV, Lw, W, [[Lw + 0.3, Lw + 1.2], [S + 0.3, S + 1.2]]);
    wallV(S, HV, D);
    wallV(hE, 0, HV, [[0.6, 1.4]]);
    L.walls.push({ u0: W - 0.08, u1: W, v0: 0, v1: HV }); // no glass in the bathroom
    kitchen();
    dining(2.4, 1.9);
    living(Lw);
    plant(0.45, D - 0.45);
    box(Lw + 1.6, 0, Lw + 3.2, 0.55, 0, 2.2, C.white); // hall wardrobe
    bedroom(Lw, HV, S, D, [S - 0.6, HV + 0.06, S - 0.06, HV + 2.0]);
    bedroom(S, HV, W, D, [S + 1.35, HV + 0.06, W - 0.1, HV + 0.66]);
    plant(W - 0.45, D - 0.45);
    bathroom(hE);
    L.spawn = { u: Lw - 0.9, v: 0.6, du: -0.4, dv: 1 };
    L.roomsCount = 3;
    L.summary = 'Living room with kitchen, 2 bedrooms';
  } else {
    const Lw = 4.6, hE = W - 2.0;
    room('Living room & kitchen', 0, 0, Lw, D);
    room('Hall', Lw, 0, hE, HV);
    room('Bathroom', hE, 0, W, HV, 'tile');
    room('Bedroom', Lw, HV, W, D);
    wallH(-0.1, -0.2, W, [[Lw - 1.4, Lw - 0.4, 'entry']], 0.2);
    wallV(-0.1, -0.2, D, [], 0.2);
    wallV(Lw, 0, D, [[0.6, 1.5]]);
    wallH(HV, Lw, W, [[Lw + 1.2, Lw + 2.1]]);
    wallV(hE, 0, HV, [[0.6, 1.4]]);
    L.walls.push({ u0: W - 0.08, u1: W, v0: 0, v1: HV });
    kitchen();
    dining(2.3, 1.9);
    living(Lw);
    plant(0.45, D - 0.45);
    box(Lw + 0.9, 0, Lw + 2.3, 0.55, 0, 2.2, C.white);
    bedroom(Lw, HV, W, D, [Lw + 2.3, HV + 0.06, W - 0.1, HV + 0.66]);
    // reading chair by the window
    box(W - 1.1, D - 1.0, W - 0.3, D - 0.25, 0, 0.42, C.cushion);
    box(W - 1.1, D - 0.4, W - 0.3, D - 0.25, 0.42, 0.85, C.cushion, false);
    bathroom(hE);
    L.spawn = { u: Lw - 0.9, v: 0.6, du: -0.4, dv: 1 };
    L.roomsCount = 2;
    L.summary = 'Living room with kitchen, 1 bedroom';
  }

  L.area = Math.round(W * D * 10) / 10;
  return L;
}
