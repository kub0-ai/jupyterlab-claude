#!/usr/bin/env bash
# proxy-helpers.sh — sourced by .bashrc
# Shell functions to route terminal traffic through Mullvad or Tor.
# Mirrors the %proxy IPython magic in claude_magic.py.

proxy-mullvad() {
    local idx="${1:-}"
    local urls="${PROXY_URLS:-}"
    if [ -z "$urls" ]; then
        echo "No PROXY_URLS configured. Set mullvad.proxySecretName in Helm values." >&2
        return 1
    fi
    IFS=',' read -ra endpoints <<< "$urls"
    local count="${#endpoints[@]}"
    local proxy
    if [ -n "$idx" ]; then
        if [ "$idx" -ge "$count" ] 2>/dev/null; then
            echo "Index out of range. Available: 0-$((count - 1))" >&2
            return 1
        fi
        proxy="${endpoints[$idx]}"
    else
        proxy="${endpoints[$((RANDOM % count))]}"
        idx="$((RANDOM % count))"
    fi
    proxy="${proxy// /}"
    export http_proxy="$proxy" https_proxy="$proxy" HTTP_PROXY="$proxy" HTTPS_PROXY="$proxy"
    unset all_proxy ALL_PROXY
    echo "→ Mullvad proxy [$idx/$((count - 1))]: $proxy"
    echo -n "  Exit IP: "
    curl -s --max-time 10 --proxy "$proxy" https://api64.ipify.org
    echo
}

proxy-tor() {
    local tor="socks5h://127.0.0.1:9050"
    local check
    check=$(curl -s --max-time 8 --proxy "$tor" https://check.torproject.org/api/ip 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "Tor sidecar not reachable on 127.0.0.1:9050" >&2
        echo "Enable with: tor.enabled=true in Helm values, then redeploy." >&2
        return 1
    fi
    export all_proxy="$tor" ALL_PROXY="$tor"
    unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
    echo "→ Tor: $tor"
    local ip is_tor
    ip=$(echo "$check" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('IP','unknown'))" 2>/dev/null || echo "unknown")
    is_tor=$(echo "$check" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('IsTor') else 'no')" 2>/dev/null || echo "unknown")
    echo "  Exit IP: $ip (Tor confirmed: $is_tor)"
}

proxy-off() {
    unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY
    echo "→ Proxy cleared."
    echo -n "  Exit IP: "
    curl -s --max-time 10 https://api64.ipify.org
    echo
}

proxy-status() {
    local p="${http_proxy:-${HTTP_PROXY:-${all_proxy:-${ALL_PROXY:-}}}}"
    if [ -n "$p" ]; then
        echo "→ Proxy: $p"
        echo -n "  Exit IP: "
        curl -s --max-time 10 --proxy "$p" https://api64.ipify.org
        echo
    else
        echo "→ Proxy: none (direct)"
        echo -n "  Exit IP: "
        curl -s --max-time 10 https://api64.ipify.org
        echo
    fi
}
