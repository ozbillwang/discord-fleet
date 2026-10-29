# Bridge tests (run inside the built image)

```sh
docker build -t bx-bridge:dev bridge/
# 1. routing (no network): T1/T2/T5, DMs/bots ignored, flood guard, per-thread sessions, hot reload, bad config rejected
docker run --rm -v $PWD/tmpdata:/data -v $PWD/bridge/tests:/t:ro --entrypoint python3 bx-bridge:dev /t/routing_test.py
# 2. real omp sessions (needs CLIAPI_API_KEY + models.yml + two agent dirs alpha/beta under /data):
#    reply, multi-turn memory, isolation between agent dirs, persona, --no-tools refusal, resume after process restart
docker run --rm -e CLIAPI_API_KEY -v $PWD/tmpdata:/data -v $PWD/bridge/tests:/t:ro --entrypoint python3 bx-bridge:dev /t/omp_session_test.py
```
Last run on 2026-10-24 (omp 18.12.6, gemini-3.8-flash-high): routing 9/9 ✅. omp: memory ✅, isolation ✅ ("不知道"), persona ✅, no-tools refusal ✅, resume ✅. Session files contain 0 tool calls, and the key was not found anywhere under /data.
