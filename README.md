# Skyline Residence – 3D building demo

Interactive 3D apartment building for real-estate sales: pick a floor, open an apartment card with its floor plan and price, then walk around inside it.

Built with [Three.js](https://threejs.org) and [Vite](https://vitejs.dev). All demo data (apartments, prices, statuses) lives in `src/data.js`; floor plans and furniture in `src/layouts.js`.

## Run locally

```bash
npm install
npm run dev
```

Then open http://localhost:5173.

## Publish

Every push to `main` is built and published to GitHub Pages by `.github/workflows/deploy.yml`.

## Controls

- **Building:** drag to rotate, scroll to zoom, click a floor, then an apartment.
- **Inside:** drag to look around, click the floor to walk there, or use WASD / arrow keys. On touch screens, use the on-screen joystick.
