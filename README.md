# jupyterlab-claude

JupyterLab with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI and IPython magic integration. Run Claude directly from notebook cells.

## Features

- **Claude Code CLI** pre-installed (via `@anthropic-ai/claude-code`)
- **IPython magic** commands — `%claude`, `%%claude`, `ask()`
- **Conversation-per-kernel** — each kernel gets a unique session ID; restart or `%claude_reset` for a fresh conversation
- **Progress indicator** — animated terminal-style display while Claude thinks
- **Persistent auth** — credentials stored on PVC, survive pod restarts
- **Proxy routing** — `%proxy mullvad` / `%proxy tor` for selective VPN/Tor exit
- **Helm chart** — deploy to any Kubernetes cluster

## Quick Start

### Helm

```bash
helm install jupyter ./chart \
  --namespace jupyter --create-namespace \
  --set ingress.enabled=true \
  --set ingress.host=jupyter.example.com
```

### Docker

```bash
cd docker
docker build -t jupyterlab-claude .
docker run -p 8888:8888 jupyterlab-claude
```

## Usage

After deploying, authenticate once:

1. Open a Terminal tab in JupyterLab (File > New > Terminal)
2. Run `claude` and follow the prompts
3. Credentials are saved to the PVC — you won't need to do this again

Then in any notebook:

```python
# Recommended — handles ? and special characters
ask("What are the three laws of robotics?")

# Line magic
%claude explain this error

# Cell magic for multi-line prompts
%%claude
Given this DataFrame:
  df = pd.DataFrame({"a": [1, 2, 3]})
How do I add a rolling average column?
```

### Session Management

```python
%claude_reset     # Start a fresh conversation (new session ID)
%claude_status    # Show session ID, turn count, auth status
%claude_version   # Show image tag and git SHA
%claude_auth      # Re-authenticate if credentials expired
%claude_thinking  # Toggle thinking section visibility
```

### Proxy Routing

Route notebook and terminal traffic through VPN or Tor exits. Requires `mullvad.enabled` or `tor.enabled` in Helm values.

```python
%proxy                  # Show usage
%proxy mullvad          # Random endpoint from proxy pool
%proxy mullvad 2        # Specific endpoint (0-indexed)
%proxy tor              # Tor SOCKS5 sidecar
%proxy off              # Clear proxy, use node IP
%proxy status           # Show current proxy and exit IP
```

Shell equivalents available in the terminal: `proxy-mullvad`, `proxy-tor`, `proxy-off`, `proxy-status`.

## Configuration

See [`chart/values.yaml`](chart/values.yaml) for all configurable values. Key options:

| Value | Default | Description |
|-------|---------|-------------|
| `image.repository` | `ghcr.io/kub0-ai/jupyterlab-claude` | Container image |
| `persistence.size` | `20Gi` | PVC size for notebooks + Claude credentials |
| `persistence.storageClass` | `""` (cluster default) | Storage class |
| `resources.limits.memory` | `8Gi` | Memory limit (Claude CLI + Node.js need headroom) |
| `jupyter.tokenAuth` | `false` | Disable JupyterLab token (use external auth) |
| `podman.fuseOverlayfs` | `false` | Mount `/dev/fuse` + grant `SYS_ADMIN` for fast Podman image pulls (overlay vs vfs) |
| `ollama.enabled` | `false` | Enable Ollama integration |
| `mullvad.enabled` | `false` | Inject `PROXY_URLS` env for `%proxy mullvad` |
| `mullvad.proxySecretName` | `""` | K8s Secret with key `proxy_urls` (comma-separated HTTP proxy endpoints) |
| `tor.enabled` | `false` | Add Tor sidecar (SOCKS5 on `127.0.0.1:9050`) for `%proxy tor` |
| `ingress.enabled` | `false` | Create an Ingress resource |

## Building the Image

```bash
cd docker
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ghcr.io/kub0-ai/jupyterlab-claude:latest --push .
```

## License

MIT
