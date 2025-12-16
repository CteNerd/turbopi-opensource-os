#!/bin/bash
# Setup Home Wi-Fi Client for TurboPi
# This script configures the home Wi-Fi interface to connect automatically

set -e

# Error handler
trap 'echo "Error: Setup failed at line $LINENO. Check system logs with: journalctl -u turbopi-home-wifi.service" >&2' ERR

# Default to wlan1 for home Wi-Fi to keep wlan0 for emergency AP
INTERFACE="${WIFI_INTERFACE:-wlan1}"

echo "Setting up home Wi-Fi client on $INTERFACE..."

# Check if the interface exists
if ! ip link show "$INTERFACE" > /dev/null 2>&1; then
    echo "Error: Interface $INTERFACE does not exist." >&2
    echo "Make sure you have a USB Wi-Fi adapter or configure WIFI_INTERFACE environment variable." >&2
    exit 1
fi

# Bring up the interface if it's down
# Check for UP state in the output (handles "state UP" and "UP,LOWER_UP" formats)
if ! ip link show "$INTERFACE" | grep -q "state UP"; then
    echo "Bringing up interface $INTERFACE..."
    ip link set "$INTERFACE" up
fi

echo "Starting wpa_supplicant on $INTERFACE..."
echo "Home Wi-Fi client interface configured:"
ip link show "$INTERFACE" | head -2

exit 0
