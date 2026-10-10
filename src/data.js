// Demo apartment list. In a real project this would come from a JSON/Excel export
// or an admin panel so the sales team can change prices and statuses.
import { FLOORS, UNIT_DEFS } from './config.js';
import { getLayout } from './layouts.js';

function mulberry32(a) {
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(20261010);

export const apartments = [];
for (let floor = 2; floor <= FLOORS; floor++) {
  UNIT_DEFS.forEach((def, i) => {
    const layout = getLayout(def.type, def.W);
    const r = rand();
    const status = r < 0.55 ? 'available' : r < 0.75 ? 'reserved' : 'sold';
    const perM2 = 1350 * (1 + (floor - 2) * 0.03) * (def.type === 'large' ? 1.04 : 1);
    apartments.push({
      id: `${floor}${def.key}`,
      number: (floor - 2) * 4 + i + 1,
      floor,
      def,
      layout,
      rooms: layout.roomsCount,
      area: layout.area,
      price: Math.round((layout.area * perM2) / 500) * 500,
      status,
    });
  });
}

export const aptsOnFloor = (floor) => apartments.filter((a) => a.floor === floor);
