# Terms and topic model (target state)

## Terms (decided by the owner, 2026-10-24; these are authoritative)

| term | what it is | where it runs | model |
|---|---|---|---|
| **Guild Manager** | the server-admin bot. Obeys the owner only, in #admin. Manages channels, topics, members, and binds Bot Users to channels | **host** (the reference host, user `bxadmin`) as a **Hermes** gateway | strong model direct from the model gateway: Claude Opus (`claude-opus-5-5`) or Fable (`claude-fable-5-1`) |
| **Bot User** | a Discord bot application that members talk to. Today there is **one** ("BuilderXAI Bot"); more may be added later | a **Docker container** (rootless, user `bx`, public egress only) | Gemini, only through the local allowlist proxy (H8) |
| **Discord Bridge** | the program inside a Bot User's container that **registers with Discord using that Bot User's token**, receives messages, and routes each channel/thread to an agent; replies go back through it | inside the Bot User's container | — |
| **Agent** | an **omp** instance that does the actual answering. **Each agent is defined by its own directory** (its `.omp/SYSTEM.md` persona, `.omp/config.yml`, MCP config, memory/sessions). Directories are isolated from each other | inside the Bot User's container, spawned by the Discord Bridge (`omp --mode rpc`, `cwd` = the agent's directory) | the Bot User's Gemini (proxy) |

Relations:
```
the owner ──#admin──▶ Guild Manager (Hermes, host)
                     │ creates channels, asks the runtime to bind
                     ▼
Discord ◀──token──▶ Discord Bridge ──channel→dir──▶ omp agent (dir A: topic A)
   (one Bot User)    (in container)                  omp agent (dir B: topic B) ...
```
- One Bot User can serve many channels. **Each channel maps to one agent directory**, so channels are different identities on the same Discord application.
- **The bridge code lives in this repo: `bridge/`** (Python + discord.py, spawns `omp --mode rpc --no-tools` with `cwd` = agent dir, one session per thread). It was derived from the maint-agent bridge. Deploy per `procedures/deploy-bridge.md`.

## Requirements
| ID | requirement |
|---|---|
| T1 | Each topic channel is bound to exactly one agent directory. Threads under the channel go to the same agent. |
| T2 | In topic channels the Bot User answers **without @mention** and **always replies in a thread**. Follow-ups happen in that thread. |
| T3 | Agents get no host access. They run with `--no-tools` or a minimal allowlisted toolset, plus Gemini via the proxy only. An agent directory must not widen this. |
| T4 | Agents, the bridge and the Bot User token live only in the Bot User's container (H1/H2/H4). Nothing runs on the host as `bx` outside the container. |
| T5 | Admin space (Admin category, #admin) is never bound to any Bot User. |
| T6 | Adding topics never grants members new Discord permissions. |
| T7 | Every binding (channel id → agent dir, date) is recorded in `hosts/<name>.md`. |
| T8 | Guild Manager is never a Bot User and never runs in the container. Bot Users never get admin permissions. |

## Acceptance
- In a new topic channel, a member message without @ → a thread opens and the reply follows that agent's persona.
- Two channels give answers in their own personas, and memory does not leak between agent dirs.
- From inside the container: no host files, no tailnet/LAN, model only via the proxy (same checks as H8 + container escape test).
- #admin → no Bot User response.

## Current deviation (2026-10-24)
**Resolved 2026-10-24 06:16 UTC:** BuilderXAI Bot runs the Discord Bridge (`bx-bridge@builderxai`); the old Hermes container is disabled. See `hosts/<name>.md`.
