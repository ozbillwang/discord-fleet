# Procedure: the operator agent deploys the repo to a fleet host

the operator agent deploys from a **committed** revision only (`git status` clean), then records the sha in `hosts/<name>.md`.

| artifact (repo) | host target | owner/mode |
|---|---|---|
| `bridge/` (git archive of HEAD) + `REVISION` file | `/srv/builderxai/bridge/` | root:root, dirs 755, files 644 |
| `hosts/<h>/bx-botctl` | `/usr/local/sbin/bx-botctl` | root 0755 |
| `hosts/<h>/bx-botctl.socket` + `bx-botctl@.service` | `/etc/systemd/system/` | root 0644; socket `/run/bx-botctl.sock` root:bxadmin 0660 |
| `hosts/<h>/botctl` (client) | `/usr/local/bin/botctl` | root 0755 |
| `hosts/<h>/bx-bridge@.service` | `/etc/systemd/system/` | root 0644, then `daemon-reload` |
| `profiles/guild/{SOUL.md,config.yaml}` | `~bxadmin/.hermes/` (merge config keys; never overwrite secrets) | bxadmin |
| `profiles/guild/skills/*` | `~bxadmin/.hermes/skills/builderxai/` | bxadmin |
| staging root | `/srv/builderxai/bots/` | bxadmin:bxadmin 0750 |

After a deploy: restart `hermes-gw@guild` if its profile changed; `sudo -u bxadmin botctl status` must work; run the acceptance checks for whatever changed.
Bot User runtime (bindings, personas, start/stop) is **not** the operator's job after deploy. Guild does it via `bx-botctl`.
