# Eternego — slim image with X11 substrate so the persona has her own desktop.
# Browser, editor, anything else — she installs herself, the way a person does.
#
# Build args:
#   INSTALL_TRAINING=true   include torch / transformers / peft / etc.
#   START_DESKTOP=false     (env var at run time) skip the X stack — channels-only deploys.
FROM python:3.13-slim

ARG INSTALL_TRAINING=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        xvfb \
        x11vnc \
        fluxbox \
        novnc \
        websockify \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# pynput pulls evdev on Linux, which compiles against linux/input.h.
# Install the build deps just for the pip step, then drop them so the
# image stays slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev linux-libc-dev \
    && pip install --no-cache-dir . \
    && if [ "$INSTALL_TRAINING" = "true" ]; then \
         pip install --no-cache-dir ".[training]"; \
       fi \
    && apt-get purge -y gcc libc6-dev linux-libc-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Defaults that make `docker run --network=host eternego:latest` just work:
# Ollama on the host is reachable as localhost when host networking is shared.
# Mac/Windows users without --network=host can override OLLAMA_BASE_URL at run time.
# WEB_HOST=0.0.0.0 so the dashboard is reachable through the published port —
# the daemon defaults to 127.0.0.1, which is right for native installs but
# leaves the container unreachable from the host.
ENV ETERNEGO_HOME=/data \
    OLLAMA_BASE_URL=http://localhost:11434 \
    WEB_HOST=0.0.0.0 \
    DISPLAY=:99 \
    XVFB_RESOLUTION=1280x720x24 \
    START_DESKTOP=true

VOLUME ["/data"]
EXPOSE 5000 6080

COPY installation/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# tini reaps zombies from the X-stack background processes.
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
