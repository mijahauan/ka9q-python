#!/usr/bin/env python3
"""
Example demonstrating the tune() method for radiod channel control

This shows how to use the tune() method to configure a radiod channel
and retrieve its status, similar to the C tune utility.
"""

import sys
from pathlib import Path

# Add parent directory to path for ka9q imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import RadiodControl, Encoding


def main():
    # Connect to radiod
    print("Connecting to radiod...")
    control = RadiodControl("radiod.local")
    
    # Example 1: Create a USB channel on 14.074 MHz (FT8 frequency)
    print("\n=== Example 1: USB channel for FT8 ===")
    ssrc1 = 14074000  # Use frequency as SSRC
    
    try:
        status = control.tune(
            ssrc=ssrc1,
            frequency_hz=14.074e6,
            preset="usb",
            sample_rate=12000,
            timeout=5.0
        )
        
        print(f"✓ Channel created successfully")
        print(f"  SSRC: {status.get('ssrc', 'N/A')}")
        print(f"  Frequency: {status.get('frequency', 0)/1e6:.6f} MHz")
        print(f"  Preset: {status.get('preset', 'N/A')}")
        print(f"  Sample Rate: {status.get('sample_rate', 'N/A')} Hz")
        if 'snr' in status:
            print(f"  SNR: {status['snr']:.1f} dB")
    
    except TimeoutError as e:
        print(f"✗ Timeout: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 2: Create an IQ channel with custom settings
    print("\n=== Example 2: IQ channel with custom filter ===")
    ssrc2 = 10000000
    
    try:
        status = control.tune(
            ssrc=ssrc2,
            frequency_hz=10.0e6,  # 10 MHz
            preset="iq",
            sample_rate=48000,
            low_edge=-24000,  # ±24 kHz passband
            high_edge=24000,
            agc_enable=False,  # Disable AGC for IQ
            timeout=5.0
        )
        
        print(f"✓ Channel created successfully")
        print(f"  SSRC: {status.get('ssrc', 'N/A')}")
        print(f"  Frequency: {status.get('frequency', 0)/1e6:.6f} MHz")
        print(f"  Preset: {status.get('preset', 'N/A')}")
        print(f"  Sample Rate: {status.get('sample_rate', 'N/A')} Hz")
        if 'low_edge' in status and 'high_edge' in status:
            print(f"  Passband: {status['low_edge']:.0f} to {status['high_edge']:.0f} Hz")
        print(f"  AGC: {'on' if status.get('agc_enable', False) else 'off'}")
    
    except TimeoutError as e:
        print(f"✗ Timeout: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 3: Adjust an existing channel's gain
    print("\n=== Example 3: Adjust channel gain ===")
    
    try:
        status = control.tune(
            ssrc=ssrc1,  # Reuse first channel
            gain=15.0,   # Set manual gain to 15 dB
            timeout=5.0
        )
        
        print(f"✓ Gain adjusted successfully")
        print(f"  SSRC: {status.get('ssrc', 'N/A')}")
        print(f"  Gain: {status.get('gain', 'N/A'):.1f} dB")
        print(f"  AGC: {'on' if status.get('agc_enable', False) else 'off'}")
    
    except TimeoutError as e:
        print(f"✗ Timeout: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 4: Re-tune frequency
    print("\n=== Example 4: Re-tune frequency ===")
    
    try:
        status = control.tune(
            ssrc=ssrc1,
            frequency_hz=14.100e6,  # Change to 14.100 MHz
            timeout=5.0
        )
        
        print(f"✓ Frequency changed successfully")
        print(f"  SSRC: {status.get('ssrc', 'N/A')}")
        print(f"  Frequency: {status.get('frequency', 0)/1e6:.6f} MHz")
    
    except TimeoutError as e:
        print(f"✗ Timeout: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Clean up
    control.close()
    print("\n✓ Done")


if __name__ == '__main__':
    main()
