# discord-fleet

**How we run an AI-staffed Discord community on one small cloud VM — and keep it from ever reaching home.**

This is the real setup behind the [BuilderX AI](https://builderxai.dev) Discord server: an admin bot that runs the server for its owner, and public bots that answer members in topic channels. It is written as **target state + acceptance checks**, so an agent (or a person) can rebuild it on a different machine instead of replaying a script.

```
Owner ──#admin──▶ Guild Manager (Hermes agent, host user bxadmin, strong model)
                    │ creates topic channels, writes personas, binds them via bx-botctl
                    ▼
Discord ◀─token─▶ Discord Bridge (rootless container, user bx)
 members            │ channel → agent directory, thread → session
                    ├─▶ omp agent  #topic-a  (own persona + memory)
                    └─▶ omp agent  #topic-b  ...
                          │ model only via local allowlist proxy (bx-llm-gw)
                          ▼
                     your model gateway (public URL, dedicated key)
```

## The idea
- **One channel = one agent.** Each topic channel is bound to its own agent directory (persona `SYSTEM.md`, config, memory). Members just talk — no @mention; every top-level message opens a thread, one session per thread.
- **The admin is an agent too.** Guild Manager obeys only the owner in a private `#admin`. It plans channels, writes personas and binds bots — but only through `bx-botctl`, a root tool that enforces policy in code (admin channels can't be bound, model must go through the proxy, no symlinks), not in prompts.
- **Public bots are assumed hostile.** Anyone can prompt them, so they run with no tools that touch the host (`omp --no-tools` + an explicit allowlist: web search/fetch, image generation), in rootless containers, as a separate Linux user, with egress filtered to the **public internet only** (no tailnet, LAN, metadata, loopback, or the host's own IP).
- **No home credentials, ever.** Every token is new and scoped; bots never hold a key to the real model gateway — a tiny local proxy holds one upstream key and hands each bot only its allowlisted models, rate limit and token ceiling.

## Repo map
| path | what |
|---|---|
| `spec/host.md` | host target state H0–H8: users per trust level, rootless runtime, egress, secret store, model proxy |
| `spec/topics.md` | terms (Guild Manager / Bot User / Discord Bridge / Agent) and the topic-channel requirements T1–T8 |
| `spec/bots/*.md` | per-bot target state (permissions, who can command it, credentials inventory) |
| `spec/acceptance.md` | the checks that define "done" (privilege, secrets, egress must-fail list, container escape, Discord behaviour) |
| `bridge/` | **Discord Bridge** source: `bridge.py` (discord.py → `omp --mode rpc`), Dockerfile, omp tool extension `webtools.ts`, agent template, tests |
| `profiles/guild/` | Guild Manager's Hermes profile: SOUL + skills (`discord-channel-admin`, `bot-runtime`, `web`, `image-gen`) |
| `procedures/` | goal + checkpoint guides: new topic, new bot, new user, new credential, deploy, migrate host |
| `hosts/example/` | artifacts as deployed on the reference host (egress script, proxy, `bx-botctl`, systemd units) |
| `AGENTS.md` | instructions for the operator agent that maintains this repo |

## Rebuild it
1. Read `spec/host.md` and converge a Linux VM to H0–H8 (`hosts/example/` shows one way). Run `spec/acceptance.md` A–C until green.
2. Create the Discord apps (`procedures/new-credential.md`): one for Guild Manager, one per public Bot User. Secrets go only into `/etc/<fleet>/secrets/`, root 0600.
3. Deploy Guild Manager (Hermes) with `profiles/guild/` and set `BX_GUILD_ID`, `BX_OWNER_ID`, `BX_PROTECTED_IDS` (admin category + #admin).
4. Build the bridge image from `bridge/` and run one container per Bot User (`procedures/deploy-bridge.md`). Run `bridge/tests`.
5. From then on, the owner says in #admin "new topic X: one-line positioning" → Guild proposes channel + persona → owner confirms → Guild creates and binds it (`procedures/new-topic.md`).

Endpoints in the code (`llm.example.com`, `search.example.com`, …) are placeholders — point them at your own model gateway and search/fetch services via env.

## Stack
[Hermes Agent](https://hermes-agent.nousresearch.com) (admin bot) · [oh-my-pi / omp](https://github.com/can1357/oh-my-pi) (member-facing agents, RPC mode) · discord.py · rootless Docker · iptables uid-owner egress.

## Status
Running in production for the BuilderX AI server since 2026-10. Published as a reference design; expect to adapt paths, uids and models. MIT licensed.
