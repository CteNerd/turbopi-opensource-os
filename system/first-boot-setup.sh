#!/bin/bash
# First-boot setup script for TurboPi OpenSource OS
# This script runs automatically on first boot to initialize the emergency AP
# and prepare the system for operation.
#
# Usage:
#   1. Copy this script to /boot/turbopi-first-boot.sh (or /boot/firmware/turbopi-first-boot.sh on newer Pi OS)
#   2. Add execution hook to /etc/rc.local or create systemd service
#   3. Script will run once and remove itself after successful completion

set -e

# Configuration
TURBOPI_REPO_DIR="/opt/turbopi"
SETUP_COMPLETE_FLAG="/etc/turbopi/.first-boot-complete"
LOG_FILE="/var/log/turbopi-first-boot.log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handler
trap 'log "ERROR: Setup failed at line $LINENO"; exit 1' ERR

# Check if we've already run
if [ -f "$SETUP_COMPLETE_FLAG" ]; then
    log "First-boot setup already completed. Exiting."
    exit 0
fi

log "=== TurboPi First-Boot Setup Starting ==="

# Ensure we're running as root
if [ "$EUID" -ne 0 ]; then 
    log "ERROR: Must run as root"
    exit 1
fi

# Create turbopi directories
log "Creating TurboPi directories..."
mkdir -p /etc/turbopi/network
mkdir -p /var/log/turbopi
mkdir -p "$TURBOPI_REPO_DIR"

# Check if repository files are already in place
if [ ! -d "$TURBOPI_REPO_DIR/system" ]; then
    log "ERROR: TurboPi repository not found at $TURBOPI_REPO_DIR"
    log "Please ensure the TurboPi repository is cloned to $TURBOPI_REPO_DIR"
    exit 1
fi

# Change to repository directory
cd "$TURBOPI_REPO_DIR"

# Install Emergency AP
log "Installing Emergency Access Point..."
if [ -f "$TURBOPI_REPO_DIR/system/install-emergency-ap.sh" ]; then
    # Run installation in non-interactive mode
    if PROMPT_TIMEOUT=5 "$TURBOPI_REPO_DIR/system/install-emergency-ap.sh" >> "$LOG_FILE" 2>&1; then
        log "Emergency AP installation completed successfully"
    else
        # Check if it failed due to missing wlan0 (might be on different hardware)
        if ip link show wlan0 > /dev/null 2>&1; then
            log "ERROR: Emergency AP installation failed"
            exit 1
        else
            log "WARNING: wlan0 not found. Emergency AP not installed."
        fi
    fi
else
    log "ERROR: install-emergency-ap.sh not found"
    exit 1
fi

# Mark setup as complete
log "Creating completion flag..."
mkdir -p "$(dirname "$SETUP_COMPLETE_FLAG")"
date > "$SETUP_COMPLETE_FLAG"

log "=== TurboPi First-Boot Setup Completed Successfully ==="
log ""
log "Emergency Access Point Details:"
log "  SSID: TurboPi-Emergency-<MAC>"
log "  IP: 192.168.50.1"
log "  Web UI: http://192.168.50.1:8080"
log ""
log "To configure home Wi-Fi, run:"
log "  sudo /opt/turbopi/system/install-home-wifi.sh"
log ""

exit 0
