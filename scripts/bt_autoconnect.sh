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

# Retry loop to handle boot timing/race conditions
RETRIES=12
SLEEP_SEC=5

for i in $(seq 1 $RETRIES); do
    bluetoothctl <<EOF
power on
agent on
default-agent
trust ${MAC}
connect ${MAC}
EOF

    # Check connection state
    if bluetoothctl info "${MAC}" | grep -q "Connected: yes"; then
        echo "✓ Connected to ${MAC}"
        exit 0
    fi

    echo "Not connected yet (attempt ${i}/${RETRIES}). Retrying in ${SLEEP_SEC}s..."
    sleep "${SLEEP_SEC}"
done

echo "⚠️  Failed to connect to ${MAC} after ${RETRIES} attempts."
exit 1
