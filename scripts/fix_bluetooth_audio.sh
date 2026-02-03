#!/usr/bin/env bash
# Bluetooth Audio Stability Fix for Raspberry Pi Zero 2W
# Addresses stuttering by disabling Wi-Fi power save, adjusting PulseAudio, and setting CPU governor.

echo "=============================================="
echo "Applying Bluetooth Audio Stability Fixes"
echo "=============================================="

# 1. Disable Wi-Fi Power Management (Major cause of interference)
if command -v iw > /dev/null; then
    echo "[1/4] Disabling Wi-Fi power save..."
    sudo iw dev wlan0 set power_save off || echo "⚠️  Failed to set Wi-Fi power save"
else
    echo "⚠️  'iw' command not found, skipping Wi-Fi power save fix"
fi

# 2. Optimize PulseAudio for Bluetooth
if [ -f /etc/pulse/daemon.conf ]; then
    echo "[2/4] Optimizing PulseAudio buffer settings..."
    # Backup
    sudo cp /etc/pulse/daemon.conf /etc/pulse/daemon.conf.bak.$(date +%s)
    
    # Increase fragments and fragment size for smoother audio
    sudo sed -i 's/^; default-fragments =.*/default-fragments = 5/' /etc/pulse/daemon.conf || \
    echo "default-fragments = 5" | sudo tee -a /etc/pulse/daemon.conf
    
    sudo sed -i 's/^; default-fragment-size-msec =.*/default-fragment-size-msec = 25/' /etc/pulse/daemon.conf || \
    echo "default-fragment-size-msec = 25" | sudo tee -a /etc/pulse/daemon.conf
    
    # Restart PulseAudio if running
    pulseaudio -k 2>/dev/null || true
    echo "✓ PulseAudio configuration updated"
fi

# 3. Set CPU Governor to Performance (Prevents stutter during frequency changes)
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    echo "[3/4] Setting CPU governor to performance..."
    echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
    
    # Make it persistent via rc.local if not already
    if ! grep -q "scaling_governor" /etc/rc.local 2>/dev/null; then
        sudo sed -i '/^exit 0/i echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor' /etc/rc.local
    fi
    echo "✓ CPU governor set to performance"
fi

# 4. Programmatic Latency Offset (Apply to existing Bluetooth device)
echo "[4/4] Setting latency offset for active Bluetooth devices..."
BT_SINK=$(pactl list short sinks | grep bluez | awk '{print $2}' | head -n 1)
if [ -n "$BT_SINK" ]; then
    # 50ms (50000 microseconds) offset is usually a good starting point
    pactl set-port-latency-offset "$BT_SINK" headset-output 50000 2>/dev/null || true
    echo "✓ Applied 50ms latency offset to $BT_SINK"
else
    echo "ℹ️  No active Bluetooth sink found to apply offset right now."
    echo "   The fix will apply to future connections via configuration."
fi

echo "=============================================="
echo "✅ Fixes applied!"
echo "Please restart your Bluetooth earphones if stuttering persists."
echo "=============================================="
