#!/usr/bin/env bash
#
# TurboPi Permission Fix Script
#
# This script audits and fixes all permission issues in the TurboPi system.
# Run as root: sudo bash fix-permissions.sh
#

set -euo pipefail

echo "=== TurboPi Permission Audit and Fix ==="
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root"
    echo "Usage: sudo bash $0"
    exit 1
fi

# Ensure turbopi user exists
if ! id turbopi &>/dev/null; then
    echo "ERROR: turbopi user does not exist"
    exit 1
fi

echo "1. Fixing /opt/turbopi directory structure..."

# Main directories
chown -R turbopi:turbopi /opt/turbopi
echo "  ✓ Set ownership turbopi:turbopi on /opt/turbopi"

# Specific permission fixes for release directories
for dir in /opt/turbopi/releases/*; do
    if [ -d "$dir" ]; then
        chown -R turbopi:turbopi "$dir"
        chmod -R u+rwX,g+rX "$dir"
        echo "  ✓ Fixed $(basename "$dir")"
    fi
done

echo
echo "2. Fixing systemd state directories..."

# StateDirectory paths (systemd should create these, but ensure they exist with correct ownership)
mkdir -p /var/lib/turbopi
chown turbopi:turbopi /var/lib/turbopi
chmod 0750 /var/lib/turbopi
echo "  ✓ /var/lib/turbopi (turbopi:turbopi, 0750)"

mkdir -p /var/log/turbopi
chown turbopi:turbopi /var/log/turbopi
chmod 0750 /var/log/turbopi
echo "  ✓ /var/log/turbopi (turbopi:turbopi, 0750)"

echo
echo "3. Fixing /etc/turbopi config directory..."

mkdir -p /etc/turbopi
chown root:turbopi /etc/turbopi
chmod 0750 /etc/turbopi
echo "  ✓ /etc/turbopi (root:turbopi, 0750)"

if [ -f /etc/turbopi/config.env ]; then
    chown root:turbopi /etc/turbopi/config.env
    chmod 0660 /etc/turbopi/config.env
    echo "  ✓ /etc/turbopi/config.env (root:turbopi, 0660)"
fi

echo
echo "4. Verifying systemd service users..."

for service in turbopi-api turbopi-ui turbopi-updater; do
    user=$(systemctl show "$service.service" -p User --value 2>/dev/null || echo "not-found")
    group=$(systemctl show "$service.service" -p Group --value 2>/dev/null || echo "not-found")
    
    if [ "$service" = "turbopi-updater" ]; then
        expected_user="root"
        expected_group="root"
    else
        expected_user="turbopi"
        expected_group="turbopi"
    fi
    
    if [ "$user" = "$expected_user" ] && [ "$group" = "$expected_group" ]; then
        echo "  ✓ $service.service runs as $user:$group"
    else
        echo "  ⚠ $service.service runs as $user:$group (expected $expected_user:$expected_group)"
    fi
done

echo
echo "5. Permission summary:"
echo
ls -ld /opt/turbopi /opt/turbopi/current /opt/turbopi/previous 2>/dev/null || true
echo
ls -ld /var/lib/turbopi /var/log/turbopi 2>/dev/null || true
echo
ls -ld /etc/turbopi /etc/turbopi/config.env 2>/dev/null || true

echo
echo "=== Permission fix complete ==="
echo
echo "Services should now have proper access to:"
echo "  - /opt/turbopi/*           (runtime code and releases)"
echo "  - /var/lib/turbopi         (state files, update triggers)"
echo "  - /var/log/turbopi         (log files)"
echo "  - /etc/turbopi/config.env  (configuration, readable by turbopi group)"
