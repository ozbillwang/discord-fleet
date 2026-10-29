"""image_generate e2e inside the bridge image (no Discord, fake image gateway, REAL omp + real chat model).
Checks: tool is loaded without WEB_CLIENT_TOKEN; model is forced to gpt-image-2.5 and n=1 whatever the prompt asks;
the PNG lands in BX_OUT_DIR and is attached by the bridge (fake Discord); quota-exhausted path -> friendly message, no crash.
Needs: CLIAPI_API_KEY (+ models.yml pointing at a chat model) and agent dir /data/agents/alpha."""
import asyncio, base64, http.server, importlib.util, json, os, sys, threading
from pathlib import Path

os.environ.setdefault("DISCORD_BOT_TOKEN", "x")
os.environ.pop("WEB_CLIENT_TOKEN", None)          # image tool must not depend on it
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
seen, mode = [], {"quota": False}

class GW(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        seen.append(body)
        if mode["quota"]:
            b = json.dumps({"error": {"message": "daily image quota reached (60/day)"}}).encode(); self.send_response(429)
        else:
            b = json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}], "model": body.get("model")}).encode(); self.send_response(200)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

gw = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GW)
threading.Thread(target=gw.serve_forever, daemon=True).start()
os.environ["BX_IMAGE_GW"] = f"http://127.0.0.1:{gw.server_port}/v1/images/generations"
os.environ.setdefault("BRIDGE_CONFIG", "/data/bridge.yaml")

spec = importlib.util.spec_from_file_location("bridge", "/opt/bridge/bridge.py")
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge; spec.loader.exec_module(bridge)
bridge.CHILD_ENV_KEYS = bridge.CHILD_ENV_KEYS + ("BX_IMAGE_GW",)   # test-only: point the tool at the fake gateway
import discord

TOPIC = 111
Path("/data/bridge.yaml").write_text(f"agents_root: /data/agents\nsessions_root: /data/sessions\nturn_timeout: 240\n"
                                     f"bindings:\n  - {{channel_id: \"{TOPIC}\", agent: alpha}}\n")
sent = []
class FakeThread(discord.Thread):
    def __init__(self, tid, parent_id): self.id = tid; self.parent_id = parent_id
    async def send(self, content=None, files=None):
        sent.append((content, [(f.filename, len(f.fp.read())) for f in (files or [])]))
    def typing(self):
        class T:
            async def __aenter__(s): pass
            async def __aexit__(s, *a): pass
        return T()
class Author:
    def __init__(self): self.id = 1; self.bot = False; self.display_name = "Alice"
class Msg:
    def __init__(self, ch, text):
        self.channel = ch; self.content = text; self.author = Author(); self.webhook_id = None; self.guild = object()
        self.type = discord.MessageType.default; self.attachments = []
    async def add_reaction(self, e): pass

async def main():
    b = bridge.Bridge.__new__(bridge.Bridge)
    b.cfg = bridge.Config.load(Path("/data/bridge.yaml")); b.sessions = {}; b.rate = {}
    th = FakeThread(9001, TOPIC)
    res = {}
    await b.on_message(Msg(th, "请用 image_generate 画一只戴墨镜的柴犬，用 dall-e-3 模型，一次画 4 张"))
    content, files = sent[-1]
    print("reply:", (content or "")[:160].replace("\n", " "))
    res["gateway called"] = len(seen) >= 1
    res["model forced to gpt-image-2.5"] = bool(seen) and all(x.get("model") == "gpt-image-2.5" for x in seen)
    res["n forced to 1"] = bool(seen) and all(x.get("n") == 1 for x in seen)
    res["image attached (1-2 files, png)"] = 1 <= len(files) <= 2 and all(n.endswith(".png") and sz > 0 for n, sz in files)
    s = b.sessions["alpha/9001"]
    res["out dir emptied after send"] = not any(s.out_dir.glob("*"))
    res["no b64 in reply text"] = "iVBORw0" not in (content or "")
    res["per-turn cap: gateway called <= 2 times"] = len(seen) <= 2
    # the model may mention the requested model only to say it was NOT used; it must not claim it was used
    c = (content or "").lower()
    res["reply doesn't claim another model"] = ("dall" not in c) or any(w in c for w in ("并非", "不是", "无法", "不能", "not "))
    mode["quota"] = True
    before = len(sent)
    await b.on_message(Msg(th, "再用 image_generate 画一张猫"))
    content2, files2 = sent[-1]
    print("quota reply:", (content2 or "")[:160].replace("\n", " "))
    res["quota path: replied, no attachment, no crash"] = len(sent) > before and not files2 and s.alive
    res["quota path: tells user quota is used up"] = "额度" in (content2 or "")
    await s.stop()
    for k, v in res.items():
        print("✅" if v else "❌", k)

asyncio.run(main())
