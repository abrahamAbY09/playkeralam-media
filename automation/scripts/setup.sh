#!/usr/bin/env bash
# One-time setup for a fresh session: fonts, the voice runtime and the two Malayalam voices.
# Safe to run again; it skips what is already there. Everything lands in automation/.cache (git-ignored).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${PK_CACHE:-$HERE/.cache}"
mkdir -p "$CACHE/fonts" "$CACHE/voices"

if [ ! -f "$CACHE/fonts/node_modules/@fontsource/manjari/700.css" ]; then
  (cd "$CACHE/fonts" && npm init -y >/dev/null 2>&1 && npm install --silent @fontsource/baloo-chettan-2 @fontsource/manjari)
fi

python3 -c "import sherpa_onnx" 2>/dev/null || pip install --quiet --break-system-packages sherpa-onnx
python3 -c "import playwright" 2>/dev/null || pip install --quiet --break-system-packages playwright
python3 -c "import numpy, PIL" 2>/dev/null || pip install --quiet --break-system-packages numpy pillow

for v in vits-piper-ml_IN-arjun-medium vits-piper-ml_IN-meera-medium; do
  if [ ! -f "$CACHE/voices/$v/tokens.txt" ]; then
    curl -sSL -m 600 -o "$CACHE/voices/$v.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/$v.tar.bz2"
    tar -xjf "$CACHE/voices/$v.tar.bz2" -C "$CACHE/voices" && rm "$CACHE/voices/$v.tar.bz2"
  fi
done

command -v ffmpeg >/dev/null || echo "WARNING: ffmpeg is missing; reels need it."
echo "setup ok: $CACHE"
