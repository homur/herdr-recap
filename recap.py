"""Herdr popup: a short recap of what each Claude agent was doing.

Reads the recap ("away_summary") that Claude Code writes into its chat file,
plus your last request and Claude's last reply. No AI calls, no cost.
Keys: 1-9 jump to that agent, any other key closes.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import termios
import textwrap
import tty
from datetime import datetime, timezone
from pathlib import Path

HERDR = os.environ.get("HERDR_BIN_PATH") or "herdr"
PROJECTS = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
STATUS = {  # order, color, label
    "blocked": (0, "\033[31m", "needs you"),
    "done": (1, "\033[32m", "done"),
    "working": (2, "\033[33m", "working"),
    "idle": (3, "\033[36m", "idle"),
}


def herdr(*args):
    out = subprocess.run([HERDR, *args], capture_output=True, text=True)
    try:
        return json.loads(out.stdout)["result"]
    except (ValueError, KeyError):
        return {}


def transcript_path(cwd, session_id):
    p = PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", cwd) / f"{session_id}.jsonl"
    if p.exists():
        return p
    hits = list(PROJECTS.glob(f"*/{session_id}.jsonl"))
    return hits[0] if hits else None


def newest(cwd):
    # Fallback for chats started before the herdr Claude hook: newest chat in that folder.
    files = sorted((PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", cwd)).glob("*.jsonl"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content
                         if isinstance(c, dict) and c.get("type") == "text")
    return ""


def read_transcript(path):
    info = {"recap": None, "recap_ts": None, "ask": None, "ask_ts": None,
            "reply": None, "last_ts": None}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = e.get("timestamp")
            if ts:
                info["last_ts"] = ts
            t = e.get("type")
            if t == "system" and e.get("subtype") == "away_summary":
                info["recap"] = re.sub(r"\s*\(disable recaps in /config\)\s*$",
                                       "", e.get("content", ""))
                info["recap_ts"] = ts
            elif t == "user" and not e.get("isMeta") and not e.get("isSidechain"):
                txt = text_of(e.get("message", {}).get("content")).strip()
                if txt and not txt.startswith("<"):
                    info["ask"], info["ask_ts"] = txt, ts
            elif t == "assistant" and not e.get("isSidechain"):
                txt = text_of(e.get("message", {}).get("content")).strip()
                if txt:
                    info["reply"] = txt
    return info


def ago(ts):
    if not ts:
        return "?"
    try:
        then = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return "?"
    s = int((datetime.now(timezone.utc) - then).total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{s // 60} min ago"
    if s < 86400:
        return f"{s // 3600} h ago"
    return f"{s // 86400} d ago"


def short(txt, limit):
    txt = " ".join(txt.split())
    return txt if len(txt) <= limit else txt[: limit - 1].rstrip() + "…"


def collect():
    labels = {w["workspace_id"]: w.get("label", w["workspace_id"])
              for w in herdr("workspace", "list").get("workspaces", [])}
    agents = []
    for p in herdr("pane", "list").get("panes", []):
        if p.get("agent") != "claude":
            continue
        pane = herdr("pane", "get", p["pane_id"]).get("pane", p)
        sess = (pane.get("agent_session") or {}).get("value")
        path = transcript_path(pane.get("cwd", ""), sess) if sess else newest(pane.get("cwd", ""))
        info = read_transcript(path) if path else {}
        agents.append({
            "pane": p["pane_id"],
            "space": labels.get(pane.get("workspace_id"), pane.get("workspace_id")),
            "title": pane.get("terminal_title_stripped") or "",
            "status": pane.get("agent_status", "unknown"),
            **info,
        })
    agents.sort(key=lambda a: (STATUS.get(a["status"], (9,))[0],
                               -(datetime.fromisoformat(a["last_ts"].replace("Z", "+00:00")).timestamp()
                                 if a.get("last_ts") else 0)))
    return agents


def render(agents):
    width = min(shutil.get_terminal_size((100, 40)).columns - 4, 110)
    wrap = lambda s, ind: textwrap.fill(s, width, initial_indent=ind, subsequent_indent=" " * len(ind))
    out = [f"{BOLD}Agent recap{RESET}  {DIM}{len(agents)} Claude agent(s){RESET}", ""]
    if not agents:
        out.append("No Claude agents are running in herdr.")
    for i, a in enumerate(agents, 1):
        _, color, label = STATUS.get(a["status"], (9, DIM, a["status"]))
        out.append(f"{BOLD}{i}{RESET}  {color}●{RESET} {BOLD}{a['space']}{RESET}"
                   f"  {color}{label}{RESET}  {DIM}{ago(a.get('last_ts'))}"
                   f"{'  · ' + a['title'] if a['title'] else ''}{RESET}")
        recap = a.get("recap")
        stale = recap and a.get("ask_ts") and a.get("recap_ts") and a["recap_ts"] < a["ask_ts"]
        if recap:
            out.append(wrap(short(recap, 400), "   Recap:  ")
                       + (f" {DIM}(older){RESET}" if stale else ""))
        if a.get("ask") and (not recap or stale):
            out.append(f"{DIM}" + wrap(short(a["ask"], 200), "   You:    ") + RESET)
        if a.get("reply") and (not recap or stale):
            out.append(f"{DIM}" + wrap(short(a["reply"], 250), "   Claude: ") + RESET)
        if not (recap or a.get("ask") or a.get("reply")):
            out.append(f"   {DIM}(no chat history found){RESET}")
        out.append("")
    if agents:
        out.append(f"{DIM}Press 1-{min(len(agents), 9)} to jump to an agent. Any other key closes.{RESET}")
    else:
        out.append(f"{DIM}Press any key to close.{RESET}")
    return "\n".join(out)


def getkey():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    agents = collect()
    sys.stdout.write("\033[2J\033[H" + render(agents) + "\n")
    sys.stdout.flush()
    key = getkey()
    if key.isdigit() and 1 <= int(key) <= min(len(agents), 9):
        subprocess.run([HERDR, "agent", "focus", agents[int(key) - 1]["pane"]],
                       capture_output=True)


if __name__ == "__main__":
    if "--print" in sys.argv:
        print(render(collect()))
    else:
        main()
