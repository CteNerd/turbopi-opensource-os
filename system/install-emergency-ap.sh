#!/bin/bash
# Installation script for TurboPi Emergency Access Point
# Run with sudo: sudo ./install-emergency-ap.sh

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "=== TurboPi Emergency Access Point Installation ==="
echo ""

# Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y hostapd dnsmasq

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
cp network/hostapd-emergency.conf /etc/turbopi/network/
cp network/dnsmasq-emergency.conf /etc/turbopi/network/
cp network/setup-emergency-ap.sh /usr/local/bin/turbopi/
chmod +x /usr/local/bin/turbopi/setup-emergency-ap.sh

# Install systemd service
echo "Installing systemd service..."
cp systemd/turbopi-emergency-ap.service /etc/systemd/system/
systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting service..."
systemctl enable turbopi-emergency-ap.service
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
echo "Connect to the TurboPi-Emergency network to access the robot."
echo ""
