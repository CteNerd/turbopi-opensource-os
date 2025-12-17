#!/bin/bash
# Installation script for TurboPi Emergency Access Point
# Run with sudo: sudo ./install-emergency-ap.sh

set -e

# Trap errors and print a helpful message
trap 'echo "Error on line $LINENO: $BASH_COMMAND" >&2; exit 99' ERR

# Helper function for prompts with timeout
# The prompt timeout can be configured via the PROMPT_TIMEOUT environment variable (default: 30 seconds).
# 30 seconds was chosen as a balance between not blocking automation and giving users time to respond.
# Usage: prompt_yes_no "prompt message" "skip message"
# Returns: 0 for yes, 1 for no/timeout/non-interactive
prompt_yes_no() {
    local prompt_msg="$1"
    local skip_msg="$2"
    local timeout="${PROMPT_TIMEOUT:-30}"
    
    if [ -t 0 ]; then
        # Interactive terminal
        local yn
        read -t "$timeout" -p "$prompt_msg [y/N]: " yn || yn="N"
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
    # Extract last 4 hex digits (last 2 bytes) from MAC address
    # For MAC aa:bb:cc:dd:ee:ff, this extracts "EEFF"
    MAC_SUFFIX=$(ip link show wlan0 | grep 'link/ether' | awk '{print $2}' | tr -d ':' | tr '[:lower:]' '[:upper:]' | tail -c 5 | head -c 4)
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

# Generate unique per-device password for security
# Use MAC address, machine-id, and salt string to generate a deterministic but unique password
echo "Generating unique per-device password..."
if [ -f /etc/machine-id ]; then
    MACHINE_ID=$(cat /etc/machine-id)
else
    # Fallback if machine-id doesn't exist (shouldn't happen on modern systems)
    MACHINE_ID=$(cat /proc/sys/kernel/random/uuid | tr -d '-')
fi

# Get full MAC address for password generation
if ip link show wlan0 > /dev/null 2>&1; then
    FULL_MAC=$(ip link show wlan0 | grep 'link/ether' | awk '{print $2}' | tr -d ':')
else
    FULL_MAC="000000000000"
fi

# Generate a strong, unique password using SHA256 hash of machine-id + MAC + salt
# Extract only the hash (first field) to avoid fragility, then take first 20 characters
UNIQUE_PASSWORD=$(echo -n "${MACHINE_ID}${FULL_MAC}turbopi-emergency-ap" | sha256sum | awk '{print $1}' | cut -c1-20)

# Update the password in the config file
sed -i "s/^wpa_passphrase=.*/wpa_passphrase=$UNIQUE_PASSWORD/" /etc/turbopi/network/hostapd-emergency.conf

# Verify the password was written correctly
if ! grep -q "^wpa_passphrase=$UNIQUE_PASSWORD$" /etc/turbopi/network/hostapd-emergency.conf; then
    echo "ERROR: Failed to update password in hostapd-emergency.conf"
    exit 1
fi

echo "[OK] Generated unique password for this device"
echo
echo "====================================================================="
echo "EMERGENCY AP PASSWORD (RECORD THIS NOW!):"
echo
echo "    $UNIQUE_PASSWORD"
echo
echo "This password is required to connect to the TurboPi Emergency Access Point."
echo "Record it securely. It will not be shown again if the install fails."
echo "====================================================================="
echo

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

# Poll for service to become active (timeout configurable via SERVICE_START_TIMEOUT, default: 10 seconds)
SERVICE_START_TIMEOUT="${SERVICE_START_TIMEOUT:-10}"
echo -n "Waiting for service to start"
service_started=0
for ((i=1; i<=SERVICE_START_TIMEOUT; i++)); do
    if systemctl is-active --quiet turbopi-emergency-ap.service; then
        echo ""
        echo "Service started successfully."
        service_started=1
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Check if service failed to start within timeout
if [ "$service_started" -ne 1 ]; then
    echo "WARNING: Service did not become active within ${SERVICE_START_TIMEOUT} seconds." >&2
    echo "It may have failed to start. Check the service status and logs:" >&2
    echo "  sudo systemctl status turbopi-emergency-ap.service" >&2
    echo "  sudo journalctl -u turbopi-emergency-ap.service" >&2
fi

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

# Verify config files are properly installed before extracting values
if [ ! -f /etc/turbopi/network/hostapd-emergency.conf ]; then
    echo "ERROR: Configuration file /etc/turbopi/network/hostapd-emergency.conf not found!" >&2
    exit 1
fi

# Extract configured SSID and password from hostapd config
CONFIGURED_SSID=$(grep '^ssid=' /etc/turbopi/network/hostapd-emergency.conf | cut -d'=' -f2)
CONFIGURED_PASSWORD=$(grep '^wpa_passphrase=' /etc/turbopi/network/hostapd-emergency.conf | cut -d'=' -f2)

# Validate extracted password (must be 8-63 characters for WPA2)
if [ -z "$CONFIGURED_PASSWORD" ] || [ ${#CONFIGURED_PASSWORD} -lt 8 ] || [ ${#CONFIGURED_PASSWORD} -gt 63 ]; then
    echo "Emergency Access Point Details:"
    echo "  SSID: $CONFIGURED_SSID"
    echo "  Password: [ERROR: Could not extract valid password from config!]"
    echo "           Please check /etc/turbopi/network/hostapd-emergency.conf"
    echo "  Robot IP: 192.168.50.1"
    echo "  Web UI: http://192.168.50.1:8080"
    echo ""
else
    echo "Emergency Access Point Details:"
    echo "  SSID: $CONFIGURED_SSID"
    echo "  Password: $CONFIGURED_PASSWORD  ⚠️  CHANGE THIS NOW!"
    echo "  Robot IP: 192.168.50.1"
    echo "  Web UI: http://192.168.50.1:8080"
    echo ""
fi

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
    echo "3. Replace '<MAC>' in ssid with last 4 hex digits after removing colons (e.g., if MAC ends in ee:ff, use EEFF)"
    echo "   Example: ssid=TurboPi-Emergency-EEFF"
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
