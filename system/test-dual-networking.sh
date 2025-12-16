#!/bin/bash
# Integration test for TurboPi Dual Networking
# This script validates that the acceptance criteria for dual networking are met
#
# Note: Not using 'set -e' because we want to continue testing even if some
# commands fail, to provide a complete test report. Each test is explicitly
# checked and results are tracked.

set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Test result tracking
test_pass() {
    local test_name="$1"
    echo -e "  ${GREEN}[PASS]${NC} $test_name"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

test_fail() {
    local test_name="$1"
    local reason="$2"
    echo -e "  ${RED}[FAIL]${NC} $test_name"
    if [ -n "$reason" ]; then
        echo "    Reason: $reason"
    fi
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

# Test functions
test_emergency_ap_files() {
    log_info "Testing Emergency AP files exist..."
    
    if [ -f "/etc/turbopi/network/hostapd-emergency.conf" ]; then
        test_pass "hostapd-emergency.conf exists"
    else
        test_fail "hostapd-emergency.conf exists" "File not found"
    fi
    
    if [ -f "/etc/turbopi/network/dnsmasq-emergency.conf" ]; then
        test_pass "dnsmasq-emergency.conf exists"
    else
        test_fail "dnsmasq-emergency.conf exists" "File not found"
    fi
    
    if [ -f "/usr/local/bin/turbopi/setup-emergency-ap.sh" ]; then
        test_pass "setup-emergency-ap.sh exists"
    else
        test_fail "setup-emergency-ap.sh exists" "File not found"
    fi
    
    if [ -x "/usr/local/bin/turbopi/setup-emergency-ap.sh" ]; then
        test_pass "setup-emergency-ap.sh is executable"
    else
        test_fail "setup-emergency-ap.sh is executable" "File not executable"
    fi
}

test_emergency_ap_service() {
    log_info "Testing Emergency AP systemd service..."
    
    if [ -f "/etc/systemd/system/turbopi-emergency-ap.service" ]; then
        test_pass "turbopi-emergency-ap.service exists"
    else
        test_fail "turbopi-emergency-ap.service exists" "File not found"
        return
    fi
    
    if systemctl is-enabled turbopi-emergency-ap.service > /dev/null 2>&1; then
        test_pass "Emergency AP service is enabled"
    else
        test_fail "Emergency AP service is enabled" "Service not enabled"
    fi
    
    if systemctl is-active turbopi-emergency-ap.service > /dev/null 2>&1; then
        test_pass "Emergency AP service is active"
    else
        test_fail "Emergency AP service is active" "Service not running"
    fi
}

test_emergency_ap_interface() {
    log_info "Testing Emergency AP network interface..."
    
    if ip link show wlan0 > /dev/null 2>&1; then
        test_pass "wlan0 interface exists"
        
        if ip link show wlan0 | grep -qw "state UP"; then
            test_pass "wlan0 interface is UP"
        else
            test_fail "wlan0 interface is UP" "Interface is DOWN"
        fi
        
        if ip addr show wlan0 | grep -q "192.168.50.1"; then
            test_pass "wlan0 has IP 192.168.50.1"
        else
            test_fail "wlan0 has IP 192.168.50.1" "IP not assigned"
        fi
    else
        test_fail "wlan0 interface exists" "Interface not found"
    fi
}

test_emergency_ap_processes() {
    log_info "Testing Emergency AP processes..."
    
    if pgrep -f "hostapd.*emergency" > /dev/null 2>&1; then
        test_pass "hostapd process is running"
    else
        test_fail "hostapd process is running" "Process not found"
    fi
    
    if pgrep -f "dnsmasq.*emergency" > /dev/null 2>&1; then
        test_pass "dnsmasq process is running"
    else
        test_fail "dnsmasq process is running" "Process not found"
    fi
}

test_home_wifi_files() {
    log_info "Testing Home Wi-Fi files (if configured)..."
    
    if [ -f "/etc/turbopi/network/wpa_supplicant-home.conf" ]; then
        test_pass "wpa_supplicant-home.conf exists"
        
        # Check permissions (should be 600)
        perms=$(stat -c %a /etc/turbopi/network/wpa_supplicant-home.conf)
        if [ "$perms" = "600" ]; then
            test_pass "wpa_supplicant-home.conf has secure permissions (600)"
        else
            test_fail "wpa_supplicant-home.conf has secure permissions" "Has $perms, should be 600"
        fi
    else
        log_warn "Home Wi-Fi not configured (wpa_supplicant-home.conf not found)"
    fi
    
    if [ -f "/usr/local/bin/turbopi/setup-home-wifi.sh" ]; then
        test_pass "setup-home-wifi.sh exists"
    else
        test_fail "setup-home-wifi.sh exists" "File not found"
    fi
}

test_home_wifi_service() {
    log_info "Testing Home Wi-Fi service (if configured)..."
    
    if [ -f "/etc/systemd/system/turbopi-home-wifi.service" ]; then
        test_pass "turbopi-home-wifi.service exists"
        
        if systemctl is-enabled turbopi-home-wifi.service > /dev/null 2>&1; then
            test_pass "Home Wi-Fi service is enabled"
            
            if systemctl is-active turbopi-home-wifi.service > /dev/null 2>&1; then
                test_pass "Home Wi-Fi service is active"
            else
                log_warn "Home Wi-Fi service not active (may not be connected)"
            fi
        else
            log_warn "Home Wi-Fi service not enabled"
        fi
    else
        log_warn "Home Wi-Fi service not installed"
    fi
}

test_home_wifi_interface() {
    log_info "Testing Home Wi-Fi interface (if configured)..."
    
    if ip link show wlan1 > /dev/null 2>&1; then
        test_pass "wlan1 interface exists"
        
        if ip link show wlan1 | grep -qw "state UP"; then
            test_pass "wlan1 interface is UP"
            
            # Check if it has an IP address (DHCP assigned)
            if ip addr show wlan1 | grep -q "inet "; then
                local ip=$(ip addr show wlan1 | grep "inet " | awk '{print $2}')
                test_pass "wlan1 has IP address: $ip"
            else
                test_fail "wlan1 has IP address" "No IP assigned"
            fi
        else
            log_warn "wlan1 interface is DOWN (may not be connected)"
        fi
    else
        log_warn "wlan1 interface not found (USB adapter may not be present)"
    fi
}

test_dual_networking_independence() {
    log_info "Testing dual networking independence..."
    
    # Both services should be independent
    if systemctl is-active turbopi-emergency-ap.service > /dev/null 2>&1 && \
       systemctl is-active turbopi-home-wifi.service > /dev/null 2>&1; then
        test_pass "Both services running simultaneously"
    else
        log_warn "Both services not running simultaneously (home Wi-Fi may not be configured)"
    fi
    
    # Emergency AP should not depend on home Wi-Fi
    if systemctl show turbopi-emergency-ap.service | grep -q "turbopi-home-wifi"; then
        test_fail "Emergency AP independent of home Wi-Fi" "Service has dependency on home Wi-Fi"
    else
        test_pass "Emergency AP independent of home Wi-Fi"
    fi
}

test_networking_persistence() {
    log_info "Testing networking persistence configuration..."
    
    # Check that services are enabled (will start on boot)
    if systemctl is-enabled turbopi-emergency-ap.service > /dev/null 2>&1; then
        test_pass "Emergency AP will persist across reboot"
    else
        test_fail "Emergency AP will persist across reboot" "Service not enabled"
    fi
    
    if [ -f "/etc/systemd/system/turbopi-home-wifi.service" ]; then
        if systemctl is-enabled turbopi-home-wifi.service > /dev/null 2>&1; then
            test_pass "Home Wi-Fi will persist across reboot"
        else
            log_warn "Home Wi-Fi service not enabled"
        fi
    fi
}

test_acceptance_criteria() {
    echo ""
    echo "========================================"
    echo "  ACCEPTANCE CRITERIA VERIFICATION"
    echo "========================================"
    echo ""
    
    # AC1: Fresh flash boots into emergency AP
    log_info "AC1: Fresh flash boots into emergency AP"
    echo "  Prerequisites:"
    echo "    - Emergency AP files and service installed"
    echo "    - Service enabled for automatic start"
    echo "    - wlan0 interface configured"
    echo ""
    
    local ac1_pass=true
    if ! systemctl is-enabled turbopi-emergency-ap.service > /dev/null 2>&1; then
        echo -e "  ${RED}[FAIL]${NC}: Emergency AP service not enabled"
        ac1_pass=false
    fi
    if ! systemctl is-active turbopi-emergency-ap.service > /dev/null 2>&1; then
        echo -e "  ${RED}[FAIL]${NC}: Emergency AP service not running"
        ac1_pass=false
    fi
    if ! ip addr show wlan0 | grep -q "192.168.50.1" 2>/dev/null; then
        echo -e "  ${RED}[FAIL]${NC}: wlan0 not configured with 192.168.50.1"
        ac1_pass=false
    fi
    
    if $ac1_pass; then
        echo -e "  ${GREEN}[PASS]${NC}: System configured to boot into emergency AP"
    fi
    echo ""
    
    # AC2: Device joins home Wi-Fi without disabling AP
    log_info "AC2: Device joins home Wi-Fi without disabling AP"
    echo "  Prerequisites:"
    echo "    - Both emergency AP and home Wi-Fi services running"
    echo "    - wlan0 (emergency AP) and wlan1 (home Wi-Fi) both active"
    echo ""
    
    local ac2_status="NOT CONFIGURED"
    if systemctl is-active turbopi-home-wifi.service > /dev/null 2>&1; then
        if systemctl is-active turbopi-emergency-ap.service > /dev/null 2>&1; then
            if ip link show wlan0 > /dev/null 2>&1 && ip link show wlan1 > /dev/null 2>&1; then
                echo -e "  ${GREEN}[PASS]${NC}: Dual networking configured and active"
                ac2_status="PASS"
            else
                echo -e "  ${YELLOW}[PARTIAL]${NC}: Services running but interfaces not both active"
                ac2_status="PARTIAL"
            fi
        else
            echo -e "  ${RED}[FAIL]${NC}: Emergency AP not running while home Wi-Fi is active"
            ac2_status="FAIL"
        fi
    else
        echo -e "  ${YELLOW}[SKIP]${NC}: Home Wi-Fi not configured (install-home-wifi.sh not run)"
    fi
    echo ""
    
    # AC3: Networking persists across reboot
    log_info "AC3: Networking persists across reboot"
    echo "  Prerequisites:"
    echo "    - Services are enabled (will start on boot)"
    echo "    - No manual intervention required after reboot"
    echo ""
    
    local ac3_pass=true
    if ! systemctl is-enabled turbopi-emergency-ap.service > /dev/null 2>&1; then
        echo -e "  ${RED}[FAIL]${NC}: Emergency AP service not enabled for boot"
        ac3_pass=false
    fi
    
    if [ -f "/etc/systemd/system/turbopi-home-wifi.service" ]; then
        if ! systemctl is-enabled turbopi-home-wifi.service > /dev/null 2>&1; then
            echo -e "  ${YELLOW}[WARN]${NC}: Home Wi-Fi service exists but not enabled"
        fi
    fi
    
    if $ac3_pass; then
        echo -e "  ${GREEN}[PASS]${NC}: Networking configured to persist across reboot"
    fi
    echo ""
}

# Main execution
main() {
    echo "========================================"
    echo "  TurboPi Dual Networking Test Suite"
    echo "========================================"
    echo ""
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then 
        log_warn "Not running as root. Some tests may fail."
        echo ""
    fi
    
    # Run tests
    test_emergency_ap_files
    echo ""
    
    test_emergency_ap_service
    echo ""
    
    test_emergency_ap_interface
    echo ""
    
    test_emergency_ap_processes
    echo ""
    
    test_home_wifi_files
    echo ""
    
    test_home_wifi_service
    echo ""
    
    test_home_wifi_interface
    echo ""
    
    test_dual_networking_independence
    echo ""
    
    test_networking_persistence
    echo ""
    
    # Verify acceptance criteria
    test_acceptance_criteria
    
    # Summary
    echo "========================================"
    echo "  TEST SUMMARY"
    echo "========================================"
    echo "  Total Tests: $TESTS_RUN"
    echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
    echo "========================================"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}[FAILED] Some tests failed${NC}"
        exit 1
    fi
}

# Run main function
main
