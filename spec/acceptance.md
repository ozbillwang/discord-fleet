# Acceptance checks

A host is done only when every check passes. Run them after every host change
and paste the results (date, pass/fail per ID) into `hosts/<name>.md`.

Commands are reference forms. Adapt them to the host and record the variant
you used. `$U` ∈ {bx, bxadmin}.

## A. Identity and privilege (each bot user)
| ID | check | expected |
|---|---|---|
| A1 | `id $U` | no sudo/wheel/docker/podman group |
| A2 | `sudo -u $U sudo -n true` | fails |
| A3 | `sudo -u $U test -w /var/run/docker.sock` (and any root runtime socket) | false |
| A4 | `stat -c %a ~$U` | 750 |
| A5 | `sudo -u bx ls ~bxadmin` and vice versa | permission denied |
| A6 | start a process as bxadmin with env `CANARY=1`, then as bx `cat /proc/<pid>/environ` | permission denied |
| A7 | `ls ~$U/.ssh/authorized_keys` | absent |

## B. Secrets
| ID | check | expected |
|---|---|---|
| B1 | `stat` the secret dir and its files | root, 0700 / 0600 |
| B2 | as each bot user, `cat` any secret file | permission denied |
| B3 | inside a public-bot sandbox: `env` | no `*TOKEN*`, `*KEY*`, `*SECRET*` |

## C. Egress (run as each bot user on the host, and again inside a bx sandbox container)
Must **succeed**:
| ID | target |
|---|---|
| C1 | DNS resolve `discord.com` |
| C2 | HTTPS `https://discord.com` |
| C3 | HTTPS to the model API the bots use (e.g. `https://llm.example.com/v1/models` → 401/200) |

Must **fail** (TCP connect, 3–4 s timeout):
| ID | target class | reference targets |
|---|---|---|
| C10 | home machines on the tailnet | each home machine's tailnet IP:22 (desktop, laptop, NAS) |
| C11 | infra on the tailnet | secret manager, internal model gateway, etc. on their tailnet IPs |
| C12 | MagicDNS | 100.100.100.100:53 (TCP) |
| C13 | the host's own tailnet IP services | e.g. tinyproxy `<host-ts-ip>:8888` |
| C14 | VPC / LAN | gateway (e.g. 10.0.0.1:22), the host's own private IP:22 |
| C15 | metadata | 169.254.169.254:80 |
| C16 | loopback | 127.0.0.1:22, any other local listener |
| C17 | 0.0.0.0 | 0.0.0.0:22 |
| C18 | the host's own public IP | `<pub-ip>`:22 |
| C19 | (sandbox only) runtime host alias | e.g. slirp4netns `10.0.2.2:22` |
| C20 | tailnet IPv6 | e.g. `[fd7a:115c:a1e0::…]:22` for a home machine |

List the host's actual listeners (`ss -ltnp`) and make sure each one is covered by some C1x target.

## D. Local file exposure
| ID | check | expected |
|---|---|---|
| D1 | as bx: read every file found by the H5 audit (e.g. monitoring compose file with API key) | permission denied |
| D2 | as bx: `find / -xdev -type f -perm -o+r \( -name '*.env' -o -name '*compose*.yml' -o -name '*.sql' -o -name '*.tar.gz' \) 2>/dev/null` outside system dirs | nothing sensitive |

## E. Runtime and resources (bx)
| ID | check | expected |
|---|---|---|
| E1 | `docker info` (as bx) | rootless; cgroup v2; no "no cpu limit support" warning |
| E2 | `docker run --rm alpine echo ok` | ok |
| E3 | delegated controllers for bx's user service | include cpu memory pids |
| E4 | bx slice memory limit | set (≤ 4G) |
| E5 | reboot the host (or restart the egress unit and the user manager) and re-run C | still all green, rules present before bot services |

## F. Host unaffected
| ID | check | expected |
|---|---|---|
| F1 | services the host already ran (record them before the change) | still active / healthy |
| F2 | system container runtime and its containers | unchanged |

## G. Gateways (after bots are configured)
| ID | check | expected |
|---|---|---|
| G1 | each gateway service | active, runs as its bot user |
| G2 | stop the egress unit | gateways stop (hard dependency) |
| G3 | guild: a non-the owner account messages it | no response |
| G4 | builderxai: a member runs `/yolo`, `/approve`, or replies `yes` to an approval | refused |
| G5 | builderxai: ask it to run a shell command | refused / no terminal tool, or runs only inside the sandbox |
