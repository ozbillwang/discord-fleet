# Procedure: new bot user (new trust level)

Goal: a new Linux user satisfies every per-user requirement in `spec/host.md`
(H1, plus H2 if it runs a sandbox) and is covered by H4 egress.

Target state for the user `<u>`:
- [ ] exists, login shell allowed (for `sudo -iu`), home `0750`, no `authorized_keys`
- [ ] no sudo, not in any container-runtime or admin group
- [ ] linger enabled
- [ ] **added to the egress filter's user list** (H4) and rules re-applied. Do this *before* any of its services start
- [ ] if low-trust with a terminal: its own rootless runtime (H2), cgroup delegation scoped to its uid, slice memory/pids ceiling
- [ ] working directories under `/srv/builderxai` per H3, if needed

Verify with acceptance A1–A7 (cross-checked against **every** other bot user),
C (as `<u>`), and E for runtime users. Record the uid, decisions, and results in
`hosts/<name>.md`, and the footprint in the servers repo.

Removal: stop its services → remove it from the egress user list and re-apply
→ remove the delegation drop-in → disable linger → delete the user and home →
update the records.
