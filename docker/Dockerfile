# syntax=docker/dockerfile:1
FROM quay.io/jupyter/scipy-notebook:latest

LABEL org.opencontainers.image.source="https://github.com/kub0-ai/jupyterlab-claude"
LABEL org.opencontainers.image.description="JupyterLab with Claude Code CLI and IPython magic"
LABEL org.opencontainers.image.licenses="MIT"

ARG GIT_SHA=unknown
ARG IMAGE_TAG=unknown
ARG VERSION=unknown
LABEL org.opencontainers.image.revision=$GIT_SHA
LABEL org.opencontainers.image.version=$VERSION
ENV IMAGE_SHA=$GIT_SHA
ENV IMAGE_TAG=$IMAGE_TAG
ENV IMAGE_VERSION=$VERSION

USER root

# System packages: dev tools + container runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        tmux \
        vim \
        jq \
        make \
        podman \
        fuse-overlayfs \
        slirp4netns \
        uidmap \
        git \
        curl \
        ca-certificates \
        gnupg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Podman rootless: subuid/subgid ranges for jovyan (UID 1000)
RUN usermod --add-subuids 100000-165535 jovyan && \
    usermod --add-subgids 100000-165535 jovyan

# kubectl
RUN curl -fsSL "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/$(dpkg --print-architecture)/kubectl" \
        -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

# helm
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Node.js 22 (required by Claude Code CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Python packages
RUN pip install --no-cache-dir ollama

# IPython magic for %claude / %%claude
COPY claude_magic.py /opt/ai/claude_magic.py

# Auto-load magic on kernel start
RUN mkdir -p /home/jovyan/.ipython/profile_default/startup
COPY 00-claude.py /home/jovyan/.ipython/profile_default/startup/00-claude.py

# Mobile-friendly custom CSS for JupyterLab 4
# Inject <link> tag directly into Lab's index.html (only reliable method for Lab 4)
COPY custom.css /opt/conda/share/jupyter/lab/static/custom.css
COPY longpress.js /opt/conda/share/jupyter/lab/static/longpress.js
RUN sed -i 's|</head>|<link rel="stylesheet" href="{{page_config.fullStaticUrl}}/custom.css">\n<script src="{{page_config.fullStaticUrl}}/longpress.js"></script>\n</head>|' \
    /opt/conda/share/jupyter/lab/static/index.html

# Also place in classic notebook path (for /tree view)
RUN mkdir -p /home/jovyan/.jupyter/custom
COPY custom.css /home/jovyan/.jupyter/custom/custom.css

# JupyterLab overrides (theme, terminal settings)
COPY overrides.json /opt/conda/share/jupyter/lab/settings/overrides.json

# Podman: rootless config — auto-detect fuse-overlayfs, fall back to vfs
# When /dev/fuse is mounted (via Helm podman.fuseOverlayfs=true), uses overlay for fast pulls
# Without /dev/fuse, falls back to vfs (slow but works without privileges)
RUN mkdir -p /home/jovyan/.config/containers
COPY podman-storage-init.sh /usr/local/bin/podman-storage-init.sh
RUN chmod +x /usr/local/bin/podman-storage-init.sh

# Proxy helpers — proxy-mullvad, proxy-tor, proxy-off, proxy-status
COPY proxy-helpers.sh /usr/local/bin/proxy-helpers.sh
RUN chmod +x /usr/local/bin/proxy-helpers.sh

# Alias: docker → podman (for muscle memory / scripts expecting docker CLI)
# Auto-detect storage driver on first terminal open
# Source proxy helpers for Mullvad/Tor routing
RUN echo 'alias docker=podman' >> /home/jovyan/.bashrc && \
    echo 'alias docker-compose="podman compose"' >> /home/jovyan/.bashrc && \
    echo '# Auto-configure Podman storage on first shell' >> /home/jovyan/.bashrc && \
    echo 'podman-storage-init.sh 2>/dev/null' >> /home/jovyan/.bashrc && \
    echo '# Proxy helpers: proxy-mullvad, proxy-tor, proxy-off, proxy-status' >> /home/jovyan/.bashrc && \
    echo 'source /usr/local/bin/proxy-helpers.sh' >> /home/jovyan/.bashrc

# Ensure jovyan owns everything
RUN chown -R jovyan:users /home/jovyan/.ipython /home/jovyan/.jupyter \
        /home/jovyan/.config /opt/ai

USER jovyan
