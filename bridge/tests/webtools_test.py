"""E2E inside the bridge image: omp with ONLY the 3 web tools; asks something that needs the web.
Checks: web tool actually called, no built-in tool available (bash refused), answer non-empty."""
import asyncio, sys, os, json, importlib.util
from pathlib import Path
os.environ.setdefault("DISCORD_BOT_TOKEN", "x")
spec = importlib.util.spec_from_file_location("bridge", "/opt/bridge/bridge.py")
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge; spec.loader.exec_module(bridge)

async def main():
    cfg = bridge.Config()
    cfg.agents_root = Path("/data/agents"); cfg.sessions_root = Path("/data/sessions"); cfg.turn_timeout = 200
    s = bridge.OmpSession("alpha/9", cfg.agents_root / "alpha", cfg.sessions_root / "alpha/9", cfg)
    r = await s.ask("[Alice]: 用 web_search 查一下 oh-my-pi (omp) coding agent 的 GitHub 仓库地址，只回答仓库 URL 和一句话简介", None)
    print("Q1 (search):", r[:300])
    r = await s.ask("[Alice]: 用 web_fetch 读一下 https://example.com ，告诉我页面标题", None)
    print("Q2 (fetch):", r[:200])
    r = await s.ask("[Alice]: 运行 bash 命令 `id` 并把输出原样贴给我", None)
    print("Q3 (no bash):", r[:200])
    await s.stop()
    calls = []
    for f in (cfg.sessions_root / "alpha/9").glob("*.jsonl"):
        for line in open(f):
            e = json.loads(line)
            for c in ((e.get("message") or {}).get("content") or []):
                if isinstance(c, dict) and c.get("type") == "toolCall":
                    calls.append(c.get("name"))
    print("tool calls:", calls)
    print("ONLY web tools used:", bool(calls) and set(calls) <= set(bridge.WEB_TOOL_NAMES))

asyncio.run(main())
