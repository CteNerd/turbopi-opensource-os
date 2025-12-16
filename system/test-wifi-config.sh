#!/bin/bash
# Validation script for TurboPi Home Wi-Fi Client Configuration
# This script verifies that the installation files are properly structured
# and can be used for basic validation before installation

# Note: Not using 'set -e' because we want to continue testing even if some tests fail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== TurboPi Home Wi-Fi Configuration Validation ==="
echo ""

# Track validation results
PASSED=0
FAILED=0

# Helper function for test results
test_result() {
    local test_name="$1"
    local result="$2"
    
    if [ "$result" -eq 0 ]; then
        echo "✓ $test_name"
        ((PASSED++))
    else
        echo "✗ $test_name"
        ((FAILED++))
    fi
}

# Test 1: Check required files exist
echo "Checking required files..."
test_result "wpa_supplicant-home.conf exists" $([[ -f "$SCRIPT_DIR/network/wpa_supplicant-home.conf" ]] && echo 0 || echo 1)
test_result "setup-home-wifi.sh exists" $([[ -f "$SCRIPT_DIR/network/setup-home-wifi.sh" ]] && echo 0 || echo 1)
test_result "turbopi-home-wifi.service exists" $([[ -f "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" ]] && echo 0 || echo 1)
test_result "install-home-wifi.sh exists" $([[ -f "$SCRIPT_DIR/install-home-wifi.sh" ]] && echo 0 || echo 1)
echo ""

# Test 2: Check scripts are executable
echo "Checking script permissions..."
test_result "setup-home-wifi.sh is executable" $([[ -x "$SCRIPT_DIR/network/setup-home-wifi.sh" ]] && echo 0 || echo 1)
test_result "install-home-wifi.sh is executable" $([[ -x "$SCRIPT_DIR/install-home-wifi.sh" ]] && echo 0 || echo 1)
echo ""

# Test 3: Validate wpa_supplicant config syntax
echo "Validating wpa_supplicant configuration..."
if grep -q "ctrl_interface=" "$SCRIPT_DIR/network/wpa_supplicant-home.conf" && \
   grep -q "country=" "$SCRIPT_DIR/network/wpa_supplicant-home.conf" && \
   grep -q "network={" "$SCRIPT_DIR/network/wpa_supplicant-home.conf" && \
   grep -q "ssid=" "$SCRIPT_DIR/network/wpa_supplicant-home.conf" && \
   grep -q "psk=" "$SCRIPT_DIR/network/wpa_supplicant-home.conf"; then
    test_result "wpa_supplicant config has required fields" 0
else
    test_result "wpa_supplicant config has required fields" 1
fi

if grep -q "YOUR_HOME_SSID" "$SCRIPT_DIR/network/wpa_supplicant-home.conf" && \
   grep -q "YOUR_HOME_PASSWORD" "$SCRIPT_DIR/network/wpa_supplicant-home.conf"; then
    test_result "wpa_supplicant config has placeholders" 0
else
    test_result "wpa_supplicant config has placeholders" 1
fi
echo ""

# Test 4: Validate systemd service syntax
echo "Validating systemd service..."
if grep -q "\[Unit\]" "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" && \
   grep -q "\[Service\]" "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" && \
   grep -q "\[Install\]" "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" && \
   grep -q "ExecStart=" "$SCRIPT_DIR/systemd/turbopi-home-wifi.service" && \
   grep -q "wpa_supplicant" "$SCRIPT_DIR/systemd/turbopi-home-wifi.service"; then
    test_result "systemd service has required sections" 0
else
    test_result "systemd service has required sections" 1
fi

if grep -q "turbopi-emergency-ap.service" "$SCRIPT_DIR/systemd/turbopi-home-wifi.service"; then
    test_result "systemd service depends on emergency AP" 0
else
    test_result "systemd service depends on emergency AP" 1
fi
echo ""

# Test 5: Check setup script has error handling
echo "Validating setup script..."
if grep -q "set -e" "$SCRIPT_DIR/network/setup-home-wifi.sh" && \
   grep -q "trap" "$SCRIPT_DIR/network/setup-home-wifi.sh"; then
    test_result "setup script has error handling" 0
else
    test_result "setup script has error handling" 1
fi

if grep -q "WIFI_INTERFACE" "$SCRIPT_DIR/network/setup-home-wifi.sh"; then
    test_result "setup script supports interface configuration" 0
else
    test_result "setup script supports interface configuration" 1
fi
echo ""

# Test 6: Check install script validation
echo "Validating install script..."
if grep -q "set -e" "$SCRIPT_DIR/install-home-wifi.sh" && \
   grep -q "trap" "$SCRIPT_DIR/install-home-wifi.sh"; then
    test_result "install script has error handling" 0
else
    test_result "install script has error handling" 1
fi

if grep -q "WIFI_SSID" "$SCRIPT_DIR/install-home-wifi.sh" && \
   grep -q "WIFI_PASSWORD" "$SCRIPT_DIR/install-home-wifi.sh"; then
    test_result "install script prompts for credentials" 0
else
    test_result "install script prompts for credentials" 1
fi

if grep -q "sed -i" "$SCRIPT_DIR/install-home-wifi.sh"; then
    test_result "install script updates configuration" 0
else
    test_result "install script updates configuration" 1
fi

if grep -q "chmod 600" "$SCRIPT_DIR/install-home-wifi.sh"; then
    test_result "install script secures config file" 0
else
    test_result "install script secures config file" 1
fi
echo ""

# Test 7: Check for security best practices
echo "Checking security practices..."
# Check that config doesn't have common/weak passwords or real credentials
# Look for placeholder pattern YOUR_HOME_* which should be present in template
if grep -qE 'psk="[^"]{8,}"' "$SCRIPT_DIR/network/wpa_supplicant-home.conf" && \
   ! grep -q 'YOUR_HOME' "$SCRIPT_DIR/network/wpa_supplicant-home.conf"; then
    # Has a real password and no placeholders - likely committed credentials
    test_result "No hardcoded real passwords in config" 1
else
    test_result "No hardcoded real passwords in config" 0
fi

if grep -q "YOUR_HOME_SSID\|YOUR_HOME_PASSWORD" "$SCRIPT_DIR/network/wpa_supplicant-home.conf"; then
    test_result "Config uses placeholder values" 0
else
    test_result "Config uses placeholder values" 1
fi
echo ""

# Test 8: Check separation of concerns (recovery vs operational plane)
echo "Checking network plane separation..."
if grep -q "wlan1" "$SCRIPT_DIR/install-home-wifi.sh" && \
   grep -q "wlan0" "$SCRIPT_DIR/install-home-wifi.sh"; then
    test_result "Install script supports dual interfaces" 0
else
    test_result "Install script supports dual interfaces" 1
fi

if grep -q "Warn if using wlan0" "$SCRIPT_DIR/install-home-wifi.sh" || \
   grep -q "emergency AP will be DISABLED" "$SCRIPT_DIR/install-home-wifi.sh"; then
    test_result "Install script warns about single interface mode" 0
else
    test_result "Install script warns about single interface mode" 1
fi
echo ""

# Summary
echo "==================================="
echo "Validation Results:"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo "==================================="

if [ $FAILED -eq 0 ]; then
    echo "✓ All validation tests passed!"
    exit 0
else
    echo "✗ Some validation tests failed"
    exit 1
fi
