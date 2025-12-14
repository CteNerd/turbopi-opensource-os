# TurboPi System Configuration

This directory contains system-level configuration files for TurboPi OpenSource OS.

## Directory Structure

- `network/` - Network configuration files
- `systemd/` - Systemd service unit files

## Emergency Access Point

The emergency access point provides always-on network access for setup and recovery.

### Network Details

- **SSID**: `TurboPi-Emergency`
- **Password**: `turbopi123`
- **Robot IP**: `192.168.50.1`
- **DHCP Range**: `192.168.50.10` - `192.168.50.50`
- **Subnet**: `192.168.50.0/24`

### Features

- Separate subnet to avoid conflicts with home Wi-Fi networks
- Survives system reboots
- Enables access to web UI and SSH (dev mode only)

### Installation

1. Install required packages:
   ```bash
   sudo apt-get update
   sudo apt-get install hostapd dnsmasq
   ```

2. Copy configuration files:
   ```bash
   sudo mkdir -p /etc/turbopi/network
   sudo mkdir -p /usr/local/bin/turbopi
   
   sudo cp system/network/hostapd-emergency.conf /etc/turbopi/network/
   sudo cp system/network/dnsmasq-emergency.conf /etc/turbopi/network/
   sudo cp system/network/setup-emergency-ap.sh /usr/local/bin/turbopi/
   sudo chmod +x /usr/local/bin/turbopi/setup-emergency-ap.sh
   ```

3. Install and enable the systemd service:
   ```bash
   sudo cp system/systemd/turbopi-emergency-ap.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable turbopi-emergency-ap.service
   sudo systemctl start turbopi-emergency-ap.service
   ```

4. Verify the service is running:
   ```bash
   sudo systemctl status turbopi-emergency-ap.service
   ```

### Accessing the Robot

Once the emergency AP is active:

1. Connect to the `TurboPi-Emergency` Wi-Fi network using password `turbopi123`
2. Open a web browser and navigate to `http://192.168.50.1:8080`
3. For SSH access (development): `ssh pi@192.168.50.1`

### Dual Networking

The emergency AP runs on `wlan0` by default. For home Wi-Fi connectivity:

- Use a second Wi-Fi adapter on `wlan1`, or
- Configure `wlan0` to connect to home Wi-Fi after initial setup (emergency AP will be disabled)

The recommended approach is to use a USB Wi-Fi adapter for home network connectivity while keeping the built-in Wi-Fi for the emergency AP.

### Security Considerations

- The default password (`turbopi123`) should be changed for production use
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
