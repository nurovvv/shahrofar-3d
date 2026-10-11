# Skyline Residence – 3D building demo

Interactive 3D model of the Shahrofar riverside complex (three towers on a curved retail podium) for real-estate sales: pick a tower and a floor, open an apartment card with its floor plan and price, then walk around inside it.

![The model rendered in Blender from the camera of the aerial marketing render](docs/aerial.jpg)

Built with [Three.js](https://threejs.org) and [Vite](https://vitejs.dev).

## Where things come from

| | Source |
|---|---|
| Apartments, rooms, walls, windows, balconies of blocks В and Б | the architect's floor plans: typical floor (sheet 7), floors 23–24 (sheet 8) |
| Floor levels | section 1-1 (sheet 13): floor 5 at +18.6, then 3.3 m per floor; roofs at +84.9 (В) and +71.7 (Б) |
| Look, site, podium, hotel, surroundings | the aerial marketing render (its camera was recovered from its vanishing points) |
| Prices and sold/reserved statuses | demo values in `src/data.js` |

| | Floors | Apartments |
|---|---|---|
| Block В | 24 | floors 5–24, 8 per floor (1–3 rooms, 41–174 m²), terraces on 23–24 |
| Block Б | 20 | floors 5–20, 8 per floor (1–3 rooms, 52–154 m²) |
| Block А | 16 | hotel, not for sale |

## Rebuilding the model

```bash
pip install bpy shapely pymupdf      # Blender as a Python module (Python 3.13); or have a Blender 4.2+ binary on PATH
blender/plans/make_plans.sh SET.pdf  # only when the drawings change: PDF -> blender/plans/plans.json
blender/export_web.sh                # -> public/models/shahrofar.glb, src/model/complex.json, src/model/plans.json
RENDER=1 blender/export_web.sh       # also renders build/shahrofar.png from the marketing render's camera
```

- `blender/plans/extract_pdf.py` pulls the vector paths and labels of one tower out of a plan sheet; `build_plans.py` turns them into walls, windows, apartments and rooms (names and areas as written on the sheet, e.g. "Хонаи хоб 15.17" → Bedroom 15.17 m²).
- `blender/build_complex.py` builds the scene; it also takes `--view "river aerial" | "avenue street" | "river street"` for other stills.
- `blender/shahrofar.blend` is a ready-made copy of the scene to open in Blender.

## Run locally

```bash
npm install
npm run dev
```

Then open http://localhost:5173.

## Publish

Every push to `main` is built and published to GitHub Pages by `.github/workflows/deploy.yml` (turn Pages on in the repository settings: Source → GitHub Actions).

## Controls

- **Complex:** drag to rotate, scroll to zoom, hover a tower to see its floors, click a floor (or pick one from the list; switch towers with the Block V / Block B tabs), then click an apartment.
- **Inside:** drag to look around, click the floor to walk there, or use WASD / arrow keys. On touch screens, use the on-screen joystick.
