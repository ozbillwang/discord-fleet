# Host target state

A host is **compliant** when every requirement below holds and every check in
`acceptance.md` passes. Implementation (package manager, firewall frontend,
init system) is the host's choice; record it in `hosts/<name>.md`.

Reference implementation: an ARM cloud VM (Ubuntu 22.04, iptables, systemd, rootless Docker). Its deployed artifacts are in `hosts/example/`.

## H0. Host prerequisites
- Linux with cgroup v2. Unprivileged user namespaces must be allowed, since rootless containers need them.
- At least 2 vCPU, ≥4 GB RAM free, and ≥20 GB disk for the fleet.
- The host has public internet egress. Its tailnet/LAN membership is the threat that H4 contains.
- The operator reaches the host over SSH as an admin account with sudo. The bot users never get SSH.

## H1. Users (one Linux user per trust level)
| user | runs | trust | container runtime |
|---|---|---|---|
| `bxadmin` | admin bot(s) (`guild`): obeys the owner only | high | none |
| `bx` | public bot(s) (`builderxai`): answers any member | low | rootless, own |

Each bot user must satisfy all of:
- Not in sudoers, not in the `docker`/`podman` group, no `authorized_keys`, and no access to the tailnet daemon.
- Home directory mode `0750`. Users must not be able to read each other's homes.
- Linger enabled, so its user services start at boot without a login.
- It cannot read `/proc/<pid>/environ` of the other bot user. Separate uids give this by default; do not relax it.

Why two users: processes running under the same uid can read each other's
environment. If the public bot escaped its sandbox while sharing a uid with
the admin bot, it would get the admin bot's Discord token and GitHub PAT.

**Adding a bot:** a new bot at an existing trust level reuses that level's user (decision recorded in `bots/<bot>.md`). A new trust level gets a new user, and every H-requirement applies to it.

## H2. Rootless container runtime (low-trust users only)
- Owned and run by the bot user itself (e.g. rootless Docker or rootless Podman). Never give a bot user access to a root daemon socket.
- Install method must not conflict with the host's existing system container runtime. Prefer user-local binaries over adding package repos.
- Started at boot as the user's service. Socket at `/run/user/<uid>/…`.
- cgroup delegation for that user includes `cpu memory pids` (and `io` where available), so container limits actually apply. Scope it to that uid only, never globally.
- Resource ceiling for the user's whole slice: memory ≤ 4 GB (tunable per host) and a pids limit, so the public bot cannot starve the host's other services.

## H3. Directories
| path | owner | mode | purpose |
|---|---|---|---|
| `/srv/builderxai` | root | 0755 | fleet data root |
| `/srv/builderxai/repos` | `bx` | 0755 | workspaces mounted into public-bot sandboxes |
| `/srv/builderxai/shared` | `bxadmin` | 0755 | admin writes; public bot mounts read-only |

Host data reaches a sandbox only through an explicit volume mount. Never mount a container socket, `~/.hermes`, or the secret store.

## H4. Egress: public internet only (both bot users)
All traffic originating from a bot user's processes is filtered. That includes rootless-container traffic, which leaves the host as that user's process. Rules:

**Allowed:** the local DNS stub, on port 53 only. Everything on the public internet.

**Rejected:**
| range | why |
|---|---|
| `127.0.0.0/8`, `::1` (except the DNS stub) | local services, e.g. a tinyproxy that forwards into the tailnet |
| `0.0.0.0/8` | connects to "0.0.0.0" land on localhost |
| `100.64.0.0/10`, `fd7a:115c:a1e0::/48` | tailnet |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7` | LAN / cloud VPC |
| `169.254.0.0/16`, `fe80::/10` | cloud metadata, link-local |
| `224.0.0.0/4`, `ff00::/8` | multicast |
| the host's **own public IP(s)** | hairpin back to host services (sshd etc.) |

Constraints:
- Match on **packet owner (uid)** at the local-output hook, not on a container bridge or FORWARD. Rootless traffic never traverses FORWARD. On tailscale exit nodes, tailscale's own FORWARD chain accepts tailnet-bound packets before Docker's hooks are reached.
- **Never** blanket-allow the loopback interface. Packets to the host's own non-loopback IPs travel over `lo`.
- Rules are re-applied at boot **before** any bot user's services start.
- Persist only these rules. Don't snapshot the whole ruleset, because that would freeze the Docker/tailscale dynamic rules too.
- Known accepted residue: the DNS stub may forward to MagicDNS, so a bot can *resolve* tailnet names but cannot connect to them.

## H5. Local file exposure
Bot users are local accounts, so anything world-readable on the host is readable by them. Required:
- No world-readable credentials anywhere. At minimum, the admin user's home is not world-traversable, and service config files holding keys (monitoring agents, old backups) are `0600`/`0640` and owned by root or the service user.
- Audit as part of convergence: search for world-readable files containing `key|token|secret|password` outside system paths. Record the findings and fixes in `hosts/<name>.md`.

## H6. Secret store
- `/etc/builderxai/secrets/` owned by root, mode `0700`. One file per credential, each `0600`, in `KEY=value` env format.
- Files are injected into a bot's gateway by the init system *as root*, before it drops to the bot user. Bot users cannot read the files.
- Inventory of files is in `bots/*.md` and `procedures/new-credential.md`. Values are filled by the owner, or by an agent in a flow where the value never appears in chat or logs.

## H7. Gateway services
- One service per bot: `hermes-gw@<bot>` or similar, running as the bot's user. It loads only that bot's secret files.
- Ordered after, and hard-dependent on, the egress rules (H4). If the rules fail to load, the bots don't start.
- Hardening where the init system supports it: no-new-privileges, read-only system, writable only `~` and `/srv/builderxai`, private tmp.
- Hermes is installed per user, in that user's home. Don't change the system Python.

## H8. Model access: allowlist proxy
- Bots never hold a key to the operator's real model gateway. A local proxy (own system user, loopback only) holds the single upstream key and exposes only allowlisted models to per-bot local keys.
- Per-bot: own local key, own model list, rate limit, and `max_tokens` ceiling. Unknown models and routes (images, audio, responses, messages) return 404.
- The upstream key is dedicated to this proxy (one entry in the gateway's key list) so it can be revoked alone.
- H4 gets exactly one local exception: `127.0.0.1:<proxy port>` over `lo`. Sandboxes still can't reach it, because the slirp host alias is not loopback.
