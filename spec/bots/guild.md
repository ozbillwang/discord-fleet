# Bot: guild (admin / server manager)

## Role
the operator's counterpart inside the public BuilderXAI Discord server. It manages the
server itself and does **not** chat with members:
- channels, categories, roles, permissions
- invites; onboarding and welcome flow; pointing newcomers to the right bot's channel
- moderation: delete/pin messages, timeouts
- managing the other bots' Discord applications where their own token allows (description, avatar, slash commands)

## Placement
| item | value |
|---|---|
| Linux user | `bxadmin` |
| Tool execution | on the host (`terminal.backend: local`). No container runtime |
| Why no sandbox | it obeys the owner only. Its risk is prompt injection from web content, which H4 egress and H5 file hygiene cover |

## Who can command it
- `DISCORD_ALLOWED_USERS` = the owner's Discord user ID only. Everyone else gets no response (acceptance G3).
- Works only in a private `#admin` channel (`allowed_channels`), visible to the owner + guild.
- `allow_admin_from` / `group_allow_admin_from` = the owner only.

## Credentials (secret files, see spec/host.md H6)
| file | key(s) | scope |
|---|---|---|
| `llm-guild.env` | model API key for model gateway (or provider) | dedicated key, spend cap |
| `guild.env` | `DISCORD_BOT_TOKEN` | new Discord application "Guild" |
| `github.env` | `GITHUB_TOKEN` | fine-grained PAT, BuilderXAI repos only |
| `email.env` | mail provider key | BuilderXAI sending domain only |

## Hermes config policy (`profiles/guild/config.yaml`)
- `discord.require_mention: false` (private channel), `auto_thread: true`
- Toolsets: the default Discord toolset is acceptable here (includes `discord_admin`, terminal, file).
- Discord bot permissions: Manage Channels, Manage Roles, Manage Messages, Manage Threads, Create Instant Invite, Moderate Members, Manage Webhooks, View Audit Log. **Not** Administrator.
- **Gap to fill:** Hermes' `discord_admin` cannot create channels or invites. Guild needs a skill that calls the Discord REST API for `POST /guilds/{id}/channels` and `POST /channels/{id}/invites`.

## SOUL (summary; full text in profiles/guild/SOUL.md)
BuilderXAI community steward. Concise, operational. Never reveals operator
infrastructure. Holds nothing about the owner's private life.
