// 2D floor plan drawn from the same layout data as the 3D interior.
// Facade (windows) is always at the top; `flip` mirrors it so it matches the real top-down view.
import { HV } from './layouts.js';

const ROOM_FILL = {
  'Living room & kitchen': '#f6eee1',
  Bedroom: '#ecf1f6',
  Hall: '#f1f0ec',
  Bathroom: '#e3eff3',
};
const SHORT = { 'Living room & kitchen': 'Living / kitchen' };

// Mirror the plan when the apartment's (u, v) frame is mirrored as seen from above (north up).
export const planFlip = ({ eu, ev }) => eu.z * ev.x - eu.x * ev.z < 0;

export function planTransform(layout, cw, ch, pad, flip) {
  const s = Math.min((cw - 2 * pad) / layout.W, (ch - 2 * pad) / layout.D);
  const ox = (cw - layout.W * s) / 2, oy = (ch - layout.D * s) / 2;
  return {
    s,
    px: (u) => ox + (flip ? layout.W - u : u) * s,
    py: (v) => oy + (layout.D - v) * s,
  };
}

export function drawPlan(canvas, layout, { flip = false, pad = 16, labels = true, dark = false } = {}) {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const cw = canvas.clientWidth || canvas.width, ch = canvas.clientHeight || canvas.height;
  canvas.width = Math.round(cw * dpr);
  canvas.height = Math.round(ch * dpr);
  const g = canvas.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, cw, ch);
  const T = planTransform(layout, cw, ch, pad, flip);
  const rect = (u0, v0, u1, v1) => {
    const x0 = T.px(u0), x1 = T.px(u1), y0 = T.py(v0), y1 = T.py(v1);
    return [Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)];
  };

  for (const r of layout.rooms) {
    g.fillStyle = dark ? 'rgba(255,255,255,0.08)' : ROOM_FILL[r.name] ?? '#f2f2f2';
    g.fillRect(...rect(r.u0, r.v0, r.u1, r.v1));
  }

  // furniture outlines
  g.strokeStyle = dark ? 'rgba(255,255,255,0.28)' : 'rgba(40,45,55,0.28)';
  g.lineWidth = 1;
  for (const it of layout.items) {
    if (it.kind === 'box' && (it.collide || it.y1 < 0.05) && it.y1 - it.y0 > 0.005) {
      g.strokeRect(...rect(it.u0, it.v0, it.u1, it.v1));
    } else if (it.kind === 'cyl' && it.collide) {
      g.beginPath();
      g.arc(T.px(it.u), T.py(it.v), it.r * T.s, 0, Math.PI * 2);
      g.stroke();
    }
  }

  // glass on the two outside walls
  g.strokeStyle = '#5fa4d6';
  g.lineWidth = Math.max(3, T.s * 0.12);
  g.beginPath();
  g.moveTo(T.px(0), T.py(layout.D));
  g.lineTo(T.px(layout.W), T.py(layout.D));
  g.lineTo(T.px(layout.W), T.py(HV));
  g.stroke();

  g.fillStyle = dark ? '#e9edf2' : '#2b2f36';
  for (const w of layout.walls) g.fillRect(...rect(w.u0, w.v0, w.u1, w.v1));

  // entrance marker
  const entry = layout.doors.find((d) => d.entry);
  if (entry) {
    const x = T.px((entry.u0 + entry.u1) / 2), y = T.py(entry.v0) + 3;
    g.fillStyle = '#e0613c';
    g.beginPath();
    g.moveTo(x, y - 9);
    g.lineTo(x - 6, y + 2);
    g.lineTo(x + 6, y + 2);
    g.closePath();
    g.fill();
  }

  if (labels) {
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    for (const r of layout.rooms) {
      const [x, y, w, h] = rect(r.u0, r.v0, r.u1, r.v1);
      const small = w < 80 || h < 50;
      g.fillStyle = '#2b2f36';
      g.font = `600 ${small ? 9 : 11}px system-ui, -apple-system, sans-serif`;
      g.fillText(SHORT[r.name] ?? r.name, x + w / 2, y + h / 2 - 7);
      g.fillStyle = '#6b7280';
      g.font = `${small ? 9 : 10}px system-ui, -apple-system, sans-serif`;
      g.fillText(`${r.area.toFixed(1)} m²`, x + w / 2, y + h / 2 + 7);
    }
  }
  return T;
}
