#!/usr/bin/env python3
"""
Live test of tune functionality against bee1-hf-status.local
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import RadiodControl, Encoding
import logging

# Enable verbose logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    print("=" * 60)
    print("LIVE TUNE FUNCTIONALITY TEST")
    print("=" * 60)
    print()
    
    radiod_address = "bee1-hf-status.local"
    test_ssrc = 99999999  # Use a unique SSRC for testing
    
    print(f"Connecting to radiod at {radiod_address}...")
    try:
        control = RadiodControl(radiod_address)
        print("✓ Connected successfully!\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return 1
    
    # Test 1: Create a simple USB channel
    print("Test 1: Creating USB channel on 14.074 MHz (FT8)")
    print("-" * 60)
    try:
        status = control.tune(
            ssrc=test_ssrc,
            frequency_hz=14.074e6,
            preset="usb",
            sample_rate=12000,
            timeout=5.0
        )
        
        print("✓ Channel created successfully!")
        print(f"  SSRC: {status.get('ssrc', 'N/A')}")
        print(f"  Frequency: {status.get('frequency', 0)/1e6:.6f} MHz")
        print(f"  Preset: {status.get('preset', 'N/A')}")
        print(f"  Sample Rate: {status.get('sample_rate', 'N/A')} Hz")
        
        if 'agc_enable' in status:
            print(f"  AGC: {'enabled' if status['agc_enable'] else 'disabled'}")
        if 'gain' in status:
            print(f"  Gain: {status['gain']:.1f} dB")
        if 'low_edge' in status and 'high_edge' in status:
            print(f"  Passband: {status['low_edge']:.0f} to {status['high_edge']:.0f} Hz")
        if 'noise_density' in status:
            print(f"  Noise Density: {status['noise_density']:.1f} dB/Hz")
        if 'baseband_power' in status:
            print(f"  Baseband Power: {status['baseband_power']:.1f} dB")
        if 'snr' in status:
            print(f"  SNR: {status['snr']:.1f} dB")
        
        print()
        
    except TimeoutError as e:
        print(f"✗ Timeout: {e}\n")
        control.close()
        return 1
    except Exception as e:
        print(f"✗ Error: {e}\n")
        import traceback
        traceback.print_exc()
        control.close()
        return 1
    
    # Test 2: Change frequency
    print("Test 2: Changing frequency to 14.100 MHz")
    print("-" * 60)
    try:
        status = control.tune(
            ssrc=test_ssrc,
            frequency_hz=14.100e6,
            timeout=5.0
        )
        
        print("✓ Frequency changed successfully!")
        print(f"  New Frequency: {status.get('frequency', 0)/1e6:.6f} MHz")
        print()
        
    except TimeoutError as e:
        print(f"✗ Timeout: {e}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # Test 3: Enable AGC
    print("Test 3: Enabling AGC")
    print("-" * 60)
    try:
        status = control.tune(
            ssrc=test_ssrc,
            agc_enable=True,
            timeout=5.0
        )
        
        print("✓ AGC enabled successfully!")
        print(f"  AGC: {'enabled' if status.get('agc_enable', False) else 'disabled'}")
        if 'gain' in status:
            print(f"  Gain: {status['gain']:.1f} dB")
        print()
        
    except TimeoutError as e:
        print(f"✗ Timeout: {e}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # Test 4: Set manual gain (disables AGC)
    print("Test 4: Setting manual gain to 20 dB")
    print("-" * 60)
    try:
        status = control.tune(
            ssrc=test_ssrc,
            gain=20.0,
            timeout=5.0
        )
        
        print("✓ Manual gain set successfully!")
        print(f"  AGC: {'enabled' if status.get('agc_enable', False) else 'disabled'}")
        print(f"  Gain: {status.get('gain', 0):.1f} dB")
        print()
        
    except TimeoutError as e:
        print(f"✗ Timeout: {e}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # Test 5: Query status without changes
    print("Test 5: Querying channel status (no changes)")
    print("-" * 60)
    try:
        status = control.tune(
            ssrc=test_ssrc,
            timeout=5.0
        )
        
        print("✓ Status retrieved successfully!")
        print(f"  Complete status dictionary:")
        for key, value in sorted(status.items()):
            if isinstance(value, float):
                print(f"    {key}: {value:.3f}")
            else:
                print(f"    {key}: {value}")
        print()
        
    except TimeoutError as e:
        print(f"✗ Timeout: {e}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # Clean up
    control.close()
    
    print("=" * 60)
    print("✅ LIVE TEST COMPLETED")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
