# Runtime Service Skeleton - Acceptance Testing

This document provides acceptance testing procedures for the Runtime Service Skeleton epic.

## Acceptance Criteria

### AC1: API, UI, updater start on boot
**Requirement**: Services must be enabled and start automatically on system boot.

### AC2: config.env loaded via systemd
**Requirement**: All services must load configuration from `/etc/turbopi/config.env` via systemd EnvironmentFile directive.

### AC3: Health endpoint available
**Requirement**: API service must provide a `/health` endpoint that returns system status.

---

## Testing Procedure

### Prerequisites

1. Raspberry Pi or compatible system running Raspberry Pi OS (Debian-based)
2. Python 3 installed (pre-installed on Raspberry Pi OS)
3. Root access
4. TurboPi repository cloned

### Installation

1. Navigate to the system directory:
   ```bash
   cd turbopi-opensource-os/system
   ```

2. Run the installation script:
   ```bash
   sudo ./install-services.sh
   ```

3. Verify installation completed without errors:
   - Check for "Installation complete!" message
   - Review any warnings or errors in output

### Test 1: Configuration File

**Verifies AC2**

1. Check configuration file exists:
   ```bash
   ls -la /etc/turbopi/config.env
   ```
   **Expected**: File exists with 640 permissions (root:turbopi, group read-only)

2. Verify content:
   ```bash
   cat /etc/turbopi/config.env
   ```
   **Expected**: File contains configuration variables (ROBOT_NAME, API_PORT, etc.)

3. Confirm systemd will load it:
   ```bash
   grep EnvironmentFile /etc/systemd/system/turbopi-api.service
   ```
   **Expected**: `EnvironmentFile=/etc/turbopi/config.env`

**Result**: ✅ Pass / ❌ Fail

---

### Test 2: Service Installation

**Verifies AC1 (Part 1)**

1. Check service files installed:
   ```bash
   ls -la /etc/systemd/system/turbopi-*.service
   ```
   **Expected**: Three service files exist
   - turbopi-api.service
   - turbopi-ui.service
   - turbopi-updater.service

2. Verify services are enabled:
   ```bash
   systemctl is-enabled turbopi-api.service
   systemctl is-enabled turbopi-ui.service
   systemctl is-enabled turbopi-updater.service
   ```
   **Expected**: All return "enabled"

**Result**: ✅ Pass / ❌ Fail

---

### Test 3: Service Startup

**Verifies AC1 (Part 2)**

1. Start all services:
   ```bash
   sudo systemctl start turbopi-api.service
   sudo systemctl start turbopi-ui.service
   sudo systemctl start turbopi-updater.service
   ```

2. Check service status:
   ```bash
   sudo systemctl status turbopi-api.service
   sudo systemctl status turbopi-ui.service
   sudo systemctl status turbopi-updater.service
   ```
   **Expected**: All services show "active (running)"

3. Check for errors in logs:
   ```bash
   sudo journalctl -u turbopi-api.service -n 20
   sudo journalctl -u turbopi-ui.service -n 20
   sudo journalctl -u turbopi-updater.service -n 20
   ```
   **Expected**: No error messages, services started successfully

**Result**: ✅ Pass / ❌ Fail

---

### Test 4: Health Endpoint

**Verifies AC3**

1. Test health endpoint:
   ```bash
   curl -s http://localhost:8080/health
   ```
   **Expected**: JSON response with status, uptime, cpu_temp, version, timestamp

2. Verify JSON structure:
   ```bash
   curl -s http://localhost:8080/health | python3 -m json.tool
   ```
   **Expected**: Valid JSON with all required fields

3. Check response code:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health
   ```
   **Expected**: 200

4. Verify health endpoint reflects configuration:
   ```bash
   curl -s http://localhost:8080/health | grep version
   ```
   **Expected**: Contains version from config.env

**Result**: ✅ Pass / ❌ Fail

---

### Test 5: Configuration Loading

**Verifies AC2 (Validation)**

1. Check API service logs for configuration:
   ```bash
   sudo journalctl -u turbopi-api.service | grep "Robot Name:"
   ```
   **Expected**: Shows robot name from config.env

2. Check UI service logs for configuration:
   ```bash
   sudo journalctl -u turbopi-ui.service | grep "Robot Name:"
   ```
   **Expected**: Shows robot name from config.env

3. Check updater service logs for configuration:
   ```bash
   sudo journalctl -u turbopi-updater.service | grep "Robot Name:"
   ```
   **Expected**: Shows robot name from config.env

4. Modify configuration:
   ```bash
   sudo sed -i 's/ROBOT_NAME=.*/ROBOT_NAME=TestBot/' /etc/turbopi/config.env
   ```

5. Restart services:
   ```bash
   sudo systemctl restart turbopi-api.service
   sudo systemctl restart turbopi-ui.service
   sudo systemctl restart turbopi-updater.service
   ```

6. Verify new configuration loaded:
   ```bash
   sudo journalctl -u turbopi-api.service -n 10 | grep "Robot Name: TestBot"
   ```
   **Expected**: Shows "Robot Name: TestBot"

**Result**: ✅ Pass / ❌ Fail

---

### Test 6: Web UI

1. Access UI in browser:
   ```
   http://localhost:8081/
   ```
   **Expected**: Status dashboard page loads

2. Verify content:
   - Page title contains robot name
   - Shows API service status
   - Shows UI service status
   - Shows configuration status

**Result**: ✅ Pass / ❌ Fail

---

### Test 7: Boot Persistence

**Verifies AC1 (Final Validation)**

1. Reboot the system:
   ```bash
   sudo reboot
   ```

2. After reboot, check services started automatically:
   ```bash
   sudo systemctl status turbopi-api.service
   sudo systemctl status turbopi-ui.service
   sudo systemctl status turbopi-updater.service
   ```
   **Expected**: All services "active (running)"

3. Verify health endpoint available:
   ```bash
   curl -s http://localhost:8080/health
   ```
   **Expected**: Valid JSON response

**Result**: ✅ Pass / ❌ Fail

---

### Test 8: Automated Test Suite

Run the automated test suite:

```bash
cd system
sudo ./test-services.sh
```

**Expected Output**:
- All tests pass
- Acceptance criteria summary shows all ✓
- Exit code 0

**Result**: ✅ Pass / ❌ Fail

---

## Acceptance Criteria Summary

### ✅ AC1: API, UI, updater start on boot
**Verified by**:
- Test 2: Services installed and enabled
- Test 3: Services can start successfully
- Test 7: Services start automatically after reboot

**Status**: ⬜ Pass / ⬜ Fail

---

### ✅ AC2: config.env loaded via systemd
**Verified by**:
- Test 1: Configuration file exists and accessible
- Test 5: Services load configuration from config.env
- Configuration changes reflected after restart

**Status**: ⬜ Pass / ⬜ Fail

---

### ✅ AC3: Health endpoint available
**Verified by**:
- Test 4: Health endpoint responds with valid JSON
- Returns required fields (status, uptime, cpu_temp, version, timestamp)
- HTTP 200 response code
- Endpoint accessible after reboot

**Status**: ⬜ Pass / ⬜ Fail

---

## Troubleshooting

### Service Won't Start

If a service fails to start:

1. Check detailed status:
   ```bash
   sudo systemctl status turbopi-api.service -l
   ```

2. View recent logs:
   ```bash
   sudo journalctl -u turbopi-api.service -n 50
   ```

3. Check Python syntax:
   ```bash
   python3 -m py_compile /opt/turbopi/current/src/api/main.py
   ```

4. Verify permissions:
   ```bash
   ls -la /opt/turbopi/current/bin/api
   ls -la /opt/turbopi/current/src/api/main.py
   ```

### Port Already in Use

If port 8080 or 8081 is already in use:

1. Find process using port:
   ```bash
   sudo netstat -tulpn | grep 8080
   ```

2. Option A: Stop conflicting service
3. Option B: Change port in config.env:
   ```bash
   sudo nano /etc/turbopi/config.env
   # Change API_PORT or UI_PORT
   sudo systemctl restart turbopi-api.service
   ```

### Configuration Not Loading

If configuration changes don't take effect:

1. Verify config file format (no syntax errors)
2. Restart services after config changes
3. Check file permissions (should be 660, owner root:turbopi, group read-write)
4. Verify systemd EnvironmentFile directive in service files

---

## Test Results Template

```
Date: _______________
Tester: _____________
System: _____________

Test 1 - Configuration File:        [ ] Pass  [ ] Fail
Test 2 - Service Installation:      [ ] Pass  [ ] Fail
Test 3 - Service Startup:            [ ] Pass  [ ] Fail
Test 4 - Health Endpoint:            [ ] Pass  [ ] Fail
Test 5 - Configuration Loading:      [ ] Pass  [ ] Fail
Test 6 - Web UI:                     [ ] Pass  [ ] Fail
Test 7 - Boot Persistence:           [ ] Pass  [ ] Fail
Test 8 - Automated Test Suite:       [ ] Pass  [ ] Fail

AC1 - Start on Boot:                 [ ] Pass  [ ] Fail
AC2 - Config Loading:                [ ] Pass  [ ] Fail
AC3 - Health Endpoint:               [ ] Pass  [ ] Fail

Notes:
_____________________________________
_____________________________________
_____________________________________
```

---

## References

- [Runtime Service Skeleton Documentation](RUNTIME_SERVICE_SKELETON.md)
- [Service Implementations](../../src/README.md)
- [System Configuration](../../system/README.md)
- [API Specification](../api/OPENAPI.yaml)
