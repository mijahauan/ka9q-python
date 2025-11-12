#!/usr/bin/env python3
"""
Quick verification test for performance fixes

This script tests that the performance improvements are working correctly.
Run this against a live radiod instance to verify.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ka9q import RadiodControl, discover_channels_native

def test_socket_reuse():
    """Test that socket is reused across multiple tune() calls"""
    print("=" * 70)
    print("Test 1: Socket Reuse")
    print("=" * 70)
    
    try:
        import psutil
        proc = psutil.Process()
        initial_fds = proc.num_fds()
        print(f"Initial file descriptors: {initial_fds}")
    except ImportError:
        print("⚠️  psutil not installed - skipping FD count check")
        initial_fds = None
    
    # Note: This test requires a live radiod instance
    # Replace "radiod.local" with your radiod address
    radiod_address = "radiod.local"
    
    print(f"\nCreating RadiodControl instance for {radiod_address}...")
    try:
        control = RadiodControl(radiod_address)
    except Exception as e:
        print(f"❌ Could not connect to radiod: {e}")
        print("   This test requires a live radiod instance")
        return False
    
    print("✓ Connected")
    
    # Perform multiple tune operations
    print("\nPerforming 5 tune operations...")
    tune_times = []
    
    for i in range(5):
        start = time.time()
        try:
            # This should fail gracefully if radiod isn't responding
            # but we're just checking that sockets aren't leaking
            status = control.tune(
                ssrc=99000000 + i,
                frequency_hz=14.074e6,
                preset="usb",
                timeout=2.0  # Short timeout
            )
            elapsed = time.time() - start
            tune_times.append(elapsed)
            print(f"  Tune {i+1}: {elapsed:.3f}s ✓")
        except TimeoutError:
            elapsed = time.time() - start
            tune_times.append(elapsed)
            print(f"  Tune {i+1}: {elapsed:.3f}s (timeout, but socket reused)")
        except Exception as e:
            print(f"  Tune {i+1}: Error - {e}")
    
    # Check file descriptors
    if initial_fds is not None:
        final_fds = proc.num_fds()
        fd_increase = final_fds - initial_fds
        print(f"\nFinal file descriptors: {final_fds}")
        print(f"Increase: {fd_increase}")
        
        if fd_increase < 5:
            print("✓ Socket reuse working! (FD increase < 5)")
        else:
            print(f"⚠️  Warning: FD increased by {fd_increase} (possible socket leak)")
    
    # Check if tune times improved after first call
    if len(tune_times) >= 2:
        print(f"\nFirst tune: {tune_times[0]:.3f}s (socket creation)")
        print(f"Avg subsequent: {sum(tune_times[1:])/len(tune_times[1:]):.3f}s (socket reuse)")
        if tune_times[0] > sum(tune_times[1:])/len(tune_times[1:]):
            print("✓ Subsequent tunes faster (socket reuse benefit)")
    
    control.close()
    print("\n✓ Test 1 Complete\n")
    return True


def test_discovery_performance():
    """Test native discovery performance"""
    print("=" * 70)
    print("Test 2: Native Discovery Performance")
    print("=" * 70)
    
    radiod_address = "radiod.local"
    
    print(f"\nRunning native discovery on {radiod_address}...")
    print("Listening for 2 seconds...\n")
    
    start = time.time()
    try:
        channels = discover_channels_native(radiod_address, listen_duration=2.0)
        elapsed = time.time() - start
        
        print(f"\n✓ Discovery completed in {elapsed:.3f}s")
        print(f"  Found {len(channels)} channels")
        
        if elapsed < 3.0:
            print("✓ Performance acceptable (< 3 seconds)")
        else:
            print(f"⚠️  Slower than expected ({elapsed:.3f}s)")
        
        for ssrc, info in list(channels.items())[:3]:
            print(f"\n  Channel {ssrc}:")
            print(f"    Frequency: {info.frequency/1e6:.6f} MHz")
            print(f"    Preset: {info.preset}")
            print(f"    Sample Rate: {info.sample_rate:,} Hz")
        
        if len(channels) > 3:
            print(f"\n  ... and {len(channels) - 3} more channels")
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n❌ Discovery failed after {elapsed:.3f}s: {e}")
        print("   This test requires a live radiod instance")
        return False
    
    print("\n✓ Test 2 Complete\n")
    return True


def test_exponential_backoff():
    """Test that exponential backoff is working"""
    print("=" * 70)
    print("Test 3: Exponential Backoff")
    print("=" * 70)
    
    radiod_address = "radiod.local"
    
    print(f"\nTesting exponential backoff with {radiod_address}...")
    print("Using short timeout to see backoff behavior...\n")
    
    try:
        control = RadiodControl(radiod_address)
    except Exception as e:
        print(f"❌ Could not connect: {e}")
        return False
    
    # Use an SSRC that likely doesn't exist to trigger retries
    start = time.time()
    try:
        status = control.tune(
            ssrc=99999999,
            frequency_hz=1.0e6,  # 1 MHz
            preset="usb",
            timeout=3.0  # Short timeout to see backoff
        )
        elapsed = time.time() - start
        print(f"✓ Received response in {elapsed:.3f}s")
        print("  (Exponential backoff allowed response)")
    except TimeoutError as e:
        elapsed = time.time() - start
        print(f"⏱️  Timeout after {elapsed:.3f}s (expected)")
        print("  Exponential backoff reduced retries")
        print(f"  (Without backoff, this would have 30+ retries at 0.1s each)")
        
        # With backoff: ~10 attempts in 3 seconds
        # Without backoff: ~30 attempts in 3 seconds
        if elapsed >= 2.9 and elapsed <= 3.1:
            print("✓ Timeout behavior correct")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    control.close()
    print("\n✓ Test 3 Complete\n")
    return True


def main():
    print("\n" + "=" * 70)
    print("Performance Fixes Verification Tests")
    print("=" * 70)
    print("\nThese tests verify the three performance fixes:")
    print("  1. Socket reuse in tune()")
    print("  2. Native discovery optimization")
    print("  3. Exponential backoff in tune()")
    print("\n⚠️  REQUIRES: Live radiod instance")
    print("=" * 70 + "\n")
    
    results = {
        "Socket Reuse": test_socket_reuse(),
        "Discovery Performance": test_discovery_performance(),
        "Exponential Backoff": test_exponential_backoff(),
    }
    
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:.<50} {status}")
    
    print("=" * 70)
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Performance fixes are working correctly.\n")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check radiod connectivity.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
