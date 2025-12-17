# TurboPi System Configuration

This directory contains system-level configuration files for TurboPi OpenSource OS.

## Quick Start

**Creating a Base OS Image**: See [docs/init/BASE_OS_IMAGE.md](../docs/init/BASE_OS_IMAGE.md) for complete instructions on creating a base OS image that boots with the emergency AP pre-configured.

**Installing Runtime Services**: Run `sudo ./install-services.sh` to install API, UI, and Updater services.

**Testing**: 
- Networking: Run `./test-dual-networking.sh` to verify dual networking setup
- Services: Run `sudo ./test-services.sh` to verify runtime services

## Directory Structure

- `network/` - Network configuration files
- `systemd/` - Systemd service unit files
- `config.env.example` - Configuration template for runtime services
- `first-boot-setup.sh` - First-boot initialization script (automatically installs emergency AP)
- `install-services.sh` - Runtime service installation script
- `test-dual-networking.sh` - Integration test suite for dual networking
- `test-services.sh` - Runtime service test suite

## Runtime Services

TurboPi uses systemd to manage three core services:

### Installation

```bash
cd system
sudo ./install-services.sh
```

This installs and enables:
- **turbopi-api.service** - REST API backend (port 8080)
- **turbopi-ui.service** - Web control interface (port 8081)
- **turbopi-updater.service** - Update management daemon

See [docs/init/RUNTIME_SERVICE_SKELETON.md](../docs/init/RUNTIME_SERVICE_SKELETON.md) for complete documentation.

### Configuration

All services load configuration from `/etc/turbopi/config.env`:

```bash
# Edit configuration
sudo nano /etc/turbopi/config.env

# Restart services to apply changes
sudo systemctl restart turbopi-api.service
sudo systemctl restart turbopi-ui.service
sudo systemctl restart turbopi-updater.service
```

### Testing

```bash
cd system
sudo ./test-services.sh
```

Verifies:
- Services installed and enabled
- Configuration loaded correctly
- Health endpoint responds
- Services can start successfully

## Emergency Access Point

The emergency access point provides always-on network access for setup and recovery.

### Network Details

- **SSID**: `TurboPi-Emergency-<MAC>` (where `<MAC>` is the last 4 hex digits of the wlan0 MAC address, after removing colons and using uppercase; e.g., if MAC ends in ee:ff, use EEFF)
- **Password**: Unique per-device password (automatically generated during installation)
- **Robot IP**: `192.168.50.1`
- **DHCP Range**: `192.168.50.10` - `192.168.50.50`
- **Subnet**: `192.168.50.0/24`

### Security

The installation script automatically generates a **unique, device-specific password** for each robot's emergency AP based on the device's machine-id and MAC address. This ensures:
- No two devices share the same password
- No publicly-known default credentials
- Strong, cryptographically-derived passwords (20 characters from SHA256 hash)

### Features

- Separate subnet to avoid conflicts with home Wi-Fi networks
- Survives system reboots
- Enables access to web UI and SSH (dev mode only)

### Installation

#### Automated Installation (Recommended)

The automated installation script handles MAC address replacement, error checking, and interactive prompts:

```bash
cd system
sudo ./install-emergency-ap.sh
```

The script will:
- Install required packages (hostapd, dnsmasq)
- Automatically replace the `<MAC>` placeholder in the SSID with your device's MAC address
- Copy configuration files to the appropriate locations
- Enable and start the systemd service
- Display the configured SSID and password

#### Manual Installation

**Note**: Run all commands from the repository root directory. If you use manual installation, you must manually replace the `<MAC>` placeholder in the hostapd configuration file with the last 4 hex digits of the wlan0 MAC address, after removing colons (for example, if your MAC is `7f:9d:2b:1c:4e:5a`, use `4E5A`).

1. Install required packages:
   ```bash
   sudo apt-get update
   sudo apt-get install hostapd dnsmasq
   ```

2. Copy configuration files (run from repository root):
   ```bash
   # Run these commands from the repository root directory
   sudo mkdir -p /etc/turbopi/network
   sudo mkdir -p /usr/local/bin/turbopi
   
   sudo cp system/network/hostapd-emergency.conf /etc/turbopi/network/
   sudo cp system/network/dnsmasq-emergency.conf /etc/turbopi/network/
   sudo cp system/network/setup-emergency-ap.sh /usr/local/bin/turbopi/
   sudo chmod +x /usr/local/bin/turbopi/setup-emergency-ap.sh
   ```

3. **IMPORTANT**: Determine your MAC address suffix:
   - Get your wlan0 MAC address by running:
     ```bash
     ip link show wlan0 | grep 'link/ether'
     ```
   - Note the last 4 hex digits (i.e., the last two bytes), **after removing colons and using uppercase letters**.  
     For example, if your MAC is `aa:bb:cc:dd:ee:ff`, use `EEFF`.

4. Replace the `<MAC>` placeholder in the SSID in the hostapd config file:
   - Edit the config file:
     ```bash
     sudo nano /etc/turbopi/network/hostapd-emergency.conf
     ```
   - Change the line `ssid=TurboPi-Emergency-<MAC>` to use your MAC suffix.  
     For example: `ssid=TurboPi-Emergency-EEFF`
5. Install and enable the systemd service (run from repository root):
   ```bash
   # Run these commands from the repository root directory
   sudo cp system/systemd/turbopi-emergency-ap.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable turbopi-emergency-ap.service
   sudo systemctl start turbopi-emergency-ap.service
   ```

6. Verify the service is running:
   ```bash
   sudo systemctl status turbopi-emergency-ap.service
   ```

### Accessing the Robot

Once the emergency AP is active:

1. Connect to the `TurboPi-Emergency-<MAC>` Wi-Fi network using password `TurboPi-7f9d2b1c4e5a` (or your customized password)
2. Open a web browser and navigate to `http://192.168.50.1:8080`
3. For SSH access (development): `ssh pi@192.168.50.1`

### Home Wi-Fi Client

The TurboPi system can connect to your home Wi-Fi network while keeping the emergency AP active.

### Recommended Configuration (Dual Wi-Fi)

- **Built-in Wi-Fi (wlan0)**: Runs emergency AP on `192.168.50.x`
- **USB Wi-Fi adapter (wlan1)**: Connects to home network via DHCP
- Both networks active simultaneously for maximum reliability

### Installation

#### Automated Installation (Recommended)

```bash
cd system
sudo ./install-home-wifi.sh
```

The script will:
- Install required packages (wpasupplicant, dhcp client)
- Prompt for your home Wi-Fi SSID and password
- Configure the home Wi-Fi client service
- Enable automatic connection on boot
- Keep the emergency AP active on wlan0

#### Non-Interactive Installation

For automated deployments, provide credentials via environment variables:

```bash
cd system
sudo WIFI_SSID="YourNetworkName" WIFI_PASSWORD="YourPassword" WIFI_INTERFACE="wlan1" ./install-home-wifi.sh
```

### Features

- **Persistent Connection**: Automatically reconnects on boot
- **Dual Access**: Robot accessible via both emergency AP (192.168.50.1) and home network IP
- **Recovery Plane Preserved**: Emergency AP remains available if home Wi-Fi fails
- **Secure**: Wi-Fi credentials stored in protected config file (600 permissions)

### Accessing the Robot

Once connected to home Wi-Fi:

1. Find the robot's IP address:
   ```bash
   # On the robot
   ip addr show wlan1 | grep 'inet '
   
   # Or check your router's DHCP client list
   ```

2. Access the web UI at `http://<robot-ip>:8080`

3. Emergency AP remains accessible at `http://192.168.50.1:8080`

### Single Wi-Fi Interface Mode

If you don't have a USB Wi-Fi adapter, you can use wlan0 for home Wi-Fi:

```bash
cd system
sudo WIFI_INTERFACE="wlan0" ./install-home-wifi.sh
```

**Warning**: This will disable the emergency AP. To restore emergency AP access:

```bash
sudo systemctl stop turbopi-home-wifi.service
sudo systemctl start turbopi-emergency-ap.service
```

### Security Considerations

- **Automatic Password Generation**: The installation script generates a unique, device-specific password
  - Password is derived from machine-id, MAC address, and a fixed salt string ("turbopi-emergency-ap") using SHA256
  - Each device receives a strong, unique 20-character password
  - Password is displayed during installation and should be securely recorded
- **SSID Customization**: Automatically configured during installation
  - The SSID includes the last 4 hex digits of wlan0 MAC address
  - Helps distinguish multiple robots in the same environment
  - Example: `TurboPi-Emergency-EEFF`
- **Password Retrieval**: If you need to retrieve the current password
  - Check `/etc/turbopi/network/hostapd-emergency.conf`
  - Look for the `wpa_passphrase` line
- **Changing Password**: To manually change the emergency AP password
  - Edit `/etc/turbopi/network/hostapd-emergency.conf` and change the `wpa_passphrase` value
  - Use a strong password of 8-63 characters
  - Restart the service: `sudo systemctl restart turbopi-emergency-ap.service`
- The emergency AP is intended for local setup and recovery only
- SSH access should be restricted to development environments
- Consider implementing additional authentication for the web UI

### Troubleshooting

Check service status:
```bash
sudo systemctl status turbopi-emergency-ap.service
```

View logs:
```bash
sudo journalctl -u turbopi-emergency-ap.service -f
```

Check hostapd:
```bash
ps aux | grep hostapd
```

Check dnsmasq:
```bash
ps aux | grep dnsmasq
```

Verify network interface:
```bash
ip addr show wlan0
```

Restart the service:
```bash
sudo systemctl restart turbopi-emergency-ap.service
```
