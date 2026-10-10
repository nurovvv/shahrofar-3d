// Sky, sun and the street trees. Ground, roads, river and neighbours come with the model.
import * as THREE from 'three';
import { TREES, toScene } from './config.js';

export function buildWorld(scene) {
  // sky dome
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(2500, 32, 16),
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
  scene.fog = new THREE.Fog(0xdfe8f0, 450, 1600);

  // lights
  scene.add(new THREE.HemisphereLight(0xe2efff, 0x8d8068, 0.9));
  // morning sun from the east-south-east, like on the marketing renders
  const sun = new THREE.DirectionalLight(0xfff0dc, 2.8);
  sun.position.set(150, 120, 60);
  sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096);
  const sc = sun.shadow.camera;
  sc.left = -120;
  sc.right = 120;
  sc.top = 120;
  sc.bottom = -120;
  sc.near = 20;
  sc.far = 450;
  sun.shadow.bias = -0.0003;
  sun.shadow.normalBias = 0.05;
  scene.add(sun);

  // street and park trees (positions from the Blender build), drawn as two instanced meshes
  const { protos, list } = TREES;
  const trunks = new THREE.InstancedMesh(
    new THREE.CylinderGeometry(0.16, 0.24, 1, 7).translate(0, 0.5, 0),
    new THREE.MeshStandardMaterial({ color: 0x5a4030, roughness: 0.9 }),
    list.length,
  );
  const crowns = new THREE.InstancedMesh(
    new THREE.IcosahedronGeometry(1, 1),
    new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.9, flatShading: true }),
    list.length * 2,
  );
  trunks.castShadow = crowns.castShadow = true;
  crowns.receiveShadow = true;
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), s = new THREE.Vector3();
  const col = new THREE.Color(), e = new THREE.Euler();
  list.forEach(([x, y, sc, sz, rot, k], i) => {
    const { h, r, light } = protos[k];
    const w = toScene(x, y);
    q.setFromEuler(e.set(0, rot, 0));
    trunks.setMatrixAt(i, m4.compose(p.set(w.x, 0, w.z), q, s.set(sc, h * 0.55 * sz, sc)));
    crowns.setMatrixAt(2 * i, m4.compose(p.set(w.x, h * 0.68 * sz, w.z), q, s.set(r * sc, r * 0.9 * sc * sz, r * sc)));
    crowns.setMatrixAt(2 * i + 1, m4.compose(p.set(w.x + 0.3 * r * Math.cos(rot), h * 0.9 * sz, w.z + 0.3 * r * Math.sin(rot)), q, s.setScalar(r * 0.62 * sc)));
    col.setHSL(0.24 + ((i * 37) % 10) * 0.005, 0.45, light ? 0.24 : 0.18);
    crowns.setColorAt(2 * i, col);
    crowns.setColorAt(2 * i + 1, col);
  });
  scene.add(trunks, crowns);

  return { sun };
}
