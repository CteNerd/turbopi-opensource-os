# Acceptance Testing for Base OS Image & Dual Networking

This document describes how to verify that the acceptance criteria for the Base OS Image & Dual Networking feature are met.

> ⚠️ **CRITICAL SECURITY WARNING**  
> The default emergency AP password (`TurboPi-7f9d2b1c4e5a`) referenced in this document is for testing and initial setup only. This password is publicly documented and **MUST** be changed immediately after first connection. **Never use the default password in production.**

## Prerequisites

- Raspberry Pi 3 or later with built-in Wi-Fi
- SD card (16GB or larger)
- USB Wi-Fi adapter (recommended for dual networking)
- Computer for flashing and testing
- Access to a home Wi-Fi network

## Acceptance Criteria

### AC1: Fresh Flash Boots into Emergency AP

**Objective**: Verify that a freshly flashed OS image automatically boots with the emergency access point active.

#### Test Procedure

1. **Prepare Fresh SD Card**
   ```bash
   # Flash Raspberry Pi OS Lite to SD card
   # Use Raspberry Pi Imager or dd command
   ```

2. **Install TurboPi Repository**
   ```bash
   # On the Raspberry Pi after first boot
   sudo apt-get update
   sudo apt-get install -y git
   sudo mkdir -p /opt/turbopi
   sudo chown $USER:$USER /opt/turbopi
   git clone https://github.com/CteNerd/turbopi-opensource-os.git /opt/turbopi
   ```

3. **Install Emergency AP**
   ```bash
   cd /opt/turbopi/system
   sudo ./install-emergency-ap.sh
   ```

4. **Verify Service Status**
   ```bash
   sudo systemctl status turbopi-emergency-ap.service
   ```
   
   **Expected Output**: Service should be "active (running)"

5. **Verify Network Interface**
   ```bash
   ip addr show wlan0
   ```
   
   **Expected Output**: Interface should have IP address 192.168.50.1

6. **Scan for Wi-Fi Network**
   ```bash
   # On another device (phone, laptop)
   # Scan for Wi-Fi networks
   ```
   
   **Expected Output**: Should see network named `TurboPi-Emergency-<MAC>` where `<MAC>` is the last 4 hex digits after removing colons from the wlan0 MAC address (e.g., if MAC ends in ee:ff, use EEFF)

7. **Connect to Emergency AP**
   - SSID: `TurboPi-Emergency-<MAC>`
   - Password: `TurboPi-7f9d2b1c4e5a`
   
   **Expected Result**: Successful connection

8. **Access Web UI**
   ```bash
   # On connected device, open browser to:
   http://192.168.50.1:8080
   ```
   
   **Expected Result**: Web UI should be accessible (or connection should be successful if UI is not yet implemented)

9. **Verify Boot Persistence**
   ```bash
   sudo reboot
   ```
   
   After reboot, repeat steps 4-7 to verify the emergency AP comes up automatically.

#### Success Criteria

- ✅ Emergency AP service starts automatically on boot
- ✅ wlan0 interface configured with 192.168.50.1
- ✅ Wi-Fi network visible and connectable
- ✅ Robot accessible at 192.168.50.1
- ✅ Configuration persists after reboot

#### Automated Test

Run the integration test:
```bash
cd /opt/turbopi/system
sudo ./test-dual-networking.sh
```

The test will verify:
- Configuration files are installed
- Services are enabled and running
- Network interfaces are configured correctly
- Processes (hostapd, dnsmasq) are running

---

### AC2: Device Joins Home Wi-Fi Without Disabling AP

**Objective**: Verify that the robot can connect to a home Wi-Fi network while keeping the emergency AP active.

#### Test Procedure

1. **Verify Emergency AP is Running**
   ```bash
   sudo systemctl status turbopi-emergency-ap.service
   ip addr show wlan0 | grep 192.168.50.1
   ```
   
   **Expected Output**: Service active, IP configured

2. **Connect USB Wi-Fi Adapter**
   - Insert USB Wi-Fi adapter into Raspberry Pi
   - Verify it's detected:
     ```bash
     ip link show wlan1
     ```
   
   **Expected Output**: wlan1 interface should be present

3. **Install Home Wi-Fi Client**
   ```bash
   cd /opt/turbopi/system
   sudo ./install-home-wifi.sh
   ```
   
   When prompted:
   - Enter your home Wi-Fi SSID
   - Enter your home Wi-Fi password
   - Select interface: wlan1 (default)

4. **Verify Home Wi-Fi Service**
   ```bash
   sudo systemctl status turbopi-home-wifi.service
   ```
   
   **Expected Output**: Service should be "active (running)"

5. **Verify Both Interfaces Active**
   ```bash
   # Check emergency AP interface
   ip addr show wlan0
   
   # Check home Wi-Fi interface
   ip addr show wlan1
   ```
   
   **Expected Output**:
   - wlan0: Should have IP 192.168.50.1
   - wlan1: Should have DHCP-assigned IP from home network

6. **Verify Both Services Running**
   ```bash
   sudo systemctl is-active turbopi-emergency-ap.service
   sudo systemctl is-active turbopi-home-wifi.service
   ```
   
   **Expected Output**: Both should return "active"

7. **Test Emergency AP Access**
   ```bash
   # From another device on emergency AP network (192.168.50.x)
   ping 192.168.50.1
   ```
   
   **Expected Result**: Successful ping

8. **Test Home Network Access**
   ```bash
   # From another device on home network
   ping <wlan1-ip>
   ```
   
   **Expected Result**: Successful ping

9. **Verify Independence**
   ```bash
   # Stop home Wi-Fi service
   sudo systemctl stop turbopi-home-wifi.service
   
   # Verify emergency AP still active
   sudo systemctl is-active turbopi-emergency-ap.service
   ping 192.168.50.1  # From device on emergency AP network
   ```
   
   **Expected Result**: Emergency AP continues to work

10. **Restart Home Wi-Fi**
    ```bash
    sudo systemctl start turbopi-home-wifi.service
    ```

#### Success Criteria

- ✅ Emergency AP remains active on wlan0
- ✅ Home Wi-Fi connects successfully on wlan1
- ✅ Both interfaces have IP addresses
- ✅ Both services running simultaneously
- ✅ Robot accessible via both networks
- ✅ Emergency AP works independently of home Wi-Fi

#### Automated Test

Run the integration test:
```bash
cd /opt/turbopi/system
sudo ./test-dual-networking.sh
```

The test will verify dual networking setup and independence.

---

### AC3: Networking Persists Across Reboot

**Objective**: Verify that both the emergency AP and home Wi-Fi connection automatically start after a system reboot.

#### Test Procedure

1. **Verify Initial State**
   ```bash
   # Before reboot, verify both services are running
   sudo systemctl is-active turbopi-emergency-ap.service
   sudo systemctl is-active turbopi-home-wifi.service
   
   # Verify both are enabled for boot
   sudo systemctl is-enabled turbopi-emergency-ap.service
   sudo systemctl is-enabled turbopi-home-wifi.service
   ```
   
   **Expected Output**: Both should be "active" and "enabled"

2. **Note Current Network State**
   ```bash
   # Record IPs before reboot
   ip addr show wlan0 | grep "inet "
   ip addr show wlan1 | grep "inet "
   ```

3. **Reboot System**
   ```bash
   sudo reboot
   ```

4. **Wait for Boot** (approximately 60-90 seconds)

5. **Verify Emergency AP Restored**
   ```bash
   # After reboot, check service status
   sudo systemctl status turbopi-emergency-ap.service
   
   # Verify interface and IP
   ip addr show wlan0 | grep 192.168.50.1
   ```
   
   **Expected Output**: Service active, IP configured

6. **Verify Home Wi-Fi Restored**
   ```bash
   # Check service status
   sudo systemctl status turbopi-home-wifi.service
   
   # Verify interface and IP
   ip addr show wlan1 | grep "inet "
   ```
   
   **Expected Output**: Service active, IP assigned

7. **Test Connectivity from Both Networks**
   ```bash
   # From device on emergency AP network
   ping 192.168.50.1
   
   # From device on home network
   ping <wlan1-ip>
   ```
   
   **Expected Result**: Both pings successful

8. **Verify No Manual Intervention Needed**
   - Confirm that no commands were run after reboot
   - Services started automatically
   - No configuration changes required

9. **Test Multiple Reboots**
   ```bash
   # Reboot 2-3 more times to ensure consistency
   sudo reboot
   # Wait and verify again
   ```
   
   **Expected Result**: Networking comes up automatically every time

#### Success Criteria

- ✅ Emergency AP service starts automatically after reboot
- ✅ Home Wi-Fi service starts automatically after reboot
- ✅ wlan0 configured with 192.168.50.1
- ✅ wlan1 obtains DHCP IP from home network
- ✅ No manual intervention required
- ✅ Consistent behavior across multiple reboots

#### Automated Test

Run the integration test after reboot:
```bash
cd /opt/turbopi/system
sudo ./test-dual-networking.sh
```

---

## Comprehensive Test Checklist

Use this checklist to verify all acceptance criteria:

### Pre-Installation
- [ ] Fresh Raspberry Pi OS installed on SD card
- [ ] USB Wi-Fi adapter available (for dual networking)
- [ ] Access to home Wi-Fi network

### AC1: Fresh Flash Boots into Emergency AP
- [ ] Emergency AP installation script runs successfully
- [ ] Service enabled: `systemctl is-enabled turbopi-emergency-ap.service`
- [ ] Service active: `systemctl is-active turbopi-emergency-ap.service`
- [ ] wlan0 has IP 192.168.50.1: `ip addr show wlan0`
- [ ] Wi-Fi network visible: `TurboPi-Emergency-<MAC>`
- [ ] Can connect to emergency AP with default password
- [ ] Can access robot at 192.168.50.1
- [ ] Configuration survives reboot

### AC2: Device Joins Home Wi-Fi Without Disabling AP
- [ ] USB Wi-Fi adapter detected as wlan1
- [ ] Home Wi-Fi installation script runs successfully
- [ ] Home Wi-Fi service enabled: `systemctl is-enabled turbopi-home-wifi.service`
- [ ] Home Wi-Fi service active: `systemctl is-active turbopi-home-wifi.service`
- [ ] wlan1 has DHCP IP: `ip addr show wlan1`
- [ ] Emergency AP still running: `systemctl is-active turbopi-emergency-ap.service`
- [ ] wlan0 still has IP 192.168.50.1
- [ ] Can connect to robot via emergency AP
- [ ] Can connect to robot via home network IP
- [ ] Emergency AP works when home Wi-Fi stopped

### AC3: Networking Persists Across Reboot
- [ ] Both services enabled for boot
- [ ] System reboots successfully
- [ ] Emergency AP comes up automatically
- [ ] Home Wi-Fi comes up automatically
- [ ] wlan0 has correct IP after reboot
- [ ] wlan1 obtains DHCP IP after reboot
- [ ] Can connect via both networks after reboot
- [ ] No manual intervention required
- [ ] Consistent across multiple reboots

### Integration Test
- [ ] `test-dual-networking.sh` runs without errors
- [ ] All test assertions pass
- [ ] Acceptance criteria verification passes

---

## Troubleshooting Failed Tests

### Emergency AP Not Starting

**Symptoms**: Service fails to start or wlan0 has no IP

**Debug Steps**:
```bash
sudo systemctl status turbopi-emergency-ap.service
sudo journalctl -u turbopi-emergency-ap.service
ps aux | grep hostapd
ps aux | grep dnsmasq
```

**Common Issues**:
- wlan0 controlled by other network manager (NetworkManager, dhcpcd)
- Conflicting services using same interface
- Hardware not supported
- Channel conflicts

**Solutions**:
- Disable conflicting network managers
- Check hardware compatibility
- Try different Wi-Fi channel in `/etc/turbopi/network/hostapd-emergency.conf`

### Home Wi-Fi Not Connecting

**Symptoms**: wlan1 has no IP or service fails

**Debug Steps**:
```bash
sudo systemctl status turbopi-home-wifi.service
sudo journalctl -u turbopi-home-wifi.service
wpa_cli -i wlan1 status
```

**Common Issues**:
- Wrong password in `/etc/turbopi/network/wpa_supplicant-home.conf`
- USB adapter not recognized
- Router MAC filtering or client limit

**Solutions**:
- Verify credentials
- Check USB adapter compatibility
- Verify router settings allow new clients

### Services Don't Start After Reboot

**Symptoms**: Must manually start services after reboot

**Debug Steps**:
```bash
sudo systemctl is-enabled turbopi-emergency-ap.service
sudo systemctl is-enabled turbopi-home-wifi.service
systemctl list-dependencies multi-user.target | grep turbopi
```

**Common Issues**:
- Services not enabled
- Systemd ordering issues

**Solutions**:
```bash
sudo systemctl enable turbopi-emergency-ap.service
sudo systemctl enable turbopi-home-wifi.service
sudo systemctl daemon-reload
```

---

## Reporting Test Results

When reporting test results, include:

1. **Hardware Configuration**
   - Raspberry Pi model
   - Built-in Wi-Fi chipset
   - USB Wi-Fi adapter model (if used)

2. **Software Versions**
   ```bash
   cat /etc/os-release
   git -C /opt/turbopi log -1 --oneline
   ```

3. **Test Results**
   - Which acceptance criteria passed/failed
   - Output from `test-dual-networking.sh`
   - Any error messages from systemctl/journalctl

4. **Network Configuration**
   ```bash
   ip link show
   ip addr show
   sudo systemctl status turbopi-*
   ```

---

## References

- [Base OS Image Creation Guide](BASE_OS_IMAGE.md)
- [System Configuration](../../system/README.md)
- [Setup and Configuration](SETUP_AND_CONFIGURATION.md)
