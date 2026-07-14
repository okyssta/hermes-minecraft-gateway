# Changelog

## v0.0.1 (2026-07-14)

Initial release of the Hermes Minecraft Gateway plugin.

### Features
- Per-player Hermes sessions (each player gets their own DM-like session)
- Full command support (`$new`, `$help`, `$model`, `$stop`) via configurable prefix
- Public chat responses with auto-chunking at 256-character limit
- Private tool progress via `/tell` whisper
- Mineflayer bot with idle wander loop (walks, jumps, looks at players)
- Offline and Microsoft auth support
- Configurable via environment variables
- Systemd drop-in integration for persistent setups
- HTTP bridge architecture (Python adapter + Node.js Mineflayer bridge)

### Compatibility
- Hermes Agent (gateway mode)
- Minecraft servers up to 1.21.11
- Node.js >= 22
- Python 3.12+
