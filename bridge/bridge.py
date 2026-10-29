#!/usr/bin/env python3
"""BuilderXAI Discord Bridge.

One Bot User (Discord app token) -> many topic channels -> one omp agent DIRECTORY per channel.
Every channel conversation happens in a Discord thread; each thread is its own omp session.

    Discord ──token── Bridge ── channel→agent dir ── omp --mode rpc (cwd=dir, session per thread)

Design rules (spec/topics.md):
- T1 channel → exactly one agent dir; threads inherit the parent channel's agent.
- T2 no @mention needed in bound channels; the reply always goes to a thread
     (a top-level message opens a thread named after it; follow-ups stay in that thread).
- T3 omp is spawned with --no-tools (no bash/edit/write/lsp). Agent dirs cannot widen this:
     the bridge passes --no-tools unconditionally and the dir may only list MCP servers
     that the operator mounted in.
- T5 unbound channels (incl. Admin space) are ignored entirely.
- Only the bridge holds the Discord token. omp children get only the model key.

Config: $BRIDGE_CONFIG (YAML, default /data/bridge.yaml), hot-reloaded on SIGHUP and on mtime change.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import discord
import yaml

TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CONFIG_PATH = Path(os.environ.get("BRIDGE_CONFIG", "/data/bridge.yaml"))
OMP_BIN = os.environ.get("OMP_BIN", "omp")
# Env passed to omp children: model key + web token + basics. Never the Discord token.
CHILD_ENV_KEYS = ("CLIAPI_API_KEY", "WEB_CLIENT_TOKEN", "BX_OUT_DIR", "BX_IN_DIR", "BX_LOGO", "PI_CODING_AGENT_DIR", "HOME", "PATH", "LANG", "TZ")
WEBTOOLS = Path(os.environ.get("BRIDGE_WEBTOOLS", "/opt/bridge/webtools.ts"))
WEB_TOOL_NAMES = ("web_search", "web_answer", "web_fetch")
IMAGE_TOOL_NAMES = ("image_generate", "image_edit")
OUT_MAX_FILES = 2                      # generated images attached per reply
OUT_MAX_BYTES = 10 * 1024 * 1024       # per attachment
IN_KEEP = 6                            # member images kept per thread as edit references (newest wins)
IN_MIME = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}   # what the image API accepts
LOGO = Path(os.environ.get("BX_LOGO", "/opt/bridge/assets/builderx-logo.png"))
IMAGE_MIME = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
RPC_LINE_LIMIT = 16 * 1024 * 1024  # omp emits one JSON line per event; big tool results exceed 64 KiB
DISCORD_CHUNK = 1900


def log(*a):
    print(time.strftime("%Y-%m-%dT%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- config

@dataclass
class Binding:
    channel_id: int
    agent: str                    # directory name under agents_root
    name: str = ""


@dataclass
class Config:
    agents_root: Path = Path("/data/agents")
    sessions_root: Path = Path("/data/sessions")
    bindings: dict[int, Binding] = field(default_factory=dict)
    admin_ids: set[int] = field(default_factory=set)      # may use !reset etc. (no other power)
    turn_timeout: int = 240
    idle_session_seconds: int = 1800   # stop an idle thread's omp process (session is kept on disk)
    max_live_sessions: int = 6         # cap concurrent omp processes (memory bound)
    per_user_per_min: int = 6          # simple flood guard
    thread_auto_archive_minutes: int = 1440

    @classmethod
    def load(cls, path: Path) -> "Config":
        raw = yaml.safe_load(path.read_text()) or {}
        c = cls()
        for k in ("turn_timeout", "idle_session_seconds", "max_live_sessions",
                  "per_user_per_min", "thread_auto_archive_minutes"):
            if k in raw:
                setattr(c, k, int(raw[k]))
        if "agents_root" in raw:
            c.agents_root = Path(raw["agents_root"])
        if "sessions_root" in raw:
            c.sessions_root = Path(raw["sessions_root"])
        c.admin_ids = {int(x) for x in raw.get("admin_ids", [])}
        for b in raw.get("bindings", []):
            agent = str(b["agent"])
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", agent):
                raise ValueError(f"bad agent name {agent!r}")
            cid = int(b["channel_id"])
            c.bindings[cid] = Binding(cid, agent, str(b.get("name", "")))
        return c


# ---------------------------------------------------------------- omp rpc session

class OmpSession:
    """One `omp --mode rpc` process for one Discord thread, cwd = the agent directory."""

    def __init__(self, key: str, agent_dir: Path, session_dir: Path, cfg: Config):
        self.key = key
        self.agent_dir = agent_dir
        self.session_dir = session_dir
        self.out_dir = session_dir / "out"
        self.in_dir = session_dir / "in"
        self.cfg = cfg
        self.proc: asyncio.subprocess.Process | None = None
        self.lock = asyncio.Lock()
        self.last_used = time.monotonic()
        self._req = 0
        self.last_error: str | None = None

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def _spawn(self):
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.in_dir.mkdir(parents=True, exist_ok=True)
        env = {k: os.environ[k] for k in CHILD_ENV_KEYS if k in os.environ}
        env["BX_OUT_DIR"] = str(self.out_dir)
        env["BX_IN_DIR"] = str(self.in_dir)
        if LOGO.is_file():
            env["BX_LOGO"] = str(LOGO)
        # Built-in tools stay off. Load ONLY our extension with an explicit tool allowlist
        # (no discovery of extensions/skills/tools from the agent dir).
        args = [OMP_BIN, "--mode", "rpc", "--no-tools", "--no-lsp", "--no-pty",
                "--no-extensions", "--no-skills", "--no-rules",
                "--session-dir", str(self.session_dir)]
        tools: list[str] = list(IMAGE_TOOL_NAMES) if os.environ.get("CLIAPI_API_KEY") else []
        if os.environ.get("WEB_CLIENT_TOKEN"):
            tools += list(WEB_TOOL_NAMES)
        if tools and WEBTOOLS.is_file():
            args += ["-e", str(WEBTOOLS), "--tools", ",".join(tools)]
        # resume this thread's conversation if it exists on disk
        if any(self.session_dir.glob("*.jsonl")):
            args.append("--continue")
        self.proc = await asyncio.create_subprocess_exec(
            *args, cwd=str(self.agent_dir), env=env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, limit=RPC_LINE_LIMIT,
        )
        while True:
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=120)
            if not line:
                raise RuntimeError("omp exited before ready")
            try:
                if json.loads(line).get("type") == "ready":
                    break
            except json.JSONDecodeError:
                continue
        log(f"[{self.key}] omp ready (agent={self.agent_dir.name})")

    async def stop(self):
        if self.alive:
            try:
                self.proc.kill()
                await asyncio.wait_for(self.proc.wait(), timeout=10)
            except Exception:
                pass
        self.proc = None

    async def ask(self, text: str, images: list | None) -> str:
        async with self.lock:
            self.last_used = time.monotonic()
            if not self.alive:
                await self._spawn()
            self._req += 1
            rid = f"r{self._req}"
            msg = {"id": rid, "type": "prompt", "message": text}
            if images:
                msg["images"] = images
            self.proc.stdin.write((json.dumps(msg) + "\n").encode())
            await self.proc.stdin.drain()

            async def pump() -> str:
                last, cur = "", []
                while True:
                    line = await self.proc.stdout.readline()
                    if not line:
                        raise RuntimeError("omp died mid-turn")
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    t = ev.get("type")
                    if t == "message_update":
                        ame = ev.get("assistantMessageEvent") or {}
                        if ame.get("type") == "text_delta":
                            cur.append(ame.get("delta") or "")
                    if t == "message_end":
                        m = ev.get("message") or {}
                        if m.get("role") == "assistant" and m.get("stopReason") == "error":
                            self.last_error = str(m.get("errorMessage") or "model error")[:200]
                    elif t in ("message_start", "message_end"):
                        if cur:
                            last, cur = "".join(cur), []
                    elif t == "agent_end":
                        return "".join(cur) if cur else last
                    elif t == "response" and ev.get("command") == "prompt" and ev.get("id") == rid:
                        if ev.get("success") is False:
                            raise RuntimeError(str(ev.get("error"))[:200])
                        if (ev.get("data") or {}).get("agentInvoked") is False:
                            return last

            self.last_error = None
            try:
                reply = await asyncio.wait_for(pump(), timeout=self.cfg.turn_timeout)
            except (asyncio.TimeoutError, RuntimeError, ValueError) as e:
                log(f"[{self.key}] turn failed: {type(e).__name__}: {e}")
                await self.stop()
                return "⚠️ 这次没能生成回复（已重置这个会话的进程），请再发一次。"
            self.last_used = time.monotonic()
            if not reply.strip() and self.last_error:
                log(f"[{self.key}] model error: {self.last_error}")
                return "⚠️ 模型暂时不可用，请稍后再试。"
            return reply.strip() or "（空回复）"


# ---------------------------------------------------------------- bridge

class Bridge(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True
        intents.guilds = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.cfg = Config.load(CONFIG_PATH)
        self.cfg_mtime = CONFIG_PATH.stat().st_mtime
        self.sessions: dict[str, OmpSession] = {}
        self.rate: dict[int, list[float]] = {}

    # -- config
    def reload(self, why: str):
        try:
            new = Config.load(CONFIG_PATH)
        except Exception as e:
            log(f"config reload ({why}) FAILED, keeping old: {e}")
            return
        self.cfg = new
        self.cfg_mtime = CONFIG_PATH.stat().st_mtime
        log(f"config reloaded ({why}): {len(new.bindings)} binding(s): "
            + ", ".join(f"{b.channel_id}->{b.agent}" for b in new.bindings.values()))

    async def setup_hook(self):
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGHUP, lambda: self.reload("SIGHUP"))
        self.loop.create_task(self._housekeeping())

    async def _housekeeping(self):
        while not self.is_closed():
            await asyncio.sleep(30)
            try:
                if CONFIG_PATH.stat().st_mtime != self.cfg_mtime:
                    self.reload("file changed")
            except FileNotFoundError:
                pass
            now = time.monotonic()
            for key, s in list(self.sessions.items()):
                if s.alive and not s.lock.locked() and now - s.last_used > self.cfg.idle_session_seconds:
                    log(f"[{key}] idle -> stop process (session kept)")
                    await s.stop()

    async def on_ready(self):
        log(f"bridge ready as {self.user} ({self.user.id}); "
            f"{len(self.cfg.bindings)} binding(s)")

    # -- routing
    def _binding_for(self, channel) -> tuple[Binding | None, bool]:
        """(binding, is_thread). Threads resolve through their parent channel."""
        if isinstance(channel, discord.Thread):
            b = self.cfg.bindings.get(channel.parent_id or 0)
            return b, True
        return self.cfg.bindings.get(channel.id), False

    def _rate_ok(self, uid: int) -> bool:
        now = time.monotonic()
        q = [t for t in self.rate.get(uid, []) if now - t < 60]
        if len(q) >= self.cfg.per_user_per_min:
            self.rate[uid] = q
            return False
        q.append(now)
        self.rate[uid] = q
        return True

    async def _session(self, b: Binding, thread_id: int) -> OmpSession | None:
        key = f"{b.agent}/{thread_id}"
        s = self.sessions.get(key)
        if s is None:
            agent_dir = self.cfg.agents_root / b.agent
            if not (agent_dir / ".omp").is_dir():
                log(f"agent dir missing: {agent_dir}")
                return None
            s = OmpSession(key, agent_dir, self.cfg.sessions_root / b.agent / str(thread_id), self.cfg)
            self.sessions[key] = s
        if not s.alive:
            live = [x for x in self.sessions.values() if x.alive]
            if len(live) >= self.cfg.max_live_sessions:
                idle = sorted((x for x in live if not x.lock.locked()), key=lambda x: x.last_used)
                if not idle:
                    return None
                log(f"[{idle[0].key}] evicted (cap {self.cfg.max_live_sessions})")
                await idle[0].stop()
        return s

    async def on_message(self, msg: discord.Message):
        if msg.author.bot or msg.webhook_id or msg.guild is None:
            return                                   # no DMs, no bots, no webhooks
        if msg.type not in (discord.MessageType.default, discord.MessageType.reply):
            return
        b, is_thread = self._binding_for(msg.channel)
        if b is None:
            return                                   # unbound channel (incl. Admin space): ignore
        text = (msg.content or "").strip()
        images, skipped = await self._images(msg)
        if not text and not images:
            return
        if text == "!reset" and is_thread:
            s = self.sessions.pop(f"{b.agent}/{msg.channel.id}", None)
            if s:
                await s.stop()
            # drop on-disk session so the next message starts fresh
            d = self.cfg.sessions_root / b.agent / str(msg.channel.id)
            for f in d.glob("*.jsonl"):
                f.rename(f.with_suffix(f".reset-{int(time.time())}"))
            await msg.channel.send("已开始新的对话。")
            return
        if not self._rate_ok(msg.author.id):
            try:
                await msg.add_reaction("⏳")
            except discord.HTTPException:
                pass
            return
        # T2: always answer in a thread
        if is_thread:
            thread = msg.channel
        else:
            title = re.sub(r"\s+", " ", text or "图片")[:80] or "讨论"
            try:
                thread = await msg.create_thread(name=title,
                                                 auto_archive_duration=self.cfg.thread_auto_archive_minutes)
            except discord.HTTPException as e:
                log(f"create_thread failed in {msg.channel.id}: {e}")
                return
        s = await self._session(b, thread.id)
        if s is None:
            await thread.send("⚠️ 现在比较忙或这个频道还没配置好，请稍后再试。")
            return
        if not text:
            text = "（用户发了一张图片，没有文字，请看图并回应）"
        ref_ids = self._save_refs(s, images)
        speaker = msg.author.display_name
        prompt = f"[{speaker}]: {text}"
        if ref_ids:
            prompt += ("\n（附图已保存，可用 image_edit 的 refs 引用："
                       + "、".join(ref_ids) + "；官方 logo 用 \"logo\"）")
        try:
            async with thread.typing():
                reply = await s.ask(prompt, images or None)
        except Exception as e:
            log(f"[{s.key}] ask error: {type(e).__name__}: {e}")
            await s.stop()
            reply = "⚠️ 处理出错了，已重置，请再试一次。"
        if skipped:
            reply += "\n\n（已跳过附件：" + "；".join(skipped) + "）"
        files, note = self._collect_out(s)
        if note:
            reply += "\n\n" + note
        chunks = [reply[i:i + DISCORD_CHUNK] for i in range(0, len(reply), DISCORD_CHUNK)] or [""]
        for i, chunk in enumerate(chunks):
            last = i == len(chunks) - 1
            try:
                if last and files:
                    await thread.send(chunk or None, files=[discord.File(str(p), filename=p.name) for p in files])
                else:
                    await thread.send(chunk)
            except discord.HTTPException as e:
                log(f"[{s.key}] send failed: {e}")
                if last and files:
                    await thread.send(chunk + "\n\n（图片发送失败，请稍后再试）")
        for p in files:
            p.unlink(missing_ok=True)

    def _save_refs(self, s: "OmpSession", images: list) -> list[str]:
        """Keep this message's member images as edit references in <session>/in/img-N.<ext> (newest IN_KEEP kept).
        The id (e.g. img-3) is the only handle the model gets; image_edit resolves it inside in/ only."""
        if not images:
            return []
        try:
            s.in_dir.mkdir(parents=True, exist_ok=True)
            existing = [int(m.group(1)) for p in s.in_dir.iterdir()
                        if (m := re.fullmatch(r"img-(\d+)\.(png|jpg|webp)", p.name))]
            n = max(existing, default=0)
            ids = []
            for im in images:
                ext = IN_MIME.get(im.get("mimeType", ""))
                if not ext:
                    continue                      # gif etc.: the model can look at it, but it can't be an edit ref
                n += 1
                (s.in_dir / f"img-{n}.{ext}").write_bytes(base64.b64decode(im["data"]))
                ids.append(f"img-{n}")
            olds = sorted((p for p in s.in_dir.iterdir() if re.fullmatch(r"img-\d+\.(png|jpg|webp)", p.name)),
                          key=lambda p: int(p.name.split("-")[1].split(".")[0]))
            for p in olds[:-IN_KEEP]:
                p.unlink(missing_ok=True)
            return ids
        except Exception as e:
            log(f"[{s.key}] save refs failed: {type(e).__name__}: {e}")
            return []

    def _collect_out(self, s: "OmpSession") -> tuple[list[Path], str]:
        """Images generated this turn: at most OUT_MAX_FILES, each <= OUT_MAX_BYTES. Everything else is deleted."""
        try:
            found = sorted((p for p in s.out_dir.glob("*.png")
                            if p.is_file() and not p.is_symlink() and not p.name.startswith(".")),
                           key=lambda p: p.stat().st_mtime)
        except FileNotFoundError:
            return [], ""
        keep, dropped = [], 0
        for p in found:
            if len(keep) < OUT_MAX_FILES and p.stat().st_size <= OUT_MAX_BYTES:
                keep.append(p)
            else:
                dropped += 1
                p.unlink(missing_ok=True)
        return keep, (f"（另有 {dropped} 张图未发出：每次最多 {OUT_MAX_FILES} 张、每张不超过 10MB）" if dropped else "")

    async def _images(self, msg) -> tuple[list, list]:
        images, skipped = [], []
        for att in msg.attachments:
            ct = (att.content_type or "").split(";")[0].strip().lower()
            if ct not in IMAGE_MIME:
                skipped.append(att.filename)
                continue
            if att.size and att.size > MAX_IMAGE_BYTES:
                skipped.append(f"{att.filename}（超过 20MB）")
                continue
            try:
                raw = await att.read()
            except Exception:
                skipped.append(att.filename)
                continue
            images.append({"type": "image", "data": base64.b64encode(raw).decode(), "mimeType": ct})
        return images, skipped

    async def close(self):
        for s in self.sessions.values():
            await s.stop()
        await super().close()


if __name__ == "__main__":
    if not CONFIG_PATH.exists():
        sys.exit(f"missing {CONFIG_PATH}")
    Bridge().run(TOKEN, log_handler=None)
