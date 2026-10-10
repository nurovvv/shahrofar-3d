// Sky, sun, ground and the neighbourhood around the building.
import * as THREE from 'three';
import { windowTexture } from './textures.js';

export function buildWorld(scene) {
  // sky dome
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(1500, 32, 16),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: {
        top: { value: new THREE.Color(0x5d9bd6) },
        bottom: { value: new THREE.Color(0xe3edf5) },
      },
      vertexShader: /* glsl */ `
        varying vec3 vDir;
        void main() {
          vDir = normalize(position);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 top;
        uniform vec3 bottom;
        varying vec3 vDir;
        void main() {
          float h = pow(clamp(vDir.y, 0.0, 1.0), 0.55);
          gl_FragColor = vec4(mix(bottom, top, h), 1.0);
          #include <colorspace_fragment>
        }`,
    }),
  );
  sky.renderOrder = -1;
  scene.add(sky);
  scene.fog = new THREE.Fog(0xdfe8f0, 220, 900);

  // lights
  scene.add(new THREE.HemisphereLight(0xe2efff, 0x8d8068, 0.9));
  const sun = new THREE.DirectionalLight(0xfff0dc, 2.8);
  sun.position.set(48, 70, 38);
  sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096);
  const sc = sun.shadow.camera;
  sc.left = -42;
  sc.right = 42;
  sc.top = 42;
  sc.bottom = -42;
  sc.near = 10;
  sc.far = 220;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.03;
  scene.add(sun);

  const std = (color, roughness = 0.95) => new THREE.MeshStandardMaterial({ color, roughness });

  // ground
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(2400, 2400), std(0x8cb36d, 1));
  grass.rotation.x = -Math.PI / 2;
  grass.position.y = -0.06;
  grass.receiveShadow = true;
  scene.add(grass);

  const slab = (w, d, x, z, top, thick, mat) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, thick, d), mat);
    m.position.set(x, top - thick / 2, z);
    m.receiveShadow = true;
    scene.add(m);
    return m;
  };
  slab(66, 50, 0, 0, -0.02, 0.06, std(0xd8d4cb));
  slab(4, 22, 0, 18.5, -0.015, 0.03, std(0xc5bfb3));
  slab(1200, 10, 0, 34, -0.03, 0.04, std(0x4b4e54, 0.9));
  slab(1200, 2.4, 0, 27.8, -0.015, 0.05, std(0xc9c5bd));
  slab(1200, 2.4, 0, 40.2, -0.015, 0.05, std(0xc9c5bd));

  // lane dashes
  const dash = new THREE.InstancedMesh(new THREE.BoxGeometry(3, 0.01, 0.18), std(0xf2f2ea), 80);
  const m4 = new THREE.Matrix4();
  for (let i = 0; i < 80; i++) {
    m4.makeTranslation(-400 + i * 10, -0.005, 34);
    dash.setMatrixAt(i, m4);
  }
  scene.add(dash);

  // hedges around the plaza
  const hedgeMat = std(0x5f8a45);
  for (const [w, d, x, z] of [
    [26, 1, -18, 24.5], [26, 1, 18, 24.5], [1, 46, -32.5, 0], [1, 46, 32.5, 0], [64, 1, 0, -24.5],
  ]) {
    const h = new THREE.Mesh(new THREE.BoxGeometry(w, 0.8, d), hedgeMat);
    h.position.set(x, 0.4, z);
    h.castShadow = h.receiveShadow = true;
    scene.add(h);
  }

  // trees
  const spots = [];
  for (let x = -60; x <= 60; x += 9) spots.push([x, 27.8], [x + 4.5, 40.2]);
  for (const [x, z] of [[-26, 18], [26, 18], [-26, -18], [26, -18], [-20, -20], [20, -20], [-28, 6], [28, 6], [-28, -6], [28, -6]]) spots.push([x, z]);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  while (spots.length < 130) {
    const x = (rnd() - 0.5) * 260, z = (rnd() - 0.5) * 220;
    if (Math.abs(x) < 36 && Math.abs(z) < 28) continue;
    if (Math.abs(z - 34) < 9) continue;
    spots.push([x, z]);
  }
  const trunks = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.15, 0.22, 1, 8), std(0x6b4f3a), spots.length);
  const crowns = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), std(0xffffff, 0.9), spots.length);
  trunks.castShadow = crowns.castShadow = true;
  crowns.receiveShadow = true;
  const q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), col = new THREE.Color();
  spots.forEach(([x, z], i) => {
    const h = 2.2 + rnd() * 1.6, r = 1.6 + rnd() * 1.2;
    trunks.setMatrixAt(i, m4.compose(p.set(x, h / 2, z), q.identity(), s.set(1, h, 1)));
    crowns.setMatrixAt(i, m4.compose(p.set(x, h + r * 0.7, z), q.setFromEuler(new THREE.Euler(0, rnd() * 3, 0)), s.set(r, r * 1.15, r)));
    crowns.setColorAt(i, col.setHSL(0.24 + rnd() * 0.06, 0.38, 0.32 + rnd() * 0.1));
  });
  scene.add(trunks, crowns);

  // street lamps along the plaza
  const poleMat = std(0x30343a, 0.6);
  const lampGeo = new THREE.CylinderGeometry(0.06, 0.08, 4.5, 8);
  for (const x of [-24, -12, 12, 24]) {
    const pole = new THREE.Mesh(lampGeo, poleMat);
    pole.position.set(x, 2.25, 25.5);
    pole.castShadow = true;
    scene.add(pole);
  }

  // parked cars
  const carColors = [0xd9dde2, 0x2f3a4a, 0xa83232, 0x1d1f22, 0x8e9aa6, 0xe8e4da, 0x3f6a8a];
  for (let i = 0; i < 12; i++) {
    const car = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.75, 1.8), new THREE.MeshStandardMaterial({ color: carColors[i % carColors.length], roughness: 0.35, metalness: 0.4 }));
    body.position.y = 0.55;
    const cab = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.6, 1.6), new THREE.MeshStandardMaterial({ color: 0x2a3036, roughness: 0.2, metalness: 0.5 }));
    cab.position.set(-0.2, 1.2, 0);
    body.castShadow = cab.castShadow = true;
    car.add(body, cab);
    car.position.set(-70 + i * 12 + rnd() * 3, 0, i % 2 ? 30.3 : 37.7);
    scene.add(car);
  }

  // neighbouring buildings
  const wt = windowTexture();
  for (const [w, h, d, x, z] of [
    [24, 19.2, 16, -72, -48], [18, 28.8, 18, 66, -54], [16, 12.8, 26, -84, 18], [20, 16, 20, 88, 12],
    [32, 22.4, 14, -26, -84], [24, 35.2, 16, 30, -90], [40, 16, 14, -60, 78], [30, 25.6, 16, 50, 80],
  ]) {
    const mats = [w, w, w, d, d, d].map(() => null);
    const side = (len) => {
      const t = wt.clone();
      t.repeat.set(len / 3, h / 3.2);
      t.needsUpdate = true;
      return new THREE.MeshStandardMaterial({ map: t, roughness: 0.9 });
    };
    const roof = std(0xb9b4ab);
    mats[0] = mats[1] = side(d);
    mats[2] = mats[3] = roof;
    mats[4] = mats[5] = side(w);
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mats);
    b.position.set(x, h / 2, z);
    b.castShadow = b.receiveShadow = true;
    scene.add(b);
  }

  return { sun };
}
