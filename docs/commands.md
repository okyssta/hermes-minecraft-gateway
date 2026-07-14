# Commands Reference

Hermes Minecraft Gateway supports all standard Hermes commands. Use the configured prefix (default: `$`) in front of commands.

## General Commands

### `$help`
Show available commands and a brief description of how to use Hermes.

```
$help
> Hermes responds with a list of commands
```

### `$new`
Reset your current session. Starts a fresh conversation with Hermes. Previous context is lost.

```
$new
> Session reset!
```

### `$model`
Show which LLM model is currently serving your session.

```
$model
> deepseek-v4-flash
```

### `$stop`
Stop the current response if Hermes is generating one.

```
$stop
```

### `$status` / `$info`
Show session info: model, token usage, session age.

```
$status
```

## Session Management

### `$sessions`
List your active sessions (admin only for other players' sessions).

### `$session <player>`
Admin command — switch to another player's session.

## Admin Commands

These require the player to be in the `MINECRAFT_ALLOWED_USERS` list.

### `$reload`
Reload the Minecraft gateway configuration without restarting.

### `$whitelist add <player>`
Add a player to the allowlist.

### `$whitelist remove <player>`
Remove a player from the allowlist.

### `$whitelist list`
List all allowed players.

## How Commands Work

1. You type `$new` in Minecraft chat
2. The bridge catches the chat event and sends it to the Python adapter
3. The adapter sees it starts with `$`, strips the prefix, and forwards `new`
4. Hermes gateway's command dispatcher recognizes `new` as a built-in command
5. The response goes back through the adapter → bridge → Minecraft chat

No server-side plugins needed. The `$` prefix prevents Minecraft's server from intercepting the command (Minecraft only intercepts `/` commands).
