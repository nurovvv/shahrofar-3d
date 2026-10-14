// Renderer and frame pipeline.
//   high: scene -> (4x MSAA, half-float) -> ambient occlusion (N8AO) -> tone mapping -> screen
//   low:  scene -> tone mapping -> screen, directly (no extra passes: phones, older laptops)
// Exposure and tone mapping are the same in both, so the two levels differ in detail, not in look.
import * as THREE from 'three';
import { EffectComposer, EffectPass, RenderPass, ToneMappingEffect, ToneMappingMode } from 'postprocessing';
import { N8AOPostPass } from 'n8ao';
import { Q } from './quality.js';

const params = new URLSearchParams(location.search);
export const EXPOSURE = +(params.get('exposure') ?? 1.0);
// tone mapping: Khronos PBR Neutral keeps the colours of the materials as they are (no extra
// saturation or contrast) and rolls off only the highlights; ?tonemap=agx|aces to compare
const TONE = { agx: [THREE.AgXToneMapping, ToneMappingMode.AGX], neutral: [THREE.NeutralToneMapping, ToneMappingMode.NEUTRAL], aces: [THREE.ACESFilmicToneMapping, ToneMappingMode.ACES_FILMIC] }[params.get('tonemap') ?? 'neutral'];

export function createRenderer() {
  const probe = document.createElement('canvas');
  if (!window.WebGL2RenderingContext || !probe.getContext('webgl2')) throw new Error('WebGL 2 is not available');
  const renderer = new THREE.WebGLRenderer({
    antialias: Q.level !== 'high', // high renders into a multisampled target instead
    powerPreference: 'high-performance',
    stencil: false,
  });
  renderer.setPixelRatio(Q.pixelRatio);
  renderer.setSize(innerWidth, innerHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMappingExposure = EXPOSURE;
  return renderer;
}

export function createPipeline(renderer, scene, camera) {
  if (Q.level !== 'high') {
    renderer.toneMapping = TONE[0];
    return {
      render: () => renderer.render(scene, camera),
      setSize: (w, h) => renderer.setSize(w, h),
      walk: () => {},
      ao: null,
    };
  }
  renderer.toneMapping = THREE.NoToneMapping; // done by the last pass
  const composer = new EffectComposer(renderer, { multisampling: 4, frameBufferType: THREE.HalfFloatType });
  composer.addPass(new RenderPass(scene, camera));
  const ao = new N8AOPostPass(scene, camera, innerWidth, innerHeight);
  Object.assign(ao.configuration, {
    aoRadius: 2.2, // metres: under balconies, at the foot of walls, where planters meet paving
    distanceFalloff: 0.6,
    intensity: 2.2,
    aoSamples: 16,
    denoiseSamples: 8,
    denoiseRadius: 10,
    halfRes: true,
    depthAwareUpsampling: true,
    gammaCorrection: false,
    color: new THREE.Color(0x0b0d10),
  });
  composer.addPass(ao);
  const tone = new ToneMappingEffect({ mode: TONE[1] });
  composer.addPass(new EffectPass(camera, tone));
  return {
    render: (dt) => composer.render(dt),
    setSize: (w, h) => {
      renderer.setSize(w, h);
      composer.setSize(w, h);
    },
    // inside a flat: smaller radius, rooms are a few metres across
    walk: (on) => {
      ao.configuration.aoRadius = on ? 0.7 : 2.2;
      ao.configuration.distanceFalloff = on ? 0.4 : 0.6;
      ao.configuration.intensity = on ? 1.6 : 2.2;
    },
    ao,
  };
}
