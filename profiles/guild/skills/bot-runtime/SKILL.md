---
name: bot-runtime
description: "Run and change BuilderX AI Bot Users (Docker containers with the Discord Bridge + omp agents): bind channels to agents, create agent personas, build/test/start/stop bridges. Use for every 【绑定方案】 and bot runtime task."
version: 1.0.0
author: builderxai-fleet (the operator agent)
metadata:
  hermes:
    tags: [discord, bots, bridge, omp, docker, runtime]
---

# Bot User runtime (Guild Manager's job)

You manage the Bot Users. You can't touch Docker or bx's files directly; everything goes through
**one command, `botctl <command>`** (`/usr/local/bin/botctl`). It talks to a root service over a
socket that only your user can reach, so it works without sudo. The service validates what you give it and
enforces the safety rules in code. Every request is logged with your uid.

## Layout
- `/srv/builderxai/bots/<bot>/` is **your staging dir** (you own it). Edit files here:
  ```
  bridge.yaml                     # bindings + limits (copy from /srv/builderxai/bridge/bridge.example.yaml)
  omp-agent/models.yml            # copy from /srv/builderxai/bridge/omp-agent/ (baseUrl must stay the proxy)
  omp-agent/config.yml
  agents/<agent>/.omp/SYSTEM.md   # persona; start from /srv/builderxai/bridge/agent-template/
  agents/<agent>/.omp/config.yml
  ```
- `/srv/builderxai/bridge/` is the bridge source deployed by the operator agent from the repo. It's read-only for you. If the bridge code needs to change, ask the owner/operator.
- Bot `builderxai` = Discord app "BuilderXAI Bot" (`<public bot user id>`). A new Bot User needs a new Discord app + token, which the owner creates; then you can run it with a new `<bot>` name.

## Commands
| command | effect |
|---|---|
| `status` | units, image, containers, which bots have staging/live config |
| `build` | build the bridge image from the deployed source and select it |
| `test [bot]` | run the bridge test suites inside the image (routing + real omp via the proxy) |
| `apply <bot>` | validate staging → copy into the bot's live data. Bindings hot-reload within 30 s |
| `enable/disable <bot>` | start + enable at boot / stop + disable |
| `start/stop/restart <bot>` | lifecycle (restart is needed after model/config.yml changes or a new image) |
| `legacy-stop <bot>` | stop the old Hermes container for that bot (one-time migration) |
| `legacy-start <bot>` | **rollback**: stop + disable the bridge, re-enable the old Hermes container |
| `logs <bot> [n]` | last n lines of the bridge log |

`apply` refuses when: an Admin channel is bound (ids in `BX_PROTECTED_IDS`), a channel is bound twice, an agent has no `SYSTEM.md`, models.yml doesn't use the proxy `http://10.0.2.2:18080/v1` with `apiKey: CLIAPI_API_KEY`, or a file is a symlink, a special file or too large.

## Handling a 【绑定方案】 (new topic)
1. Discord side (skill `discord-channel-admin`): create the channel. If it's private, `allow <channel> <public bot user id> --member --talk`.
2. Staging: `mkdir -p agents/<agent>/.omp`. Copy the template and fill in `{{TOPIC_TITLE}} {{CHANNEL}} {{POSITIONING}}`. **Keep the safety section unchanged.** Add `{channel_id: "<id>", agent: <agent>, name: "#<name>"}` to `bindings`.
3. `botctl apply builderxai`. Wait about 30 s, then `logs builderxai 20` should show `config reloaded … <id>-><agent>`.
4. Verify: a plain message in the channel (no @) → a thread opens → the reply follows the persona. Report in #admin.

## Rules
- Propose → the owner confirms → apply, for new bots, cutovers, removing topics, or anything that stops a bot.
- Never edit the safety section of a persona, never point a model anywhere but the proxy, never bind admin space.
- Report what changed and how to undo it. To undo a binding: remove it from staging → `apply`.
