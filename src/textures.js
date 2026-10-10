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

// Facade of neighbouring buildings: 1 tile = one window bay (3 m x 3.2 m)
export function windowTexture() {
  const c = document.createElement('canvas');
  c.width = 64;
  c.height = 64;
  const g = c.getContext('2d');
  g.fillStyle = '#ece6da';
  g.fillRect(0, 0, 64, 64);
  g.fillStyle = '#5f7486';
  g.fillRect(12, 14, 40, 34);
  g.fillStyle = 'rgba(255,255,255,0.18)';
  g.fillRect(12, 14, 40, 8);
  return finish(c, 4);
}

export function signTexture(text) {
  const c = document.createElement('canvas');
  c.width = 1024;
  c.height = 64;
  const g = c.getContext('2d');
  g.fillStyle = '#23272d';
  g.fillRect(0, 0, 1024, 64);
  g.fillStyle = '#f4ede0';
  g.font = '600 38px system-ui, -apple-system, Helvetica, Arial, sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.letterSpacing = '14px';
  g.fillText(text, 512, 34);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
