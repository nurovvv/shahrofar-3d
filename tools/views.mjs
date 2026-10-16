// Fixed cameras for the before/after screenshots (scene metres: x east, y up, z south).
const HOME = { pos: [-12, 150, 190], target: [5, 28, -5] };

export const VIEWS = {
  // the marketing render's aerial view, with the sales UI
  aerial: { ...HOME, ui: true },
  // same view without UI
  aerial_clean: { ...HOME },
  // from over the river, north-east
  aerial_river: { pos: [135, 120, -175], target: [0, 28, 5] },
  // block V: balconies, windows, slab bands
  facade_v: { pos: [-5, 28, 30], target: [-36, 30, -14] },
  // hotel curtain wall and the podium corner
  hotel_glass: { pos: [10, 6, 120], target: [32, 22, 50] },
  // podium roof deck: pool, planting, playground
  deck: { pos: [81, 60, -60], target: [25, 14, 0] },
  // street, trees, cars and the neighbour blocks
  street: { pos: [62, 1.7, 112], target: [25, 12, 40] },
  // close-ups: hotel curtain wall, block B windows and balconies, the landscape at eye height
  glass_close: { pos: [52, 14, 66], target: [36, 24, 50] },
  facade_b_close: { pos: [36, 34, 22], target: [22, 36, -6] },
  landscape: { pos: [5, 3.5, 92], target: [-12, 1.5, 62] },
  // the ground-level playground by the car park: from above the street, and at a parent's eye height
  playground: { pos: [30, 16, 68], target: [-6, 0, 30] },
  playground_top: { pos: [-4, 46, 48], target: [-4, 0, 30.5] },
  playground_eye: { pos: [0.5, 1.6, 50], target: [-1, 0.9, 30] },
  // parked cars, close
  cars: { pos: [-26, 2.5, 46], target: [-24, 0.6, 30] },
  // walls between apartments, close: the same cut-away floor, camera low over the party walls
  walls_v12: { floor: ['V', 12], from: HOME, pos: [-30, 60, 4], target: [-38, 43, -14] },
  // walking inside a flat: the entrance hall of flat V12-7, looking west into the flat
  walk_v12: { walk: 'V12-7', at: [-34.38, -7.76], yaw: 3.035, pitch: -0.08 },
  // cut-away floor views (camera from the app's own flight)
  floor_v12: { floor: ['V', 12], ui: true, from: HOME },
  floor_b8: { floor: ['B', 8], ui: true, from: HOME },
  floor_v23: { floor: ['V', 23], ui: true, from: HOME },
};
