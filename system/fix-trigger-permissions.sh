#!/usr/bin/env bash
#
# Quick fix for /var/lib/turbopi permission issue
# This resolves: [Errno 13] Permission denied: '/var/lib/turbopi/update-trigger.json.tmp'
#
# Run on the robot: sudo bash fix-trigger-permissions.sh
#

set -e

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Must run as root"
    echo "Usage: sudo bash $0"
    exit 1
fi

echo "Fixing /var/lib/turbopi permissions for turbopi user..."

# Ensure directory exists with correct ownership
mkdir -p /var/lib/turbopi
chown turbopi:turbopi /var/lib/turbopi
chmod 0750 /var/lib/turbopi

echo "✓ Directory permissions fixed"
echo ""
echo "Restarting API service to retry update..."
systemctl restart turbopi-api

echo "✓ API service restarted"
echo ""
echo "You can now retry the update from the web UI."
