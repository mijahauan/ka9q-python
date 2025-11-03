#!/usr/bin/env python3
"""
Comprehensive channel operation testing

This script tests the exact issues reported:
1. Creating new channels
2. Tuning existing channels to different frequencies
3. Changing gain/volume on existing channels

Run with: python3 test_channel_operations.py <radiod_address>
Example: python3 test_channel_operations.py radiod.local
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ka9q import RadiodControl, discover_channels
import logging

# Enable detailed logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_create_new_channel(control, ssrc, freq, preset='usb'):
    """Test creating a brand new channel"""
    print(f"\n{'='*70}")
    print(f"TEST 1: Creating New Channel")
    print(f"{'='*70}")
    print(f"SSRC: {ssrc}")
    print(f"Frequency: {freq/1e6:.6f} MHz")
    print(f"Preset: {preset}")
    print(f"{'-'*70}\n")
    
    try:
        print("Sending tune command to create channel...")
        status = control.tune(
            ssrc=ssrc,
            frequency_hz=freq,
            preset=preset,
            sample_rate=12000,
            timeout=10.0
        )
        
        print("\n✓ SUCCESS - Received status response!")
        print(f"\nReturned status fields:")
        for key, value in sorted(status.items()):
            if key == 'frequency':
                print(f"  {key:20s}: {value/1e6:.6f} MHz ({value} Hz)")
            elif key == 'ssrc':
                print(f"  {key:20s}: {value} (0x{value:08x})")
            elif key in ['gain', 'rf_gain', 'rf_atten']:
                print(f"  {key:20s}: {value:.2f} dB")
            else:
                print(f"  {key:20s}: {value}")
        
        # Verify key fields
        print(f"\n{'-'*70}")
        print("Verification:")
        
        if 'ssrc' in status and status['ssrc'] == ssrc:
            print(f"  ✓ SSRC matches: {ssrc}")
        else:
            print(f"  ✗ SSRC mismatch: expected {ssrc}, got {status.get('ssrc', 'MISSING')}")
            return False
        
        if 'frequency' in status:
            actual_freq = status['frequency']
            freq_diff = abs(actual_freq - freq)
            if freq_diff < 1.0:
                print(f"  ✓ Frequency matches: {actual_freq/1e6:.6f} MHz (diff: {freq_diff:.3f} Hz)")
            else:
                print(f"  ✗ Frequency mismatch: expected {freq/1e6:.6f}, got {actual_freq/1e6:.6f} (diff: {freq_diff} Hz)")
                return False
        else:
            print(f"  ✗ Frequency field missing in status")
            return False
        
        if 'preset' in status and status['preset'].lower() == preset.lower():
            print(f"  ✓ Preset matches: {status['preset']}")
        else:
            print(f"  ⚠ Preset: expected {preset}, got {status.get('preset', 'MISSING')}")
        
        print(f"\n{'='*70}")
        print("TEST 1: ✓ PASSED - Channel created successfully")
        print(f"{'='*70}\n")
        return True
        
    except TimeoutError as e:
        print(f"\n✗ TIMEOUT: {e}")
        print("\nPossible causes:")
        print("  - radiod not responding")
        print("  - Wrong multicast address")
        print("  - Firewall blocking multicast")
        print("  - radiod not sending status for this SSRC")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retune_frequency(control, ssrc, old_freq, new_freq, preset='usb'):
    """Test changing frequency of an existing channel"""
    print(f"\n{'='*70}")
    print(f"TEST 2: Re-tune Existing Channel (Change Frequency)")
    print(f"{'='*70}")
    print(f"SSRC: {ssrc} (existing channel)")
    print(f"Old Frequency: {old_freq/1e6:.6f} MHz")
    print(f"New Frequency: {new_freq/1e6:.6f} MHz")
    print(f"Change: {(new_freq - old_freq)/1e3:.1f} kHz")
    print(f"{'-'*70}\n")
    
    try:
        print("Sending tune command to change frequency...")
        status = control.tune(
            ssrc=ssrc,
            frequency_hz=new_freq,
            preset=preset,
            timeout=10.0
        )
        
        print("\n✓ SUCCESS - Received status response!")
        
        if 'frequency' in status:
            actual_freq = status['frequency']
            freq_diff = abs(actual_freq - new_freq)
            print(f"\nFrequency verification:")
            print(f"  Requested:  {new_freq/1e6:.6f} MHz")
            print(f"  Reported:   {actual_freq/1e6:.6f} MHz")
            print(f"  Difference: {freq_diff:.3f} Hz")
            
            if freq_diff < 1.0:
                print(f"  ✓ Frequency change SUCCESSFUL")
                
                # Also verify it's different from old frequency
                if abs(actual_freq - old_freq) > 100:
                    print(f"  ✓ Confirmed different from old frequency")
                    print(f"\n{'='*70}")
                    print("TEST 2: ✓ PASSED - Frequency re-tuning works")
                    print(f"{'='*70}\n")
                    return True
                else:
                    print(f"  ✗ Still at old frequency!")
                    return False
            else:
                print(f"  ✗ Frequency not changed correctly (diff: {freq_diff} Hz)")
                return False
        else:
            print(f"  ✗ Frequency field missing in status")
            return False
            
    except TimeoutError as e:
        print(f"\n✗ TIMEOUT: {e}")
        print("\nThis means the re-tune command was not acknowledged by radiod")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_change_gain(control, ssrc, freq, old_gain, new_gain, preset='usb'):
    """Test changing gain/volume of an existing channel"""
    print(f"\n{'='*70}")
    print(f"TEST 3: Change Gain/Volume on Existing Channel")
    print(f"{'='*70}")
    print(f"SSRC: {ssrc} (existing channel)")
    print(f"Frequency: {freq/1e6:.6f} MHz (unchanged)")
    print(f"Old Gain: {old_gain:.1f} dB")
    print(f"New Gain: {new_gain:.1f} dB")
    print(f"Change: {new_gain - old_gain:+.1f} dB")
    print(f"{'-'*70}\n")
    
    try:
        print("Sending tune command to change gain...")
        status = control.tune(
            ssrc=ssrc,
            frequency_hz=freq,
            preset=preset,
            gain=new_gain,
            timeout=10.0
        )
        
        print("\n✓ SUCCESS - Received status response!")
        
        if 'gain' in status:
            actual_gain = status['gain']
            gain_diff = abs(actual_gain - new_gain)
            print(f"\nGain verification:")
            print(f"  Requested: {new_gain:.1f} dB")
            print(f"  Reported:  {actual_gain:.1f} dB")
            print(f"  Difference: {gain_diff:.3f} dB")
            
            if gain_diff < 0.5:
                print(f"  ✓ Gain change SUCCESSFUL")
                
                # Verify AGC is disabled when manual gain is set
                if 'agc_enable' in status:
                    if not status['agc_enable']:
                        print(f"  ✓ AGC correctly disabled")
                    else:
                        print(f"  ⚠ AGC still enabled (unexpected)")
                
                print(f"\n{'='*70}")
                print("TEST 3: ✓ PASSED - Gain adjustment works")
                print(f"{'='*70}\n")
                return True
            else:
                print(f"  ✗ Gain not changed correctly (diff: {gain_diff} dB)")
                return False
        else:
            print(f"  ✗ Gain field missing in status")
            print(f"  ⚠ radiod may not support gain for this preset")
            return False
            
    except TimeoutError as e:
        print(f"\n✗ TIMEOUT: {e}")
        print("\nThis means the gain change command was not acknowledged by radiod")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_channel_operations.py <radiod_address>")
        print("Example: python3 test_channel_operations.py radiod.local")
        return 1
    
    radiod_address = sys.argv[1]
    
    print(f"\n{'#'*70}")
    print(f"# Channel Operations Testing")
    print(f"# radiod address: {radiod_address}")
    print(f"{'#'*70}\n")
    
    print("Connecting to radiod...")
    try:
        control = RadiodControl(radiod_address)
        print(f"✓ Connected to {radiod_address}")
        print(f"  Multicast address: {control.status_mcast_addr}")
        print(f"  Destination: {control.dest_addr}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return 1
    
    # Use a unique test SSRC
    test_ssrc = 99999001
    
    # Test parameters
    freq1 = 14.074e6  # 14.074 MHz (FT8 frequency)
    freq2 = 14.076e6  # 14.076 MHz (2 kHz higher)
    freq3 = 14.070e6  # 14.070 MHz (4 kHz lower than freq1)
    gain1 = 0.0
    gain2 = 10.0
    gain3 = 20.0
    
    results = {}
    
    # TEST 1: Create new channel
    results['create_channel'] = test_create_new_channel(
        control, test_ssrc, freq1, preset='usb'
    )
    
    if not results['create_channel']:
        print("\n⚠️  Channel creation failed. Cannot proceed with re-tuning tests.")
        print("    Check radiod connectivity and configuration.")
        control.close()
        return 1
    
    # Give radiod a moment to stabilize
    time.sleep(1.0)
    
    # TEST 2: Re-tune to different frequency
    results['retune_frequency'] = test_retune_frequency(
        control, test_ssrc, freq1, freq2, preset='usb'
    )
    
    # Give radiod a moment
    time.sleep(1.0)
    
    # TEST 3: Change gain
    results['change_gain'] = test_change_gain(
        control, test_ssrc, freq2, gain1, gain2, preset='usb'
    )
    
    # Give radiod a moment
    time.sleep(1.0)
    
    # BONUS TEST: Try another frequency change
    print(f"\n{'='*70}")
    print(f"BONUS TEST: Re-tune to third frequency")
    print(f"{'='*70}\n")
    results['retune_again'] = test_retune_frequency(
        control, test_ssrc, freq2, freq3, preset='usb'
    )
    
    # Cleanup
    control.close()
    
    # Summary
    print(f"\n{'#'*70}")
    print(f"# TEST SUMMARY")
    print(f"{'#'*70}\n")
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name.replace('_', ' ').title():.<50} {status}")
    
    print(f"\n{'#'*70}\n")
    
    all_passed = all(results.values())
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe package is working correctly:")
        print("  ✓ Can create new channels")
        print("  ✓ Can re-tune existing channels to different frequencies")
        print("  ✓ Can change gain/volume on existing channels")
        print()
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nIssues detected:")
        if not results.get('create_channel'):
            print("  ✗ Cannot create new channels")
        if not results.get('retune_frequency'):
            print("  ✗ Cannot re-tune existing channels to different frequencies")
        if not results.get('change_gain'):
            print("  ✗ Cannot change gain on existing channels")
        print("\nPlease review the detailed output above for diagnostics.")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
