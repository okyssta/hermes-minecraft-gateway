"""
Minecraft Platform Adapter for Hermes Agent.

Spawns a Node.js Mineflayer bridge as a subprocess and relays messages
between Minecraft chat and the Hermes gateway. Per-player sessions,
256-char chat chunking, offline/Microsoft auth.
"""

import asyncio
import json
import logging
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from gateway.platforms.base import (
    BasePlatformAdapter,
    SendResult,
    MessageEvent,
    MessageType,
)

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────

def _find_node() -> Optional[str]:
    for exe in ("node", "nodejs"):
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return exe
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _resolve_bridge_dir() -> Path:
    return Path(__file__).resolve().parent / "bridge"


def _ensure_bridge_deps(bridge_dir: Path) -> bool:
    if (bridge_dir / "node_modules" / "mineflayer").is_dir():
        return True
    logger.info("Minecraft: installing bridge deps (npm install)")
    r = subprocess.run(
        ["npm", "install", "--production", "--no-audit", "--no-fund"],
        cwd=str(bridge_dir), capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        logger.error("Minecraft: npm install failed: %s", r.stderr[:500])
        return False
    return True


def _kill_port(port: int):
    """Kill any process listening on TCP port."""
    try:
        r = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=5,
        )
        for line in r.stdout.strip().splitlines():
            try:
                os.kill(int(line), signal.SIGTERM)
            except (ValueError, ProcessLookupError, PermissionError):
                pass
    except FileNotFoundError:
        pass
    except Exception:
        pass


# ── Minecraft formatting ──────────────────────────────────────────
# Converts basic markdown to Minecraft section-sign (§) color codes.
# The LLM can also output § codes directly — this catches leftover
# markdown that slips through.

def _mc_format(text: str) -> str:
    # Strip Minecraft section-sign codes — server rejects them
    text = re.sub("\u00a7[0-9a-fklmnor]", "", text)
    # Strip markdown formatting (convert to plain text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"```.*?\n(.+?)```", r"\1", text, flags=re.DOTALL)
    return text.strip()


# ── Adapter ───────────────────────────────────────────────────────

class MinecraftPlatformAdapter(BasePlatformAdapter):
    """Minecraft gateway adapter — delegates MC protocol to a Node.js bridge."""

    MAX_MESSAGE_LENGTH = 256
    supports_code_blocks = False
    typed_command_prefix = "/"

    def __init__(self, config, **kwargs):
        from gateway.config import Platform
        platform = Platform("minecraft")
        super().__init__(config=config, platform=platform)
        cfg = config.extra
        self.server = cfg.get("server") or os.getenv("MINECRAFT_SERVER", "")
        self.port = int(cfg.get("port", os.getenv("MINECRAFT_PORT", "25565")))
        self.mc_username = cfg.get("username") or os.getenv("MINECRAFT_USERNAME", "HermesBot")
        self.auth = cfg.get("auth") or os.getenv("MINECRAFT_AUTH", "offline")
        self.prefix = (cfg.get("prefix") or os.getenv("MINECRAFT_PREFIX", "")).strip()
        self.private_msgs = (cfg.get("private_messages") or os.getenv("MINECRAFT_PRIVATE_MESSAGES", "false")).lower() in ("true", "1", "yes")
        self.bridge_port = int(cfg.get("bridge_port", os.getenv("MINECRAFT_BRIDGE_PORT", "13000")))

        self.bridge_dir = _resolve_bridge_dir()
        self._process: Optional[subprocess.Popen] = None
        self._http_session = None
        self._poll_task: Optional[asyncio.Task] = None
        self._running = False
        self._log_fh = None

    @property
    def name(self) -> str:
        return "minecraft"

    # ── Connection lifecycle ──────────────────────────────────────

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        self._running = True
        node = _find_node()
        if not node:
            logger.error("Minecraft: Node.js not found")
            return False

        if not _ensure_bridge_deps(self.bridge_dir):
            return False

        _kill_port(self.bridge_port)

        bridge_script = str(self.bridge_dir / "index.js")
        log_dir = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "minecraft-bridge.log"
        self._log_fh = open(log_path, "a")
        self._log_fh.write(f"\n--- Bridge start {time.time()} ---\n")
        self._log_fh.flush()

        env = os.environ.copy()
        env["MINECRAFT_SERVER"] = self.server
        env["MINECRAFT_PORT"] = str(self.port)
        env["MINECRAFT_USERNAME"] = self.mc_username
        env["MINECRAFT_AUTH"] = self.auth
        env["MINECRAFT_BRIDGE_PORT"] = str(self.bridge_port)

        self._process = subprocess.Popen(
            [node, bridge_script], env=env, stdout=self._log_fh, stderr=subprocess.STDOUT,
        )

        # Wait for bridge HTTP to come up (up to 15s)
        import aiohttp
        self._http_session = aiohttp.ClientSession()
        for attempt in range(15):
            await asyncio.sleep(1)
            if self._process.poll() is not None:
                logger.error("Minecraft: bridge died (exit %d)", self._process.returncode)
                return False
            try:
                async with self._http_session.get(
                    f"http://127.0.0.1:{self.bridge_port}/health", timeout=2,
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        logger.info("Minecraft: bridge ready (status=%s)", data.get("status"))
                        break
            except Exception:
                continue
        else:
            logger.warning("Minecraft: bridge HTTP not responding after 15s")

        self._poll_task = asyncio.create_task(self._poll_loop())
        self._mark_connected()
        return True

    async def disconnect(self):
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        if self._process:
            try:
                self._process.terminate()
                await asyncio.sleep(1)
                if self._process.poll() is None:
                    self._process.kill()
            except ProcessLookupError:
                pass
            self._process = None
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
        if self._log_fh:
            try:
                self._log_fh.close()
            except Exception:
                pass
            self._log_fh = None

    # ── Sending ───────────────────────────────────────────────────

    async def send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[dict] = None, **kwargs) -> SendResult:
        if not self._http_session:
            return SendResult(False, error="no bridge")
        # Strip non-ASCII and strip/convert markdown
        text = _mc_format(content)
        # Only allow printable ASCII (32-126), tab (9), newline (10)
        text = "".join(c for c in text if 32 <= ord(c) <= 126 or c in "\t\n")
        # Chunk at MC 256-char limit
        limit = self.MAX_MESSAGE_LENGTH
        if limit < 10:
            limit = self.MAX_MESSAGE_LENGTH - 10
        chunks = [text[i:i+limit] for i in range(0, len(text), limit)]
        for i, chunk in enumerate(chunks):
            if self.private_msgs:
                display = chunk
            else:
                display = f"[{i+1}/{len(chunks)}] {chunk}" if len(chunks) > 1 else chunk
            try:
                async with self._http_session.post(
                    f"http://127.0.0.1:{self.bridge_port}/send",
                    json={"text": display, "target": chat_id if self.private_msgs else ""}, timeout=5,
                ) as r:
                    await r.json()
            except Exception as e:
                logger.error("Minecraft: send failed: %s", e)
                return SendResult(False, error=str(e))
            await asyncio.sleep(0.3)
        return SendResult(True)

    async def send_typing(self, chat_id: str):
        await self.send(chat_id, "Thinking...")

    async def send_private_notice(
        self,
        chat_id: str,
        user_id: Optional[str],
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> SendResult:
        """Send progress/debug messages via /tell private whisper."""
        if not self._http_session:
            return SendResult(False, error="no bridge")
        text = _mc_format(content)
        text = "".join(c for c in text if 32 <= ord(c) <= 126 or c in "\t\n")
        try:
            async with self._http_session.post(
                f"http://127.0.0.1:{self.bridge_port}/send",
                json={"text": text, "target": chat_id}, timeout=5,
            ) as r:
                await r.json()
            return SendResult(True)
        except Exception as e:
            logger.error("Minecraft: private notice failed: %s", e)
            return SendResult(False, error=str(e))

    async def get_chat_info(self, chat_id: str) -> dict:
        return {"name": chat_id, "type": "dm", "chat_id": chat_id}

    # ── Bridge polling ────────────────────────────────────────────

    async def _poll_loop(self):
        while self._running and self._http_session:
            try:
                async with self._http_session.get(
                    f"http://127.0.0.1:{self.bridge_port}/messages", timeout=10,
                ) as r:
                    if r.status == 200:
                        for m in await r.json():
                            await self._handle_incoming(m)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            await asyncio.sleep(0.5)

    async def _handle_incoming(self, data: dict):
        player = data.get("player", "")
        message = data.get("message", "")
        if not player or not message:
            return

        # Strip command prefix ($) if present, but don't block non-prefixed messages
        if self.prefix and message.startswith(self.prefix):
            clean = message[len(self.prefix):].strip()
        else:
            clean = message

        source = self.build_source(
            chat_id=player.lower(),
            chat_name=player,
            chat_type="dm",
            user_id=player.lower(),
            user_name=player,
        )
        event = MessageEvent(text=clean, source=source, message_type=MessageType.TEXT)
        await self.handle_message(event)


# ── Plugin entry points ───────────────────────────────────────────

def check_requirements() -> bool:
    return bool(_find_node()) and _resolve_bridge_dir().joinpath("index.js").is_file()


def _env_enablement() -> Optional[dict]:
    if os.getenv("MINECRAFT_ENABLED", "").lower() not in ("true", "1", "yes"):
        return None
    extra = {
        "server": os.getenv("MINECRAFT_SERVER", ""),
        "port": os.getenv("MINECRAFT_PORT", "25565"),
        "username": os.getenv("MINECRAFT_USERNAME", "HermesBot"),
        "auth": os.getenv("MINECRAFT_AUTH", "offline"),
        "prefix": os.getenv("MINECRAFT_PREFIX", ""),
        "private_messages": os.getenv("MINECRAFT_PRIVATE_MESSAGES", "false"),
        "notice_delivery": "private",
        "bridge_port": os.getenv("MINECRAFT_BRIDGE_PORT", "13000"),
    }
    home = (os.getenv("MINECRAFT_HOME_CHANNEL") or "").lower() or None
    return {"extra": extra, "home_channel": home}


def register(ctx):
    """Plugin entry point — called by the Hermes plugin system."""
    ctx.register_platform(
        name="minecraft",
        label="Minecraft",
        adapter_factory=lambda cfg: MinecraftPlatformAdapter(cfg),
        check_fn=check_requirements,
        required_env=["MINECRAFT_ENABLED", "MINECRAFT_SERVER"],
        install_hint="Requires Node.js (nodejs + npm) — run: apt install nodejs npm",
        env_enablement_fn=_env_enablement,
        allowed_users_env="MINECRAFT_ALLOWED_USERS",
        allow_all_env="MINECRAFT_ALLOW_ALL_USERS",
        max_message_length=256,
        emoji="⛏",
        pii_safe=True,
        allow_update_command=True,
        platform_hint=(
            "You are chatting via Minecraft. Minecraft chat has a 256-character "
            "message limit — long responses are automatically split with [1/N] markers. "
            "Formatting is plain text only — no markdown, no colors, no bold, no codes. "
            "Do NOT use any formatting symbols. Keep responses concise."
        ),
    )
