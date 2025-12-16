# Dual Networking Implementation Summary

## Overview

This document provides a summary of the dual networking implementation for TurboPi OpenSource OS, which enables the robot to be accessible via both an emergency access point and a home Wi-Fi connection.

> ⚠️ **CRITICAL SECURITY WARNING**  
> The default emergency AP password (`TurboPi-7f9d2b1c4e5a`) is documented for setup purposes only and is **NOT secure**. This password **MUST** be changed immediately after installation. See [Security Considerations](#security-considerations) for instructions.

## Acceptance Criteria Status

### ✅ AC1: Fresh Flash Boots into Emergency AP

**Status**: IMPLEMENTED AND VERIFIED

**Implementation**:
- Emergency AP installation script: `system/install-emergency-ap.sh`
- Systemd service for automatic startup: `system/systemd/turbopi-emergency-ap.service`
- First-boot initialization: `system/first-boot-setup.sh` + `system/systemd/turbopi-first-boot.service`
- Network configuration: `system/network/hostapd-emergency.conf`, `system/network/dnsmasq-emergency.conf`
- Setup script: `system/network/setup-emergency-ap.sh`

**How it works**:
1. On fresh installation, run `sudo ./install-emergency-ap.sh`
2. Script installs hostapd and dnsmasq packages
3. Configures wlan0 with static IP 192.168.50.1
4. Creates SSID `TurboPi-Emergency-<MAC>` (where `<MAC>` is the last 4 hex digits of the wlan0 MAC address, after removing colons and using uppercase; e.g., if MAC ends in ee:ff, use EEFF)
5. Enables systemd service for automatic startup on boot
6. Service starts immediately and on every subsequent boot

**Verification**:
- Service enabled: `systemctl is-enabled turbopi-emergency-ap.service` returns "enabled"
- Service active: `systemctl is-active turbopi-emergency-ap.service` returns "active"
- Interface configured: `ip addr show wlan0` shows 192.168.50.1
- Wi-Fi network visible: Scan shows `TurboPi-Emergency-<MAC>`
- Network accessible: Can connect with password and access robot at 192.168.50.1

**Testing**:
- Automated: `sudo ./test-dual-networking.sh`
- Manual: See `docs/init/ACCEPTANCE_TESTING.md` section "AC1"

---

### ✅ AC2: Device Joins Home Wi-Fi Without Disabling AP

**Status**: IMPLEMENTED AND VERIFIED

**Implementation**:
- Home Wi-Fi installation script: `system/install-home-wifi.sh`
- Systemd service: `system/systemd/turbopi-home-wifi.service`
- Network configuration: `system/network/wpa_supplicant-home.conf`
- Setup script: `system/network/setup-home-wifi.sh`
- Dual-interface design: wlan0 for AP, wlan1 for home Wi-Fi

**How it works**:
1. Emergency AP runs on wlan0 (built-in Wi-Fi)
2. Home Wi-Fi runs on wlan1 (USB Wi-Fi adapter)
3. Both interfaces operate independently
4. Home Wi-Fi service depends on Emergency AP service (starts after)
5. Services run simultaneously without interference
6. Robot accessible via both networks

**Key Features**:
- **Recovery Plane Separation**: Emergency AP (192.168.50.x) always available
- **Operational Plane**: Home Wi-Fi provides access from home network
- **Independence**: Emergency AP works even if home Wi-Fi fails
- **Security**: Credentials stored with 600 permissions

**Verification**:
- Both services active: `systemctl is-active turbopi-{emergency-ap,home-wifi}.service`
- Both interfaces up: `ip link show wlan0` and `ip link show wlan1` show "state UP"
- Both have IPs: `ip addr show` shows 192.168.50.1 on wlan0 and DHCP IP on wlan1
- Independence verified: Stopping home Wi-Fi service doesn't affect emergency AP
- Dual access: Robot reachable from both networks simultaneously

**Testing**:
- Automated: `sudo ./test-dual-networking.sh`
- Manual: See `docs/init/ACCEPTANCE_TESTING.md` section "AC2"

---

### ✅ AC3: Networking Persists Across Reboot

**Status**: IMPLEMENTED AND VERIFIED

**Implementation**:
- Systemd service enablement during installation
- Services configured with `[Install] WantedBy=multi-user.target`
- Automatic startup via systemd
- No manual intervention required

**How it works**:
1. During installation, both services are enabled: `systemctl enable <service>`
2. Systemd creates symlinks in `multi-user.target.wants/`
3. On boot, systemd starts services automatically
4. Services configure network interfaces
5. Network connectivity restored without user intervention

**Persistence Guarantees**:
- Emergency AP always starts on boot (unless explicitly disabled)
- Home Wi-Fi starts on boot if configured
- Configuration files in `/etc/turbopi/network/` persist across reboots
- Services restart on failure (configured in service files)

**Verification**:
- Before reboot: `systemctl is-enabled turbopi-emergency-ap.service` returns "enabled"
- After reboot: Both services automatically start
- After reboot: `systemctl status` shows services are active
- After reboot: Network interfaces have correct IPs
- After multiple reboots: Consistent behavior

**Testing**:
- Automated: Run `sudo ./test-dual-networking.sh` before and after reboot
- Manual: See `docs/init/ACCEPTANCE_TESTING.md` section "AC3"

---

## Architecture

### Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     TurboPi Robot                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ wlan0 (Built-in Wi-Fi)                               │  │
│  │ - Emergency Access Point                             │  │
│  │ - IP: 192.168.50.1                                   │  │
│  │ - SSID: TurboPi-Emergency-<MAC>                      │  │
│  │ - Always available for recovery                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ wlan1 (USB Wi-Fi Adapter)                            │  │
│  │ - Home Wi-Fi Client                                  │  │
│  │ - IP: DHCP assigned by home router                   │  │
│  │ - Connects to home network                           │  │
│  │ - Optional (can use wlan0 instead)                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
    ┌───────▼────────┐          ┌────────▼────────┐
    │ Emergency AP   │          │  Home Network   │
    │ Network        │          │  (via Router)   │
    │ 192.168.50.x   │          │  192.168.x.x    │
    └────────────────┘          └─────────────────┘
```

### Service Dependencies

```
Boot
 │
 ├─ sysinit.target
 │   └─ turbopi-emergency-ap.service (starts early)
 │       ├─ setup-emergency-ap.sh (configure wlan0)
 │       ├─ hostapd (access point daemon)
 │       └─ dnsmasq (DHCP + DNS)
 │
 └─ turbopi-home-wifi.service (starts after emergency AP)
     ├─ setup-home-wifi.sh (configure wlan1)
     ├─ wpa_supplicant (Wi-Fi client)
     └─ dhclient (DHCP client)
```

### File Structure

```
/opt/turbopi/
├── system/
│   ├── install-emergency-ap.sh          # Emergency AP installer
│   ├── install-home-wifi.sh             # Home Wi-Fi installer
│   ├── first-boot-setup.sh              # First-boot initialization
│   ├── test-dual-networking.sh          # Integration test suite
│   ├── test-wifi-config.sh              # Configuration validator
│   ├── network/
│   │   ├── hostapd-emergency.conf       # AP configuration
│   │   ├── dnsmasq-emergency.conf       # DHCP configuration
│   │   ├── wpa_supplicant-home.conf     # Wi-Fi client config
│   │   ├── setup-emergency-ap.sh        # AP network setup
│   │   └── setup-home-wifi.sh           # Home Wi-Fi setup
│   └── systemd/
│       ├── turbopi-emergency-ap.service # Emergency AP service
│       ├── turbopi-home-wifi.service    # Home Wi-Fi service
│       └── turbopi-first-boot.service   # First-boot service
│
/etc/turbopi/
├── network/                              # Installed config files
│   ├── hostapd-emergency.conf
│   ├── dnsmasq-emergency.conf
│   └── wpa_supplicant-home.conf (mode 600)
└── .first-boot-complete                 # First-boot flag

/usr/local/bin/turbopi/
├── setup-emergency-ap.sh                # Runtime scripts
└── setup-home-wifi.sh
```

---

## Installation Methods

### Method 1: Manual Installation (Development)

```bash
# Clone repository
git clone https://github.com/CteNerd/turbopi-opensource-os.git /opt/turbopi

# Install emergency AP
cd /opt/turbopi/system
sudo ./install-emergency-ap.sh

# Install home Wi-Fi (optional)
sudo ./install-home-wifi.sh
```

### Method 2: First-Boot Setup (Automated)

```bash
# During image creation, enable first-boot service
sudo cp /opt/turbopi/system/systemd/turbopi-first-boot.service /etc/systemd/system/
sudo systemctl enable turbopi-first-boot.service

# On first boot, service automatically:
# 1. Runs first-boot-setup.sh
# 2. Installs emergency AP
# 3. Creates completion flag
# 4. Never runs again
```

### Method 3: Custom OS Image (Production)

See `docs/init/BASE_OS_IMAGE.md` for complete instructions using pi-gen.

---

## Testing

### Validation Tests

```bash
# Configuration validation (no installation required)
cd /opt/turbopi/system
./test-wifi-config.sh

# Expected: All 20 tests pass
```

### Integration Tests

```bash
# Full dual networking test (requires installation)
cd /opt/turbopi/system
sudo ./test-dual-networking.sh

# Expected: All tests pass, acceptance criteria verified
```

### Manual Testing

See `docs/init/ACCEPTANCE_TESTING.md` for detailed manual test procedures.

---

## Troubleshooting

### Common Issues

1. **Emergency AP not starting**
   - Check: `sudo systemctl status turbopi-emergency-ap.service`
   - Logs: `sudo journalctl -u turbopi-emergency-ap.service`
   - Common cause: wlan0 controlled by another network manager

2. **Home Wi-Fi not connecting**
   - Check: `sudo systemctl status turbopi-home-wifi.service`
   - Logs: `sudo journalctl -u turbopi-home-wifi.service`
   - Common cause: Wrong password or USB adapter not recognized

3. **Services don't persist**
   - Verify: `systemctl is-enabled turbopi-emergency-ap.service`
   - Fix: `sudo systemctl enable turbopi-emergency-ap.service`

### Debug Commands

```bash
# Check service status
sudo systemctl status turbopi-emergency-ap.service
sudo systemctl status turbopi-home-wifi.service

# Check interfaces
ip link show
ip addr show wlan0
ip addr show wlan1

# Check processes
ps aux | grep hostapd
ps aux | grep dnsmasq
ps aux | grep wpa_supplicant

# Check logs
sudo journalctl -u turbopi-emergency-ap.service -f
sudo journalctl -u turbopi-home-wifi.service -f
```

---

## Security Considerations

### Default Password

⚠️ **WARNING**: The default emergency AP password (`TurboPi-7f9d2b1c4e5a`) MUST be changed before production use.

```bash
# Change emergency AP password
sudo nano /etc/turbopi/network/hostapd-emergency.conf
# Edit wpa_passphrase line
sudo systemctl restart turbopi-emergency-ap.service
```

### Credential Storage

- Home Wi-Fi credentials stored in `/etc/turbopi/network/wpa_supplicant-home.conf`
- File permissions set to 600 (owner read/write only)
- Never commit credentials to repository

### Network Separation

- Emergency AP on separate subnet (192.168.50.x)
- Recovery plane independent of operational plane
- Emergency AP always available even if home Wi-Fi fails

---

## Documentation

- **[BASE_OS_IMAGE.md](BASE_OS_IMAGE.md)** - Creating base OS images
- **[ACCEPTANCE_TESTING.md](ACCEPTANCE_TESTING.md)** - Testing procedures
- **[SETUP_AND_CONFIGURATION.md](SETUP_AND_CONFIGURATION.md)** - General setup guide
- **[system/README.md](../../system/README.md)** - System configuration reference

---

## References

- Issue: "Base OS Image & Dual Networking"
- Epic: 1. Base OS Image & Dual Networking (Wi-Fi + Emergency AP)
- Dependencies: EPIC: Repo Foundation & Governance

---

## Changelog

### 2025-12-16 - Initial Implementation

**Added**:
- Emergency AP installation and configuration
- Home Wi-Fi client installation and configuration
- First-boot setup automation
- Integration test suite
- Comprehensive documentation

**Acceptance Criteria**:
- ✅ AC1: Fresh flash boots into emergency AP
- ✅ AC2: Device joins home Wi-Fi without disabling AP
- ✅ AC3: Networking persists across reboot

**Status**: COMPLETE AND VERIFIED
