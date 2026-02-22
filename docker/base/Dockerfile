# syntax=docker/dockerfile:1
# jupyterlab-base: all slow layers — rebuilds monthly or on Python/scipy bumps.
# Claude/Gemini tooling lives in jupyterlab-claude (FROM this image).
FROM python:3.14.3-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/kub0-ai/jupyterlab-claude"
LABEL org.opencontainers.image.description="JupyterLab base: Python 3.14 + uv + system tools + scientific stack"
LABEL org.opencontainers.image.licenses="MIT"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

USER root

# System packages: dev tools, math libs, container runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        tmux vim jq make git curl ca-certificates gnupg \
        build-essential libopenblas-dev liblapack-dev gfortran \
        podman fuse-overlayfs slirp4netns uidmap \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# kubectl
RUN curl -fsSL "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/$(dpkg --print-architecture)/kubectl" \
        -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

# helm
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Node.js 22 (required by Claude Code and Gemini CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# jovyan user (uid/gid 1000, subuid/subgid ranges for rootless Podman)
RUN useradd -m -s /bin/bash -u 1000 jovyan && \
    usermod --add-subuids 100000-165535 jovyan && \
    usermod --add-subgids 100000-165535 jovyan

# Python scientific stack — pre-built wheels, no compilation
RUN uv pip install --system --no-cache \
    jupyterlab \
    scipy \
    pandas \
    matplotlib \
    numpy \
    ollama \
    ipykernel

# JupyterLab static customizations
# sys.prefix=/usr/local → static files at /usr/local/share/jupyter/lab/static/
COPY custom.css /usr/local/share/jupyter/lab/static/custom.css
COPY longpress.js /usr/local/share/jupyter/lab/static/longpress.js
RUN sed -i 's|</head>|<link rel="stylesheet" href="{{page_config.fullStaticUrl}}/custom.css">\n<script src="{{page_config.fullStaticUrl}}/longpress.js"></script>\n</head>|' \
    /usr/local/share/jupyter/lab/static/index.html

RUN mkdir -p /home/jovyan/.jupyter/custom
COPY custom.css /home/jovyan/.jupyter/custom/custom.css

RUN mkdir -p /usr/local/share/jupyter/lab/settings
COPY overrides.json /usr/local/share/jupyter/lab/settings/overrides.json

# Podman rootless storage init
RUN mkdir -p /home/jovyan/.config/containers
COPY podman-storage-init.sh /usr/local/bin/podman-storage-init.sh
RUN chmod +x /usr/local/bin/podman-storage-init.sh

# Proxy helpers (mullvad, tor, off, status)
COPY proxy-helpers.sh /usr/local/bin/proxy-helpers.sh
RUN chmod +x /usr/local/bin/proxy-helpers.sh

# Shell baseline (claude alias and gemini-flash added in jupyterlab-claude layer)
RUN echo 'alias docker=podman' >> /home/jovyan/.bashrc && \
    echo 'alias docker-compose="podman compose"' >> /home/jovyan/.bashrc && \
    echo 'podman-storage-init.sh 2>/dev/null' >> /home/jovyan/.bashrc && \
    echo 'source /usr/local/bin/proxy-helpers.sh' >> /home/jovyan/.bashrc

RUN chown -R jovyan:jovyan \
    /home/jovyan/.jupyter \
    /home/jovyan/.config

ENV PATH="/home/jovyan/.local/bin:$PATH"
ENV SHELL=/bin/bash

USER jovyan
WORKDIR /home/jovyan
EXPOSE 8888
