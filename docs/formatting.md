# Formatting

Hermes Minecraft Gateway uses **plain text only**. Minecraft chat has no markdown, no colors, no formatting codes that work reliably across servers — most servers strip or reject section-sign (§) codes as "illegal characters".

## What works

Plain text. That's it.

```
Hello! I found your file at /tmp/test.txt
The weather is sunny with a high of 25C
```

## What doesn't work

| Format | Example | Why |
|--------|---------|-----|
| `**bold**` | `**hello**` | Sent as literal text |
| `*italic*` | `*hello*` | Sent as literal text |
| `§l§r` codes | `§lhello§r` | Server rejects as illegal characters |
| Markdown | `[link](url)` | Sent as literal text |
| Backticks | `` `code` `` | Sent as literal text |

## Markdown fallback

If the LLM accidentally includes markdown in its response, the adapter strips the formatting markers automatically. `**bold**` becomes `bold`, `` `code` `` becomes `code`.

## Recommendation

Keep responses concise and readable as plain text. Hermes is told in the system prompt to avoid formatting.
