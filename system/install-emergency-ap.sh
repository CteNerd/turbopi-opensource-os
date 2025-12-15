#!/bin/bash
# Installation script for TurboPi Emergency Access Point
# Run with sudo: sudo ./install-emergency-ap.sh

set -e

# Trap errors and print a helpful message
trap 'echo "Error on line $LINENO: $BASH_COMMAND" >&2; exit 99' ERR

# Helper function for prompts with timeout
# Usage: prompt_yes_no "prompt message" "skip message"
# Returns: 0 for yes, 1 for no/timeout/non-interactive
prompt_yes_no() {
    local prompt_msg="$1"
    local skip_msg="$2"
    
    if [ -t 0 ]; then
        # Interactive terminal
        local yn
        read -t 30 -p "$prompt_msg [y/N]: " yn || yn="N"
        case "$yn" in
            [Yy]*) return 0 ;;
            *) echo "$skip_msg"; return 1 ;;
        esac
    else
        # Non-interactive environment
        echo "Non-interactive environment detected. Skipping service start." >&2
        echo "$skip_msg"
        return 1
    fi
}

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

# Auto-generate SSID with MAC address suffix if wlan0 exists
if ip link show wlan0 > /dev/null 2>&1; then
    MAC_SUFFIX=$(ip link show wlan0 | grep 'link/ether' | awk '{print $2}' | tail -c 9 | tr -d ':' | tr '[:lower:]' '[:upper:]')
    if [ -n "$MAC_SUFFIX" ] && [ ${#MAC_SUFFIX} -eq 4 ]; then
        echo "Configuring SSID with MAC suffix: $MAC_SUFFIX"
        sed -i "s/TurboPi-Emergency-<MAC>/TurboPi-Emergency-$MAC_SUFFIX/g" /etc/turbopi/network/hostapd-emergency.conf
    else
        echo "WARNING: Could not extract MAC address suffix. SSID will use placeholder." >&2
        echo "You must manually edit /etc/turbopi/network/hostapd-emergency.conf before the AP will work." >&2
    fi
else
    echo "WARNING: wlan0 not found. SSID will use <MAC> placeholder." >&2
    echo "You must manually edit /etc/turbopi/network/hostapd-emergency.conf before the AP will work." >&2
fi

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
    if ! prompt_yes_no "Continue and attempt to start the service anyway?" \
        "Skipping service start. You can start it manually later with: systemctl start turbopi-emergency-ap.service"; then
        exit 0
    fi
else
    # Check if wlan0 is currently connected
    if iw wlan0 link 2>/dev/null | grep -q 'Connected'; then
        echo "WARNING: wlan0 is currently connected to another network." >&2
        echo "This may cause the emergency AP service to fail to start." >&2
        if ! prompt_yes_no "Continue and attempt to start the service anyway?" \
            "Skipping service start. You can start it manually later with: systemctl start turbopi-emergency-ap.service"; then
            exit 0
        fi
    fi
fi

echo "Starting service..."
systemctl start turbopi-emergency-ap.service

# Poll for service to become active (up to 10 seconds)
echo "Waiting for service to start..."
for i in {1..10}; do
    if systemctl is-active --quiet turbopi-emergency-ap.service; then
        echo "Service started successfully."
        break
    fi
    sleep 1
done

# Check service status
echo ""
echo "=== Service Status ==="
systemctl status turbopi-emergency-ap.service --no-pager || true

echo ""
echo "=== Installation Complete ==="
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              ⚠️  SECURITY WARNING ⚠️                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "The emergency AP is using a DEFAULT PASSWORD that MUST be changed"
echo "immediately after first connection for production use!"
echo ""
# Extract configured SSID and password from hostapd config
CONFIGURED_SSID=$(grep '^ssid=' /etc/turbopi/network/hostapd-emergency.conf | cut -d'=' -f2)
CONFIGURED_PASSWORD=$(grep '^wpa_passphrase=' /etc/turbopi/network/hostapd-emergency.conf | cut -d'=' -f2)

echo "Emergency Access Point Details:"
echo "  SSID: $CONFIGURED_SSID"
echo "  Password: $CONFIGURED_PASSWORD  ⚠️  CHANGE THIS NOW!"
echo "  Robot IP: 192.168.50.1"
echo "  Web UI: http://192.168.50.1:8080"
echo ""

if echo "$CONFIGURED_SSID" | grep -q '<MAC>'; then
    echo "⚠️  CRITICAL: Configuration Required Before Use ⚠️"
    echo "The SSID contains a placeholder and the AP will NOT work!"
    echo ""
    echo "1. Get your wlan0 MAC address:"
    echo "   ip link show wlan0 | grep 'link/ether'"
    echo ""
    echo "2. Edit the hostapd config:"
    echo "   sudo nano /etc/turbopi/network/hostapd-emergency.conf"
    echo ""
    echo "3. Replace '<MAC>' in ssid with last 4 hex chars (e.g., if MAC ends in ee:ff, use EEFF)"
    echo "   Example: ssid=TurboPi-Emergency-A1B2"
    echo ""
    echo "4. Change 'wpa_passphrase' to a strong unique password (8-63 characters)"
    echo ""
    echo "5. Restart the service:"
    echo "   sudo systemctl restart turbopi-emergency-ap.service"
else
    echo "⚠️  IMPORTANT: Security Configuration Required ⚠️"
    echo "The SSID has been configured automatically, but you should:"
    echo ""
    echo "1. Change 'wpa_passphrase' in /etc/turbopi/network/hostapd-emergency.conf"
    echo "   to a strong unique password (8-63 characters)"
    echo ""
    echo "2. Restart the service:"
    echo "   sudo systemctl restart turbopi-emergency-ap.service"
fi
echo ""
echo "Connect to the TurboPi-Emergency network to access the robot."
echo ""
