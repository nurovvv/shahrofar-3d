// Procedural canvas textures so the demo needs no image files.
import * as THREE from 'three';

function finish(canvas, anisotropy = 8) {
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = anisotropy;
  return tex;
}

// 512px = 1.2 m of oak planks
export function woodTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d');
  const plankH = 64;
  for (let y = 0; y < 512; y += plankH) {
    let x = -Math.random() * 300;
    while (x < 512) {
      const len = 200 + Math.random() * 220;
      const light = 52 + Math.random() * 12;
      for (const off of [-512, 0, 512]) {
        g.fillStyle = `hsl(30, 38%, ${light}%)`;
        g.fillRect(x + off, y, len, plankH);
        g.strokeStyle = 'rgba(80, 50, 25, 0.12)';
        g.lineWidth = 1;
        for (let k = 0; k < 6; k++) {
          const gy = y + 6 + Math.random() * (plankH - 12);
          g.beginPath();
          g.moveTo(x + off, gy);
          g.bezierCurveTo(x + off + len / 3, gy + 3, x + off + (2 * len) / 3, gy - 3, x + off + len, gy);
          g.stroke();
        }
        g.fillStyle = 'rgba(60, 38, 20, 0.45)';
        g.fillRect(x + off, y, 2, plankH);
      }
      x += len;
    }
    g.fillStyle = 'rgba(60, 38, 20, 0.45)';
    g.fillRect(0, y, 512, 2);
  }
  return finish(c);
}

// 512px = 1.2 m, 4x4 tiles
export function tileTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d');
  g.fillStyle = '#b9b6b0';
  g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      const l = 86 + Math.random() * 4;
      g.fillStyle = `hsl(40, 8%, ${l}%)`;
      g.fillRect(i * 128 + 2, j * 128 + 2, 124, 124);
    }
  }
  return finish(c);
}

// Ground textures for the site (model UVs are in metres; `metres` = size of one tile)
function noiseCanvas(size, base, spots) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = base;
  g.fillRect(0, 0, size, size);
  let seed = 3;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (const [n, rmin, rmax, colors, alpha] of spots) {
    for (let i = 0; i < n; i++) {
      const x = rnd() * size, y = rnd() * size, r = rmin + rnd() * (rmax - rmin);
      g.globalAlpha = alpha * (0.4 + rnd() * 0.6);
      g.fillStyle = colors[Math.floor(rnd() * colors.length)];
      for (const ox of [-size, 0, size]) {
        for (const oy of [-size, 0, size]) {
          g.beginPath();
          g.arc(x + ox, y + oy, r, 0, Math.PI * 2);
          g.fill();
        }
      }
    }
  }
  g.globalAlpha = 1;
  return { c, g };
}

export function groundTexture(kind) {
  let canvas, metres;
  if (kind === 'grass') {
    const { c } = noiseCanvas(256, '#5f6e1a', [
      [60, 18, 40, ['#6f7f22', '#56661a', '#4d5c16', '#7a8a2a'], 0.35],
      [1800, 0.6, 1.8, ['#84952e', '#46541a', '#6a7a20'], 0.5],
    ]);
    canvas = c; metres = 14;
  } else if (kind === 'asphalt') {
    const { c } = noiseCanvas(256, '#57585c', [
      [40, 10, 30, ['#5d5e62', '#515256'], 0.3],
      [4000, 0.4, 1.0, ['#6a6b70', '#47484c', '#77787c'], 0.6],
    ]);
    canvas = c; metres = 6;
  } else {
    // paving slabs with joints
    const { c, g } = noiseCanvas(256, kind === 'deck' ? '#dcb88f' : '#c8bcab', [[1200, 0.5, 1.2, ['#d4c9b9', '#b9ad9c'], 0.4]]);
    g.strokeStyle = 'rgba(90, 80, 70, 0.35)';
    g.lineWidth = 2;
    for (let i = 0; i <= 4; i++) {
      g.beginPath(); g.moveTo(i * 64, 0); g.lineTo(i * 64, 256); g.stroke();
      g.beginPath(); g.moveTo(0, i * 64); g.lineTo(256, i * 64); g.stroke();
    }
    canvas = c; metres = 2.4;
  }
  const tex = finish(canvas, 8);
  tex.repeat.set(1 / metres, 1 / metres);
  return tex;
}
