# Setup & Configuration

## First Boot Experience

1. Bot boots into AP mode
2. User connects to Setup UI
3. Wizard collects:
   - Wi-Fi credentials
   - API keys
   - Wake word
4. Config written to `/etc/turbopi/config.env`
5. Services restarted automatically

For information on creating a base OS image with the emergency AP pre-configured, see [BASE_OS_IMAGE.md](BASE_OS_IMAGE.md).

## Emergency Access Point

The TurboPi system includes an always-on emergency access point for setup and recovery.

### Network Configuration

- **SSID**: `TurboPi-Emergency-<XXXX>` (where `<XXXX>` is the last 4 hex digits of the `wlan0` MAC address, colons removed; e.g., `EEFF` from `aa:bb:cc:dd:ee:ff`)
- **Password**: `TurboPi-7f9d2b1c4e5a` (default - must be changed in production)
- **Robot IP**: `192.168.50.1`
- **DHCP Range**: `192.168.50.10` - `192.168.50.50`
- **Subnet**: `192.168.50.0/24`

### Key Features

- **Separate Subnet**: Uses `192.168.50.x` to avoid conflicts with common home networks (`192.168.0.x`, `192.168.1.x`)
- **Survives Reboot**: Automatically starts on system boot via systemd
- **Always Available**: Provides fallback access even if home Wi-Fi fails
- **Dual Access**: UI reachable at `http://192.168.50.1:8080`, SSH at `192.168.50.1` (dev only)

### Implementation

The emergency AP is implemented using:
- `hostapd` for access point functionality
- `dnsmasq` for DHCP and DNS services
- `systemd` service for automatic startup
- See `/system/README.md` for installation instructions

### Home Wi-Fi Connection

The robot can connect to your home Wi-Fi network while keeping the emergency AP available for recovery.

**Automated Setup (Recommended)**

```bash
cd system
sudo ./install-home-wifi.sh
```

This script will:
- Prompt for your home Wi-Fi SSID and password
- Configure automatic connection on boot
- Keep the emergency AP active (if using USB Wi-Fi adapter)

**Dual Networking Options**

**Option 1: USB Wi-Fi Adapter (Recommended)**
- Built-in Wi-Fi (`wlan0`) runs emergency AP at `192.168.50.1`
- USB Wi-Fi adapter (`wlan1`) connects to home network via DHCP
- Both networks active simultaneously
- Robot accessible via both IPs
- Emergency AP always available for recovery

**Option 2: Single Wi-Fi Interface**
- Use `wlan0` for home Wi-Fi (disables emergency AP)
- Set `WIFI_INTERFACE=wlan0` during installation
- Emergency AP must be manually re-enabled if home network fails
- Not recommended for production use

### Network Persistence

Once configured, the home Wi-Fi connection:
- Persists across reboots (systemd service auto-starts)
- Automatically reconnects if connection drops
- Does not interfere with emergency AP (when using separate interface)
- Uses DHCP for automatic IP assignment

## Configuration Rules

- Secrets never stored in repo
- Secrets never exposed to browser JS
- All services load config via systemd

## Motor HAL Backend Configuration

Motor output remains routed through the control arbiter and HAL. Select backend in
`/etc/turbopi/config.env`:

- `HAL_MOTOR_BACKEND=sim` for simulation (default)
- `HAL_MOTOR_BACKEND=vendor` for Hiwonder vendor SDK on target robot
- `HAL_MOTOR_VENDOR_REQUIRED=true` to fail startup if vendor SDK is unavailable

Field-hardening controls:

- `HAL_MOTOR_MAX_DUTY` caps duty output (1-100)
- `HAL_MOTOR_DISABLED_CHANNELS` can disable known-bad channels (example `3`)
- `HAL_MOTOR_BLOCK_ON_DISABLED_CHANNELS=true` fail-safes by rejecting non-zero
   motion commands that would energize a disabled channel
- `HAL_MOTOR_CHANNEL_SCALE_1..4` provides optional per-wheel tuning multipliers
   for minor variance after bench validation

Control diagnostics now expose motor runtime status at `/control/state`:

- `motor_backend`
- `motor_disabled_channels`
- `motor_degraded`
- `motor_degraded_reason`
