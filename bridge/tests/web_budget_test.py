"""Web budget: a fake search backend that never finds the thing. The model must stop at <= MAX calls and still answer
(no turn timeout). Real omp + real chat model; fake TinyFish/Tavily inside the test, so no web quota is spent."""
import asyncio, http.server, importlib.util, json, os, sys, threading, time
from pathlib import Path

os.environ.setdefault("DISCORD_BOT_TOKEN", "x")
hits = {"n": 0}

class Web(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _ok(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):   # TinyFish search
        hits["n"] += 1
        self._ok({"results": [{"title": "Unrelated page", "url": "https://example.com/x", "snippet": "nothing about the requested logo here"}]})
    def do_POST(self):  # TinyFish fetch / Tavily
        self.rfile.read(int(self.headers.get("Content-Length") or 0)); hits["n"] += 1
        if self.path.startswith("/search"):
            self._ok({"answer": "No information found.", "results": []})
        else:
            self._ok({"results": [{"title": "Unrelated", "url": "https://example.com/x", "text": "Nothing relevant on this page."}]})

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Web)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_port}"
os.environ.update(WEB_CLIENT_TOKEN="test", TINYFISH_SEARCH=base, TINYFISH_FETCH=base, TAVILY_SERVER=base)

spec = importlib.util.spec_from_file_location("bridge", "/opt/bridge/bridge.py")
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge; spec.loader.exec_module(bridge)
bridge.CHILD_ENV_KEYS = bridge.CHILD_ENV_KEYS + ("TINYFISH_SEARCH", "TINYFISH_FETCH", "TAVILY_SERVER")

async def main():
    cfg = bridge.Config(); cfg.agents_root = Path("/data/agents"); cfg.sessions_root = Path("/data/sessions"); cfg.turn_timeout = 240
    s = bridge.OmpSession("alpha/web", cfg.agents_root / "alpha", cfg.sessions_root / "alpha" / "web", cfg)
    t = time.time()
    r = await s.ask("[Alice]: 帮我在网上找到 'Zorblax Quantum Llama 9000' 这个不存在的乐队的官方 logo 的直接下载链接。"
                    "一定要找到，多搜几次，各种关键词都试一下，不要放弃。", None)
    dt = time.time() - t
    await s.stop()
    print(f"web calls: {hits['n']} | {dt:.0f}s | reply: {r[:150]!r}")
    res = {
        "web calls capped (<= 15)": hits["n"] <= 15,
        "turn finished before timeout": dt < cfg.turn_timeout and not r.startswith("⚠️"),
        "gave a real reply": len(r.strip()) > 5,
    }
    for k, v in res.items():
        print("✅" if v else "❌", k)

asyncio.run(main())
