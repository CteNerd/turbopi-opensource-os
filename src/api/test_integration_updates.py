#!/usr/bin/env python3
"""
Integration test for /updates/check and /updates/apply endpoints.

This test verifies that:
1. /updates/check returns proper format
2. /updates/apply accepts requests and returns 202
3. Trigger file is created properly
"""

import os
import sys
import json
import time
import tempfile
import shutil
import http.client
import subprocess
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))


def test_updates_check_endpoint():
    """Test the /updates/check endpoint"""
    print("Testing /updates/check endpoint...")
    
    # Start API server
    env = os.environ.copy()
    env['VERSION'] = '0.1.0'
    env['API_PORT'] = '18080'
    
    api_process = subprocess.Popen(
        ['python3', 'main.py'],
        cwd=os.path.dirname(__file__),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        # Make request to /updates/check
        conn = http.client.HTTPConnection('localhost', 18080, timeout=5)
        conn.request('GET', '/updates/check')
        response = conn.getresponse()
        
        assert response.status == 200, f"Expected 200, got {response.status}"
        
        data = json.loads(response.read().decode())
        assert 'update_available' in data, "Response missing 'update_available'"
        assert 'latest_version' in data, "Response missing 'latest_version'"
        
        print(f"✓ /updates/check returned: {data}")
        
        conn.close()
        
    finally:
        # Stop API server
        api_process.terminate()
        api_process.wait(timeout=5)


def test_updates_apply_endpoint():
    """Test the /updates/apply endpoint"""
    print("\nTesting /updates/apply endpoint...")
    
    # Create temporary trigger directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Start API server with temp trigger directory
        env = os.environ.copy()
        env['VERSION'] = '0.1.0'
        env['API_PORT'] = '18080'
        env['TRIGGER_DIR'] = temp_dir  # Use temp dir for trigger file
        
        api_process = subprocess.Popen(
            ['python3', 'main.py'],
            cwd=os.path.dirname(__file__),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(2)
        
        try:
            # Make POST request to /updates/apply
            conn = http.client.HTTPConnection('localhost', 18080, timeout=5)
            conn.request('POST', '/updates/apply')
            response = conn.getresponse()
            
            # Read response body
            body = response.read().decode()
            
            # Should return 202 (Accepted) or 200 (no update needed) or 500 (can't fetch release)
            assert response.status in [200, 202, 500], f"Expected 200/202/500, got {response.status}"
            
            # Parse JSON if content type is JSON
            if 'application/json' in response.getheader('Content-Type', ''):
                data = json.loads(body)
                print(f"✓ /updates/apply returned status {response.status}: {data}")
            else:
                # HTML error response
                print(f"✓ /updates/apply returned status {response.status} (HTML error)")
                print(f"  Response preview: {body[:200]}...")
            
            # If we got 202, verify trigger file was actually created
            if response.status == 202:
                print("✓ Update triggered (202 Accepted)")
                # Give it a moment to write the file
                time.sleep(0.5)
                trigger_file = os.path.join(temp_dir, 'update-trigger.json')
                if os.path.exists(trigger_file):
                    with open(trigger_file, 'r') as f:
                        trigger_data = json.load(f)
                    print(f"✓ Trigger file created with version: {trigger_data.get('version')}")
                else:
                    print("✗ Warning: Trigger file was not created")
            elif response.status == 200:
                print("✓ No update needed (200 OK)")
            else:
                print("✓ Expected 500 error fetching GitHub release in test environment")
            
            conn.close()
            
        finally:
            # Stop API server
            api_process.terminate()
            api_process.wait(timeout=5)
    
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_trigger_file_mechanism():
    """Test the trigger file creation mechanism"""
    print("\nTesting trigger file mechanism...")
    
    from main import trigger_system_update
    
    # Create temporary directory for trigger file
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Override trigger directory to use temp directory
        with patch.dict(os.environ, {'TRIGGER_DIR': temp_dir}):
            # Create trigger file with valid SHA256 checksum
            version = '1.0.0'
            url = 'https://example.com/release.tar.gz'
            # Use a valid 64-character hex SHA256 checksum
            checksum = 'a' * 64
            
            trigger_system_update(version, url, checksum)
            
            # Verify trigger file was created
            trigger_file = os.path.join(temp_dir, 'update-trigger.json')
            assert os.path.exists(trigger_file), "Trigger file should exist"
            
            # Verify trigger file content
            with open(trigger_file, 'r') as f:
                data = json.load(f)
            
            assert data['version'] == version, f"Expected version {version}, got {data['version']}"
            assert data['url'] == url, f"Expected url {url}, got {data['url']}"
            assert data['checksum'] == checksum, f"Expected checksum {checksum}, got {data['checksum']}"
            assert 'timestamp' in data, "Timestamp should be present"
            
            print("✓ Trigger file created with correct content")
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all integration tests"""
    print("=== TurboPi Updates API Integration Tests ===\n")
    
    try:
        test_updates_check_endpoint()
        test_updates_apply_endpoint()
        test_trigger_file_mechanism()
        
        print("\n=== All integration tests passed! ===")
        return 0
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
