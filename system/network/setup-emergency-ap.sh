#!/bin/bash
# Setup Emergency Access Point for TurboPi
# This script configures the emergency AP network interface

set -e

INTERFACE="wlan0"
IP_ADDRESS="192.168.50.1"
CIDR="24"

echo "Setting up emergency access point on $INTERFACE..."

# Bring down the interface first
ip link set $INTERFACE down 2>/dev/null || true

# Wait a moment for interface to settle
sleep 1

# Configure the interface with static IP
ip addr flush dev $INTERFACE
ip addr add ${IP_ADDRESS}/${CIDR} dev $INTERFACE

# Bring up the interface
ip link set $INTERFACE up

# Enable IP forwarding for potential future use
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "Emergency AP interface configured:"
ip addr show $INTERFACE

exit 0
