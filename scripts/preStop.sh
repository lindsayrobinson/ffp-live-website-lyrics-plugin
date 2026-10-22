#!/bin/bash
set -euo pipefail
if [ -f /etc/systemd/system/loe-lyrics.service ] && grep -q 'fpp-plugin-loe-lyrics/supervisor.py' /etc/systemd/system/loe-lyrics.service; then
    systemctl stop loe-lyrics.service 2>/dev/null || true
fi
