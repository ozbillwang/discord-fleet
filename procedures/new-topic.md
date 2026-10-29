# Procedure: new topic channel (operators: Guild Manager + the deployer)

Terms are defined in `spec/topics.md`. Goal: the new topic satisfies T1–T8.

1. the owner names the topic and a one-line positioning.
2. **Guild Manager** creates the channel (Topics category, member default permissions) and posts a 【绑定请求】 in #admin: Bot User, channel id, agent dir name, persona.
3. **Deployer**, inside the Bot User's container data:
   - create the agent directory `<agents>/<name>/` with `.omp/SYSTEM.md` (persona + the public safety block) and `.omp/config.yml`. Copy from the base agent dir; never widen tools (T3);
   - add `channel id → <name>` to the Discord Bridge's channel map;
   - restart the Bot User container (or send the bridge's reload signal if it has one).
4. Verify per `spec/topics.md` Acceptance; record it in `hosts/<name>.md` (T7).

Removing: drop the map entry → restart → archive the agent dir → Guild archives the channel → record it.
