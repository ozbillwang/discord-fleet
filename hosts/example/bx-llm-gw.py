#!/usr/bin/env python3
"""bx-llm-gw: tiny model-allowlist proxy in front of model gateway (BuilderXAI fleet).

- Listens on 127.0.0.1 only.
- Clients authenticate with per-bot local keys (env BXGW_KEYS="name:key,name:key").
- Each client sees ONLY its allowed models (env BXGW_MODELS="name:alias=upstream|alias=upstream;name2:...").
- Rewrites the model to the upstream id, injects the upstream key (env CLIAPI_UPSTREAM_KEY).
- Per-client rate limit (requests/min) and max_tokens ceiling.
- Image generation: per-client image model allowlist (env BXGW_IMAGE_MODELS, same syntax), n<=BXGW_IMAGE_MAX_N,
  per-client daily image quota (BXGW_IMAGE_DAILY), always returns b64_json (no upstream URLs leak).
- Image edits: POST /v1/images/edits with JSON {model, prompt, size, images:[b64,...]} (<= 2 refs, png/jpeg/webp,
  <= 10 MB each); the gateway builds the multipart upstream call. Same allowlist, rate limit and daily quota.
- Routes: GET /v1/models, POST /v1/chat/completions (incl. stream), POST /v1/images/generations, POST /v1/images/edits.
  Everything else 404.
Stdlib only. Never logs keys, prompts or message content.
"""
import base64, http.server, json, os, socketserver, sys, threading, time, urllib.request, urllib.error, collections, uuid

UPSTREAM = os.environ.get("BXGW_UPSTREAM", "https://llm.example.com/v1").rstrip("/")
UP_KEY = os.environ["CLIAPI_UPSTREAM_KEY"]
LISTEN = os.environ.get("BXGW_LISTEN", "127.0.0.1:18080")
RPM = int(os.environ.get("BXGW_RPM", "20"))
MAX_TOKENS = int(os.environ.get("BXGW_MAX_TOKENS", "8192"))
MAX_BODY = int(os.environ.get("BXGW_MAX_BODY", str(8 * 1024 * 1024)))

KEYS = {}
for pair in filter(None, os.environ.get("BXGW_KEYS", "").split(",")):
    name, key = pair.split(":", 1)
    KEYS[key.strip()] = name.strip()
MODELS = {}   # client -> {alias: upstream}
for block in filter(None, os.environ.get("BXGW_MODELS", "").split(";")):
    name, spec = block.split(":", 1)
    MODELS[name.strip()] = dict(p.split("=", 1) for p in spec.split("|") if p)
IMAGE_MODELS = {}   # client -> {alias: upstream}
for block in filter(None, os.environ.get("BXGW_IMAGE_MODELS", "").split(";")):
    name, spec = block.split(":", 1)
    IMAGE_MODELS[name.strip()] = dict(p.split("=", 1) for p in spec.split("|") if p)
IMAGE_MAX_N = int(os.environ.get("BXGW_IMAGE_MAX_N", "2"))
IMAGE_DAILY = int(os.environ.get("BXGW_IMAGE_DAILY", "100"))
IMAGE_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}
_img_day = {}   # client -> (yyyymmdd, count)
EDIT_MAX_REFS = 2
EDIT_MAX_REF_BYTES = 10 * 1024 * 1024
EDIT_MAX_BODY = 32 * 1024 * 1024
IMAGE_MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png", "png"), (b"\xff\xd8\xff", "image/jpeg", "jpg"))

_hits = collections.defaultdict(collections.deque)
_lock = threading.Lock()

def log(*a):
    print(time.strftime("%Y-%m-%dT%H:%M:%S"), *a, file=sys.stderr, flush=True)

def rate_ok(client):
    now = time.time()
    with _lock:
        q = _hits[client]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RPM:
            return False
        q.append(now)
        return True

def image_quota_ok(client, n):
    day = time.strftime("%Y%m%d")
    with _lock:
        d, c = _img_day.get(client, (day, 0))
        if d != day:
            c = 0
        if c + n > IMAGE_DAILY:
            return False, IMAGE_DAILY - c
        _img_day[client] = (day, c + n)
        return True, IMAGE_DAILY - c - n

class H(http.server.BaseHTTPRequestHandler):
    server_version = "bx-llm-gw/1"
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _client(self):
        auth = self.headers.get("Authorization", "")
        key = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        return KEYS.get(key)

    def do_GET(self):
        client = self._client()
        if not client:
            return self._json(401, {"error": {"message": "invalid api key"}})
        if self.path.rstrip("/") in ("/v1/models", "/models"):
            data = [{"id": a, "object": "model", "owned_by": "builderxai"} for a in MODELS.get(client, {})]
            data += [{"id": a, "object": "model", "owned_by": "builderxai", "type": "image"} for a in IMAGE_MODELS.get(client, {})]
            return self._json(200, {"object": "list", "data": data})
        if self.path == "/healthz":
            return self._json(200, {"ok": True})
        return self._json(404, {"error": {"message": "not found"}})

    def do_POST(self):
        client = self._client()
        if not client:
            return self._json(401, {"error": {"message": "invalid api key"}})
        if self.path.rstrip("/") in ("/v1/images/generations", "/images/generations"):
            return self._images(client)
        if self.path.rstrip("/") in ("/v1/images/edits", "/images/edits"):
            return self._image_edits(client)
        if self.path.rstrip("/") not in ("/v1/chat/completions", "/chat/completions"):
            return self._json(404, {"error": {"message": "not found"}})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return self._json(413, {"error": {"message": "body too large or empty"}})
        try:
            body = json.loads(self.rfile.read(n))
        except Exception:
            return self._json(400, {"error": {"message": "invalid json"}})
        allowed = MODELS.get(client, {})
        alias = body.get("model")
        if alias not in allowed:
            # tolerate clients that send the upstream id directly
            rev = {v: k for k, v in allowed.items()}
            if alias in rev:
                alias = rev[alias]
            else:
                return self._json(404, {"error": {"message": f"model not available; allowed: {sorted(allowed)}"}})
        if not rate_ok(client):
            return self._json(429, {"error": {"message": f"rate limit {RPM}/min"}})
        body["model"] = allowed[alias]
        for k in ("max_tokens", "max_completion_tokens"):
            if isinstance(body.get(k), int) and body[k] > MAX_TOKENS:
                body[k] = MAX_TOKENS
        if "max_tokens" not in body and "max_completion_tokens" not in body:
            body["max_tokens"] = MAX_TOKENS
        stream = bool(body.get("stream"))
        req = urllib.request.Request(UPSTREAM + "/chat/completions", data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": "Bearer " + UP_KEY, "Content-Type": "application/json",
                     "Accept": "text/event-stream" if stream else "application/json"})
        t0 = time.time()
        try:
            resp = urllib.request.urlopen(req, timeout=600)
        except urllib.error.HTTPError as e:
            data = e.read()
            log(client, alias, "upstream", e.code, f"{time.time()-t0:.1f}s")
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        except Exception as e:
            log(client, alias, "upstream error", type(e).__name__)
            return self._json(502, {"error": {"message": "upstream unavailable"}})
        self.send_response(resp.status)
        self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
        if stream:
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            while True:
                chunk = resp.read1(8192) if hasattr(resp, "read1") else resp.read(8192)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                    self.wfile.flush()
                except BrokenPipeError:
                    break
        else:
            data = resp.read()
            try:
                d = json.loads(data)
                if isinstance(d, dict) and "model" in d:
                    d["model"] = alias
                    data = json.dumps(d).encode()
            except Exception:
                pass
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        log(client, alias, resp.status, "stream" if stream else "", f"{time.time()-t0:.1f}s")

    # ---- images: shared validation + result handling
    def _image_common(self, client, max_body):
        """Validate auth/allowlist/body; returns (body, alias, size) or None after sending the error."""
        allowed = IMAGE_MODELS.get(client, {})
        if not allowed:
            self._json(403, {"error": {"message": "image generation not enabled for this client"}}); return None
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > max_body:
            self._json(413, {"error": {"message": "body too large or empty"}}); return None
        try:
            body = json.loads(self.rfile.read(n))
        except Exception:
            self._json(400, {"error": {"message": "invalid json"}}); return None
        alias = body.get("model") or next(iter(allowed))
        if alias not in allowed:
            self._json(404, {"error": {"message": f"image model not available; allowed: {sorted(allowed)}"}}); return None
        prompt = body.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
            self._json(400, {"error": {"message": "prompt must be a non-empty string <= 4000 chars"}}); return None
        size = body.get("size", "1024x1024")
        if size not in IMAGE_SIZES:
            self._json(400, {"error": {"message": f"size must be one of {sorted(IMAGE_SIZES)}"}}); return None
        return body, alias, size

    def _image_gate(self, client, count):
        if not rate_ok(client):
            self._json(429, {"error": {"message": f"rate limit {RPM}/min"}}); return None
        ok, left = image_quota_ok(client, count)
        if not ok:
            self._json(429, {"error": {"message": f"daily image quota reached ({IMAGE_DAILY}/day)"}}); return None
        return left

    def _image_upstream(self, client, kind, alias, req, left):
        t0 = time.time()
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=300).read())
        except urllib.error.HTTPError as e:
            data = e.read()[:2000]
            log(client, kind, alias, "upstream", e.code, f"{time.time()-t0:.1f}s")
            return self._json(e.code if 400 <= e.code < 600 else 502,
                              {"error": {"message": "upstream refused: " + data.decode("utf-8", "replace")[:300]}})
        except Exception as e:
            log(client, kind, alias, "upstream error", type(e).__name__)
            return self._json(502, {"error": {"message": "upstream unavailable"}})
        out = []
        for item in d.get("data", []):
            if item.get("b64_json"):
                out.append({"b64_json": item["b64_json"]})
            elif item.get("url"):   # fetch server-side so callers never see upstream URLs
                try:
                    with urllib.request.urlopen(item["url"], timeout=60) as r:
                        out.append({"b64_json": base64.b64encode(r.read()).decode()})
                except Exception:
                    pass
        log(client, kind, alias, 200, f"n={len(out)}", f"{time.time()-t0:.1f}s", f"quota_left={left}")
        return self._json(200, {"created": int(time.time()), "model": alias, "data": out})

    def _images(self, client):
        v = self._image_common(client, 64 * 1024)
        if not v:
            return
        body, alias, size = v
        count = body.get("n", 1)
        if not isinstance(count, int) or not 1 <= count <= IMAGE_MAX_N:
            return self._json(400, {"error": {"message": f"n must be 1..{IMAGE_MAX_N}"}})
        left = self._image_gate(client, count)
        if left is None:
            return
        up = {"model": IMAGE_MODELS[client][alias], "prompt": body["prompt"], "n": count, "size": size, "response_format": "b64_json"}
        req = urllib.request.Request(UPSTREAM + "/images/generations", data=json.dumps(up).encode(), method="POST",
            headers={"Authorization": "Bearer " + UP_KEY, "Content-Type": "application/json"})
        return self._image_upstream(client, "image", alias, req, left)

    def _image_edits(self, client):
        v = self._image_common(client, EDIT_MAX_BODY)
        if not v:
            return
        body, alias, size = v
        refs = body.get("images")
        if not isinstance(refs, list) or not 1 <= len(refs) <= EDIT_MAX_REFS:
            return self._json(400, {"error": {"message": f"images must be a list of 1..{EDIT_MAX_REFS} base64 images"}})
        files = []
        for i, r in enumerate(refs):
            try:
                raw = base64.b64decode(r, validate=True) if isinstance(r, str) else None
            except Exception:
                raw = None
            if not raw:
                return self._json(400, {"error": {"message": f"images[{i}] is not valid base64"}})
            if len(raw) > EDIT_MAX_REF_BYTES:
                return self._json(400, {"error": {"message": f"images[{i}] larger than 10 MB"}})
            kind = next(((ct, ext) for magic, ct, ext in IMAGE_MAGIC if raw.startswith(magic)), None)
            if kind is None and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
                kind = ("image/webp", "webp")
            if kind is None:
                return self._json(400, {"error": {"message": f"images[{i}] must be png, jpeg or webp"}})
            files.append((raw, kind[0], kind[1]))
        left = self._image_gate(client, 1)
        if left is None:
            return
        b = uuid.uuid4().hex
        parts = []
        for k, val in (("model", IMAGE_MODELS[client][alias]), ("prompt", body["prompt"]), ("n", "1"),
                       ("size", size), ("response_format", "b64_json")):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{val}\r\n'.encode())
        field = "image" if len(files) == 1 else "image[]"
        for i, (raw, ct, ext) in enumerate(files):
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="ref{i}.{ext}"\r\n'
                         f'Content-Type: {ct}\r\n\r\n'.encode() + raw + b"\r\n")
        data = b"".join(parts) + f"--{b}--\r\n".encode()
        req = urllib.request.Request(UPSTREAM + "/images/edits", data=data, method="POST",
            headers={"Authorization": "Bearer " + UP_KEY, "Content-Type": f"multipart/form-data; boundary={b}"})
        return self._image_upstream(client, f"image-edit refs={len(files)}", alias, req, left)

class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    host, port = LISTEN.rsplit(":", 1)
    assert host in ("127.0.0.1", "::1"), "must listen on loopback only"
    log("bx-llm-gw listening", LISTEN, "clients:", sorted(MODELS), "rpm", RPM, "max_tokens", MAX_TOKENS,
        "image clients:", {c: sorted(m) for c, m in IMAGE_MODELS.items()}, "image daily", IMAGE_DAILY)
    S((host, int(port)), H).serve_forever()
