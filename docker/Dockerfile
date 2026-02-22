# syntax=docker/dockerfile:1
# jupyterlab-claude: jupyterlab-base + Claude Code + Gemini CLI
# Fast rebuild: FROM pre-built base + npm install only (~60-90s including QEMU)
FROM ghcr.io/kub0-ai/jupyterlab-base:latest

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

USER root

# The only frequent-change layer: AI agent tooling
RUN npm install -g @anthropic-ai/claude-code @google/gemini-cli

# IPython magic for %claude / %%claude / ask()
RUN mkdir -p /opt/ai
COPY claude_magic.py /opt/ai/claude_magic.py
RUN mkdir -p /home/jovyan/.ipython/profile_default/startup
COPY 00-claude.py /home/jovyan/.ipython/profile_default/startup/00-claude.py

# gemini-flash alias (claude-specific)
RUN echo 'alias gemini-flash="gemini -m gemini-2.5-flash"' >> /home/jovyan/.bashrc

RUN chown -R jovyan:jovyan \
    /home/jovyan/.ipython \
    /opt/ai

USER jovyan
WORKDIR /home/jovyan
EXPOSE 8888

