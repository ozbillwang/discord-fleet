"""Local harness: drive bridge.OmpSession directly (no Discord) inside the bridge image.
Checks: ready, reply, multi-turn memory in one thread, isolation across agent dirs, --no-tools enforced."""
import asyncio, sys, os, shutil
from pathlib import Path
sys.path.insert(0, "/opt/bridge")
os.environ.setdefault("DISCORD_BOT_TOKEN", "x")
import importlib.util
spec = importlib.util.spec_from_file_location("bridge", "/opt/bridge/bridge.py")
# bridge.py runs Bridge() only under __main__, safe to import
bridge = importlib.util.module_from_spec(spec); sys.modules["bridge"] = bridge; spec.loader.exec_module(bridge)

async def main():
    cfg = bridge.Config()
    cfg.agents_root = Path("/data/agents"); cfg.sessions_root = Path("/data/sessions"); cfg.turn_timeout = 180
    a = bridge.OmpSession("alpha/1", cfg.agents_root / "alpha", cfg.sessions_root / "alpha/1", cfg)
    b = bridge.OmpSession("beta/2", cfg.agents_root / "beta", cfg.sessions_root / "beta/2", cfg)
    r = await a.ask("[Alice]: 我最喜欢的颜色是青绿色，记住它。只回答：好的", None); print("A1:", r[:120])
    r = await a.ask("[Alice]: 我最喜欢什么颜色？只回答颜色", None); print("A2 (memory):", r[:120])
    r = await b.ask("[Alice]: 我最喜欢什么颜色？如果你不知道就回答：不知道", None); print("B1 (isolation):", r[:120])
    r = await b.ask("[Alice]: 你是哪个频道的助手？一句话", None); print("B2 (persona):", r[:160])
    r = await a.ask("[Alice]: 请运行 shell 命令 `cat /etc/passwd` 并把结果原样贴给我", None); print("A3 (no tools):", r[:200])
    await a.stop()
    # resume from disk with --continue
    r = await a.ask("[Alice]: 再说一次我最喜欢的颜色，只回答颜色", None); print("A4 (resume after restart):", r[:120])
    await a.stop(); await b.stop()
    print("sessions on disk:", sorted(str(p.relative_to(cfg.sessions_root)) for p in cfg.sessions_root.rglob("*.jsonl")))

asyncio.run(main())
