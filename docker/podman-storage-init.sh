#!/bin/bash
# Auto-configure Podman storage driver based on /dev/fuse availability.
# Called from .bashrc on every shell — only writes config when driver changes.
CONF="$HOME/.config/containers/storage.conf"
mkdir -p "$(dirname "$CONF")"

if [ -c /dev/fuse ] && command -v fuse-overlayfs >/dev/null 2>&1; then
    WANT="overlay"
else
    WANT="vfs"
fi

# Only write if driver changed or conf missing
CURRENT=$(grep -oP 'driver\s*=\s*"\K[^"]+' "$CONF" 2>/dev/null)
if [ "$CURRENT" = "$WANT" ]; then
    exit 0
fi

# Driver changed — reset Podman storage to avoid "store is already initialized" errors
podman system reset --force 2>/dev/null

if [ "$WANT" = "overlay" ]; then
    cat > "$CONF" <<'EOF'
[storage]
driver = "overlay"

[storage.options.overlay]
mount_program = "/usr/bin/fuse-overlayfs"
EOF
    echo "podman: configured fuse-overlayfs (fast layer dedup)"
else
    cat > "$CONF" <<'EOF'
[storage]
driver = "vfs"
EOF
    echo "podman: configured vfs (slow — enable podman.fuseOverlayfs in Helm for overlay)"
fi
