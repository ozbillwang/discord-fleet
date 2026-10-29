"""Offline tests for bx-llm-gw image routes (fake upstream; no network, no keys).
Run: python3 hosts/example/tests/bx_llm_gw_test.py"""
import base64, importlib.util, json, os, re, threading, urllib.error, urllib.request, http.server
from pathlib import Path

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
JPG = b"\xff\xd8\xff\xe0" + b"0" * 64
calls = []


class Up(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        ct = self.headers.get("Content-Type", "")
        rec = {"path": self.path, "ct": ct}
        if ct.startswith("multipart/"):
            rec["files"] = re.findall(rb'name="([^"]+)"; filename=', raw)
            rec["model"] = re.search(rb'name="model"\r\n\r\n([^\r]+)', raw).group(1).decode()
        else:
            rec["model"] = json.loads(raw).get("model")
        calls.append(rec)
        b = json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


up = http.server.HTTPServer(("127.0.0.1", 0), Up)
threading.Thread(target=up.serve_forever, daemon=True).start()
os.environ.update(CLIAPI_UPSTREAM_KEY="up", BXGW_UPSTREAM=f"http://127.0.0.1:{up.server_port}", BXGW_LISTEN="127.0.0.1:0",
                  BXGW_KEYS="guild:gk,builderxai:bk,other:ok", BXGW_MODELS="guild:m=m;builderxai:m=m;other:m=m",
                  BXGW_IMAGE_MODELS="guild:gpt-image-2=gpt-image-2;builderxai:gpt-image-2.5=gpt-image-2.5",
                  BXGW_IMAGE_DAILY="3")
src = Path(__file__).resolve().parent.parent / "bx-llm-gw.py"
spec = importlib.util.spec_from_file_location("gw", src)
gw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)
srv = gw.S(("127.0.0.1", 0), gw.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def post(path, key, body):
    r = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}{path}", data=json.dumps(body).encode(), method="POST",
                               headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        x = urllib.request.urlopen(r)
        return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


G, E = "/v1/images/generations", "/v1/images/edits"
b64 = lambda b: base64.b64encode(b).decode()
res = {}
res["generations ok"] = post(G, "gk", {"prompt": "x"})[0] == 200
res["generations: model not allowed -> 404"] = post(G, "gk", {"prompt": "x", "model": "dall-e-3"})[0] == 404
res["no image models for client -> 403 (edits)"] = post(E, "ok", {"prompt": "x", "images": [b64(PNG)]})[0] == 403
res["bad key -> 401 (edits)"] = post(E, "zz", {"prompt": "x", "images": [b64(PNG)]})[0] == 401
s, d = post(E, "bk", {"prompt": "put the logo top-left", "images": [b64(PNG)]})
res["edits 1 ref -> 200 + b64"] = s == 200 and d["data"][0]["b64_json"] == b64(PNG)
res["edits upstream: multipart, field 'image', model mapped"] = calls[-1]["path"] == "/images/edits" and calls[-1]["files"] == [b"image"] and calls[-1]["model"] == "gpt-image-2.5"
s, _ = post(E, "bk", {"prompt": "combine", "images": [b64(PNG), b64(JPG)]})
res["edits 2 refs -> field 'image[]' x2"] = s == 200 and calls[-1]["files"] == [b"image[]", b"image[]"]
res["edits 3 refs -> 400"] = post(E, "bk", {"prompt": "x", "images": [b64(PNG)] * 3})[0] == 400
res["edits no refs -> 400"] = post(E, "bk", {"prompt": "x", "images": []})[0] == 400
res["edits bad base64 -> 400"] = post(E, "bk", {"prompt": "x", "images": ["not base64!!"]})[0] == 400
res["edits non-image bytes -> 400"] = post(E, "bk", {"prompt": "x", "images": [b64(b"GIF89a....")]})[0] == 400
res["edits >10MB ref -> 400"] = post(E, "bk", {"prompt": "x", "images": [b64(b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024 + 1))]})[0] == 400
res["edits model not allowed -> 404"] = post(E, "bk", {"prompt": "x", "model": "gpt-image-2", "images": [b64(PNG)]})[0] == 404
# builderxai has used 2 (edits) so far; quota 3 is shared between generations and edits
res["quota shared: 3rd ok"] = post(G, "bk", {"prompt": "x"})[0] == 200
res["quota shared: 4th (edit) -> 429"] = post(E, "bk", {"prompt": "x", "images": [b64(PNG)]})[0] == 429
for k, v in res.items():
    print("✅" if v else "❌", k)
raise SystemExit(0 if all(res.values()) else 1)
