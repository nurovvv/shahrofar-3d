#!/usr/bin/env bash
# Rebuild the 3D model of the complex and copy it into the web viewer.
#
#   pip install bpy shapely          # Blender as a Python module (Python 3.13), or run with a Blender 4.2+ binary
#   blender/export_web.sh            # writes public/models/shahrofar.glb and src/model/complex.json
#
# Also leaves build/shahrofar.blend (open it in Blender) and, with RENDER=1, build/shahrofar.png:
# a still from the camera that matches the aerial marketing render.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=${PYTHON:-python3}
OUT=build/shahrofar
mkdir -p build public/models src/model

args=(--out "$OUT")
if [[ "${RENDER:-0}" == "1" ]]; then args+=(--render "$OUT.png" --scale 1 --samples 64); fi

if command -v blender >/dev/null && [[ -z "${PYTHON:-}" ]]; then
  blender -b -P blender/build_complex.py -- "${args[@]}"
else
  "$PY" blender/build_complex.py "${args[@]}"
fi

# meshopt compression: ~11 MB -> ~2.6 MB
GT="npx --yes @gltf-transform/cli@4"
$GT dedup "$OUT.glb" "$OUT.dedup.glb"
$GT weld "$OUT.dedup.glb" "$OUT.weld.glb"
$GT meshopt "$OUT.weld.glb" public/models/shahrofar.glb
rm -f "$OUT.dedup.glb" "$OUT.weld.glb"
cp "$OUT.json" src/model/complex.json
ls -la public/models/shahrofar.glb src/model/complex.json
