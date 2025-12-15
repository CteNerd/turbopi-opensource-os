#!/bin/bash
# Installation script for TurboPi Emergency Access Point
# Run with sudo: sudo ./install-emergency-ap.sh

set -e

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "=== TurboPi Emergency Access Point Installation ==="
echo ""

# Verify required files exist
echo "Verifying required files..."
if [ ! -f "$SCRIPT_DIR/network/hostapd-emergency.conf" ] || \
   [ ! -f "$SCRIPT_DIR/network/dnsmasq-emergency.conf" ] || \
   [ ! -f "$SCRIPT_DIR/network/setup-emergency-ap.sh" ] || \
   [ ! -f "$SCRIPT_DIR/systemd/turbopi-emergency-ap.service" ]; then
    echo "Error: Required configuration files not found in $SCRIPT_DIR" >&2
    echo "Please run this script from the system/ directory of the repository." >&2
    exit 2
fi

# Install required packages
echo "Installing required packages..."
if ! apt-get update; then
    echo "Error: 'apt-get update' failed. Please check your network connection and package sources." >&2
    exit 3
fi

if ! apt-get install -y hostapd dnsmasq; then
    echo "Error: 'apt-get install' failed. Please check your network connection, package sources, and dependencies." >&2
    exit 4
fi

# Stop services during installation
echo "Stopping services..."
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
systemctl disable hostapd 2>/dev/null || true
systemctl disable dnsmasq 2>/dev/null || true

# Create directories
echo "Creating directories..."
mkdir -p /etc/turbopi/network
mkdir -p /usr/local/bin/turbopi

# Copy configuration files
echo "Installing configuration files..."
cp "$SCRIPT_DIR/network/hostapd-emergency.conf" /etc/turbopi/network/
cp "$SCRIPT_DIR/network/dnsmasq-emergency.conf" /etc/turbopi/network/
cp "$SCRIPT_DIR/network/setup-emergency-ap.sh" /usr/local/bin/turbopi/
chmod +x /usr/local/bin/turbopi/setup-emergency-ap.sh

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/systemd/turbopi-emergency-ap.service" /etc/systemd/system/
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable turbopi-emergency-ap.service

# Check if wlan0 is available before starting
if ! ip link show wlan0 > /dev/null 2>&1; then
    echo "WARNING: wlan0 interface not found. The emergency AP service may not work." >&2
    read -p "Continue and attempt to start the service anyway? [y/N]: " yn
    case "$yn" in
        [Yy]*) ;;
        *) echo "Skipping service start. You can start it manually later with: systemctl start turbopi-emergency-ap.service"; exit 0;;
    esac
else
    # Check if wlan0 is currently connected
    if iw wlan0 link 2>/dev/null | grep -q 'Connected'; then
        echo "WARNING: wlan0 is currently connected to another network." >&2
        echo "This may cause the emergency AP service to fail to start." >&2
        read -p "Continue and attempt to start the service anyway? [y/N]: " yn
        case "$yn" in
            [Yy]*) ;;
            *) echo "Skipping service start. You can start it manually later with: systemctl start turbopi-emergency-ap.service"; exit 0;;
        esac
    fi
fi

echo "Starting service..."
systemctl start turbopi-emergency-ap.service

# Wait a moment for service to start
sleep 2

# Check service status
echo ""
echo "=== Service Status ==="
systemctl status turbopi-emergency-ap.service --no-pager || true

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Emergency Access Point Details:"
echo "  SSID: TurboPi-Emergency"
echo "  Password: turbopi123"
echo "  Robot IP: 192.168.50.1"
echo "  Web UI: http://192.168.50.1:8080"
echo ""
echo "⚠️  SECURITY WARNING ⚠️"
echo "The default password 'turbopi123' is WEAK and must be changed for production use!"
echo "To change the password:"
echo "  1. Edit /etc/turbopi/network/hostapd-emergency.conf"
echo "  2. Change the 'wpa_passphrase' value to a strong 8-63 character password"
echo "  3. Restart the service: sudo systemctl restart turbopi-emergency-ap.service"
echo ""
echo "Connect to the TurboPi-Emergency network to access the robot."
echo ""
