#!/bin/bash
# Setup Emergency Access Point for TurboPi
# This script configures the emergency AP network interface

set -e

# Error handler
trap 'echo "Error: Setup failed at line $LINENO. Check system logs with: journalctl -u turbopi-emergency-ap.service" >&2' ERR

INTERFACE="wlan0"
IP_ADDRESS="192.168.50.1"
CIDR="24"

echo "Setting up emergency access point on $INTERFACE..."

# Check if the interface exists
if ! ip link show "$INTERFACE" > /dev/null 2>&1; then
    echo "Error: Interface $INTERFACE does not exist." >&2
    exit 1
fi

# Check if the interface is already configured with the desired IP and is up
if ip addr show "$INTERFACE" | grep -q "${IP_ADDRESS}/${CIDR}" && ip link show "$INTERFACE" | grep -q "state UP"; then
    echo "Interface $INTERFACE is already configured for the emergency AP. Skipping reconfiguration."
    ip addr show "$INTERFACE"
    exit 0
fi

# Bring down the interface first
ip link set "$INTERFACE" down 2>/dev/null || true

# Allow kernel and driver to fully release the interface after bringing it down.
# This delay helps prevent race conditions or configuration errors when reconfiguring the interface.
# 1 second is typically sufficient for most hardware; adjust if issues are observed.
sleep 1

# Configure the interface with static IP
ip addr flush dev "$INTERFACE"
ip addr add "${IP_ADDRESS}/${CIDR}" dev "$INTERFACE"

# Bring up the interface
ip link set "$INTERFACE" up

# Note: IP forwarding is not enabled here, as it is not required for the emergency AP setup.
# If IP forwarding is needed in the future for routing between interfaces,
# enable it intentionally and document why (e.g., for internet sharing).

echo "Emergency AP interface configured:"
ip addr show "$INTERFACE"

exit 0
