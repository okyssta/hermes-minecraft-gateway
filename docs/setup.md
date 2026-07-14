# Setup Guide

## Prerequisites

- **Hermes Agent** — installed and running (`hermes gateway run` or systemd service)
- **Node.js** >= 22 (`node --version`)
- **A Minecraft server** — accessible from the Hermes machine (offline or online mode)
- **npm** — for installing Mineflayer deps

## Step 1: Install the Plugin

```bash
# Clone the repo
git clone https://github.com/kyssta-exe/hermes-minecraft-gateway ~/.hermes/plugins/minecraft

# Install Node.js dependencies
cd ~/.hermes/plugins/minecraft/bridge
npm install --production --no-audit --no-fund
```

> Already have it? `cd ~/.hermes/plugins/minecraft && git pull`

## Step 2: Configure Env Vars

### Option A: Systemd drop-in (recommended for persistent setups)

Create `~/.config/systemd/user/hermes-gateway.service.d/minecraft.conf`:

```ini
[Service]
Environment="MINECRAFT_ENABLED=true"
Environment="MINECRAFT_SERVER=127.0.0.1"
Environment="MINECRAFT_PORT=25565"
Environment="MINECRAFT_USERNAME=HermesBot"
Environment="MINECRAFT_AUTH=offline"
Environment="MINECRAFT_ALLOW_ALL_USERS=true"
Environment="MINECRAFT_PREFIX=$"
```

Then reload and restart:

```bash
systemctl --user daemon-reload
systemctl --user restart hermes-gateway
```

### Option B: Export before running Hermes

```bash
export MINECRAFT_ENABLED=true
export MINECRAFT_SERVER=127.0.0.1
export MINECRAFT_PORT=25565
export MINECRAFT_USERNAME=HermesBot
export MINECRAFT_AUTH=offline
export MINECRAFT_ALLOW_ALL_USERS=true
export MINECRAFT_PREFIX=$
hermes gateway restart
```

### Option C: Hermes config

```bash
hermes config set minecraft.enabled true
hermes config set minecraft.server 127.0.0.1
hermes config set minecraft.port 25565
# ... etc
hermes gateway restart
```

## Step 3: Verify it's running

```bash
# Check gateway logs
journalctl --user -u hermes-gateway --no-pager -n 20 | grep -i minecraft

# Check bridge health
curl -s http://127.0.0.1:13000/health

# Expected response:
# {"status":"connected","players":["HermesBot","iQvt"],"username":"HermesBot"}
```

## Step 4: Join the Minecraft server

Join your server. The bot should be online and wandering. Type something in chat:

```
hello
```

Hermes should reply. Try a command:

```
$help
```

## Microsoft Auth (Online Mode)

For online-mode servers, set `MINECRAFT_AUTH=microsoft`. Mineflayer will prompt with a device code URL on first launch:

```bash
export MINECRAFT_AUTH=microsoft
hermes gateway restart
```

Check the bridge logs for the device code URL, visit it, and enter the code.

## Troubleshooting

### "Bot connects then gets kicked"

Check for illegal characters. The adapter strips non-Latin-1 characters automatically. If you see "Illegal characters in chat" in the server logs, it's likely the username itself — use a plain ASCII username.

### "No response from Hermes"

1. Check the bridge is connected: `curl -s http://127.0.0.1:13000/health`
2. Check logs: `journalctl --user -u hermes-gateway --no-pager -n 50 | grep minecraft`
3. Check bridge logs: `cat ~/.hermes/logs/minecraft-bridge.log`
4. Make sure `MINECRAFT_ENABLED=true` is set

### "The bot isn't moving"

The idle wander loop runs every 8-15 seconds. If the bot is receiving messages, it's working fine. Wandering is a background cosmetic feature.

### Gateway restart blocked

If `hermes gateway restart` says "Blocked: cannot restart from inside the gateway process":

```bash
systemctl --user restart hermes-gateway
```
