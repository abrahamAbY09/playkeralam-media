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

# Always install with "python3 -m pip": plain "pip" can belong to a different Python than "python3" (it did on
# the cloud runner: pip was 3.13, python3 was 3.11), which left the scripts unable to import what was installed.
PY=python3
echo "using $($PY --version 2>&1) at $(command -v $PY)"
$PY -c "import sherpa_onnx" 2>/dev/null || $PY -m pip install --quiet --break-system-packages sherpa-onnx
$PY -c "import playwright" 2>/dev/null || $PY -m pip install --quiet --break-system-packages playwright
$PY -c "import numpy, PIL" 2>/dev/null || $PY -m pip install --quiet --break-system-packages numpy pillow

# The playwright package and the Chromium on the machine can be different revisions; the scripts cope with that
# (common.launch_chromium falls back to the installed Chromium). Check it works so a problem shows up here.
(cd "$HERE/scripts" && $PY - <<'PYEOF'
from playwright.sync_api import sync_playwright
from common import launch_chromium
with sync_playwright() as p:
    b = launch_chromium(p)
    b.close()
print("chromium ok")
PYEOF
) || echo "WARNING: no usable Chromium for Playwright; try: python3 -m playwright install chromium"

for v in vits-piper-ml_IN-arjun-medium vits-piper-ml_IN-meera-medium; do
  if [ ! -f "$CACHE/voices/$v/tokens.txt" ]; then
    curl -sSL -m 600 -o "$CACHE/voices/$v.tar.bz2" "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/$v.tar.bz2"
    tar -xjf "$CACHE/voices/$v.tar.bz2" -C "$CACHE/voices" && rm "$CACHE/voices/$v.tar.bz2"
  fi
done

command -v ffmpeg >/dev/null || echo "WARNING: ffmpeg is missing; reels need it."
echo "setup ok: $CACHE"
