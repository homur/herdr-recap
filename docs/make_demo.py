"""Render the README screenshot page (docs/demo.html) from recap.py with fake agents.

    COLUMNS=86 python3 docs/make_demo.py

Then open docs/demo.html in a browser and screenshot the .window element.
"""
import html
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import recap  # noqa: E402


def ts(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


AGENTS = [
    {"pane": "w2:p1", "space": "api-server", "status": "blocked", "title": "Rate limiter tests",
     "last_ts": ts(2), "recap_ts": ts(3), "ask_ts": ts(40),
     "recap": "Adding a token-bucket rate limiter to the public API; all tests pass locally. "
              "Next: confirm the request limits for the free tier before I wire it into the gateway."},
    {"pane": "w3:p1", "space": "web", "status": "done", "title": "Checkout page layout",
     "last_ts": ts(25), "recap_ts": ts(20), "ask_ts": ts(60),
     "recap": "Reworked the checkout page for mobile; the form now fits on one screen and the "
              "pay button stays visible. Next: review the screenshots and approve the change."},
    {"pane": "w4:p1", "space": "docs", "status": "working", "title": "Migration guide",
     "last_ts": ts(0), "ask": "can you write the v2 migration guide, start with the breaking changes",
     "reply": "Sure. I found 6 breaking changes in the changelog. I will start with the new config format."},
    {"pane": "w5:p1", "space": "infra", "status": "idle", "title": "Nightly backup job",
     "last_ts": ts(180), "recap_ts": ts(170), "ask_ts": ts(200),
     "recap": "Moved the nightly database backup to object storage with 30-day retention. "
              "Next: run a restore test on staging."},
]

COLORS = {"31": "red", "32": "green", "33": "yellow", "36": "aqua"}


def ansi_to_html(text):
    out, classes = [], set()
    for part in re.split(r"(\033\[[0-9;]*m)", text):
        m = re.fullmatch(r"\033\[([0-9;]*)m", part)
        if m:
            for code in m.group(1).split(";"):
                if code in ("", "0"):
                    classes.clear()
                elif code == "1":
                    classes.add("b")
                elif code == "2":
                    classes.add("dim")
                elif code in COLORS:
                    classes = {c for c in classes if c not in COLORS.values()} | {COLORS[code]}
            continue
        if part:
            esc = html.escape(part)
            out.append(f'<span class="{" ".join(sorted(classes))}">{esc}</span>' if classes else esc)
    return "".join(out)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  body {{ margin:0; background:#1d2021; display:flex; justify-content:center; padding:32px; }}
  .window {{ background:#282828; border:1px solid #504945; border-radius:10px; padding:0 0 18px;
            box-shadow:0 18px 50px rgba(0,0,0,.5); }}
  .bar {{ color:#a89984; font:13px 'JetBrains Mono',monospace; padding:9px 16px; border-bottom:1px solid #3c3836; }}
  pre {{ margin:0; padding:16px 22px 0; color:#ebdbb2; font:15px/1.5 'JetBrains Mono',monospace; }}
  .b {{ font-weight:700; color:#fbf1c7; }} .dim {{ color:#928374; }}
  .red {{ color:#fb4934; }} .green {{ color:#b8bb26; }} .yellow {{ color:#fabd2f; }} .aqua {{ color:#8ec07c; }}
</style></head>
<body><div class="window"><div class="bar">herdr · prefix + a</div><pre>{body}</pre></div></body></html>
"""

if __name__ == "__main__":
    agents = sorted(AGENTS, key=lambda a: recap.STATUS[a["status"]][0])
    (ROOT / "docs" / "demo.html").write_text(PAGE.format(body=ansi_to_html(recap.render(agents))))
    print(recap.render(agents))
