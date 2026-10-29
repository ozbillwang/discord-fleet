# hosts/example — reference artifacts

What was actually deployed on the reference host (Ubuntu 22.04 ARM VM, systemd, iptables, rootless Docker).
These are **examples**, not the source of truth: `spec/` is. Adapt paths, uids and the public IP to your host.

| file | what | spec |
|---|---|---|
| `bx-egress.sh` | uid-owner iptables chain: bot users reach the public internet only (needs `PUB_IP`) | H4 |
| `bx-llm-gw.py` + `.service` | stdlib allowlist proxy in front of your model gateway: per-bot keys, model allowlist, rate limit, max_tokens, image quota | H8 |
| `bx-botctl` + `.socket` + `@.service`, `botctl` | the only root tool Guild Manager may call: validates staging, refuses admin-channel bindings, builds the bridge image, starts/stops Bot Users | topics T5/T8 |
| `bx-bridge@.service` | one rootless container per Bot User (`--cap-drop ALL`, no-new-privileges, memory/pids/cpu limits) | H2, T4 |
| `hermes-gw@.service` + drop-ins | Guild Manager (Hermes) gateway as user `bxadmin` | H7 |
| `hermes-bot@.service` | earlier variant: whole Hermes gateway in a container (superseded by the bridge) | — |
| `discord-ops.py`, `discord-policy.py` | one-off root helpers: bot avatars, private #admin, member permission policy (ids from env `BX_*`) | spec/bots |
| `tests/bx_llm_gw_test.py` | offline tests for the proxy | H8 |

Hard-coded in these files: user `bx` uid `1002`, data roots `/srv/builderxai`, `/home/bx/bridges`, proxy port `18080`.
