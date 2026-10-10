// The complex: three towers on a retail podium. Tower geometry (floor levels, apartment
// positions) comes from the Blender build in blender/, exported to model/complex.json.
import complex from './model/complex.json';

export const MODEL_URL = `${import.meta.env.BASE_URL}models/shahrofar.glb`;

export const CEIL = 2.9; // clear room height inside the apartments
export const UNIT_D = 6.65; // apartment depth, corridor wall -> facade

// Site plan coordinates (metres, x east, y north) -> scene (x, z) with the complex at the origin.
const [CX, CY] = complex.site_centre;
export const toScene = (x, y) => ({ x: x - CX, z: -(y - CY) });

const rot2 = (deg, [x, y]) => {
  const a = (deg * Math.PI) / 180, c = Math.cos(a), s = Math.sin(a);
  return [c * x - s * y, s * x + c * y];
};

// Tower-local plan point / direction -> scene
export function towerPoint(t, p) {
  const [x, y] = rot2(t.rot, p);
  return toScene(t.origin[0] + x, t.origin[1] + y);
}
export function towerDir(t, d) {
  const [x, y] = rot2(t.rot, d);
  return { x, z: -y };
}

export const TOWERS = complex.towers;
export const RESIDENTIAL = TOWERS.filter((t) => !t.hotel);
export const towerByKey = Object.fromEntries(TOWERS.map((t) => [t.key, t]));
export const TREES = { protos: complex.tree_protos, list: complex.trees };

// Apartment order on every floor, clockwise from the land side.
export const UNIT_KEYS = ['S', 'E', 'N', 'W'];

export const STATUS = {
  available: { label: 'Available', color: 0x22b573, css: '#22b573' },
  reserved: { label: 'Reserved', color: 0xf0a92e, css: '#f0a92e' },
  sold: { label: 'Sold', color: 0xe14d4d, css: '#e14d4d' },
};
