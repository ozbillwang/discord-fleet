#!/usr/bin/env python3
"""Run as root on the fleet host. Inspect / apply BuilderX AI member permission policy using the Guild bot token.
usage: discord-policy.py show | apply"""
import json, sys, urllib.request, urllib.error
GUILD = os.environ["BX_GUILD_ID"]
OWNER = os.environ["BX_OWNER_ID"]
GUILD_BOT = os.environ["BX_GUILD_BOT_ID"]
PUB_BOT = os.environ["BX_PUBLIC_BOT_ID"]
def tok():
    for l in open("/etc/builderxai/secrets/guild.env"):
        if l.startswith("DISCORD_BOT_TOKEN="): return l.split("=", 1)[1].strip()
def api(method, path, body=None):
    r = urllib.request.Request("https://discord.com/api/v10" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bot " + tok(), "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (builderxai-fleet, 1)", "X-Audit-Log-Reason": "builderxai-fleet member policy"})
    try:
        d = urllib.request.urlopen(r, timeout=30).read(); return json.loads(d) if d else {}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "body": e.read().decode()[:300]}
P = {n: 1 << b for n, b in dict(CREATE_INSTANT_INVITE=0, KICK_MEMBERS=1, BAN_MEMBERS=2, ADMINISTRATOR=3, MANAGE_CHANNELS=4,
    MANAGE_GUILD=5, ADD_REACTIONS=6, VIEW_AUDIT_LOG=7, PRIORITY_SPEAKER=8, STREAM=9, VIEW_CHANNEL=10, SEND_MESSAGES=11,
    SEND_TTS_MESSAGES=12, MANAGE_MESSAGES=13, EMBED_LINKS=14, ATTACH_FILES=15, READ_MESSAGE_HISTORY=16, MENTION_EVERYONE=17,
    USE_EXTERNAL_EMOJIS=18, VIEW_GUILD_INSIGHTS=19, CONNECT=20, SPEAK=21, MUTE_MEMBERS=22, DEAFEN_MEMBERS=23, MOVE_MEMBERS=24,
    USE_VAD=25, CHANGE_NICKNAME=26, MANAGE_NICKNAMES=27, MANAGE_ROLES=28, MANAGE_WEBHOOKS=29, MANAGE_GUILD_EXPRESSIONS=30,
    USE_APPLICATION_COMMANDS=31, REQUEST_TO_SPEAK=32, MANAGE_EVENTS=33, MANAGE_THREADS=34, CREATE_PUBLIC_THREADS=35,
    CREATE_PRIVATE_THREADS=36, USE_EXTERNAL_STICKERS=37, SEND_MESSAGES_IN_THREADS=38, USE_EMBEDDED_ACTIVITIES=39,
    MODERATE_MEMBERS=40, VIEW_CREATOR_MONETIZATION_ANALYTICS=41, USE_SOUNDBOARD=42, CREATE_GUILD_EXPRESSIONS=43,
    CREATE_EVENTS=44, USE_EXTERNAL_SOUNDS=45, SEND_VOICE_MESSAGES=46, SEND_POLLS=49, USE_EXTERNAL_APPS=50).items()}
def names(v):
    v = int(v); return [n for n, b in P.items() if v & b]
# Members (@everyone) may only: see, read history, talk, react, embed/attach, external emoji, public threads, voice basics.
MEMBER = ["VIEW_CHANNEL", "READ_MESSAGE_HISTORY", "SEND_MESSAGES", "SEND_MESSAGES_IN_THREADS", "CREATE_PUBLIC_THREADS",
          "ADD_REACTIONS", "EMBED_LINKS", "ATTACH_FILES", "USE_EXTERNAL_EMOJIS", "CHANGE_NICKNAME",
          "CONNECT", "SPEAK", "USE_VAD", "STREAM", "SEND_VOICE_MESSAGES"]
READ_ONLY_CHANNELS = ["welcome-and-rules", "announcements"]
cmd = sys.argv[1]
roles = api("GET", f"/guilds/{GUILD}/roles")
chs = api("GET", f"/guilds/{GUILD}/channels")
if cmd == "show":
    for r in sorted(roles, key=lambda r: -r["position"]):
        print("role", r["id"], repr(r["name"]), "pos", r["position"], "managed", r.get("managed"), "\n   ", names(r["permissions"]))
    for c in sorted(chs, key=lambda c: c["position"]):
        ows = [(o["id"], o["type"], names(o["allow"]), names(o["deny"])) for o in c.get("permission_overwrites", [])]
        print("ch", c["name"], c["type"], ows)
elif cmd == "apply":
    everyone = next(r for r in roles if r["id"] == GUILD)
    want = sum(P[n] for n in MEMBER)
    before = names(everyone["permissions"])
    r = api("PATCH", f"/guilds/{GUILD}/roles/{GUILD}", {"permissions": str(want)})
    print("@everyone:", "ok" if "id" in r else r, "\n  removed:", sorted(set(before) - set(MEMBER)), "\n  added:", sorted(set(MEMBER) - set(before)))
    for c in chs:
        if c["name"] in READ_ONLY_CHANNELS and c["type"] == 0:
            # a bot may only set overwrite bits it holds itself; CREATE_PRIVATE_THREADS is already off for @everyone guild-wide
            deny = P["SEND_MESSAGES"] | P["CREATE_PUBLIC_THREADS"] | P["SEND_MESSAGES_IN_THREADS"] | P["ADD_REACTIONS"]
            r1 = api("PUT", f"/channels/{c['id']}/permissions/{GUILD}", {"type": 0, "allow": "0", "deny": str(deny)})
            r2 = api("PUT", f"/channels/{c['id']}/permissions/{OWNER}", {"type": 1, "allow": str(P["SEND_MESSAGES"] | P["VIEW_CHANNEL"]), "deny": "0"})
            r3 = api("PUT", f"/channels/{c['id']}/permissions/{GUILD_BOT}", {"type": 1, "allow": str(P["SEND_MESSAGES"] | P["VIEW_CHANNEL"]), "deny": "0"})
            print("read-only #" + c["name"], [x.get("http", "ok") if isinstance(x, dict) else "ok" for x in (r1, r2, r3)])
