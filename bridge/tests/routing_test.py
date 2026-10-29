"""Unit-test the Discord-side routing of bridge.py with fake discord objects (no network)."""
import asyncio, sys, os, types, importlib.util, json
from pathlib import Path
os.environ["DISCORD_BOT_TOKEN"] = "x"
os.environ["BRIDGE_CONFIG"] = "/data/bridge.yaml"
spec = importlib.util.spec_from_file_location("bridge", "/opt/bridge/bridge.py")
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge; spec.loader.exec_module(bridge)
import discord

TOPIC, ADMIN, OTHER = 111, 999, 222
Path("/data/bridge.yaml").write_text(f"""
agents_root: /data/agents
sessions_root: /data/sessions
per_user_per_min: 3
bindings:
  - {{channel_id: "{TOPIC}", agent: alpha, name: "#alpha"}}
""")

for _a in ("alpha", "beta"):
    Path(f"/data/agents/{_a}/.omp").mkdir(parents=True, exist_ok=True)
    Path(f"/data/agents/{_a}/.omp/SYSTEM.md").write_text("test")

sent = []
class FakeThread(discord.Thread):
    def __init__(self, tid, parent_id):
        self.id = tid; self.parent_id = parent_id
    async def send(self, text): sent.append((self.id, text))
    def typing(self):
        class T:
            async def __aenter__(s): pass
            async def __aexit__(s, *a): pass
        return T()
class FakeChannel:
    def __init__(self, cid): self.id = cid
class Author:
    def __init__(self, uid, bot=False): self.id = uid; self.bot = bot; self.display_name = f"u{uid}"
created = []
class Msg:
    def __init__(self, ch, text, uid=1, bot=False, guild=True):
        self.channel = ch; self.content = text; self.author = Author(uid, bot); self.webhook_id = None
        self.guild = object() if guild else None; self.type = discord.MessageType.default; self.attachments = []
        self.reactions = []
    async def create_thread(self, name, auto_archive_duration):
        t = FakeThread(5000 + len(created), self.channel.id); created.append((t.id, name)); return t
    async def add_reaction(self, e): self.reactions.append(e)

async def main():
    b = bridge.Bridge.__new__(bridge.Bridge)          # skip discord.Client.__init__ (no network)
    b.cfg = bridge.Config.load(Path("/data/bridge.yaml")); b.sessions = {}; b.rate = {}
    async def fake_ask(self, text, images):  # don't call the model here; routing only
        return f"echo<{self.agent_dir.name}>:{text}"
    bridge.OmpSession.ask = fake_ask
    res = {}
    await b.on_message(Msg(FakeChannel(TOPIC), "本地模型怎么量化？")); res["T2 top-level opens thread"] = len(created) == 1 and sent[-1][0] == created[0][0]
    th = FakeThread(created[0][0], TOPIC)
    await b.on_message(Msg(th, "继续问")); res["T1 thread routes to parent agent, no new thread"] = len(created) == 1 and "echo<alpha>" in sent[-1][1]
    n = len(sent)
    await b.on_message(Msg(FakeChannel(ADMIN), "hi")); await b.on_message(Msg(FakeThread(7, ADMIN), "hi")); await b.on_message(Msg(FakeChannel(OTHER), "hi"))
    res["T5 unbound/admin ignored"] = len(sent) == n
    await b.on_message(Msg(FakeChannel(TOPIC), "hi", guild=False)); await b.on_message(Msg(FakeChannel(TOPIC), "hi", bot=True))
    res["DM and bot messages ignored"] = len(sent) == n
    m = None
    for i in range(4):
        m = Msg(th, f"flood {i}", uid=42); await b.on_message(m)
    res["flood guard (3/min) -> ⏳"] = m.reactions == ["⏳"]
    res["speaker prefix"] = sent[-1][1].startswith("echo<alpha>:[u42]:")
    res["sessions keyed per thread"] = list(b.sessions) == [f"alpha/{th.id}"]
    # hot reload: bind OTHER, then it routes
    Path("/data/bridge.yaml").write_text(Path("/data/bridge.yaml").read_text() + f'  - {{channel_id: "{OTHER}", agent: beta}}\n')
    b.reload("test"); await b.on_message(Msg(FakeChannel(OTHER), "voice?")); res["hot reload adds binding"] = "echo<beta>" in sent[-1][1]
    Path("/data/bridge.yaml").write_text("bindings: [{channel_id: 1, agent: '../etc'}]\n"); b.reload("bad")
    res["bad config rejected, old kept"] = OTHER in b.cfg.bindings
    for k, v in res.items(): print("✅" if v else "❌", k)
asyncio.run(main())
