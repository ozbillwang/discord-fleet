#!/usr/bin/env python3
"""Discord REST helper for Guild Manager (BuilderX AI). Token from env BX_GUILD_REST_TOKEN; never printed."""
import argparse, json, os, sys, urllib.request, urllib.error

GUILD = os.environ["BX_GUILD_ID"]
PROTECTED = set(filter(None, os.environ.get("BX_PROTECTED_IDS", "").split(",")))  # Admin category, #admin
OWNER = os.environ["BX_OWNER_ID"]  # server owner
API = "https://discord.com/api/v10"
B = {n: 1 << i for n, i in dict(VIEW=10, SEND=11, HISTORY=16, REACT=6, EMBED=14, ATTACH=15,
                                  PUB_THREADS=35, SEND_THREADS=38, PRIV_THREADS=36).items()}
TALK = sum(B[k] for k in ("VIEW", "SEND", "HISTORY", "REACT", "EMBED", "ATTACH", "PUB_THREADS", "SEND_THREADS"))
READ = B["VIEW"] | B["HISTORY"]
SEND_ALL = B["SEND"] | B["SEND_THREADS"] | B["PUB_THREADS"] | B["REACT"]


def audit_reason(reason: str) -> str:
    """X-Audit-Log-Reason is an HTTP header (latin-1 only); Discord expects URL-encoded UTF-8."""
    from urllib.parse import quote
    return quote(reason[:400], safe=" -_.,:;()#/@")


def api(method, path, body=None, reason="guild-manager"):
    tok = os.environ.get("BX_GUILD_REST_TOKEN")
    if not tok:
        sys.exit("BX_GUILD_REST_TOKEN not in environment (host config issue: tell the operator agent)")
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bot " + tok, "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (builderxai-guild, 1)", "X-Audit-Log-Reason": audit_reason(reason)})
    try:
        raw = urllib.request.urlopen(req, timeout=30).read()
        return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:300]}")


def guard(cid):
    if str(cid) in PROTECTED:
        sys.exit(f"refused: {cid} is a protected admin channel")


_SELF = None


def self_id():
    global _SELF
    if _SELF is None:
        _SELF = api("GET", "/users/@me")["id"]
    return _SELF


def ow_everyone_private():
    # hide from @everyone, but keep Guild itself (and the owner) in, or the bot locks itself out
    return [{"id": GUILD, "type": 0, "allow": "0", "deny": str(B["VIEW"])},
            {"id": self_id(), "type": 1, "allow": str(TALK), "deny": "0"},  # only bits Guild itself holds (Discord rejects granting Manage Permissions)
            {"id": OWNER, "type": 1, "allow": str(TALK), "deny": "0"}]


def main():
    p = argparse.ArgumentParser(prog="dc.py")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("list")
    c = s.add_parser("create-category"); c.add_argument("name"); c.add_argument("--private", action="store_true")
    c = s.add_parser("create-channel"); c.add_argument("name"); c.add_argument("--parent"); c.add_argument("--topic")
    c.add_argument("--private", action="store_true"); c.add_argument("--readonly", action="store_true")
    c = s.add_parser("edit-channel"); c.add_argument("id"); c.add_argument("--name"); c.add_argument("--topic"); c.add_argument("--parent")
    c = s.add_parser("delete-channel"); c.add_argument("id"); c.add_argument("--confirm", action="store_true")
    c = s.add_parser("allow"); c.add_argument("channel"); c.add_argument("target")
    g = c.add_mutually_exclusive_group(); g.add_argument("--member", action="store_true"); g.add_argument("--role", action="store_true")
    g2 = c.add_mutually_exclusive_group(); g2.add_argument("--talk", action="store_true"); g2.add_argument("--read", action="store_true")
    c = s.add_parser("deny-everyone"); c.add_argument("channel")
    g = c.add_mutually_exclusive_group(required=True); g.add_argument("--view", action="store_true"); g.add_argument("--send", action="store_true")
    c = s.add_parser("clear"); c.add_argument("channel"); c.add_argument("target")
    c = s.add_parser("invite"); c.add_argument("channel"); c.add_argument("--max-age", type=int, default=86400); c.add_argument("--max-uses", type=int, default=10)
    c = s.add_parser("create-thread"); c.add_argument("channel"); c.add_argument("name"); c.add_argument("--archive-minutes", type=int, default=10080)
    c = s.add_parser("timeout"); c.add_argument("user"); c.add_argument("minutes", type=int); c.add_argument("--reason", default="moderation")
    c = s.add_parser("untimeout"); c.add_argument("user")
    c = s.add_parser("ban"); c.add_argument("user"); c.add_argument("--reason", required=True); c.add_argument("--confirm", action="store_true")
    c = s.add_parser("unban"); c.add_argument("user")
    a = p.parse_args()

    if a.cmd == "list":
        chs = api("GET", f"/guilds/{GUILD}/channels")
        roles = {r["id"]: r["name"] for r in api("GET", f"/guilds/{GUILD}/roles")}
        for ch in sorted(chs, key=lambda x: (x.get("parent_id") or x["id"], x["type"] != 4, x["position"])):
            ows = [f'{roles.get(o["id"], o["id"])}(+{o["allow"]}/-{o["deny"]})' for o in ch.get("permission_overwrites", [])]
            print(f'{ch["id"]}  type={ch["type"]}  parent={ch.get("parent_id") or "-"}  #{ch["name"]}  {" ".join(ows)}')
        return
    if a.cmd == "create-category":
        r = api("POST", f"/guilds/{GUILD}/channels", {"name": a.name, "type": 4,
                "permission_overwrites": ow_everyone_private() if a.private else []}, f"create category {a.name}")
        print("created category", r["id"], r["name"]); return
    if a.cmd == "create-channel":
        if a.parent: guard(a.parent)
        ows = ow_everyone_private() if a.private else []
        if a.readonly:
            ows = [o for o in ows if o["id"] != GUILD] + [
                {"id": GUILD, "type": 0, "allow": "0", "deny": str(SEND_ALL | (B["VIEW"] if a.private else 0))},
                {"id": self_id(), "type": 1, "allow": str(TALK), "deny": "0"}]
        body = {"name": a.name, "type": 0, "permission_overwrites": ows}
        if a.parent: body["parent_id"] = a.parent
        if a.topic: body["topic"] = a.topic
        r = api("POST", f"/guilds/{GUILD}/channels", body, f"create channel {a.name}")
        print("created channel", r["id"], "#" + r["name"], "parent", r.get("parent_id")); return
    if a.cmd == "edit-channel":
        guard(a.id)
        body = {k: v for k, v in (("name", a.name), ("topic", a.topic), ("parent_id", a.parent)) if v}
        r = api("PATCH", f"/channels/{a.id}", body, "edit channel"); print("edited", r["id"], "#" + r["name"]); return
    if a.cmd == "delete-channel":
        guard(a.id)
        if not a.confirm: sys.exit("refused: add --confirm (only after the owner confirmed)")
        r = api("DELETE", f"/channels/{a.id}", None, "delete channel (owner confirmed)"); print("deleted", r.get("id"), r.get("name")); return
    if a.cmd == "allow":
        guard(a.channel)
        kind = 0 if a.role else 1
        bits = READ if a.read else TALK
        api("PUT", f"/channels/{a.channel}/permissions/{a.target}", {"type": kind, "allow": str(bits), "deny": "0"}, "grant access")
        print(f"allowed {'role' if kind == 0 else 'member'} {a.target} in {a.channel}: {'read' if a.read else 'talk'}"); return
    if a.cmd == "deny-everyone":
        guard(a.channel)
        bits = B["VIEW"] if a.view else SEND_ALL
        api("PUT", f"/channels/{a.channel}/permissions/{GUILD}", {"type": 0, "allow": "0", "deny": str(bits)}, "restrict @everyone")
        print(f"@everyone {'cannot view' if a.view else 'read-only'} in {a.channel}"); return
    if a.cmd == "clear":
        guard(a.channel)
        api("DELETE", f"/channels/{a.channel}/permissions/{a.target}", None, "clear overwrite"); print("cleared", a.target, "in", a.channel); return
    if a.cmd == "invite":
        guard(a.channel)
        r = api("POST", f"/channels/{a.channel}/invites", {"max_age": a.max_age, "max_uses": a.max_uses, "unique": True}, "create invite")
        print(f'https://discord.gg/{r["code"]}  (expires in {a.max_age}s, {a.max_uses} uses)'); return


    if a.cmd == "create-thread":
        guard(a.channel)
        if a.archive_minutes not in (60, 1440, 4320, 10080):
            sys.exit("archive-minutes must be 60, 1440, 4320 or 10080")
        r = api("POST", f"/channels/{a.channel}/threads",
                {"name": a.name[:100], "type": 11, "auto_archive_duration": a.archive_minutes}, f"create thread {a.name}")
        print("created thread", r["id"], r["name"]); return
    if a.cmd in ("timeout", "untimeout", "ban", "unban"):
        if a.user in (OWNER, self_id()):
            sys.exit("refused: cannot moderate the owner or Guild itself")
    if a.cmd == "timeout":
        if not 1 <= a.minutes <= 40320:
            sys.exit("minutes must be 1..40320 (28 days)")
        import datetime
        until = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=a.minutes)).isoformat()
        api("PATCH", f"/guilds/{GUILD}/members/{a.user}", {"communication_disabled_until": until}, a.reason)
        print(f"timed out {a.user} for {a.minutes} min (until {until[:16]}Z)"); return
    if a.cmd == "untimeout":
        api("PATCH", f"/guilds/{GUILD}/members/{a.user}", {"communication_disabled_until": None}, "lift timeout")
        print(f"timeout lifted for {a.user}"); return
    if a.cmd == "ban":
        if not a.confirm: sys.exit("refused: add --confirm (only after the owner confirmed)")
        api("PUT", f"/guilds/{GUILD}/bans/{a.user}", {"delete_message_seconds": 0}, a.reason + " (owner confirmed)")
        print(f"banned {a.user}"); return
    if a.cmd == "unban":
        api("DELETE", f"/guilds/{GUILD}/bans/{a.user}", None, "unban"); print(f"unbanned {a.user}"); return


if __name__ == "__main__":
    main()
