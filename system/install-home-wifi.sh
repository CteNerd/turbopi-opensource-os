#!/bin/bash
# Installation script for TurboPi Home Wi-Fi Client
# Run with sudo: sudo ./install-home-wifi.sh
# This configures the robot to connect to a home Wi-Fi network while keeping the emergency AP active

set -e

# Trap errors and print a helpful message (do not leak secrets)
trap 'echo "Error on line $LINENO. See above for details." >&2; exit 99' ERR

# Detect script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "=== TurboPi Home Wi-Fi Client Installation ==="
echo ""

# Verify required files exist
echo "Verifying required files..."
if [ ! -f "$SCRIPT_DIR/network/wpa_supplicant-home.conf" ] || \
   [ ! -f "$SCRIPT_DIR/network/setup-home-wifi.sh" ] || \
   [ ! -f "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" ]; then
    echo "Error: Required configuration files not found in $SCRIPT_DIR" >&2
    echo "Please run this script from the system/ directory of the repository." >&2
    exit 2
fi

# Install required packages (if not already installed)
echo "Checking required packages..."
PACKAGES_TO_INSTALL=""
# wpasupplicant for Wi-Fi client, isc-dhcp-client for DHCP
# Note: Using isc-dhcp-client (dhclient) which is standard on Raspberry Pi OS
for pkg in wpasupplicant isc-dhcp-client; do
    if ! dpkg -l | grep -qw "^ii  $pkg"; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $pkg"
    fi
done

if [ -n "$PACKAGES_TO_INSTALL" ]; then
    echo "Installing required packages:$PACKAGES_TO_INSTALL"
    if ! apt-get update; then
        echo "Error: 'apt-get update' failed. Please check your network connection and package sources." >&2
        exit 3
    fi
    
    if ! apt-get install -y "$PACKAGES_TO_INSTALL"; then
        echo "Error: 'apt-get install' failed. Please check your network connection, package sources, and dependencies." >&2
        exit 4
    fi
else
    echo "All required packages are already installed."
fi

# Create directories
echo "Creating directories..."
mkdir -p /etc/turbopi/network
mkdir -p /usr/local/bin/turbopi

# Copy configuration files
echo "Installing configuration files..."
cp "$SCRIPT_DIR/network/wpa_supplicant-home.conf" /etc/turbopi/network/
cp "$SCRIPT_DIR/network/setup-home-wifi.sh" /usr/local/bin/turbopi/
chmod +x /usr/local/bin/turbopi/setup-home-wifi.sh

# Prompt for Wi-Fi credentials
echo ""
echo "=== Wi-Fi Configuration ==="
echo ""

# Check for non-interactive mode
if [ -t 0 ]; then
    # Interactive mode - prompt for credentials
    read -t 30 -p "Enter your home Wi-Fi SSID: " WIFI_SSID || WIFI_SSID=""
    
    # Validate SSID
    if [ -z "$WIFI_SSID" ]; then
        echo "Error: SSID cannot be empty" >&2
        exit 5
    fi
    
    # Read password securely
    read -t 30 -sp "Enter your home Wi-Fi password: " WIFI_PASSWORD || WIFI_PASSWORD=""
    echo ""
    
    # Validate password (WPA2 requires 8-63 characters)
    if [ -z "$WIFI_PASSWORD" ] || [ ${#WIFI_PASSWORD} -lt 8 ] || [ ${#WIFI_PASSWORD} -gt 63 ]; then
        echo "Error: Password must be 8-63 characters for WPA2" >&2
        exit 6
    fi
    
    # Confirm password
    read -t 30 -sp "Confirm your home Wi-Fi password: " WIFI_PASSWORD_CONFIRM || WIFI_PASSWORD_CONFIRM=""
    echo ""
    
    if [ "$WIFI_PASSWORD" != "$WIFI_PASSWORD_CONFIRM" ]; then
        echo "Error: Passwords do not match" >&2
        exit 7
    fi
    
    # Update configuration file with credentials using wpa_passphrase
    echo "Updating configuration with your credentials..."
    # Generate WPA-PSK config block using wpa_passphrase (handles special characters safely)
    if ! WPA_BLOCK=$(wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" 2>&1 | grep -v '^[[:space:]]*#psk='); then
        echo "Error: wpa_passphrase failed to generate configuration" >&2
        exit 10
    fi
    
    # Validate wpa_passphrase output
    if [ -z "$WPA_BLOCK" ] || ! echo "$WPA_BLOCK" | grep -q "network={"; then
        echo "Error: Invalid wpa_passphrase output" >&2
        exit 11
    fi
    
    # Replace the placeholder network block in the config file
    # Use awk to safely replace the network block
    awk -v block="$WPA_BLOCK" '
        BEGIN {inblock=0}
        /^network={/ {print block; inblock=1; next}
        /^}/ && inblock {inblock=0; next}
        !inblock
    ' /etc/turbopi/network/wpa_supplicant-home.conf > /etc/turbopi/network/wpa_supplicant-home.conf.tmp
    mv /etc/turbopi/network/wpa_supplicant-home.conf.tmp /etc/turbopi/network/wpa_supplicant-home.conf
    
    # Optional: Prompt for interface
    echo ""
    echo "Which Wi-Fi interface should be used for home Wi-Fi?"
    echo "  wlan1 (recommended): Use USB Wi-Fi adapter, keep wlan0 for emergency AP"
    echo "  wlan0 (not recommended): Use built-in Wi-Fi, emergency AP will be disabled"
    read -t 30 -p "Enter interface [wlan1]: " WIFI_INTERFACE || WIFI_INTERFACE=""
    WIFI_INTERFACE="${WIFI_INTERFACE:-wlan1}"
else
    # Non-interactive mode - credentials must be provided via environment variables
    echo "Non-interactive mode detected."
    if [ -z "$WIFI_SSID" ] || [ -z "$WIFI_PASSWORD" ]; then
        echo "Error: In non-interactive mode, WIFI_SSID and WIFI_PASSWORD environment variables must be set" >&2
        exit 8
    fi
    
    # Validate SSID is not empty or whitespace-only
    if [ -z "$(echo "$WIFI_SSID" | tr -d '[:space:]')" ]; then
        echo "Error: SSID cannot be empty or whitespace-only in non-interactive mode" >&2
        exit 5
    fi
    
    # Validate password length
    if [ ${#WIFI_PASSWORD} -lt 8 ] || [ ${#WIFI_PASSWORD} -gt 63 ]; then
        echo "Error: Password must be 8-63 characters for WPA2" >&2
        exit 6
    fi
    
    # Update configuration file with credentials from environment using wpa_passphrase
    echo "Using credentials from environment variables..."
    # Generate WPA-PSK config block using wpa_passphrase (handles special characters safely)
    if ! WPA_BLOCK=$(wpa_passphrase "$WIFI_SSID" "$WIFI_PASSWORD" 2>&1 | grep -v '^[[:space:]]*#psk='); then
        echo "Error: wpa_passphrase failed to generate configuration" >&2
        exit 10
    fi
    
    # Validate wpa_passphrase output
    if [ -z "$WPA_BLOCK" ] || ! echo "$WPA_BLOCK" | grep -q "network={"; then
        echo "Error: Invalid wpa_passphrase output" >&2
        exit 11
    fi
    
    # Replace the placeholder network block in the config file
    # Use awk to safely replace the network block
    awk -v block="$WPA_BLOCK" '
        BEGIN {inblock=0}
        /^network={/ {print block; inblock=1; next}
        /^}/ && inblock {inblock=0; next}
        !inblock
    ' /etc/turbopi/network/wpa_supplicant-home.conf > /etc/turbopi/network/wpa_supplicant-home.conf.tmp
    mv /etc/turbopi/network/wpa_supplicant-home.conf.tmp /etc/turbopi/network/wpa_supplicant-home.conf
    
    WIFI_INTERFACE="${WIFI_INTERFACE:-wlan1}"
fi

# Set proper permissions on config file (contains password)
chmod 600 /etc/turbopi/network/wpa_supplicant-home.conf

# Validate configuration file after generation
echo "Validating configuration..."
if [ ! -f /etc/turbopi/network/wpa_supplicant-home.conf ]; then
    echo "Error: Configuration file not found after generation" >&2
    exit 12
fi

if ! grep -q "network={" /etc/turbopi/network/wpa_supplicant-home.conf; then
    echo "Error: Configuration file does not contain network block" >&2
    exit 13
fi

if ! grep -q "ssid=" /etc/turbopi/network/wpa_supplicant-home.conf; then
    echo "Error: Configuration file does not contain SSID" >&2
    exit 14
fi

# Install systemd service
echo ""
echo "Installing systemd service..."
cp "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" /etc/systemd/system/

# Create systemd override to set the interface
if [ "$WIFI_INTERFACE" != "wlan1" ]; then
    echo "Creating systemd override for interface $WIFI_INTERFACE..."
    
    # Validate interface name to prevent injection
    if ! echo "$WIFI_INTERFACE" | grep -qE '^wlan[0-9]+$'; then
        echo "Error: Invalid interface name. Must be wlan0, wlan1, etc." >&2
        exit 9
    fi
    
    mkdir -p /etc/systemd/system/turbopi-home-wifi.service.d
    cat > /etc/systemd/system/turbopi-home-wifi.service.d/interface.conf <<EOF
[Service]
Environment="WIFI_INTERFACE=$WIFI_INTERFACE"
EOF
fi

systemctl daemon-reload

# Check if interface exists
if ! ip link show "$WIFI_INTERFACE" > /dev/null 2>&1; then
    echo ""
    echo "WARNING: Interface $WIFI_INTERFACE does not exist." >&2
    if [ "$WIFI_INTERFACE" = "wlan1" ]; then
        echo "  - Make sure a USB Wi-Fi adapter is connected" >&2
        echo "  - Or rerun this script and choose wlan0 (will disable emergency AP)" >&2
    fi
    echo ""
    echo "Service installed but not enabled. Enable it manually after connecting the adapter:" >&2
    echo "  sudo systemctl enable turbopi-home-wifi.service" >&2
    echo "  sudo systemctl start turbopi-home-wifi.service" >&2
    exit 0
fi

# Enable service
echo "Enabling service..."
systemctl enable turbopi-home-wifi.service

# Warn if using wlan0
if [ "$WIFI_INTERFACE" = "wlan0" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    ⚠️  WARNING ⚠️                              ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "You are using wlan0 for home Wi-Fi."
    echo "The emergency AP will be DISABLED when this service starts."
    echo "You will NOT be able to access the robot via the emergency AP."
    echo ""
    echo "To stop home Wi-Fi and re-enable emergency AP:"
    echo "  sudo systemctl stop turbopi-home-wifi.service"
    echo "  sudo systemctl start turbopi-emergency-ap.service"
    echo ""
    if [ -t 0 ]; then
        read -t 30 -p "Press Enter to continue or Ctrl+C to abort..." || true
    else
        echo "Non-interactive mode: Continuing without confirmation."
    fi
fi

# Start the service
echo "Starting service..."
systemctl start turbopi-home-wifi.service

# Poll for service to become active (timeout configurable via SERVICE_START_TIMEOUT, default: 10 seconds)
SERVICE_START_TIMEOUT="${SERVICE_START_TIMEOUT:-10}"
echo -n "Waiting for service to start"
service_started=0
for ((i=1; i<=SERVICE_START_TIMEOUT; i++)); do
    if systemctl is-active --quiet turbopi-home-wifi.service; then
        echo ""
        echo "✓ Service started successfully"
        service_started=1
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# Check if service failed to start within timeout
if [ "$service_started" -ne 1 ]; then
    echo "⚠ Service did not become active within ${SERVICE_START_TIMEOUT} seconds." >&2
    echo "  Check status: sudo systemctl status turbopi-home-wifi.service" >&2
    echo "  Check logs: sudo journalctl -u turbopi-home-wifi.service" >&2
else
    # Wait a bit more for IP assignment (timeout configurable via CONNECTION_WAIT_TIMEOUT, default: 5 seconds)
    CONNECTION_WAIT_TIMEOUT="${CONNECTION_WAIT_TIMEOUT:-5}"
    echo "Waiting for Wi-Fi connection (${CONNECTION_WAIT_TIMEOUT}s)..."
    sleep "$CONNECTION_WAIT_TIMEOUT"
    
    # Try to get IP address
    IP_ADDRESS=$(ip -4 addr show "$WIFI_INTERFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "")
    if [ -n "$IP_ADDRESS" ]; then
        echo "✓ Connected to home Wi-Fi"
        echo "  IP Address: $IP_ADDRESS"
        echo "  Interface: $WIFI_INTERFACE"
    else
        echo "⚠ Service is running but no IP address assigned yet"
        echo "  Check status: sudo systemctl status turbopi-home-wifi.service"
        echo "  Check logs: sudo journalctl -u turbopi-home-wifi.service"
    fi
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Home Wi-Fi Client Configuration:"
echo "  SSID: $WIFI_SSID"
echo "  Interface: $WIFI_INTERFACE"
if [ "$WIFI_INTERFACE" != "wlan0" ]; then
    echo "  Emergency AP: Active on wlan0 (192.168.50.1)"
else
    echo "  Emergency AP: Disabled (wlan0 used for home Wi-Fi)"
fi
echo ""
echo "The robot will automatically connect to this network on boot."
echo ""
echo "To access the robot:"
echo "  1. Make sure you're on the same network"
if [ -n "$IP_ADDRESS" ]; then
    echo "  2. Open browser to: http://$IP_ADDRESS:8080"
else
    echo "  2. Find the robot's IP address in your router's DHCP client list"
    echo "  3. Open browser to: http://<robot-ip>:8080"
fi
echo ""
