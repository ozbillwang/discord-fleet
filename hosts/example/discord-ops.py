#!/usr/bin/env python3
"""Run as root on the fleet host. Discord ops with bot tokens that never leave the host.
usage: discord-ops.py status | avatar <bot> <png> | mkadmin <owner_id>"""
import json, sys, base64, urllib.request, urllib.error
GUILD = os.environ["BX_GUILD_ID"]
SEC = "/etc/builderxai/secrets/"
def tok(bot):
    for l in open(SEC + bot + ".env"):
        if l.startswith("DISCORD_BOT_TOKEN="): return l.split("=", 1)[1].strip()
def api(bot, method, path, body=None):
    r = urllib.request.Request("https://discord.com/api/v10" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bot " + tok(bot), "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (builderxai-fleet, 1)"})
    try:
        d = urllib.request.urlopen(r, timeout=30).read()
        return json.loads(d) if d else {}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "body": e.read().decode()[:300]}
cmd = sys.argv[1]
if cmd == "status":
    for b in ("guild", "builderxai"):
        me = api(b, "GET", "/users/@me")
        gs = api(b, "GET", "/users/@me/guilds")
        print(b, me.get("id"), me.get("username"), "avatar:", bool(me.get("avatar")),
              "in BuilderX AI:", any(g.get("id") == GUILD for g in gs) if isinstance(gs, list) else gs)
    chs = api("guild", "GET", f"/guilds/{GUILD}/channels")
    if isinstance(chs, list):
        for c in sorted(chs, key=lambda c: (c.get("position", 0))):
            print("  ch", c["id"], c["type"], c["name"], c.get("parent_id"))
    else:
        print("  channels:", chs)
elif cmd == "avatar":
    bot, png = sys.argv[2], sys.argv[3]
    data = "data:image/png;base64," + base64.b64encode(open(png, "rb").read()).decode()
    r = api(bot, "PATCH", "/users/@me", {"avatar": data})
    print(bot, "avatar set:", bool(r.get("avatar")), r.get("http", ""), r.get("body", "")[:200])
elif cmd == "mkadmin":
    owner = sys.argv[2]
    me = api("guild", "GET", "/users/@me")
    VIEW_SEND = str((1 << 10) | (1 << 11) | (1 << 16))  # view, send, read history
    cat = api("guild", "POST", f"/guilds/{GUILD}/channels", {"name": "Admin", "type": 4, "permission_overwrites": [
        {"id": GUILD, "type": 0, "deny": str(1 << 10)},
        {"id": owner, "type": 1, "allow": VIEW_SEND},
        {"id": me["id"], "type": 1, "allow": VIEW_SEND}]})
    ch = api("guild", "POST", f"/guilds/{GUILD}/channels", {"name": "admin", "type": 0, "parent_id": cat.get("id"),
        "topic": "Private: the owner ↔ Guild manager only", "permission_overwrites": [
        {"id": GUILD, "type": 0, "deny": str(1 << 10)},
        {"id": owner, "type": 1, "allow": VIEW_SEND},
        {"id": me["id"], "type": 1, "allow": VIEW_SEND}]})
    print("category", cat.get("id", cat), "admin", ch.get("id", ch))
