# Procedure: bring up / migrate to another host

Goal: a different machine becomes a compliant fleet host and the bots move
there with minimal downtime and no credential reuse across trust boundaries.

1. **Assess the candidate.** Check H0 prerequisites (cgroup v2, unprivileged
   userns, resources, public egress). Record: distro, init system, firewall
   frontend (iptables-nft / nftables / firewalld), container runtimes present,
   listeners (`ss -ltnp`), public and private IPs, tailnet membership,
   world-readable secrets (H5 audit). Pick an implementation for each
   H-requirement that suits this host. Write it as a plan in a new
   `hosts/<new>.md`.
2. **Confirm with the owner.** Show the plan, the firewall changes, and anything
   that touches existing services on that host.
3. **Converge** H1–H7. Use `hosts/<name>.md` as a worked example, not as a
   script.
4. **Acceptance A–F** on the new host. Fix until all green.
5. **Move bots one at a time:**
   - Copy profile data that matters (memories, skills, cron) from the old host
     to the new one under the same Linux user names. Never copy secrets between
     hosts over chat; re-create or re-enter them per `new-credential.md`.
     Copying the secret file root-to-root over SSH between two fleet hosts is
     acceptable.
   - Stop the gateway on the old host **before** starting it on the new one.
     A Discord token must not run in two places at once.
   - Run acceptance G.
6. **Decommission the old host's fleet layer** (`new-user.md` removal for each
   user, remove the egress rules, delete `/etc/builderxai` and `/srv/builderxai`),
   then update both hosts' records here and in the servers repo.

## Portability notes
- Nothing in `spec/` assumes Ubuntu, iptables, Docker, or systemd. Those are
  the reference host's choices.
- Things that change per host and must be re-measured, never copied: public IP
  (H4 hairpin rule), private subnet, the host's tailnet IP, the listener list,
  CPU arch (container images and runtime binaries), and the resolver chain.
