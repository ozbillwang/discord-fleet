#!/usr/bin/env python3
"""BuilderX AI image generation via local bx-llm-gw (127.0.0.1:18080). Key from env BX_LLM_GW_KEY. Never prints it."""
import argparse, base64, json, os, sys, urllib.error, urllib.request

GW = os.environ.get("BX_LLM_GW_URL", "http://127.0.0.1:18080/v1")


def main():
    ap = argparse.ArgumentParser(prog="imagine.py")
    ap.add_argument("prompt")
    ap.add_argument("output", help="output PNG path (for n>1 an index is appended)")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--size", default="1024x1024", choices=["1024x1024", "1024x1536", "1536x1024", "auto"])
    ap.add_argument("--n", type=int, default=1)
    a = ap.parse_args()
    key = os.environ.get("BX_LLM_GW_KEY")
    if not key:
        sys.exit("BX_LLM_GW_KEY not in environment (host config issue: tell the operator agent)")
    body = {"model": a.model, "prompt": a.prompt, "n": a.n, "size": a.size}
    req = urllib.request.Request(f"{GW}/images/generations", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=320).read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"gateway error: {e}")
    items = d.get("data") or []
    if not items:
        sys.exit("no image returned")
    root, ext = os.path.splitext(a.output)
    for i, it in enumerate(items):
        data = base64.b64decode(it["b64_json"])
        real = ".png" if data[:8] == b"\x89PNG\r\n\x1a\n" else ".jpg" if data[:3] == b"\xff\xd8\xff" else ".webp" if data[8:12] == b"WEBP" else (ext or ".png")
        base = a.output if len(items) == 1 else f"{root}-{i + 1}{ext or real}"
        path = os.path.splitext(base)[0] + real   # extension follows the real format (grok returns JPEG)
        with open(path, "wb") as f:
            f.write(data)
        print(f"saved {path} ({len(data)} bytes, model {d.get('model')})")


if __name__ == "__main__":
    main()
