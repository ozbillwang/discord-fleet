# BuilderXAI Discord Bridge image: python bridge + omp (bun) — runs as a Bot User container.
FROM oven/bun:1.3-debian

ARG OMP_VERSION=18.12.6
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*

# omp (global, pinned)
ENV BUN_INSTALL=/opt/bun
RUN bun install -g @oh-my-pi/pi-coding-agent@${OMP_VERSION} \
 && (cd /opt/bun/install/global && bun pm -g untrusted || true) \
 && (cd /opt/bun/install/global && bun pm -g trust --all || true) \
 && omp --version

# bridge
RUN python3 -m venv /opt/venv
COPY requirements.txt /opt/bridge/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /opt/bridge/requirements.txt
COPY bridge.py entrypoint.sh webtools.ts /opt/bridge/
COPY assets/builderx-logo.png /opt/bridge/assets/builderx-logo.png
RUN chmod 0644 /opt/bridge/bridge.py /opt/bridge/requirements.txt /opt/bridge/webtools.ts /opt/bridge/assets/builderx-logo.png && chmod 0755 /opt/bridge/assets && chmod 0755 /opt/bridge/entrypoint.sh /opt/bridge

# unprivileged runtime user (inside rootless docker this maps to a host subuid, not bx)
RUN useradd -m -u 10001 -s /usr/sbin/nologin agent
USER agent
ENV HOME=/home/agent PI_CODING_AGENT_DIR=/data/omp-agent BRIDGE_CONFIG=/data/bridge.yaml PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /home/agent
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/bridge/entrypoint.sh"]
