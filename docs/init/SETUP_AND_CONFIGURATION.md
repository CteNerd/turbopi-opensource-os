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

## Emergency Access Point

The TurboPi system includes an always-on emergency access point for setup and recovery.

### Network Configuration

- **SSID**: `TurboPi-Emergency`
- **Password**: `turbopi123` (should be changed in production)
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

### Dual Networking Options

**Option 1: USB Wi-Fi Adapter (Recommended)**
- Built-in Wi-Fi (`wlan0`) runs emergency AP
- USB Wi-Fi adapter (`wlan1`) connects to home network
- Both networks active simultaneously

**Option 2: Single Wi-Fi Interface**
- Emergency AP active by default
- Can be disabled after connecting to home Wi-Fi
- User must re-enable AP for recovery if home network fails

## Configuration Rules

- Secrets never stored in repo
- Secrets never exposed to browser JS
- All services load config via systemd
