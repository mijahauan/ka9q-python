#!/usr/bin/env python3
"""
Debug test to see what's happening with tune
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import RadiodControl
import logging

# Enable DEBUG logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def main():
    radiod_address = "bee1-hf-status.local"
    test_ssrc = 99999999
    
    print(f"Connecting to {radiod_address}...")
    control = RadiodControl(radiod_address)
    print(f"Connected! Dest addr: {control.dest_addr}\n")
    
    print("Attempting to tune...")
    try:
        status = control.tune(
            ssrc=test_ssrc,
            frequency_hz=14.074e6,
            preset="usb",
            sample_rate=12000,
            timeout=10.0  # Longer timeout for debugging
        )
        
        print("\n✓ SUCCESS!")
        print(f"Status: {status}")
        
    except TimeoutError as e:
        print(f"\n✗ Timeout: {e}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        control.close()

if __name__ == '__main__':
    main()
