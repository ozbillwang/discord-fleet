#!/usr/bin/env python3
"""Guild's web tool: search (TinyFish), answer (Tavily), fetch (TinyFish). Token from env BX_WEB_CLIENT_TOKEN."""
import argparse, json, os, sys, urllib.error, urllib.parse, urllib.request

TF_SEARCH = os.environ.get("TINYFISH_SEARCH", "https://search.example.com")
TF_FETCH = os.environ.get("TINYFISH_FETCH", "https://fetch.example.com")
TAVILY = os.environ.get("TAVILY_SERVER", "https://answer.example.com")
MAX_CHARS = 30000


def tok():
    t = os.environ.get("BX_WEB_CLIENT_TOKEN")
    if not t:
        sys.exit("BX_WEB_CLIENT_TOKEN not in environment (host config issue: tell the operator agent)")
    return t


def req(url, method="GET", headers=None, body=None, timeout=60):
    h = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=h), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} from {url.split('?')[0]}: {e.read().decode()[:200]}")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"error from {url.split('?')[0]}: {e}")


def main():
    p = argparse.ArgumentParser(prog="web.py")
    s = p.add_subparsers(dest="cmd", required=True)
    a = s.add_parser("search"); a.add_argument("query"); a.add_argument("--limit", type=int, default=8)
    a = s.add_parser("answer"); a.add_argument("question")
    a = s.add_parser("fetch"); a.add_argument("url")
    a = p.parse_args()

    if a.cmd == "search":
        d = req(f"{TF_SEARCH}/?" + urllib.parse.urlencode({"query": a.query}), headers={"X-API-Key": tok()})
        rows = (d.get("results") or [])[: a.limit]
        if not rows:
            print(f'(no results for "{a.query}") - try `answer` or another query'); return
        for i, r in enumerate(rows, 1):
            print(f"{i}. {r.get('title')}\n   {r.get('url')}\n   {r.get('snippet') or ''}")
    elif a.cmd == "answer":
        d = req(f"{TAVILY}/search", "POST", {"Authorization": "Bearer " + tok()},
                {"query": a.question, "max_results": 5, "include_answer": True})
        print("ANSWER:", d.get("answer") or "(none)", "\n\nSOURCES:")
        for i, r in enumerate(d.get("results") or [], 1):
            print(f"{i}. {r.get('title')} — {r.get('url')}")
    elif a.cmd == "fetch":
        if not a.url.lower().startswith(("http://", "https://")):
            sys.exit("only http(s) URLs")
        d = req(f"{TF_FETCH}/", "POST", {"X-API-Key": tok()}, {"urls": [a.url], "format": "markdown"})
        r = (d.get("results") or [{}])[0]
        text = (r.get("text") or "").replace("\\_", "_")
        if not text:
            print(f"(could not read {a.url}) {json.dumps(d.get('errors'))[:200]}"); return
        print(f"# {r.get('title') or a.url}\n{r.get('final_url') or a.url}\n")
        print(text[:MAX_CHARS] + ("\n\n[truncated]" if len(text) > MAX_CHARS else ""))


if __name__ == "__main__":
    main()
