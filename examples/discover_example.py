#!/usr/bin/env python3
"""
Example showing channel discovery methods

This demonstrates both native Python discovery and the control utility fallback.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for ka9q imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import discover_channels, discover_channels_native, discover_channels_via_control

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def main():
    # Replace with your radiod status address
    status_address = "radiod.local"
    
    print("=" * 70)
    print("Ka9q-Python Channel Discovery Example")
    print("=" * 70)
    print()
    
    # Method 1: Automatic (tries native first, falls back to control)
    print("Method 1: Automatic discovery (native with fallback)")
    print("-" * 70)
    channels = discover_channels(status_address)
    
    if channels:
        print(f"Found {len(channels)} channels:\n")
        for ssrc, info in channels.items():
            print(f"  SSRC {ssrc}:")
            print(f"    Frequency:  {info.frequency/1e6:.6f} MHz")
            print(f"    Preset:     {info.preset}")
            print(f"    Sample Rate: {info.sample_rate:,} Hz")
            print(f"    SNR:        {info.snr:.1f} dB" if info.snr != float('-inf') else "    SNR:        N/A")
            print(f"    Destination: {info.multicast_address}:{info.port}")
            print()
    else:
        print("No channels found")
    
    print()
    
    # Method 2: Native Python only
    print("Method 2: Native Python discovery (no external dependencies)")
    print("-" * 70)
    try:
        channels_native = discover_channels_native(status_address, listen_duration=3.0)
        
        if channels_native:
            print(f"Found {len(channels_native)} channels:\n")
            for ssrc, info in channels_native.items():
                print(f"  SSRC {ssrc}: {info.frequency/1e6:.3f} MHz, {info.preset}, {info.sample_rate} Hz")
        else:
            print("No channels found (radiod may not be broadcasting)")
    except Exception as e:
        print(f"Native discovery failed: {e}")
    
    print()
    
    # Method 3: Control utility (requires ka9q-radio installed)
    print("Method 3: Using 'control' utility (requires ka9q-radio)")
    print("-" * 70)
    try:
        channels_control = discover_channels_via_control(status_address)
        
        if channels_control:
            print(f"Found {len(channels_control)} channels:\n")
            for ssrc, info in channels_control.items():
                print(f"  SSRC {ssrc}: {info.frequency/1e6:.3f} MHz, {info.preset}, {info.sample_rate} Hz")
        else:
            print("No channels found")
    except Exception as e:
        print(f"Control utility discovery failed: {e}")
        print("(This is expected if 'control' is not installed)")
    
    print()
    
    # Method 4: Multi-homed system (specify network interface)
    print("Method 4: Multi-homed system (specify interface)")
    print("-" * 70)
    print("For systems with multiple network interfaces, you can specify")
    print("which interface to use for multicast traffic.")
    print()
    print("Example usage:")
    print("  # Specify your interface IP address")
    print("  my_interface = '192.168.1.100'  # Replace with your interface IP")
    print("  channels = discover_channels(status_address, interface=my_interface)")
    print()
    print("To find your interface IP:")
    print("  Linux/macOS: ip addr show  or  ifconfig")
    print("  Windows:     ipconfig")
    print()
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()
