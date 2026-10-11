// Sky, sun, trees, cars and people. Ground, roads, river and neighbours come with the model.
import * as THREE from 'three';
import { CARS, PEOPLE, TREES, toScene } from './config.js';
import { addCars, addPeople, addTrees } from './props.js';

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
  sky.userData.isSky = true;
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

  // trees, cars and people (positions from the Blender build)
  addTrees(scene, TREES.protos, TREES.list, toScene);
  addCars(scene, CARS, toScene);
  addPeople(scene, PEOPLE, toScene);

  return { sun, sky };
}
