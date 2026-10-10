// Building dimensions (meters). Floor 1 is the lobby, floors 2..FLOORS hold apartments.
export const FLOORS = 10;
export const FLOOR_H = 3.2;
export const SLAB = 0.3;
export const CEIL = FLOOR_H - SLAB; // clear room height
export const UNIT_D = 6.65; // apartment depth, corridor wall -> facade
export const CORR = 1.1; // corridor half width incl. wall

// Four apartments per floor. Each apartment is described in its own local frame:
// u runs along the facade from the party wall, v runs from the corridor to the windows.
// World position: x = ox + sx * u, z = sz * (CORR + v).
export const UNIT_DEFS = [
  { key: 'A', sx: -1, sz: 1, ox: -2.1, W: 9.65, type: 'small', view: 'Boulevard & park' },
  { key: 'B', sx: 1, sz: 1, ox: -1.9, W: 13.65, type: 'large', view: 'Boulevard & park' },
  { key: 'C', sx: 1, sz: -1, ox: 2.1, W: 9.65, type: 'small', view: 'Quiet courtyard' },
  { key: 'D', sx: -1, sz: -1, ox: 1.9, W: 13.65, type: 'large', view: 'Quiet courtyard' },
];

export const STATUS = {
  available: { label: 'Available', color: 0x22b573, css: '#22b573' },
  reserved: { label: 'Reserved', color: 0xf0a92e, css: '#f0a92e' },
  sold: { label: 'Sold', color: 0xe14d4d, css: '#e14d4d' },
};

export const floorBase = (floor) => (floor - 1) * FLOOR_H;
