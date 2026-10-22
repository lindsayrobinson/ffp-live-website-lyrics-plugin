#!/bin/bash
set -euo pipefail
UNIT=/etc/systemd/system/loe-lyrics.service
# Only remove the service when this plugin owns it; never remove a restored legacy service.
if [ -f "$UNIT" ] && grep -q 'fpp-plugin-loe-lyrics/supervisor.py' "$UNIT"; then
    systemctl disable --now loe-lyrics.service 2>/dev/null || true
    rm -f "$UNIT"
    systemctl daemon-reload
fi
echo 'Live Website Lyrics sending stopped. Playback and aircraft controls are unchanged.'
