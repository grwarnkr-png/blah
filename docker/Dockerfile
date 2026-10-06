# Claude's private desktop: Xvfb + fluxbox + Firefox, driven over MCP,
# viewable by you in a browser through noVNC.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    WIDTH=1280 \
    HEIGHT=800 \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb xdotool x11vnc novnc python3-websockify fluxbox \
        firefox-esr xterm pcmanfm mousepad xclip \
        fonts-dejavu fonts-noto-color-emoji dbus-x11 ca-certificates \
        python3 python3-venv tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/sidecar
COPY requirements.txt /tmp/requirements.txt
RUN /opt/sidecar/bin/pip install --no-cache-dir -r /tmp/requirements.txt

RUN useradd --create-home --shell /bin/bash claude
COPY sidecar /opt/sidecar/app/sidecar
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER claude
WORKDIR /home/claude
# 8765: MCP (streamable HTTP)   6080: noVNC viewer
EXPOSE 8765 6080
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
