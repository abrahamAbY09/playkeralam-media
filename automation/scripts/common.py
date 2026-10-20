"""Shared paths, brand colours, fonts and helpers for the Play Keralam post and reel scripts."""
import html
import json
import os
import pathlib

AUTOMATION = pathlib.Path(__file__).resolve().parent.parent
REPO = AUTOMATION.parent
CACHE = pathlib.Path(os.environ.get("PK_CACHE", AUTOMATION / ".cache"))
ASSETS = AUTOMATION / "assets"

CONFIG = json.loads((AUTOMATION / "config.json").read_text(encoding="utf-8"))
GAMES = json.loads((AUTOMATION / "games.json").read_text(encoding="utf-8"))["games"]

INK = "#1d1a16"
CREAM = "#FFF6E0"
YELLOW = "#FFC23C"
YELLOW2 = "#FFD472"
GREEN = "#1FA35C"
RED = "#E8452C"
BLUE = "#2C6BE0"
PINK = "#FF8FB1"
DARK = "#16271f"


def esc(text):
    """Escape text for HTML and keep line breaks."""
    return html.escape(str(text or "")).replace("\n", "<br>")


def fonts_head():
    """Link tags for Baloo Chettan 2 and Manjari from the local @fontsource install (setup.sh)."""
    base = CACHE / "fonts" / "node_modules" / "@fontsource"
    links = []
    for pkg, weights in (("baloo-chettan-2", (600, 800)), ("manjari", (400, 700))):
        for w in weights:
            css = base / pkg / f"{w}.css"
            if not css.exists():
                raise SystemExit(f"Missing font {css}. Run automation/scripts/setup.sh first.")
            links.append(f'<link rel="stylesheet" href="file://{css}">')
    return "".join(links)


def logo_uri(file_name):
    path = ASSETS / "logos" / file_name
    if not path.exists():
        raise SystemExit(f"Missing logo {path}")
    return f"file://{path}"


def badge_uri():
    return logo_uri("play-keralam.png")


def game(game_id):
    if game_id not in GAMES:
        raise SystemExit(f"Unknown game '{game_id}'. Known: {', '.join(GAMES)}")
    return GAMES[game_id]


def shade(hex_color, factor):
    """Lighten (factor > 1) or darken (factor < 1) a #RRGGBB colour."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if factor >= 1:
        r, g, b = (int(c + (255 - c) * (factor - 1)) for c in (r, g, b))
    else:
        r, g, b = (int(c * factor) for c in (r, g, b))
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


def is_dark(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0.299 * r + 0.587 * g + 0.114 * b) < 150


def luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b
