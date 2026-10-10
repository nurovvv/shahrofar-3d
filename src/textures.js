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
