// The complex (three towers, podium, surroundings), loaded from the Blender export.
// Floors of every tower are separate objects so they can be hidden for the cut-away view,
// and every apartment has an invisible pick volume used for hovering and highlighting.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { MODEL_URL, toScene, towerByKey } from './config.js';

const GLASS = new Set(['Window glass', 'Curtain glass', 'Shop glass', 'Pool water', 'River']);

function tuneMaterial(m) {
  if (GLASS.has(m.name)) {
    m.envMapIntensity = 1.4;
    m.roughness = Math.min(m.roughness, 0.12);
  }
  if (m.name === 'Railing glass' || m.name === 'Neighbour') {
    m.transparent = true;
    m.depthWrite = false;
    m.side = THREE.DoubleSide;
  }
  if (m.name.startsWith('Leaves') || m.name === 'Shrub' || m.name === 'Grass' || m.name === 'Lawn') m.envMapIntensity = 0.4;
}

export async function loadComplex(apartments, onProgress) {
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const gltf = await loader.loadAsync(MODEL_URL, (e) => e.total && onProgress?.(e.loaded / e.total));
  const root = gltf.scene;
  const o = toScene(0, 0);
  root.position.set(o.x, 0, o.z);

  const towers = {}; // key -> { floors: { n: { slab, walls } }, roof }
  const tower = (k) => (towers[k] ??= { floors: {}, roof: null });
  const picks = [];
  const tuned = new Set();

  root.traverse((obj) => {
    const d = obj.userData;
    if (d.pick) {
      picks.push(obj);
      return;
    }
    if (obj.isMesh) {
      obj.castShadow = true;
      obj.receiveShadow = true;
      for (const m of [obj.material].flat()) {
        if (!tuned.has(m)) {
          tuneMaterial(m);
          tuned.add(m);
        }
        if (m.transparent) obj.castShadow = false;
      }
    }
    if (d.tower && d.part === 'roof') tower(d.tower).roof = obj;
    else if (d.tower && d.floor) {
      const f = (tower(d.tower).floors[d.floor] ??= {});
      f[d.part === 'walls' ? 'walls' : 'slab'] = obj;
    }
  });

  // pick volumes -> highlight overlays
  const units = new Map();
  let hotelPick = null;
  const box = new THREE.Box3();
  root.updateMatrixWorld(true);
  for (const mesh of picks) {
    mesh.material = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false });
    mesh.renderOrder = 10;
    mesh.visible = false;
    mesh.castShadow = mesh.receiveShadow = false;
    const d = mesh.userData;
    if (d.hotel) {
      mesh.userData.hotel = towerByKey[d.tower];
      hotelPick = mesh;
      continue;
    }
    const id = `${d.tower}${d.floor}${d.unit}`;
    const apt = apartments.find((a) => a.id === id);
    if (!apt) continue;
    mesh.userData.apt = apt;
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(mesh.geometry, 35),
      new THREE.LineBasicMaterial({ transparent: true, opacity: 0.95 }),
    );
    edges.renderOrder = 11;
    edges.visible = false;
    mesh.add(edges);
    box.setFromObject(mesh);
    const c = box.getCenter(new THREE.Vector3());
    units.set(apt.id, { overlay: mesh, edges, center: new THREE.Vector3(c.x, apt.place.baseY, c.z), top: box.max.y });
  }

  const each = (fn) => {
    for (const [k, t] of Object.entries(towers)) {
      for (const [n, f] of Object.entries(t.floors)) fn(k, +n, f, t);
    }
  };
  const setVisible = (o, v) => o && (o.visible = v);

  return {
    group: root,
    towers,
    units,
    hotelPick,
    pickables: [...units.values()].map((u) => u.overlay).concat(hotelPick ? [hotelPick] : []),
    // Cut-away: hide everything above `floor` in `towerKey` and open up that floor.
    showUpTo(towerKey, floor) {
      each((k, n, f, t) => {
        const above = k === towerKey && n > floor;
        setVisible(f.slab, !above);
        setVisible(f.walls, !above && !(k === towerKey && n === floor));
        setVisible(t.roof, k !== towerKey);
      });
    },
    // Everything visible, except the walls of an apartment floor someone is walking around in.
    showAll(openTower = null, openFloor = null) {
      each((k, n, f, t) => {
        setVisible(f.slab, true);
        setVisible(f.walls, !(k === openTower && n === openFloor));
        setVisible(t.roof, true);
      });
    },
  };
}
