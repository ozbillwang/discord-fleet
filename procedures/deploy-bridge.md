# Procedure: deploy / update the Discord Bridge (operator: the deployer)

Source of truth: `bridge/` in this repo. The host only receives built artifacts and data. Nobody edits code on the host.

## Deploy (first time, per Bot User)
1. Copy `bridge/` to the host (e.g. `git archive HEAD bridge | ssh host tar x -C /tmp/bx-bridge-src`), then build **as the Bot User's runtime user** on its rootless engine: `docker build -t bx-bridge:<git-sha> .` Tag with the git sha so the running version can be traced back.
2. Create the data volume `/home/<user>/bots/<botuser>/` (0700) with:
   - `bridge.yaml` from `bridge.example.yaml` (bindings filled in from Guild's 【绑定请求】)
   - `omp-agent/models.yml` + `omp-agent/config.yml` from `bridge/omp-agent/` (base URL = the H8 proxy as seen from the container)
   - `agents/<name>/.omp/` from `bridge/agent-template/` for each binding
3. Container unit (replaces any previous runtime for that Bot User): env `DISCORD_BOT_TOKEN` + `CLIAPI_API_KEY` from the root-owned secret files, passed by name. `-v <data>:/data`, H2 limits, `--security-opt no-new-privileges`, image `bx-bridge:<git-sha>`.
4. Acceptance: `bridge/tests` (routing + omp) pass inside the image on the host; `spec/topics.md` Acceptance passes live; the container escape / H8 checks still pass. Record the sha + results in `hosts/<name>.md`.

## Update
Build a new sha tag → restart the unit with the new tag → run acceptance → record. To roll back, restart on the previous tag.

## Bindings change (no code change)
Edit `/data/bridge.yaml` and add/remove the agent dir. The bridge hot-reloads within 30 s; a bad config is rejected and the old one kept.
