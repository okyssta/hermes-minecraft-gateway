# Hermes Minecraft Gateway ⛏️

A first-class [Hermes Agent](https://hermes-agent.nousresearch.com) platform plugin that lets you chat with Hermes directly inside **Minecraft**.

Join a Minecraft server with a Mineflayer bot, and every player gets their own Hermes session — same features as Discord, Telegram, or WhatsApp. Tools, commands, code execution, file editing — all accessible from in-game chat.

![Minecraft](https://img.shields.io/badge/Minecraft-1.21.11-green)
![Hermes](https://img.shields.io/badge/Hermes-Plugin-blue)
![Node](https://img.shields.io/badge/Node-%3E%3D22-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12-blue)

## Features

- **Per-player sessions** — each player gets their own Hermes session (like DMs on Discord)
- **Full command support** — `$new`, `$help`, `$model`, `$stop` all work in chat
- **Rich formatting** — use Minecraft § codes for bold, italic, colors
- **Public chat responses** — Hermes replies in public chat with `§lbold§r`, `§oitalic§r`, colors
- **Private tool progress** — terminal/file operations go via `/tell` private whisper
- **Auto-wander** — the bot wanders, jumps, and looks at nearby players
- **256-char chunking** — long responses split with `[1/3]` markers
- **Configurable prefix** — `$command` syntax keeps server commands from conflicting
- **Offline or Microsoft auth** — supports both offline and online-mode servers
- **Persistence** — survives gateway restarts via systemd drop-in

## Quick Start

### Prerequisites

- Hermes Agent installed and running (`hermes gateway run`)
- Node.js >= 22
- A Minecraft server (offline or online mode)
- Python 3.12+

### Installation

The plugin lives at `~/.hermes/plugins/minecraft/`. Install it:

```bash
# Clone or copy the plugin
git clone https://github.com/kyssta-exe/hermes-minecraft-gateway ~/.hermes/plugins/minecraft
# or symlink:
ln -sf /path/to/hermes-minecraft-gateway ~/.hermes/plugins/minecraft

# Install Node dependencies
cd ~/.hermes/plugins/minecraft/bridge
npm install --production --no-audit --no-fund
```

### Configuration

Set environment variables (via systemd drop-in, `.env`, or `hermes config`):

```bash
export MINECRAFT_ENABLED=true
export MINECRAFT_SERVER=your.server.ip
export MINECRAFT_PORT=25565
export MINECRAFT_USERNAME=HermesBot
export MINECRAFT_AUTH=offline    # or "microsoft"
export MINECRAFT_PREFIX=$        # prefix for Hermes commands ($new, $help)
export MINECRAFT_ALLOW_ALL_USERS=true
```

Or create a systemd drop-in at `~/.config/systemd/user/hermes-gateway.service.d/minecraft.conf`:

```ini
[Service]
Environment="MINECRAFT_ENABLED=true"
Environment="MINECRAFT_SERVER=your.server.ip"
Environment="MINECRAFT_PORT=25565"
Environment="MINECRAFT_USERNAME=HermesBot"
Environment="MINECRAFT_AUTH=offline"
Environment="MINECRAFT_ALLOW_ALL_USERS=true"
Environment="MINECRAFT_PREFIX=$"
```

### Starting

```bash
# Reload systemd, then restart gateway
systemctl --user daemon-reload
systemctl --user restart hermes-gateway

# Or if running in foreground:
hermes gateway restart
```

### Usage

Join your Minecraft server. The bot (`HermesBot`) will be wandering around.

| What to type | What happens |
|---|---|
| `hi` | Hermes replies in public chat |
| `$new` | Reset your session |
| `$help` | Show available commands |
| `$model` | Show current LLM model |
| `write a poem` | Hermes writes and responds |
| `what's the time?` | Hermes checks and replies |

> **Tip:** The `$` prefix is only needed for commands. Regular chat goes straight to Hermes.

## Minecraft Formatting

Hermes uses Minecraft's § (section-sign) color codes in responses:

| Code | Effect | Example |
|---|---|---|
| `§ltext§r` | **Bold** | `§lHello§r` → **Hello** |
| `§otext§r` | *Italic* | `§oHello§r` → *Hello* |
| `§ntext§r` | Underline | `§nHello§r` → <ins>Hello</ins> |
| `§mtext§r` | Strikethrough | `§mHello§r` → ~~Hello~~ |
| `§7text§r` | Gray (inline code) | `§7const x = 1§r` |
| `§a` | Green | |
| `§c` | Red | |
| `§e` | Yellow | |
| `§r` | Reset formatting | Always close with `§r` |

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `MINECRAFT_ENABLED` | — | Required: `true` to enable the adapter |
| `MINECRAFT_SERVER` | — | Required: Minecraft server hostname/IP |
| `MINECRAFT_PORT` | `25565` | Server port |
| `MINECRAFT_USERNAME` | `HermesBot` | Bot's in-game username |
| `MINECRAFT_AUTH` | `offline` | `offline` or `microsoft` |
| `MINECRAFT_PREFIX` | `` (none) | Command prefix (`$new`, `$help`). Empty = no prefix |
| `MINECRAFT_PRIVATE_MESSAGES` | `false` | `true` = all replies via `/tell` private |
| `MINECRAFT_BRIDGE_PORT` | `13000` | Internal bridge HTTP port |
| `MINECRAFT_ALLOWED_USERS` | — | Comma-separated allowlist of usernames |
| `MINECRAFT_ALLOW_ALL_USERS` | `false` | `true` = any player can use the bot |
| `MINECRAFT_HOME_CHANNEL` | — | Default player for cron/notification delivery |

## Architecture

```
Minecraft Server
      ↑ Mineflayer (TCP/MC protocol)
      ↓
Node.js Bridge (bridge/index.js)
  - Mineflayer bot
  - HTTP server (health, messages, send)
  - Idle wander loop
      ↑ HTTP poll (500ms)
      ↓
Python Adapter (adapter.py)
  - Hermes BasePlatformAdapter
  - Per-player session management
  - Message chunking (256-char limit)
  - § formatting / markdown conversion
      ↑
      ↓
Hermes Gateway
  - LLM + tools
  - Command dispatch
  - Session persistence
```

## File Structure

```
hermes-minecraft-gateway/
├── README.md              # You are here
├── LICENSE                # MIT
├── CHANGELOG.md           # Release history
├── plugin.yaml            # Hermes plugin metadata
├── __init__.py            # Plugin entry point
├── adapter.py             # Python adapter (gateway integration)
├── bridge/
│   ├── package.json       # Node deps
│   └── index.js           # Mineflayer bot + HTTP bridge
├── docs/
│   ├── setup.md           # Detailed setup guide
│   ├── commands.md        # Command reference
│   ├── configuration.md   # All config options
│   ├── architecture.md    # Architecture deep-dive
│   └── formatting.md      # Minecraft § codes reference
└── scripts/
    └── install.sh         # One-shot install script
```

## Development

```bash
# Clone the repo
git clone https://github.com/kyssta-exe/hermes-minecraft-gateway
cd hermes-minecraft-gateway

# Install Python deps (none extra — uses Hermes gateway packages)
# Install Node deps
cd bridge && npm install

# Symlink to Hermes plugins
ln -sf $PWD ~/.hermes/plugins/minecraft

# Set env vars and restart gateway
hermes gateway restart
```

## Version History

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT © Kyssta
