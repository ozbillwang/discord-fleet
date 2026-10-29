---
name: discord-channel-admin
description: "Create/edit/delete Discord channels and categories, set permission overwrites (private channels, read-only, add a bot to a channel), and create invites in the BuilderX AI server via Discord REST. Use when Hermes' discord_admin tool lacks the action."
version: 1.0.0
author: builderxai-fleet (the operator agent)
metadata:
  hermes:
    tags: [discord, channels, permissions, invites, admin]
---

# Discord channel admin (REST)

Hermes' built-in `discord_admin` tool can't create channels, edit permissions or make invites. This skill fills that gap with one script:
`python3 ${HERMES_SKILL_DIR}/scripts/dc.py <command> ...` (run with the terminal tool).

The script reads `BX_GUILD_REST_TOKEN` (your own bot token, injected by the host under a name Hermes doesn't strip) and **never prints it**. If you get "not in environment", tell the operator agent. Every write goes into the Discord audit log with a reason.

## Commands
| command | what it does |
|---|---|
| `list` | channels with id / type / parent / overwrites, plus roles |
| `create-category <name> [--private]` | new category; `--private` = @everyone can't see it |
| `create-channel <name> [--parent <cat_id>] [--topic T] [--private] [--readonly]` | new text channel |
| `edit-channel <id> [--name N] [--topic T] [--parent <cat_id>]` | rename / move |
| `delete-channel <id> --confirm` | **destructive**: only after the owner confirms |
| `allow <channel_id> <user_or_role_id> [--member\|--role] [--talk\|--read]` | grant access (e.g. put a bot or person into a private channel) |
| `deny-everyone <channel_id> [--view\|--send]` | hide from members, or make it read-only |
| `clear <channel_id> <user_or_role_id>` | remove an overwrite |
| `invite <channel_id> [--max-age S] [--max-uses N]` | invite link (default 24 h, 10 uses) |
| `create-thread <channel_id> <name> [--archive-minutes 60\|1440\|4320\|10080]` | public thread in a channel |
| `timeout <user_id> <minutes> [--reason R]` / `untimeout <user_id>` | mute a member (max 28 days) / lift it |
| `ban <user_id> --reason R --confirm` / `unban <user_id>` | **destructive**: ban only after the owner confirms |

`--talk` = View + Send + Send in Threads + History + Create Public Threads + React + Embed + Attach. `--read` = View + History.

## Rules (from SOUL.md; non-negotiable)
- Propose → the owner confirms → execute, for anything structural, permission-related or destructive.
- Never touch the Admin category or #admin (`BX_PROTECTED_IDS`), except to keep them private.
- Never grant members or Bot Users ADMINISTRATOR / MANAGE_* / MENTION_EVERYONE.
- **Putting a Bot User "into" a channel = two steps.** (1) Discord permission: `allow <channel> <bot_user_id> --member --talk`, only needed for private channels; public channels already work. (2) Runtime binding: skill `bot-runtime` (staging + `botctl apply`).
- Known Bot Users: BuilderXAI Bot = `<public bot user id>`.
- After each change, run `list` and report what changed and how to undo it.

## Pitfalls
- **Fixed 2026-10-24:** Chinese (non-ASCII) names used to crash with `UnicodeEncodeError: latin-1`, because the audit-log reason is an HTTP header. `dc.py` now URL-encodes the reason, so Chinese channel and thread names work directly. The old workaround (raw `dc.api(...)` with an ASCII reason) is no longer needed.
- To create a thread, use `create-thread` instead of calling `POST /channels/<id>/threads` by hand.
