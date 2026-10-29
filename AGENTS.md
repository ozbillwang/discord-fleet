# discord-fleet (agent instructions)

Design and policy repo for the **BuilderXAI public Discord bot fleet**. Maintained by the operator agent.

## Roles (decided by the owner, 2026-10-24, revised)

**Terminology:** `omp` is the agent *technology* inside Bot User containers (see `spec/topics.md`). It is not a person or an operator role.

| who | owns | does NOT do |
|---|---|---|
| **the operator agent** (e.g. a Hermes agent on the operator's machine) | this repo (spec, bridge code, Guild profile + skills, host artifacts). **Deploys repo artifacts to the host** (host layer, `/srv/builderxai/bridge`, `bx-botctl`, units). **Manages Guild Manager's Hermes**: config, SOUL, skills, model, `hermes-gw@guild` | the operator agent doesn't operate Bot Users day to day (bindings, personas, starting/stopping bots) |
| **Guild Manager** (Hermes on the host, user `bxadmin`) | the Discord server (channels, roles, invites) **and the Bot User runtimes**: Docker containers, Discord Bridge config, omp agent dirs. It works through the `bx-botctl` root tool only | it never edits code or the host layer, and never answers members |
| **Bot Users** (bridge + omp agents in bx's rootless containers) | answer members in their bound channels | they never manage anything |
| **the owner** | plans topics; creates new Discord apps/tokens; final say | — |

Interfaces:
- the operator agent → host: deploy from a git revision (`/srv/builderxai/bridge/REVISION`), install/update `bx-botctl`, units, Guild's Hermes profile.
- Guild → Bot Users: `botctl …` with staging in `/srv/builderxai/bots/<bot>/` (skill `bot-runtime`).
- Policy that must hold regardless of prompts is enforced **in `bx-botctl`** (admin channels unbindable, model only via the proxy, no symlinks/special files), not in SOUL text.

## How this repo works: target state, not scripts
- `spec/` holds target states and acceptance checks (what must be true + how to verify).
- `hosts/<name>.md` is the instance record (facts, decisions, deviations, latest acceptance results), kept by whoever operates the host.
- `procedures/` holds goal + checkpoint guides (new topic, new bot, new user, new credential, migrate host).
- `hosts/<name>/` holds reference artifacts as deployed on that host (units, proxy, policy scripts). They are examples, not the source of truth.

## Boundary with your servers repo
| | servers repo (server ops) | this repo (the operator agent) |
|---|---|---|
| Owns | the machine: OS, packages, users, container runtime, firewall, systemd, disk | the business: bots, roles, Discord policy, credential *inventory* (never values), target state |
| Records | *what is installed*, with a pointer here | *why*, *target state*, acceptance |

## Rules
1. **Secret values never enter this repo, chat, or logs.**
2. Host-layer and Guild changes are made by the operator agent from this repo; Bot User runtime changes are made by Guild Manager via `bx-botctl`. Nobody edits code on the host.
3. **Never reuse home credentials.** No personal agent, home-gateway or secret-manager tokens, no SSH keys, nothing that can reach the tailnet.
4. Hosts never hold credentials that can reach home.
5. Every host change must leave `spec/acceptance.md` green, with results recorded in `hosts/<name>.md`.

## Layout
```
spec/host.md            host-layer target state (H1–H8)
spec/bots/<bot>.md      per-bot target state
spec/topics.md          terms (Guild Manager / Bot User / Discord Bridge / Agent) + topic-channel model
bridge/                 Discord Bridge source (owned here; image built from this dir), templates, tests
spec/acceptance.md      checks that define "done"
profiles/<bot>/         Hermes profile templates, no secrets
procedures/*.md         deploy-operator (operator's host deploy) / new topic / deploy-bridge / new bot / new user / new credential / migrate host
hosts/<name>.md         instance records; hosts/<name>/ reference artifacts
```
