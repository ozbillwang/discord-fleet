# Procedure: new bot (a.k.a. new service)

Goal: a new Hermes bot runs on a fleet host, meets `spec/host.md`, has its own
`spec/bots/<bot>.md`, and passes `spec/acceptance.md`.

1. **Decide the trust level.** Will it obey only the owner, or answer the public?
   - Same level as an existing user → reuse that user (`bxadmin` or `bx`).
   - A new level, or a need for isolation from same-level bots (e.g. it holds different high-value credentials) → `procedures/new-user.md` first.
2. **Write `spec/bots/<bot>.md`** (copy the closest existing one). Fill in: role, Linux user, tool execution placement, who can command it, credentials table, Hermes config policy, Discord permissions.
3. **Write the profile template** `profiles/<bot>/config.yaml` and `SOUL.md`. No secrets, no private the owner context.
4. **Credentials:** run `procedures/new-credential.md` for each row in the bot's credentials table.
5. **On the host** (after confirmation from the owner):
   - Create the Hermes profile under the bot's user and install the template.
   - Create its gateway service per H7. It loads only its own secret files and depends on the egress unit.
   - If it is low-trust and uses a terminal: point it at that user's rootless runtime and set the volume mounts per H3.
6. **Discord side:** guild (or the owner) creates its channel and role and sets channel permissions. the owner opens the invite URL.
7. **Acceptance:** re-run sections B, C, and G of `spec/acceptance.md`, plus A and D if a user was added. Record the results in `hosts/<name>.md`.
8. **Report:** if a user, service unit, or runtime changed, update the host's footprint in the servers repo.

## Removing a bot
Stop and disable its service → delete its profile → revoke its credentials at
the provider (see `new-credential.md`, Rotation / revocation) → delete its
secret files → kick it from the Discord server → update `hosts/<name>.md` and
the servers-repo footprint.
