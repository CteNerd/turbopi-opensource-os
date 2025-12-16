# TurboPi Base OS Image Creation

This document describes how to create a base OS image for TurboPi that boots with the emergency access point pre-configured.

> ⚠️ **CRITICAL SECURITY WARNING**  
> The default emergency AP password (`TurboPi-7f9d2b1c4e5a`) is documented publicly and **MUST** be changed immediately after first connection. This default password is provided only for initial setup and is **NOT secure** for production use. See [Security Recommendations](#security-recommendations) section for instructions on changing the password.

## Overview

The TurboPi base OS image is built on Raspberry Pi OS and includes:
- Emergency Access Point (automatically starts on first boot)
- Home Wi-Fi client support (configured via setup wizard)
- All necessary system services and configurations
- Persistent network configuration across reboots

## Quick Start - Pre-built Image (When Available)

1. Download the latest TurboPi OS image from the releases page
2. Flash to SD card using Raspberry Pi Imager or `dd`
3. Insert SD card and power on the Raspberry Pi
4. Connect to `TurboPi-Emergency-<MAC>` Wi-Fi network
5. Access web UI at `http://192.168.50.1:8080`

## Creating a Custom Base Image

### Prerequisites

- Raspberry Pi OS Lite (latest) - [Download](https://www.raspberrypi.com/software/operating-systems/)
- SD card (16GB or larger recommended)
- Raspberry Pi (3 or later) with Wi-Fi capability
- USB Wi-Fi adapter (recommended for dual networking)
- Computer for image preparation

### Method 1: Manual Installation (Recommended for Development)

This method installs TurboPi on an existing Raspberry Pi OS installation.

#### Step 1: Flash Base Raspberry Pi OS

1. Download Raspberry Pi OS Lite
2. Flash to SD card using Raspberry Pi Imager
3. Optional: Enable SSH by creating empty file `/boot/ssh` on the boot partition
4. Boot the Raspberry Pi and complete initial setup

#### Step 2: Clone TurboPi Repository

```bash
# Install git if not already installed
sudo apt-get update
sudo apt-get install -y git

# Clone repository to /opt/turbopi
sudo mkdir -p /opt/turbopi
sudo chown $USER:$USER /opt/turbopi
git clone https://github.com/CteNerd/turbopi-opensource-os.git /opt/turbopi
cd /opt/turbopi
```

#### Step 3: Install Emergency Access Point

```bash
cd /opt/turbopi/system
sudo ./install-emergency-ap.sh
```

The emergency AP will:
- Install required packages (hostapd, dnsmasq)
- Configure the access point on wlan0
- Set SSID to `TurboPi-Emergency-<MAC>` (where `<MAC>` is the last 4 hex digits of the wlan0 MAC address, after removing colons and using uppercase; e.g., if MAC ends in ee:ff, use EEFF)
- Enable systemd service for automatic startup
- Start immediately

Verify the AP is running:
```bash
sudo systemctl status turbopi-emergency-ap.service
```

#### Step 4: Configure Home Wi-Fi (Optional)

If you have a USB Wi-Fi adapter:

```bash
cd /opt/turbopi/system
sudo ./install-home-wifi.sh
```

Follow the prompts to enter your Wi-Fi credentials. The setup will:
- Configure wlan1 (USB adapter) for home Wi-Fi
- Keep wlan0 running the emergency AP
- Enable automatic connection on boot

#### Step 5: Verify Dual Networking

Both networks should now be active:

```bash
# Check emergency AP (wlan0)
ip addr show wlan0

# Check home Wi-Fi (wlan1)
ip addr show wlan1

# Verify services
sudo systemctl status turbopi-emergency-ap.service
sudo systemctl status turbopi-home-wifi.service
```

#### Step 6: Test Reboot Persistence

```bash
sudo reboot
```

After reboot, verify both networks come up automatically:
```bash
sudo systemctl status turbopi-emergency-ap.service
sudo systemctl status turbopi-home-wifi.service
```

#### Step 7: Create Image Backup (Optional)

Once configured, create an image backup:

```bash
# On your computer, with SD card connected
# Replace /dev/sdX with your SD card device
sudo dd if=/dev/sdX of=turbopi-base-$(date +%Y%m%d).img bs=4M status=progress

# Compress the image
gzip turbopi-base-$(date +%Y%m%d).img
```

This image can be flashed to other SD cards for deployment.

### Method 2: Automated First-Boot Setup

This method uses a first-boot script that automatically installs the emergency AP on first boot.

#### Step 1: Prepare Base Image

1. Flash Raspberry Pi OS Lite to SD card
2. Mount the boot partition on your computer

#### Step 2: Copy TurboPi Files

```bash
# Mount SD card boot partition (adjust path as needed)
BOOT_MOUNT="/media/$USER/boot"  # Or /media/$USER/bootfs on newer Pi OS

# Create turbopi directory on SD card root partition
ROOT_MOUNT="/media/$USER/rootfs"
sudo mkdir -p "$ROOT_MOUNT/opt/turbopi"

# Copy repository contents
sudo cp -r /path/to/turbopi-opensource-os/* "$ROOT_MOUNT/opt/turbopi/"
```

#### Step 3: Install First-Boot Service

```bash
# Copy first-boot service file
sudo cp "$ROOT_MOUNT/opt/turbopi/system/systemd/turbopi-first-boot.service" \
        "$ROOT_MOUNT/etc/systemd/system/"

# Enable the service (create symlink)
sudo mkdir -p "$ROOT_MOUNT/etc/systemd/system/multi-user.target.wants"
sudo ln -sf /etc/systemd/system/turbopi-first-boot.service \
           "$ROOT_MOUNT/etc/systemd/system/multi-user.target.wants/turbopi-first-boot.service"
```

#### Step 4: Unmount and Boot

```bash
sync
sudo umount "$BOOT_MOUNT"
sudo umount "$ROOT_MOUNT"
```

Insert SD card into Raspberry Pi and power on. The first-boot setup will:
1. Detect it's the first boot
2. Automatically install the emergency AP
3. Mark setup as complete (won't run again)

### Method 3: Image Building with pi-gen (Advanced)

For creating custom OS images from scratch, use the official Raspberry Pi image builder.

#### Prerequisites

```bash
# On Ubuntu/Debian build machine
sudo apt-get install coreutils quilt parted qemu-user-static debootstrap zerofree zip \
                     dosfstools libarchive-tools libcap2-bin grep rsync xz-utils file git curl bc
```

#### Create Custom Stage

1. Clone pi-gen:
```bash
git clone https://github.com/RPi-Distro/pi-gen.git
cd pi-gen
```

2. Create TurboPi stage:
```bash
mkdir -p stage-turbopi/00-turbopi/files
cp -r /path/to/turbopi-opensource-os stage-turbopi/00-turbopi/files/opt/turbopi
```

3. Create install script:
```bash
cat > stage-turbopi/00-turbopi/01-run.sh << 'EOF'
#!/bin/bash -e

# Install TurboPi emergency AP
cd /opt/turbopi/system
./install-emergency-ap.sh

# Enable first-boot setup for future use
cp /opt/turbopi/system/systemd/turbopi-first-boot.service /etc/systemd/system/
systemctl enable turbopi-first-boot.service
EOF

chmod +x stage-turbopi/00-turbopi/01-run.sh
```

4. Configure build:
```bash
echo "IMG_NAME='TurboPi-OS'" > config
echo "STAGE_LIST='stage0 stage1 stage2 stage-turbopi'" >> config
```

5. Build image:
```bash
sudo ./build.sh
```

The resulting image will be in `deploy/` directory.

## Acceptance Criteria Verification

For detailed testing procedures and comprehensive acceptance criteria verification, see [ACCEPTANCE_TESTING.md](ACCEPTANCE_TESTING.md).

### Quick Verification

Run the automated integration test:
```bash
cd /opt/turbopi/system
sudo ./test-dual-networking.sh
```

### AC1: Fresh Flash Boots into Emergency AP

1. Flash the image to a fresh SD card
2. Insert into Raspberry Pi and power on
3. Wait 2-3 minutes for first boot setup
4. Scan for Wi-Fi networks - should see `TurboPi-Emergency-<MAC>` (where `<MAC>` is the last 4 hex digits after removing colons from the wlan0 MAC address; e.g., if MAC ends in ee:ff, use EEFF)
5. Connect using password `TurboPi-7f9d2b1c4e5a`
6. Access `http://192.168.50.1:8080` in browser

✅ **Pass**: Emergency AP is accessible on fresh boot

### AC2: Device Joins Home Wi-Fi Without Disabling AP

1. Connect to emergency AP
2. Run home Wi-Fi setup:
   ```bash
   ssh pi@192.168.50.1
   cd /opt/turbopi/system
   sudo ./install-home-wifi.sh
   ```
3. Enter home Wi-Fi credentials when prompted
4. Verify both interfaces:
   ```bash
   ip addr show wlan0  # Should have 192.168.50.1
   ip addr show wlan1  # Should have DHCP-assigned IP
   ```
5. Verify both services running:
   ```bash
   sudo systemctl status turbopi-emergency-ap.service
   sudo systemctl status turbopi-home-wifi.service
   ```

✅ **Pass**: Both networks active simultaneously

### AC3: Networking Persists Across Reboot

1. With both networks configured, reboot:
   ```bash
   sudo reboot
   ```
2. After reboot, verify services:
   ```bash
   sudo systemctl status turbopi-emergency-ap.service
   sudo systemctl status turbopi-home-wifi.service
   ```
3. Verify interfaces have IPs:
   ```bash
   ip addr show wlan0
   ip addr show wlan1
   ```
4. Test connectivity:
   ```bash
   # From another device on emergency AP network
   ping 192.168.50.1
   
   # From another device on home network
   ping <wlan1-ip>
   ```

✅ **Pass**: Both networks come up automatically after reboot

## Troubleshooting

### Emergency AP Not Starting

Check service status:
```bash
sudo systemctl status turbopi-emergency-ap.service
sudo journalctl -u turbopi-emergency-ap.service
```

Common issues:
- **wlan0 not found**: Ensure Pi has built-in Wi-Fi or adapter connected
- **Interface already in use**: Another network manager may be controlling wlan0
- **Channel conflicts**: Edit `/etc/turbopi/network/hostapd-emergency.conf` and try different channel

### Home Wi-Fi Not Connecting

Check service status:
```bash
sudo systemctl status turbopi-home-wifi.service
sudo journalctl -u turbopi-home-wifi.service
```

Common issues:
- **wlan1 not found**: USB Wi-Fi adapter not connected or not recognized
- **Wrong password**: Check credentials in `/etc/turbopi/network/wpa_supplicant-home.conf`
- **No DHCP**: May need to wait longer or manually request: `sudo dhclient wlan1`

### Both Services Start but Can't Connect

- Verify interfaces are UP: `ip link show wlan0` and `ip link show wlan1`
- Check IP addresses: `ip addr show`
- Verify no IP conflicts with home network
- Check router firewall settings
- Try restarting services: `sudo systemctl restart turbopi-emergency-ap.service`

## Security Recommendations

### Before Production Deployment

1. **Change Emergency AP Password**:
   ```bash
   sudo nano /etc/turbopi/network/hostapd-emergency.conf
   # Change wpa_passphrase to strong unique password
   sudo systemctl restart turbopi-emergency-ap.service
   ```

2. **Generate Unique SSID** (if MAC-based SSID not auto-generated):
   ```bash
   # Edit hostapd config and replace <MAC> with unique identifier
   sudo nano /etc/turbopi/network/hostapd-emergency.conf
   sudo systemctl restart turbopi-emergency-ap.service
   ```

3. **Secure SSH Access**:
   - Disable password authentication
   - Use SSH keys only
   - Change default user password

4. **Configure Firewall** (optional):
   ```bash
   sudo apt-get install ufw
   sudo ufw allow from 192.168.50.0/24  # Allow emergency AP subnet
   sudo ufw enable
   ```

## References

- [Raspberry Pi OS Documentation](https://www.raspberrypi.com/documentation/computers/os.html)
- [hostapd Documentation](https://w1.fi/hostapd/)
- [wpa_supplicant Documentation](https://w1.fi/wpa_supplicant/)
- [systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [TurboPi System Configuration](../system/README.md)
