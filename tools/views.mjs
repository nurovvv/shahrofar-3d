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
  // cut-away floor views (camera from the app's own flight)
  floor_v12: { floor: ['V', 12], ui: true, from: HOME },
  floor_b8: { floor: ['B', 8], ui: true, from: HOME },
  floor_v23: { floor: ['V', 23], ui: true, from: HOME },
};
