# bridge/ — BuilderXAI Discord Bridge (source of truth)

This code is **owned by this repo**. The runtime (omp) deploys it as-is: build the image from this directory and run one container per Bot User. Changes go through this repo, never as edits on the host.

## What it does
```
Discord ──(Bot User token)── bridge.py ──channel→agent dir── omp --mode rpc --no-tools
                                                (cwd = agents/<name>, one session per thread)
```
- **T1** `bridge.yaml` maps `channel_id → agent`. Threads go through their parent channel.
- **T2** In bound channels, no @ is needed. A top-level message opens a thread, and the reply plus all follow-ups stay in that thread. `!reset` inside a thread starts a fresh conversation.
- **T3** omp always runs `--no-tools --no-lsp --no-pty`. An agent dir can't turn tools back on. omp children get only `CLIAPI_API_KEY` (never the Discord token).
- **T5** Unbound channels and DMs are ignored. That includes the Admin space.
- One omp process per **active thread**. Idle processes stop after `idle_session_seconds`; the session stays on disk and resumes with `--continue`. `max_live_sessions` caps memory.
- Flood guard: `per_user_per_min`. Extra messages get ⏳ and are not processed.
- Config hot-reload: on SIGHUP or file mtime change (checked every 30 s). A bad config is rejected and the old one kept.

## Layout of a Bot User's data volume (`/data`)
```
/data/bridge.yaml                 # bindings + limits (see bridge.example.yaml)
/data/omp-agent/models.yml        # shared model config (PI_CODING_AGENT_DIR); apiKey: CLIAPI_API_KEY (env name)
/data/agents/<name>/.omp/SYSTEM.md   # persona + safety block (template: agent-template/)
/data/agents/<name>/.omp/config.yml  # per-agent omp settings (compaction etc.)
/data/sessions/<name>/<thread_id>/   # omp session files (isolated per agent and thread)
```

## Image
`Dockerfile`: `oven/bun` + pinned `@oh-my-pi/pi-coding-agent` + Python venv (discord.py, PyYAML) + tini. It runs as uid 10001. Inside the Bot User's rootless runtime that maps to an unprivileged host subuid.

## Run (target state, implementation left to the operator)
- Container per Bot User. Env: `DISCORD_BOT_TOKEN` and `CLIAPI_API_KEY`, passed in by name only. Volume `/data` rw. Limits like H2 (memory, pids, cpus, no-new-privileges).
- Model base URL in `models.yml` = the H8 proxy as seen from the container (`http://10.0.2.2:18080/v1` on rootless + host-loopback).
- Acceptance: `spec/topics.md` + the H8/container escape checks, run from inside this container.
