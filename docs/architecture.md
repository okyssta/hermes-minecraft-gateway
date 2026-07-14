# Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Minecraft Server                   │
│                    (TCP 25565)                      │
└────────────────────┬────────────────────────────────┘
                     │ Mineflayer (MC protocol)
                     ▼
┌─────────────────────────────────────────────────────┐
│              Node.js Bridge (index.js)               │
│                                                     │
│  ┌─────────────┐  ┌──────────────────────────────┐  │
│  │ Mineflayer  │  │     HTTP Server (13000)       │  │
│  │ Bot         │  │                              │  │
│  │             │  │  GET /health   → status      │  │
│  │ • Connect   │  │  GET /messages → chat queue  │  │
│  │ • Chat      │  │  POST /send   → send chat   │  │
│  │ • Wander    │  │                              │  │
│  │ • Look      │  └──────────┬───────────────────┘  │
│  └─────────────┘             │                       │
└──────────────────────────────┼───────────────────────┘
                               │ HTTP (500ms poll)
                               ▼
┌─────────────────────────────────────────────────────┐
│              Python Adapter (adapter.py)             │
│                                                     │
│  MinecraftPlatformAdapter(BasePlatformAdapter)       │
│                                                     │
│  • Spawns/manages Node.js subprocess                │
│  • Polls /messages every 500ms                      │
│  • Creates per-player Hermes sessions               │
│  • Chunks responses at 256 characters               │
│  • Converts markdown to plain text                      │
│  • Strips non-Latin-1 characters                    │
│  • Routes tool progress → /tell private             │
│                                                     │
└────────────────────┬────────────────────────────────┘
                     │ Hermes Gateway API
                     ▼
┌─────────────────────────────────────────────────────┐
│               Hermes Agent Gateway                   │
│                                                     │
│  • Session management (per Minecraft player)        │
│  • LLM inference (DeepSeek, Claude, etc.)           │
│  • Tool execution (terminal, files, web, etc.)      │
│  • Command dispatch ($new, $help, $model)           │
│  • Message streaming & formatting                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Component Details

### Bridge (`bridge/index.js`)

A minimal Node.js process with no external HTTP dependencies (uses Node's built-in `http` module). Mineflayer handles the Minecraft protocol. The bridge:

1. Connects to the Minecraft server with configurable auth (offline or Microsoft)
2. Listens for chat events and queues them
3. Provides an HTTP API for the Python adapter:
   - `GET /health` — connection status, player list
   - `GET /messages` — drain the chat message queue
   - `POST /send` — send a chat message (public or `/tell`)
4. Runs an idle wander loop — walks random directions, jumps, looks at nearby players

The bridge communicates with the adapter over HTTP on `127.0.0.1:13000`. No external dependencies beyond `mineflayer`.

### Adapter (`adapter.py`)

A Python class extending `BasePlatformAdapter` from the Hermes gateway framework. The adapter:

1. **Startup**: Finds Node.js, ensures bridge deps are installed, spawns the bridge as a subprocess, waits for `GET /health` to succeed (up to 15 seconds)
2. **Polling**: Runs an async loop that `GET /messages` every 500ms. Each message becomes a `MessageEvent` dispatched to the Hermes gateway
3. **Session mapping**: Each Minecraft player gets their own Hermes session identified by lowercased username
4. **Sending**: Chunks responses at 256 characters (Minecraft's limit), applies § formatting, strips non-Latin-1 characters
5. **Private notices**: Tool progress events go through `send_private_notice()` → `/tell` whisper
6. **Config**: Reads all `MINECRAFT_*` env vars, supports Hermes config system

### Gateway Integration

The adapter is discovered by Hermes' plugin system via `plugin.yaml`. On gateway start:

1. Hermes scans `~/.hermes/plugins/` for `plugin.yaml`
2. Finds the Minecraft plugin, calls `register()` which registers the platform
3. Gateway creates an instance of `MinecraftPlatformAdapter` and calls `connect()`
4. The adapter spawns the bridge and starts the poll loop
5. Messages flow: Player chat → Bridge → Adapter → Gateway → LLM → Adapter → Bridge → Server

## Data Flow for a Typical Interaction

```
1. Player types "what's 2+2?" in Minecraft chat
2. Mineflayer fires 'chat' event → bridge pushes to messageQueue
3. Adapter polls GET /messages → receives [{"player":"iQvt","message":"what's 2+2?"}]
4. Adapter creates MessageEvent → calls handle_message(event) on gateway
5. Gateway creates/finds session for "iqvt" → dispatches to LLM
6. LLM processes → generates streaming response
7. Gateway streams content to adapter.send()
8. Adapter chunks at 250 chars → sends each chunk via POST /send
9. Bridge calls bot.chat("what's 2+2? It's 4!") for each chunk
10. Player sees HermesBot: "what's 2+2? It's 4!" in chat
```

## Minecraft Version Support

The plugin uses Mineflayer 4.37.1 which supports Minecraft up to **1.21.11** via the PrismarineJS/minecraft-data library. Minecraft 26.x+ is not yet supported — the bot will connect but may experience protocol errors.

To check for updated support, watch [PrismarineJS/minecraft-data](https://github.com/PrismarineJS/minecraft-data) for 26.x protocol data.
