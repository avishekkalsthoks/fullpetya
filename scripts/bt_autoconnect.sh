#!/usr/bin/env bash
set -euo pipefail

# Auto-connect to a trusted Bluetooth device.
# Usage: bt_autoconnect.sh AA:BB:CC:DD:EE:FF
# Or set BT_DEVICE_MAC in your environment.

MAC="${1:-${BT_DEVICE_MAC:-}}"

if [ -z "${MAC}" ]; then
    echo "No Bluetooth MAC provided. Set BT_DEVICE_MAC or pass as argument."
    exit 0
fi

echo "Connecting to Bluetooth device: ${MAC}"

bluetoothctl <<EOF
power on
agent on
default-agent
trust ${MAC}
connect ${MAC}
EOF
