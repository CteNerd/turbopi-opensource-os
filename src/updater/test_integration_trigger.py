#!/usr/bin/env python3
"""
Integration test for updater service trigger processing.

This test verifies that the updater service can:
1. Detect trigger files
2. Process trigger data
3. Call apply_update_to_system with correct parameters
"""

import os
import sys
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from main import UpdaterService


def test_updater_processes_trigger():
    """Test that updater service processes trigger files correctly"""
    print("Testing updater service trigger processing...")
    
    # Create temporary trigger directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create trigger file
        trigger_file = os.path.join(temp_dir, 'update-trigger.json')
        trigger_data = {
            'version': '1.0.0',
            'url': 'https://example.com/release.tar.gz',
            'checksum': 'abc123def456',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        
        with open(trigger_file, 'w') as f:
            json.dump(trigger_data, f)
        
        print(f"✓ Created trigger file: {trigger_file}")
        
        # Create updater service instance with custom trigger dir
        with patch.dict(os.environ, {'TRIGGER_DIR': temp_dir}):
            service = UpdaterService()
            
            # Mock the apply_update_to_system method
            with patch.object(service, 'apply_update_to_system') as mock_apply:
                mock_apply.return_value = True
                
                # Check for trigger
                result = service.check_for_update_trigger()
                
                # Verify trigger was processed
                assert result, "Expected trigger to be processed"
                
                # Verify apply_update_to_system was called with correct parameters
                mock_apply.assert_called_once_with(
                    version='1.0.0',
                    url='https://example.com/release.tar.gz',
                    checksum='abc123def456',
                    requires_reboot=False
                )
                
                print("✓ Trigger processed successfully")
                print(f"✓ apply_update_to_system called with: {mock_apply.call_args}")
        
        # Verify trigger file was removed
        assert not os.path.exists(trigger_file), "Trigger file should be removed after processing"
        print("✓ Trigger file removed after processing")
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_updater_handles_invalid_trigger():
    """Test that updater handles invalid trigger files gracefully"""
    print("\nTesting invalid trigger file handling...")
    
    # Create temporary trigger directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create invalid trigger file (missing required fields)
        trigger_file = os.path.join(temp_dir, 'update-trigger.json')
        trigger_data = {
            'version': '1.0.0'
            # Missing url and checksum
        }
        
        with open(trigger_file, 'w') as f:
            json.dump(trigger_data, f)
        
        # Create updater service instance
        with patch.dict(os.environ, {'TRIGGER_DIR': temp_dir}):
            service = UpdaterService()
            
            # Check for trigger
            result = service.check_for_update_trigger()
            
            # Verify trigger was not processed (invalid)
            assert not result, "Expected invalid trigger to be rejected"
            print("✓ Invalid trigger rejected")
        
        # Verify invalid trigger file was removed
        assert not os.path.exists(trigger_file), "Invalid trigger file should be removed"
        print("✓ Invalid trigger file removed")
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_updater_no_trigger_file():
    """Test that updater handles missing trigger file gracefully"""
    print("\nTesting missing trigger file handling...")
    
    # Create temporary trigger directory (no trigger file)
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create updater service instance
        with patch.dict(os.environ, {'TRIGGER_DIR': temp_dir}):
            service = UpdaterService()
            
            # Check for trigger (none exists)
            result = service.check_for_update_trigger()
            
            # Verify no trigger was processed
            assert not result, "Expected no trigger to be found"
            print("✓ No trigger file - gracefully handled")
    
    finally:
        # Clean up
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all integration tests"""
    print("=== TurboPi Updater Service Integration Tests ===\n")
    
    try:
        test_updater_processes_trigger()
        test_updater_handles_invalid_trigger()
        test_updater_no_trigger_file()
        
        print("\n=== All updater service integration tests passed! ===")
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
