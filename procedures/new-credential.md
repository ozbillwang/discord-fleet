# Procedure: new credential

Goal: a fresh credential exists, is scoped minimally, sits in the host secret
store (`spec/host.md` H6), and its value has **never** appeared in chat, logs,
shell history, or this repo.

## Rules
- Always create a new credential. Never reuse one from home (personal agents, home gateways, secret managers, personal tokens).
- Scope down: least privilege, a spend cap or quota where the provider supports one, and an expiry where sensible.
- Record the *inventory* (file name, key name, provider, scope, created date, owner account) in `hosts/<name>.md` → "Credentials". Never record the value.

## Transport of the value (pick one, in order of preference)
1. **the owner types it directly on the host:** `ssh <admin>@<host> sudoedit /etc/builderxai/secrets/<file>.env`.
2. **Agent-driven browser → host via stdin, no echo.** The agent reads the token from the page DOM inside the browser automation process and pipes it straight into `ssh <host> 'sudo tee -a <file> >/dev/null'`. The value must not be printed, returned to the model, or written to disk on the operator machine. The agent only reports "written, N bytes, sha256 prefix".
3. Never: paste into Discord or any chat, put it in a commit, or pass it as a command-line argument (visible in `ps` and history).

After writing: `sudo stat -c '%U %a %s' <file>` → `root 600 <non-zero>`, then restart the gateway that uses it.

## Accounts: who owns the provider account
- **Discord**: the owner's personal account (2FA on) owns the BuilderXAI server and the bot applications (decided 2026-10-24). To hand over later: transfer server ownership in Server Settings, and move the apps into a Developer Portal **Team**.
- Other providers (GitHub, mail, model API): a BuilderXAI identity is preferred where it's cheap. the owner creates any new account himself, because phone verification, captchas and 2FA need a human. Agents never register accounts on their own; it violates most ToS and fails verification anyway.
- 2FA on every provider. Recovery codes go into a password manager.

## Headed-browser flow (agent drives, the owner verifies)
Used when a provider has no API for creating credentials (Discord Developer
Portal, GitHub PAT UI, most mail providers).

Setup:
- Use a **headed** Chromium on a machine with a display that the owner can see, with a **dedicated browser profile** for the BuilderXAI identity (e.g. `~/.config/builderxai-browser`). Never use the owner's personal profile.
- The agent drives it via Playwright/CDP (or `computer_use`) in the background. the owner watches the window.

Steps:
1. Agent opens the provider login page in the dedicated profile.
2. **Human checkpoint: login.** the owner logs in, or the agent shows a QR code for the owner to scan with the phone app (Discord supports QR login from the mobile app). The agent then waits for the post-login URL. It never types passwords.
3. **Human checkpoint: captcha / 2FA / email confirmation**, if any. The agent pauses, says exactly what's on screen, and waits.
4. Agent performs the creation clicks (see the provider recipes below) and **screenshots each step** for the record.
5. Agent extracts the value per transport option 2, then verifies the file on the host.
6. Agent records the inventory in `hosts/<name>.md` and closes the tab. The browser profile keeps the session for next time.

## Provider recipes (targets, not click-paths, because UIs change)

### Discord bot application
- Create an application named after the bot (e.g. `BuilderXAI Guild`).
- Bot tab: enable **Server Members Intent** and **Message Content Intent**. Turn off "Public Bot" so only the owner can invite it.
- Reset Token → value → `<bot>.env` as `DISCORD_BOT_TOKEN=…`.
- Record the Application ID (not secret) in `hosts/<name>.md`.
- Invite URL: `https://discord.com/oauth2/authorize?client_id=<APP_ID>&scope=bot%20applications.commands&permissions=<INT>`. The permission set comes from `spec/bots/<bot>.md`. Compute the integer from the named flags and record both. the owner opens the URL and picks the server, which is the human checkpoint.

### GitHub fine-grained PAT
- Resource owner: the BuilderXAI org (or machine user). Repository access: only the listed repos.
- Permissions: Contents RW, Pull requests RW, Metadata R. Nothing else. Expiry ≤ 1 year.
- → `github.env` as `GITHUB_TOKEN=…`.

### Model API key (your gateway or provider)
- One key per bot (`llm-<bot>.env`), so that each bot has its own spend cap and revoking one doesn't affect the others.
- If the model gateway is self-hosted, issuing a key there is a home-side operation in your servers repo. The fleet reaches the model gateway only via its **public** URL, never the tailnet IP.

### Email sending
- Provider TBD (Resend / Brevo / other). Requirements: sending-domain restricted, an API key with send-only scope, and SPF/DKIM on the BuilderXAI domain.

## Rotation / revocation
- Rotate: create the new credential → write it → restart the gateway → verify → revoke the old one.
- Leak suspected: revoke at the provider **first**, then rotate. For Discord, Reset Token instantly invalidates the old one.
