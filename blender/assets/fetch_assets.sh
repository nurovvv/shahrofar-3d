#!/usr/bin/env bash
# Download the CC0 assets the Blender build uses (Poly Haven, https://polyhaven.com, CC0).
# Poly Haven's own servers first; the three.js repository mirrors some of the same HDRIs.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p hdri
get() {  # get <dest> <url>...
  local dest=$1; shift
  [[ -s "$dest" ]] && return 0
  for url in "$@"; do
    if curl -fsSL -m 300 -o "$dest.part" "$url"; then mv "$dest.part" "$dest"; echo "got $dest"; return 0; fi
  done
  rm -f "$dest.part"; echo "could not download $dest" >&2; return 1
}
get hdri/san_giuseppe_bridge_2k.hdr \
  https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/san_giuseppe_bridge_2k.hdr \
  https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/equirectangular/san_giuseppe_bridge_2k.hdr
