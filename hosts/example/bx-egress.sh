#!/bin/bash
# bx-egress: users bx / bxadmin may reach the public internet only (BuilderXAI fleet).
# Target state: discord-fleet spec/host.md H4. Idempotent; replayed at boot by bx-egress.service.
set -euo pipefail
USERS="bx bxadmin"
PUB_IP="${PUB_IP:?set to this host public IP (curl -s https://ifconfig.me)}"
LLM_GW_PORT=18080       # bx-llm-gw on 127.0.0.1 (H8): the only allowed local service besides DNS

for T in iptables ip6tables; do
  $T -N BX-EGRESS 2>/dev/null || $T -F BX-EGRESS
  for U in $USERS; do
    id "$U" >/dev/null 2>&1 || continue
    $T -C OUTPUT -m owner --uid-owner "$U" -j BX-EGRESS 2>/dev/null || \
      $T -I OUTPUT 1 -m owner --uid-owner "$U" -j BX-EGRESS
  done
done

# IPv4: allowed local destinations
iptables -A BX-EGRESS -d 127.0.0.53/32 -p udp --dport 53 -j RETURN
iptables -A BX-EGRESS -d 127.0.0.53/32 -p tcp --dport 53 -j RETURN
iptables -A BX-EGRESS -d 127.0.0.1/32 -o lo -p tcp --dport "$LLM_GW_PORT" -j RETURN
for NET in 127.0.0.0/8 0.0.0.0/8 100.64.0.0/10 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 \
           169.254.0.0/16 224.0.0.0/4 "$PUB_IP/32"; do
  iptables -A BX-EGRESS -d "$NET" -j REJECT
done

# IPv6
for NET in ::1/128 ::/128 fd7a:115c:a1e0::/48 fc00::/7 fe80::/10 ff00::/8; do
  ip6tables -A BX-EGRESS -d "$NET" -j REJECT
done

echo "bx-egress applied"
