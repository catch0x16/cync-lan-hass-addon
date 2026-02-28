#!/usr/bin/env bash
set -euo pipefail

# Ensure persistent cert directory exists
mkdir -p /data/certs

# Generate self-signed TLS cert only if missing — same params as upstream image
# Devices trust this cert once; it must survive add-on updates
if [[ ! -f /data/certs/server.pem ]] || [[ ! -f /data/certs/server.key ]]; then
    echo "[run.sh] Generating self-signed TLS certificate..."
    openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
        -keyout /data/certs/server.key \
        -out    /data/certs/server.pem \
        -subj   "/CN=*.xlink.cn"
    echo "[run.sh] Certificate generated."
fi

# Parse add-on options from /data/options.json using jq
# Use // empty so optional fields yield an empty shell variable when absent/null
MQTT_HOST=$(jq -r '.mqtt_host'        /data/options.json)
MQTT_PORT=$(jq -r '.mqtt_port'        /data/options.json)
MQTT_USER=$(jq -r '.mqtt_user // empty' /data/options.json)
MQTT_PASS=$(jq -r '.mqtt_pass // empty' /data/options.json)
MQTT_TOPIC=$(jq -r '.mqtt_topic'      /data/options.json)
HASS_TOPIC=$(jq -r '.hass_topic'      /data/options.json)
MQTT_CONN_DELAY=$(jq -r '.mqtt_conn_delay' /data/options.json)
CMD_BROADCASTS=$(jq -r '.cmd_broadcasts'   /data/options.json)
MAX_TCP_CONN=$(jq -r '.max_tcp_conn'       /data/options.json)
TCP_WHITELIST=$(jq -r '.tcp_whitelist // empty' /data/options.json)
DEBUG=$(jq -r 'if .debug then "1" else "0" end'         /data/options.json)
RAW_DEBUG=$(jq -r 'if .raw_debug then "1" else "0" end' /data/options.json)

# Required MQTT / topic settings
export CYNC_MQTT_HOST="$MQTT_HOST"
export CYNC_MQTT_PORT="$MQTT_PORT"
export CYNC_TOPIC="$MQTT_TOPIC"
export CYNC_HASS_TOPIC="$HASS_TOPIC"
export CYNC_MQTT_CONN_DELAY="$MQTT_CONN_DELAY"
export CYNC_CMD_BROADCASTS="$CMD_BROADCASTS"
export CYNC_MAX_TCP_CONN="$MAX_TCP_CONN"
export CYNC_DEBUG="$DEBUG"
export CYNC_RAW_DEBUG="$RAW_DEBUG"

# Optional — only export when non-empty to avoid passing empty strings to MQTT library
if [[ -n "$MQTT_USER" ]]; then
    export CYNC_MQTT_USER="$MQTT_USER"
fi
if [[ -n "$MQTT_PASS" ]]; then
    export CYNC_MQTT_PASS="$MQTT_PASS"
fi
if [[ -n "$TCP_WHITELIST" ]]; then
    export CYNC_TCP_WHITELIST="$TCP_WHITELIST"
fi

# Hardcoded values — not exposed as options
export CYNC_HOST=0.0.0.0
export CYNC_PORT=23779
export CYNC_CERT=/data/certs/server.pem
export CYNC_KEY=/data/certs/server.key

# Bootstrap mesh config on first run — run requires the file to exist
if [[ ! -f /data/cync_mesh.yaml ]]; then
    printf 'account data: {}\n' > /data/cync_mesh.yaml
fi

echo "[run.sh] Starting FastAPI export server on port 23778..."
python3 /exporter.py &

echo "[run.sh] Starting cync-lan..."

# exec replaces this shell — cync-lan becomes PID 1 for correct signal handling
exec python3 /root/cync-lan/cync-lan.py run /data/cync_mesh.yaml
