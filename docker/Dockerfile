# syntax=docker/dockerfile:1
# Conda-free JupyterLab: python:3.14.3-slim-bookworm + uv + Claude + Gemini
FROM python:3.14.3-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/kub0-ai/jupyterlab-claude"
LABEL org.opencontainers.image.description="Conda-free JupyterLab with Claude & Gemini agents"
LABEL org.opencontainers.image.licenses="MIT"

ARG GIT_SHA=unknown
ARG IMAGE_TAG=unknown
ARG VERSION=unknown
LABEL org.opencontainers.image.revision=$GIT_SHA
LABEL org.opencontainers.image.version=$VERSION
ENV IMAGE_SHA=$GIT_SHA
ENV IMAGE_TAG=$IMAGE_TAG
ENV IMAGE_VERSION=$VERSION

# uv — fast, telemetry-free Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

USER root

# System packages: dev tools, math libs (needed by scipy/numpy wheel builds), container runtime
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

# Claude Code + Gemini CLI
RUN npm install -g @anthropic-ai/claude-code @google/gemini-cli

# jovyan user (standard Jupyter container user, UID/GID 1000)
RUN useradd -m -s /bin/bash -u 1000 jovyan && \
    usermod --add-subuids 100000-165535 jovyan && \
    usermod --add-subgids 100000-165535 jovyan

# Python stack via uv — replaces the massive scipy-notebook conda layer
# Runs as root so --system can write to /usr/local/lib/python3.14/site-packages
RUN uv pip install --system --no-cache \
    jupyterlab \
    scipy \
    pandas \
    matplotlib \
    numpy \
    ollama \
    ipykernel

# IPython magic for %claude / %%claude / ask()
RUN mkdir -p /opt/ai
COPY claude_magic.py /opt/ai/claude_magic.py
RUN mkdir -p /home/jovyan/.ipython/profile_default/startup
COPY 00-claude.py /home/jovyan/.ipython/profile_default/startup/00-claude.py

# Mobile-friendly custom CSS + longpress.js
# With system Python (sys.prefix=/usr/local), Lab static files are at:
# /usr/local/share/jupyter/lab/static/ — same pattern as /opt/conda/share/...
COPY custom.css /usr/local/share/jupyter/lab/static/custom.css
COPY longpress.js /usr/local/share/jupyter/lab/static/longpress.js
RUN sed -i 's|</head>|<link rel="stylesheet" href="{{page_config.fullStaticUrl}}/custom.css">\n<script src="{{page_config.fullStaticUrl}}/longpress.js"></script>\n</head>|' \
    /usr/local/share/jupyter/lab/static/index.html

# Classic notebook path (for /tree view)
RUN mkdir -p /home/jovyan/.jupyter/custom
COPY custom.css /home/jovyan/.jupyter/custom/custom.css

# JupyterLab overrides (theme, terminal settings)
RUN mkdir -p /usr/local/share/jupyter/lab/settings
COPY overrides.json /usr/local/share/jupyter/lab/settings/overrides.json

# Podman rootless: auto-detect fuse-overlayfs, fall back to vfs
RUN mkdir -p /home/jovyan/.config/containers
COPY podman-storage-init.sh /usr/local/bin/podman-storage-init.sh
RUN chmod +x /usr/local/bin/podman-storage-init.sh

# Proxy helpers — proxy-mullvad, proxy-tor, proxy-off, proxy-status
COPY proxy-helpers.sh /usr/local/bin/proxy-helpers.sh
RUN chmod +x /usr/local/bin/proxy-helpers.sh

# Shell aliases + startup hooks
RUN echo 'alias docker=podman' >> /home/jovyan/.bashrc && \
    echo 'alias docker-compose="podman compose"' >> /home/jovyan/.bashrc && \
    echo 'alias gemini-flash="gemini -m gemini-2.5-flash"' >> /home/jovyan/.bashrc && \
    echo '# Auto-configure Podman storage on first shell' >> /home/jovyan/.bashrc && \
    echo 'podman-storage-init.sh 2>/dev/null' >> /home/jovyan/.bashrc && \
    echo '# Proxy helpers: proxy-mullvad, proxy-tor, proxy-off, proxy-status' >> /home/jovyan/.bashrc && \
    echo 'source /usr/local/bin/proxy-helpers.sh' >> /home/jovyan/.bashrc

# Ownership — jovyan:jovyan, no 'users' group in slim images
RUN chown -R jovyan:jovyan \
    /home/jovyan/.ipython \
    /home/jovyan/.jupyter \
    /home/jovyan/.config \
    /opt/ai

ENV PATH="/home/jovyan/.local/bin:$PATH"

USER jovyan
WORKDIR /home/jovyan
EXPOSE 8888
