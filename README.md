# herdr-recap

A [herdr](https://herdr.dev) plugin for people juggling several coding agents.
It answers "what was that agent doing again?" and "which one did I touch last?"

- **Recap popup** (`prefix` + `a`): every Claude Code agent in your herdr
  session, with a short recap of what it was working on and what comes next.
- **Newest first** (`prefix` + `t`): the Agents sidebar puts the agent with the
  most recent activity at the top. Turn it on once and it stays on.

## Recap popup

![The recap popup, listing four Claude Code agents with their status and a short recap](docs/screenshot.png)

<sub>Demo data. Rebuild the picture with `docs/make_demo.py`.</sub>

- Agents that need you come first, then done, working, and idle ones.
- Press a number to jump to that agent's pane.
- No AI calls and no cost. It reads the recap that Claude Code already writes
  into its chat file after you step away. When there is no recap yet, or it is
  older than your last message, it shows your last request and Claude's last
  reply instead.

## Install

```bash
herdr plugin install homur/herdr-recap
herdr integration install claude      # lets herdr match each pane to its chat
```

Then bind keys in `~/.config/herdr/config.toml` (herdr binds no plugin keys
by default) and reload:

```toml
[[keys.command]]
key = "prefix+a"
type = "plugin_action"
command = "homur.recap.open"
description = "agent recap"

[[keys.command]]
key = "prefix+t"
type = "plugin_action"
command = "homur.recap.toggle-sort"
description = "agents: newest first on/off"
```

```bash
herdr server reload-config
```

Now press `prefix` then `a` for the recap, and `prefix` then `t` to turn
newest-first on. Pick other keys if these clash with yours; `prefix+?` lists
the keys in use.

## Newest first

herdr's Agents sidebar groups agents by workspace. With newest first on, the
agent whose state changed last (it started working, finished, or asked you
something) moves to the top. Write to an agent and it jumps up; agents you
have left alone sink down.

- `prefix` + `t` switches between newest first and herdr's normal order. A
  small notification says which one is active.
- It is off until you turn it on.
- The choice survives restarts. herdr forgets sidebar orderings when its
  server stops, so the plugin saves your choice and re-applies it each time
  herdr starts.
- It changes only the sidebar. It does not change `herdr agent list`,
  notifications, or the recap popup.

## Requirements

- herdr 0.9.0 or newer
- Claude Code
- `python3` (standard library only)
- Linux or macOS. Tested on Linux (WSL2).

## How it works

**Recap popup**

1. Lists herdr panes running Claude Code (`herdr pane list`).
2. Finds each pane's chat file through the session id that herdr's Claude
   integration reports. Chats started before the integration was installed
   fall back to the newest chat file for that folder.
3. Reads the latest `away_summary` recap, your last message, and Claude's
   last reply from `~/.claude/projects/` (or `$CLAUDE_CONFIG_DIR/projects/`).

Nothing is sent anywhere. The plugin only reads local files.

**Newest first** sets a herdr agent view (`agent.view.set`) sorted by
`state_change_seq`, newest first. Your choice is saved in
`$HERDR_PLUGIN_STATE_DIR/sort`, and a startup hook re-applies it.

## Troubleshooting

**"no chat history found"** — herdr cannot link that pane to a chat yet. Run
`herdr integration install claude`, then restart Claude in that pane.

**No recap line** — Claude Code writes recaps only after you have been away
from a chat for a while, and only when recaps are on (`/config` in Claude Code).

**Newest first is off after a restart** — check the saved choice and the
startup log:

```bash
cat ~/.local/state/herdr/plugins/homur.recap/sort    # want: recent
herdr plugin log list --plugin homur.recap
```

**Key does nothing** — check that the plugin is enabled and the action exists:

```bash
herdr plugin list
herdr plugin action list --plugin homur.recap
herdr plugin log list --plugin homur.recap
```

## License

MIT
