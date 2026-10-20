"""Screenshot a Play Keralam page as a phone shows it, from a local copy of the site.

    python3 shoot.py --site <site checkout> --date YYYY-MM-DD --page /wordle/ --out shot.png [--lang ml] [--keep-help]

The clock is set to 8 pm India time on the day BEFORE --date, so a daily game shows a puzzle that is
already over by the time the post goes out (no spoiler). The "how to play" box is closed unless
--keep-help is given. Output is 780x1688 (a 390x844 phone at 2x).
"""
import argparse
import datetime as dt
import functools
import http.server
import socketserver
import threading

from playwright.sync_api import sync_playwright


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="ml")
    ap.add_argument("--keep-help", action="store_true")
    ap.add_argument("--wait", type=int, default=1500)
    a = ap.parse_args()

    server = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=a.site))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    y, m, d = map(int, a.date.split("-"))
    when = dt.datetime(y, m, d, 20, 0, tzinfo=ist) - dt.timedelta(days=1)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                  locale="en-IN", timezone_id="Asia/Kolkata", is_mobile=True, has_touch=True)
        ctx.add_init_script(f"try {{ localStorage.setItem('keralamtimes.lang', '{a.lang}'); }} catch (e) {{}}")
        page = ctx.new_page()
        page.clock.install(time=when)
        page.goto(f"http://127.0.0.1:{port}{a.page}", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(a.wait)
        if not a.keep_help:
            page.evaluate("""() => {
              document.querySelectorAll('dialog[open]').forEach(d => { try { d.close(); } catch (e) {} });
              const h = document.getElementById('help');
              if (h) { try { if (h.close) h.close(); } catch (e) {} h.hidden = true; h.style.display = 'none'; }
            }""")
            page.wait_for_timeout(300)
        page.screenshot(path=a.out)
        browser.close()
    server.shutdown()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
