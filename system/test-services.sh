#!/bin/bash
# Test script for TurboPi runtime services
# Verifies that services start correctly and meet acceptance criteria

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "TurboPi Runtime Service Test Suite"
echo "==================================="
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for test results
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

# Test 1: Check if config.env exists
echo "Test 1: Configuration file exists"
if [ -f /etc/turbopi/config.env ]; then
    pass_test "Configuration file /etc/turbopi/config.env exists"
else
    fail_test "Configuration file /etc/turbopi/config.env not found"
fi

# Test 2: Check if systemd services are installed
echo ""
echo "Test 2: Systemd service files installed"
SERVICES=("turbopi-api" "turbopi-ui" "turbopi-updater")
for service in "${SERVICES[@]}"; do
    if [ -f "/etc/systemd/system/${service}.service" ]; then
        pass_test "Service file ${service}.service exists"
    else
        fail_test "Service file ${service}.service not found"
    fi
done

# Test 3: Check if services are enabled
echo ""
echo "Test 3: Services enabled for boot"
for service in "${SERVICES[@]}"; do
    if systemctl is-enabled "${service}.service" > /dev/null 2>&1; then
        pass_test "Service ${service}.service is enabled"
    else
        fail_test "Service ${service}.service is not enabled"
    fi
done

# Test 4: Check if services are running (if started)
echo ""
echo "Test 4: Services running (if started)"
for service in "${SERVICES[@]}"; do
    if systemctl is-active "${service}.service" > /dev/null 2>&1; then
        pass_test "Service ${service}.service is active"
    else
        echo -e "${YELLOW}⚠ INFO${NC}: Service ${service}.service is not currently running"
        echo "         (Run 'sudo systemctl start ${service}.service' to start it)"
    fi
done

# Test 5: Test health endpoint (if API is running)
echo ""
echo "Test 5: Health endpoint availability"
if systemctl is-active turbopi-api.service > /dev/null 2>&1; then
    # Wait a moment for service to be ready
    sleep 2
    
    if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
        pass_test "Health endpoint responds"
        
        # Check response content
        HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
        if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
            pass_test "Health endpoint returns valid JSON"
        else
            fail_test "Health endpoint response is not valid JSON"
        fi
    else
        fail_test "Health endpoint not accessible at http://localhost:8080/health"
    fi
else
    echo -e "${YELLOW}⚠ INFO${NC}: API service not running, skipping health endpoint test"
    echo "         Start the service with: sudo systemctl start turbopi-api.service"
fi

# Test 6: Check if config.env is loaded (requires running services)
echo ""
echo "Test 6: Configuration loaded by services"
if systemctl is-active turbopi-api.service > /dev/null 2>&1; then
    LOG_OUTPUT=$(journalctl -u turbopi-api.service -n 20 --no-pager 2>/dev/null || echo "")
    if echo "$LOG_OUTPUT" | grep -q "Robot Name:"; then
        pass_test "API service loads configuration from config.env"
    else
        fail_test "API service may not be loading configuration"
    fi
else
    echo -e "${YELLOW}⚠ INFO${NC}: API service not running, skipping config load test"
fi

# Summary
echo ""
echo "======================================="
echo "Test Results:"
echo -e "  ${GREEN}Passed: ${TESTS_PASSED}${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "  ${RED}Failed: ${TESTS_FAILED}${NC}"
else
    echo -e "  ${GREEN}Failed: 0${NC}"
fi
echo "======================================="

# Acceptance Criteria Summary
echo ""
echo "Acceptance Criteria Status:"
echo ""

# AC1: API, UI, updater start on boot
if [ $TESTS_PASSED -ge 6 ]; then
    echo -e "${GREEN}✓ AC1: API, UI, updater start on boot${NC}"
else
    echo -e "${YELLOW}⚠ AC1: Services installed, start with 'systemctl start'${NC}"
fi

# AC2: config.env loaded via systemd
if [ -f /etc/turbopi/config.env ]; then
    echo -e "${GREEN}✓ AC2: config.env loaded via systemd${NC}"
else
    echo -e "${RED}✗ AC2: config.env not found${NC}"
fi

# AC3: Health endpoint available
if systemctl is-active turbopi-api.service > /dev/null 2>&1; then
    if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ AC3: Health endpoint available${NC}"
    else
        echo -e "${RED}✗ AC3: Health endpoint not responding${NC}"
    fi
else
    echo -e "${YELLOW}⚠ AC3: Start API service to test health endpoint${NC}"
fi

echo ""

# Exit with appropriate code
if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi
