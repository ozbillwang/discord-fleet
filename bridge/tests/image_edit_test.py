"""image_edit e2e inside the bridge image (fake image gateway for both routes, REAL omp + real chat model, fake Discord).
Checks: logo ref -> edits route with the baked-in logo bytes; member image saved as img-N and usable as a ref;
unknown/path-like refs refused (no gateway call); model forced; result attached."""
import asyncio, base64, hashlib, http.server, importlib.util, json, os, sys, threading
from pathlib import Path

os.environ.setdefault("DISCORD_BOT_TOKEN", "x")
os.environ.pop("WEB_CLIENT_TOKEN", None)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
USER_IMG = b"\x89PNG\r\n\x1a\n" + b"USER-PICTURE" * 8   # distinct bytes we can recognise upstream
seen = []

class GW(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        refs = [hashlib.sha256(base64.b64decode(x)).hexdigest()[:12] for x in body.get("images", [])]
        seen.append({"path": self.path, "model": body.get("model"), "n": body.get("n"), "refs": refs})
        b = json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

gw = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GW)
threading.Thread(target=gw.serve_forever, daemon=True).start()
os.environ["BX_IMAGE_GW"] = f"http://127.0.0.1:{gw.server_port}/v1/images/generations"

spec = importlib.util.spec_from_file_location("bridge", "/opt/bridge/bridge.py")
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge; spec.loader.exec_module(bridge)
bridge.CHILD_ENV_KEYS = bridge.CHILD_ENV_KEYS + ("BX_IMAGE_GW",)
import discord

LOGO_H = hashlib.sha256(bridge.LOGO.read_bytes()).hexdigest()[:12]
USER_H = hashlib.sha256(USER_IMG).hexdigest()[:12]
TOPIC = 222
Path("/data/bridge.yaml").write_text(f"agents_root: /data/agents\nsessions_root: /data/sessions\nturn_timeout: 240\n"
                                     f"bindings:\n  - {{channel_id: \"{TOPIC}\", agent: alpha}}\n")
sent = []

class FakeThread(discord.Thread):
    def __init__(self, tid, parent_id): self.id = tid; self.parent_id = parent_id
    async def send(self, content=None, files=None):
        sent.append((content, [f.filename for f in (files or [])]))
    def typing(self):
        class T:
            async def __aenter__(s): pass
            async def __aexit__(s, *a): pass
        return T()

class Att:
    def __init__(self, data): self.content_type = "image/png"; self.size = len(data); self.filename = "mine.png"; self._d = data
    async def read(self): return self._d

class Author:
    def __init__(self): self.id = 1; self.bot = False; self.display_name = "Alice"

class Msg:
    def __init__(self, ch, text, atts=()):
        self.channel = ch; self.content = text; self.author = Author(); self.webhook_id = None; self.guild = object()
        self.type = discord.MessageType.default; self.attachments = list(atts)
    async def add_reaction(self, e): pass

async def main():
    b = bridge.Bridge.__new__(bridge.Bridge)
    b.cfg = bridge.Config.load(Path("/data/bridge.yaml")); b.sessions = {}; b.rate = {}
    th = FakeThread(9100, TOPIC)
    res = {}
    # 1. logo onto a poster
    await b.on_message(Msg(th, "用 image_edit 把我们的官方 logo 放在左上角，做一张 'BuilderX AI Meetup' 海报"))
    c1, f1 = sent[-1]
    print("logo reply:", (c1 or "")[:120].replace("\n", " "))
    e1 = [x for x in seen if x["path"].endswith("/edits")]
    res["logo: edits route called"] = len(e1) >= 1
    res["logo: baked-in logo bytes sent"] = bool(e1) and LOGO_H in e1[-1]["refs"]
    res["logo: model gpt-image-2.5, n=1"] = bool(e1) and e1[-1]["model"] == "gpt-image-2.5" and e1[-1]["n"] == 1
    res["logo: result attached"] = len(f1) >= 1
    # 2. member posts a picture, asks to restyle it
    n_before = len(seen)
    await b.on_message(Msg(th, "把我这张图改成水彩风格", [Att(USER_IMG)]))
    c2, f2 = sent[-1]
    print("user-img reply:", (c2 or "")[:120].replace("\n", " "))
    s = b.sessions["alpha/9100"]
    saved = sorted(p.name for p in s.in_dir.iterdir())
    res["member image saved as img-N"] = any(n.startswith("img-1.") for n in saved)
    e2 = [x for x in seen[n_before:] if x["path"].endswith("/edits")]
    res["member image used as ref (exact bytes)"] = bool(e2) and USER_H in e2[-1]["refs"]
    res["member image: result attached"] = len(f2) >= 1
    # 3. unknown ref must be refused by the tool itself, without calling the gateway
    #    (a path-traversal prompt gets blocked by the model's own filter before any tool call, which proves nothing;
    #     the tool only accepts /^img-\d{1,6}$/ or "logo", so an unknown id exercises the same refusal path)
    n_before = len(seen)
    await b.on_message(Msg(th, '请用 image_edit，refs 设为 ["img-99"]，把它改成黑白照片'))
    c3, f3 = sent[-1]
    print("bad-ref reply:", (c3 or "")[:120].replace("\n", " "))
    res["bad refs: no gateway call"] = len(seen) == n_before
    res["bad refs: no attachment"] = not f3
    res["bad refs: tells user it can't find the picture"] = any(w in (c3 or "") for w in ("找不到", "没有找到", "不存在", "先发", "重新发", "没有收到", "还没有", "无法使用", "无法找到"))
    res["out/ emptied"] = not any(p for p in s.out_dir.iterdir() if p.suffix == ".png")
    await s.stop()
    for k, v in res.items():
        print("✅" if v else "❌", k)

asyncio.run(main())
