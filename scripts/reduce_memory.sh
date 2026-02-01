#!/usr/bin/env bash
# Memory Optimization Script for Raspberry Pi Zero 2W
# Reduces memory usage and improves performance for Smart Vision Guide

set -euo pipefail

echo "================================================"
echo "Pi Zero 2W Memory Optimization Script"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script must be run as root (sudo)"
    exit 1
fi

echo "[1/7] Disabling unnecessary services..."

# Disable services that consume RAM but aren't needed for headless operation
SERVICES_TO_DISABLE=(
    "bluetooth.service"  # Re-enable if using Bluetooth audio
    "avahi-daemon.service"
    "triggerhappy.service"
    "hciuart.service"
)

for service in "${SERVICES_TO_DISABLE[@]}"; do
    if systemctl is-enabled "$service" 2>/dev/null | grep -q "enabled"; then
        echo "  Disabling $service..."
        systemctl disable "$service" --now || true
    fi
done

echo "  ✓ Unnecessary services disabled"
echo "  NOTE: Re-enable bluetooth if using Bluetooth audio:"
echo "        sudo systemctl enable bluetooth.service"

echo ""
echo "[2/7] Configuring swap file..."

# Configure swap for better OOM handling
SWAP_SIZE=512  # MB

if [ -f /etc/dphys-swapfile ]; then
    # Backup original
    cp /etc/dphys-swapfile /etc/dphys-swapfile.bak
    
    # Set swap size
    sed -i "s/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=$SWAP_SIZE/" /etc/dphys-swapfile
    
    # Restart swap
    dphys-swapfile swapoff
    dphys-swapfile setup
    dphys-swapfile swapon
    
    echo "  ✓ Swap configured to ${SWAP_SIZE}MB"
else
    echo "  ⚠️  dphys-swapfile not found - skipping swap configuration"
fi

echo ""
echo "[3/7] Optimizing GPU memory split..."

# Reduce GPU memory if not using desktop
if [ -f /boot/config.txt ]; then
    # Backup
    cp /boot/config.txt /boot/config.txt.memopt.bak
    
    # For camera + headless, 128MB GPU is enough
    if ! grep -q "^gpu_mem=" /boot/config.txt; then
        echo "gpu_mem=128" >> /boot/config.txt
        echo "  ✓ Set gpu_mem=128"
    else
        echo "  gpu_mem already configured"
    fi
else
    echo "  ⚠️  /boot/config.txt not found"
fi

echo ""
echo "[4/7] Configuring kernel parameters..."

# Optimize kernel parameters for low memory
if [ ! -f /etc/sysctl.d/99-pi-zero-optimize.conf ]; then
    cat > /etc/sysctl.d/99-pi-zero-optimize.conf <<EOF
# Pi Zero 2W Memory Optimizations

# Reduce swappiness (only swap when really needed)
vm.swappiness=10

# Minimum free memory to maintain
vm.min_free_kbytes=8192

# Improve memory management under pressure
vm.vfs_cache_pressure=50

# Overcommit memory (needed for fork-heavy processes)
vm.overcommit_memory=1
EOF
    
    sysctl -p /etc/sysctl.d/99-pi-zero-optimize.conf
    echo "  ✓ Kernel parameters optimized"
else
    echo "  ✓ Kernel parameters already optimized"
fi

echo ""
echo "[5/7] Cleaning up unnecessary packages..."

# Remove unnecessary packages
apt-get autoremove -y
apt-get autoclean -y

echo "  ✓ Cleaned up unused packages"

echo ""
echo "[6/7] Creating memory monitoring script..."

# Create a simple memory monitor script
cat > /usr/local/bin/check-memory <<'EOF'
#!/bin/bash
# Quick memory check for Pi Zero 2W

echo "Pi Zero 2W Memory Status"
echo "========================"
free -h
echo ""
echo "Temperature: $(vcgencmd measure_temp)"
EOF

chmod +x /usr/local/bin/check-memory

echo "  ✓ Created check-memory command"
echo "  Usage: check-memory"

echo ""
echo "[7/7] Optimizing PulseAudio for low memory..."

# Configure PulseAudio for minimal memory usage
if [ -d /etc/pulse ]; then
    if [ ! -f /etc/pulse/daemon.conf.backup ]; then
        cp /etc/pulse/daemon.conf /etc/pulse/daemon.conf.backup
    fi
    
    # Add low-memory settings
    cat >> /etc/pulse/daemon.conf <<EOF

# Pi Zero 2W Optimizations
resample-method = speex-float-0
default-fragments = 8
default-fragment-size-msec = 5
realtime-scheduling = yes
realtime-priority = 5
EOF
    
    echo "  ✓ PulseAudio optimized for low memory"
else
    echo "  PulseAudio not found - skipping"
fi

echo ""
echo "================================================"
echo "✅ Memory Optimization Complete!"
echo "================================================"
echo ""
echo "Summary of changes:"
echo "  • Disabled unnecessary services"
echo "  • Configured ${SWAP_SIZE}MB swap"
echo "  • Set GPU memory to 128MB"
echo "  • Optimized kernel parameters"
echo "  • Cleaned up packages"
echo "  • Created check-memory monitoring tool"
echo "  • Optimized PulseAudio"
echo ""
echo "⚠️  A reboot is recommended to apply all changes:"
echo "    sudo reboot"
echo ""
echo "Monitoring commands:"
echo "  • check-memory          - Quick memory status"
echo "  • htop                  - Interactive process viewer"
echo "  • free -h               - Memory usage"
echo "  • vcgencmd measure_temp - CPU temperature"
echo ""
echo "To revert changes:"
echo "  • Restore /boot/config.txt from /boot/config.txt.memopt.bak"
echo "  • Restore /etc/dphys-swapfile from /etc/dphys-swapfile.bak"
echo "  • Remove /etc/sysctl.d/99-pi-zero-optimize.conf"
echo ""
echo "================================================"
