# Eternego — slim image by default. Set INSTALL_TRAINING=true at build time
# for the full variant (torch / transformers / peft / bitsandbytes etc.).
FROM python:3.13-slim

ARG INSTALL_TRAINING=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir . \
    && if [ "$INSTALL_TRAINING" = "true" ]; then \
         pip install --no-cache-dir ".[training]"; \
       fi

ENV ETERNEGO_HOME=/data
VOLUME ["/data"]
EXPOSE 5000

CMD ["python", "index.py", "daemon"]
