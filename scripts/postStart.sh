#!/bin/bash
set -euo pipefail
# FPP media/plugins survives an OS-image upgrade; /etc/systemd may not.
PLUGIN_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -f /etc/systemd/system/loe-lyrics.service ]; then
    bash "${PLUGIN_DIR}/scripts/fpp_install.sh"
else
    systemctl start loe-lyrics.service
fi
