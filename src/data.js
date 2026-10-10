// Demo apartment list. In a real project this would come from a JSON/Excel export
// or an admin panel so the sales team can change prices and statuses.
import { RESIDENTIAL, UNIT_KEYS, towerDir, towerPoint } from './config.js';
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
const VIEW_PREMIUM = { N: 1.08, E: 1.03, S: 1.0, W: 1.0 }; // river side costs more

export const apartments = [];
for (const tower of RESIDENTIAL) {
  let number = 0;
  const first = tower.floors[0].floor;
  for (const fl of tower.floors) {
    for (const key of UNIT_KEYS) {
      const u = tower.units[key];
      const layout = getLayout(u.type, u.W);
      const r = rand();
      const status = r < 0.55 ? 'available' : r < 0.75 ? 'reserved' : 'sold';
      const perM2 = 1350 * (1 + (fl.floor - first) * 0.02) * (u.type === 'large' ? 1.04 : 1) * VIEW_PREMIUM[key];
      apartments.push({
        id: `${tower.key}${fl.floor}${key}`,
        tower: tower.key,
        towerLabel: tower.label,
        number: ++number,
        floor: fl.floor,
        floors: tower.levels,
        unit: key,
        view: u.view,
        // where the apartment sits: corner (u = 0, v = 0) at the corridor, eu along the facade,
        // ev from the corridor towards the windows, floor at baseY
        place: {
          o: towerPoint(tower, u.o),
          eu: towerDir(tower, u.eu),
          ev: towerDir(tower, u.ev),
          baseY: fl.z + tower.slab,
        },
        layout,
        rooms: layout.roomsCount,
        area: layout.area,
        price: Math.round((layout.area * perM2) / 500) * 500,
        status,
      });
    }
  }
}

export const aptsOnFloor = (tower, floor) => apartments.filter((a) => a.tower === tower && a.floor === floor);
