#!/bin/bash
# Install TurboPi runtime services
# This script sets up the API, UI, and Updater services with systemd

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "TurboPi Runtime Service Installer"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Usage: sudo ./install-services.sh"
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p /opt/turbopi/current/bin
mkdir -p /opt/turbopi/current/src
mkdir -p /opt/turbopi/downloads
mkdir -p /etc/turbopi
mkdir -p /var/log/turbopi

# Copy service implementations
echo "Installing service binaries..."
cp -r "$REPO_ROOT/src/api" /opt/turbopi/current/src/
cp -r "$REPO_ROOT/src/ui" /opt/turbopi/current/src/
cp -r "$REPO_ROOT/src/updater" /opt/turbopi/current/src/
cp -r "$REPO_ROOT/src/control" /opt/turbopi/current/src/
cp -r "$REPO_ROOT/src/hal" /opt/turbopi/current/src/
cp -r "$REPO_ROOT/src/vision" /opt/turbopi/current/src/
cp -r "$REPO_ROOT/src/voice" /opt/turbopi/current/src/

if [ -d /home/pi/TurboPi/HiwonderSDK ] && [ ! -d /opt/turbopi/current/HiwonderSDK ]; then
    echo "Preserving vendor SDK from /home/pi/TurboPi/HiwonderSDK..."
    cp -r /home/pi/TurboPi/HiwonderSDK /opt/turbopi/current/
fi

if [ -f /home/pi/TurboPi/servo_config.yaml ] && [ ! -f /opt/turbopi/current/servo_config.yaml ]; then
    echo "Preserving vendor servo configuration from /home/pi/TurboPi/servo_config.yaml..."
    cp /home/pi/TurboPi/servo_config.yaml /opt/turbopi/current/
fi

# Create wrapper scripts in bin directory
echo "Creating service wrappers..."

cat > /opt/turbopi/current/bin/api << 'EOF'
#!/bin/bash
cd /opt/turbopi/current || exit 1
exec /usr/bin/python3 /opt/turbopi/current/src/api/main.py
EOF

cat > /opt/turbopi/current/bin/ui << 'EOF'
#!/bin/bash
cd /opt/turbopi/current || exit 1
exec /usr/bin/python3 /opt/turbopi/current/src/ui/main.py
EOF

cat > /opt/turbopi/current/bin/updater << 'EOF'
#!/bin/bash
cd /opt/turbopi/current || exit 1
exec /usr/bin/python3 /opt/turbopi/current/src/updater/main.py
EOF

cat > /opt/turbopi/current/bin/wake-word << 'EOF'
#!/bin/bash
cd /opt/turbopi/current || exit 1
exec /usr/bin/python3 /opt/turbopi/current/src/voice/main.py
EOF

chmod +x /opt/turbopi/current/bin/api
chmod +x /opt/turbopi/current/bin/ui
chmod +x /opt/turbopi/current/bin/updater
chmod +x /opt/turbopi/current/bin/wake-word

# Create config.env if it doesn't exist
if [ ! -f /etc/turbopi/config.env ]; then
    echo "Creating default configuration..."
    cp "$REPO_ROOT/system/config.env.example" /etc/turbopi/config.env
    echo -e "${GREEN}✓ Created /etc/turbopi/config.env${NC}"
    echo -e "${YELLOW}  Please review and customize this file for your robot${NC}"
else
    echo -e "${YELLOW}! Configuration file /etc/turbopi/config.env already exists${NC}"
    echo "  Skipping configuration creation to preserve existing settings"
fi

# Create turbopi user if it doesn't exist
if ! id -u turbopi > /dev/null 2>&1; then
    echo "Creating turbopi user..."
    useradd -r -s /bin/false -d /opt/turbopi turbopi
    echo -e "${GREEN}✓ Created turbopi user${NC}"
fi

# Set ownership and permissions (comprehensive setup)
echo "Setting permissions..."

# /opt/turbopi directory tree
chown -R turbopi:turbopi /opt/turbopi
chmod -R u+rwX,g+rX /opt/turbopi
echo "  ✓ /opt/turbopi owned by turbopi:turbopi"

# State and log directories
mkdir -p /var/lib/turbopi
chown turbopi:turbopi /var/lib/turbopi
chmod 0750 /var/lib/turbopi

mkdir -p /var/log/turbopi
chown turbopi:turbopi /var/log/turbopi
chmod 0750 /var/log/turbopi
echo "  ✓ State and log directories created"

# Config directory and file
chown root:turbopi /etc/turbopi
chmod 0750 /etc/turbopi
chown root:turbopi /etc/turbopi/config.env
chmod 0660 /etc/turbopi/config.env
echo "  ✓ Configuration permissions set"

# Install systemd service files
echo "Installing systemd services..."
cp "$REPO_ROOT/system/systemd/turbopi-api.service" /etc/systemd/system/
cp "$REPO_ROOT/system/systemd/turbopi-ui.service" /etc/systemd/system/
cp "$REPO_ROOT/system/systemd/turbopi-updater.service" /etc/systemd/system/
cp "$REPO_ROOT/system/systemd/turbopi-wake-word.service" /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable services
echo "Enabling services..."
systemctl enable turbopi-api.service
systemctl enable turbopi-ui.service
systemctl enable turbopi-updater.service
# Note: Wake word service is optional - enable manually if using standalone mode
# systemctl enable turbopi-wake-word.service

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Services installed:"
echo "  - turbopi-api.service    (API Backend on port 8080, includes wake word)"
echo "  - turbopi-ui.service     (Web UI on port 8081)"
echo "  - turbopi-updater.service (Update Service)"
echo "  - turbopi-wake-word.service (Optional standalone wake word service)"
echo ""
echo "To start the services now:"
echo "  sudo systemctl start turbopi-api.service"
echo "  sudo systemctl start turbopi-ui.service"
echo "  sudo systemctl start turbopi-updater.service"
echo ""
echo "To check service status:"
echo "  sudo systemctl status turbopi-api.service"
echo "  sudo systemctl status turbopi-ui.service"
echo "  sudo systemctl status turbopi-updater.service"
echo ""
echo "Configuration file: /etc/turbopi/config.env"
echo ""
