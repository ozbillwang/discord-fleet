# Bot: builderxai (public community bot)

## Role
Answers members in the BuilderXAI server's discussion channels, and posts the
AI news digest. Its audience is the AI builder community. Preferred topics:
Claude / coding agents / local models / voice & TTS. High-discussion topics
rank high, and community viewpoints and debates are surfaced.

## Placement
| item | value |
|---|---|
| Linux user | `bx` |
| Runtime | **the whole Hermes gateway runs inside a container** on bx's rootless runtime (official image), not just its tools. Host data enters only through its own data dir mount |
| Network | H4 egress, public internet only |

## Server model (the owner's design, 2026-10-24)
- the owner plans topics and has Guild create the channels. Members cannot manage anything.
- Members talk **only by @-mentioning BuilderXAI Bot** in channels. They may open public threads to continue a discussion.
- Members can't reach Guild: it ignores everyone but the owner, and its #admin is invisible to them.
- Members can't run slash commands on any bot (`@everyone` has no Use Application Commands).

## Who can command it
Any server member, in its allowed channels. Because of that, **Hermes approvals
are not a security boundary** for this bot. Verified against Hermes source
(`gateway/run.py` treats `yes`/`ok`/`👍` as approve, any allowed user can press
approval buttons, and `/yolo` is open unless restricted). Required:
- `group_allow_admin_from` / `allow_admin_from` = the owner only
- `group_user_allowed_commands` = a small whitelist (e.g. `help`, `new`). No `yolo`, `approve`, `sethome`, or `model`.
- `quick_commands: {}`
- `platform_toolsets.discord` listed **explicitly**. Not `hermes-discord`, which includes terminal, process, and `discord_admin`.
- `discord_admin` is **never** given to this bot.
- `docker_forward_env: []`, so no secrets go into the sandbox.
- DMs cannot be disabled in Hermes, and `allowed_channels` does not cover DMs. Accept this, or restrict with `dm_policy` if it's supported in the deployed version.

**Open decision:** keep `terminal` at all? Without it, the rootless runtime
(H2) is defence-in-depth only. With it, members can run code in the sandbox.
Default for first launch: **no terminal/file/code_execution**. Use web, search,
memory, and skills only. Revisit later.

## Credentials
| file | key(s) | scope |
|---|---|---|
| `llm-builderxai.env` | model API key | dedicated key, low spend cap |
| `builderxai.env` | `DISCORD_BOT_TOKEN` | new Discord application "BuilderXAI" |
| (optional) `github-ro.env` | read-only PAT | only if digest needs repo reads |

## Data carried over from a private assistant profile
Community positioning, digest scoring rules, and topic preferences go into
SOUL.md and memory. **Never** copy private memories wholesale, because they
contain private context.

## Discord bot permissions
View Channels, Send Messages, Send Messages in Threads, Create Public Threads,
Embed Links, Attach Files, Read Message History, Add Reactions.
