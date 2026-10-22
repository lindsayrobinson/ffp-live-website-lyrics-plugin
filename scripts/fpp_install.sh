#!/bin/bash
set -euo pipefail
: "${FPPDIR:=/opt/fpp}"
. "${FPPDIR}/scripts/common"
PLUGIN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT=/etc/systemd/system/loe-lyrics.service
PRIVATE="${PLUGIN_DIR}/.private"
install -d -m 700 -o fpp -g fpp "${PRIVATE}"
if [ ! -f "${PRIVATE}/csrf.key" ]; then
    python3 - "${PRIVATE}/csrf.key" <<'PY'
import os, secrets, sys
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write(secrets.token_hex(32))
PY
    chown fpp:fpp "${PRIVATE}/csrf.key"
fi
if [ ! -e "${PRIVATE}/config.json" ]; then
    if [ -f "${MEDIADIR}/config/loe-lyrics.json" ]; then
        install -m 600 -o fpp -g fpp "${MEDIADIR}/config/loe-lyrics.json" "${PRIVATE}/config.json"
        python3 - "${PRIVATE}/config.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
c = json.loads(p.read_text())
c.setdefault('enabled', True)
p.write_text(json.dumps(c, indent=2) + '\n')
PY
    else
        install -m 600 -o fpp -g fpp "${PLUGIN_DIR}/config.example.json" "${PRIVATE}/config.json"
    fi
fi
if [ -e "$UNIT" ] && ! grep -q 'fpp-plugin-loe-lyrics/supervisor.py' "$UNIT" && [ ! -e "${PRIVATE}/legacy-service.backup" ]; then
    install -m 600 "$UNIT" "${PRIVATE}/legacy-service.backup"
fi
# One service name replaces the legacy sender, preventing duplicate uploads.
systemctl stop loe-lyrics.service 2>/dev/null || true
cat > "$UNIT" <<EOF
[Unit]
Description=Live Website Lyrics FPP plugin
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=fpp
UMask=0077
ExecStart=/usr/bin/python3 "${PLUGIN_DIR}/supervisor.py" --config "${PRIVATE}/config.json" --log "${LOGDIR}/plugin-fpp-plugin-loe-lyrics.log"
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths="${PRIVATE}" "${LOGDIR}"
[Install]
WantedBy=multi-user.target
EOF
chmod 644 "$UNIT"
systemctl daemon-reload
if ! systemctl enable --now loe-lyrics.service; then
    if [ -f "${PRIVATE}/legacy-service.backup" ]; then
        install -m 644 "${PRIVATE}/legacy-service.backup" "$UNIT"
        systemctl daemon-reload
        systemctl enable --now loe-lyrics.service
    fi
    exit 1
fi
echo 'Live Website Lyrics plugin installed. Settings: Content Setup > Live Website Lyrics.'
