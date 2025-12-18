#!/usr/bin/env python3
"""
Manual test script to demonstrate download and verification functionality.

This script demonstrates:
1. Successful download and verification
2. Checksum mismatch detection
3. Download error handling
"""

import os
import sys
import tempfile
import hashlib
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

from download import download_and_verify, DownloadError, ChecksumError


def test_scenario_1_success():
    """Test successful download and verification with a real file"""
    print("\n" + "="*70)
    print("SCENARIO 1: Successful Download and Verification")
    print("="*70)
    
    # Create a test file to simulate download
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source file
        source_content = b"This is a simulated release artifact for TurboPi v0.1.0"
        source_path = os.path.join(tmpdir, "source.txt")
        with open(source_path, 'wb') as f:
            f.write(source_content)
        
        # Calculate actual checksum
        actual_checksum = hashlib.sha256(source_content).hexdigest()
        print(f"\nTest file created: {source_path}")
        print(f"Expected checksum: {actual_checksum}")
        
        # Test with file:// URL (local file)
        file_url = f"file://{source_path}"
        dest_path = os.path.join(tmpdir, "downloaded.txt")
        
        try:
            download_and_verify(file_url, dest_path, actual_checksum)
            print(f"\n✓ SUCCESS: File downloaded and verified successfully")
            print(f"  Downloaded to: {dest_path}")
            
            # Verify content matches
            with open(dest_path, 'rb') as f:
                downloaded_content = f.read()
            
            if downloaded_content == source_content:
                print(f"✓ Content verification: PASSED")
            else:
                print(f"✗ Content verification: FAILED")
                
        except (DownloadError, ChecksumError) as e:
            print(f"✗ FAILED: {e}")
            return False
    
    return True


def test_scenario_2_checksum_mismatch():
    """Test that checksum mismatch is detected"""
    print("\n" + "="*70)
    print("SCENARIO 2: Checksum Mismatch Detection")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source file
        source_content = b"This is a potentially malicious or corrupted file"
        source_path = os.path.join(tmpdir, "bad_source.txt")
        with open(source_path, 'wb') as f:
            f.write(source_content)
        
        # Use wrong checksum
        wrong_checksum = "0" * 64
        print(f"\nTest file created: {source_path}")
        print(f"Using wrong checksum: {wrong_checksum}")
        
        file_url = f"file://{source_path}"
        dest_path = os.path.join(tmpdir, "downloaded.txt")
        
        try:
            download_and_verify(file_url, dest_path, wrong_checksum)
            print(f"\n✗ FAILED: Should have detected checksum mismatch!")
            return False
            
        except ChecksumError as e:
            print(f"\n✓ SUCCESS: Checksum mismatch detected as expected")
            print(f"  Error: {e}")
            
            # Verify file was cleaned up
            if not os.path.exists(dest_path):
                print(f"✓ File cleanup: Invalid file was removed")
            else:
                print(f"✗ File cleanup: Invalid file still exists")
                return False
                
        except DownloadError as e:
            print(f"✗ FAILED: Wrong exception type: {e}")
            return False
    
    return True


def test_scenario_3_download_error():
    """Test download error handling"""
    print("\n" + "="*70)
    print("SCENARIO 3: Download Error Handling")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Use invalid URL
        invalid_url = "http://nonexistent.invalid.domain.example/file.tar.gz"
        dest_path = os.path.join(tmpdir, "downloaded.txt")
        checksum = "abc123"
        
        print(f"\nAttempting download from invalid URL: {invalid_url}")
        
        try:
            download_and_verify(invalid_url, dest_path, checksum, timeout=5)
            print(f"\n✗ FAILED: Should have failed with download error!")
            return False
            
        except DownloadError as e:
            print(f"\n✓ SUCCESS: Download error handled correctly")
            print(f"  Error: {e}")
            
            # Verify no partial file remains
            if not os.path.exists(dest_path):
                print(f"✓ File cleanup: No partial download remains")
            else:
                print(f"✗ File cleanup: Partial download still exists")
                return False
                
        except ChecksumError as e:
            print(f"✗ FAILED: Wrong exception type: {e}")
            return False
    
    return True


def main():
    """Run all manual test scenarios"""
    print("\n" + "="*70)
    print("TurboPi Updater - Download & Verification Manual Test")
    print("="*70)
    print("\nThis script demonstrates the download and verification functionality")
    print("required by docs/updater/PROTOCOL.md")
    
    results = []
    
    # Run test scenarios
    results.append(("Successful Download & Verification", test_scenario_1_success()))
    results.append(("Checksum Mismatch Detection", test_scenario_2_checksum_mismatch()))
    results.append(("Download Error Handling", test_scenario_3_download_error()))
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n✓ All tests passed! Download and verification working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
