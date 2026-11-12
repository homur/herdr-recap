"""Recent-first ordering for herdr's Agents sidebar.

    python3 sort.py apply    # re-apply the saved choice (runs at herdr startup)
    python3 sort.py toggle   # switch between "recent" and herdr's default order

"recent" puts the agent whose state changed last (started working, finished,
asked a question) at the top. The choice is saved in the plugin state dir,
because herdr forgets agent views when the server restarts.
"""
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

PLUGIN_ID = os.environ.get("HERDR_PLUGIN_ID", "homur.recap")
SOURCE = f"plugin:{PLUGIN_ID}"
STATE = Path(os.environ.get("HERDR_PLUGIN_STATE_DIR", ".")) / "sort"
SOCKET = os.environ.get("HERDR_SOCKET_PATH") or os.path.expanduser("~/.config/herdr/herdr.sock")
HERDR = os.environ.get("HERDR_BIN_PATH") or "herdr"


def call(method, params):
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(SOCKET)
        s.sendall((json.dumps({"id": "recap-sort", "method": method, "params": params}) + "\n").encode())
        return json.loads(s.makefile().readline())


def apply(mode):
    if mode == "recent":
        return call("agent.view.set", {
            "source": SOURCE,
            "label": "recent first",
            "sort": [{"field": "state_change_seq", "order": "desc"}],
        })
    return call("agent.view.clear", {"source": SOURCE})


def main():
    mode = STATE.read_text().strip() if STATE.exists() else "default"
    if sys.argv[1:] == ["toggle"]:
        mode = "default" if mode == "recent" else "recent"
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(mode + "\n")
    reply = apply(mode)
    if "error" in reply:
        print(json.dumps(reply), file=sys.stderr)
        sys.exit(1)
    if sys.argv[1:] == ["toggle"]:
        title = "Agents: newest first" if mode == "recent" else "Agents: herdr default order"
        subprocess.run([HERDR, "notification", "show", title, "--sound", "none"], capture_output=True)


if __name__ == "__main__":
    main()
