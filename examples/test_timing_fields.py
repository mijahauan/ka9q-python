#!/usr/bin/env python3
"""
Test script to verify GPS_TIME and RTP_TIMESNAP fields are captured

This demonstrates the timing information needed for RTP timestamp synchronization
as used in radiod's pcmrecord.c
"""

import sys
import logging
from ka9q import discover_channels

# Set up logging to see details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_timing_fields(status_address: str):
    """
    Discover channels and display timing information
    
    Args:
        status_address: radiod status multicast address (e.g., "radiod.local")
    """
    print(f"\nDiscovering channels from {status_address}...")
    print("=" * 80)
    
    channels = discover_channels(status_address, listen_duration=3.0)
    
    if not channels:
        print("\n❌ No channels discovered")
        return False
    
    print(f"\n✓ Found {len(channels)} channel(s)\n")
    
    has_timing = False
    for ssrc, channel in channels.items():
        print(f"Channel SSRC {ssrc}:")
        print(f"  Frequency:    {channel.frequency/1e6:12.6f} MHz")
        print(f"  Sample Rate:  {channel.sample_rate:12,} Hz")
        print(f"  Preset:       {channel.preset:>12}")
        print(f"  Destination:  {channel.multicast_address}:{channel.port}")
        print(f"  SNR:          {channel.snr:12.1f} dB")
        
        if channel.gps_time is not None and channel.rtp_timesnap is not None:
            print(f"  GPS Time:     {channel.gps_time:>12,} ns")
            print(f"  RTP Timesnap: {channel.rtp_timesnap:>12,}")
            print("  ✓ Timing fields present")
            has_timing = True
        else:
            print("  ⚠ Timing fields missing")
            if channel.gps_time is None:
                print("    - GPS_TIME not received")
            if channel.rtp_timesnap is None:
                print("    - RTP_TIMESNAP not received")
        
        print()
    
    if has_timing:
        print("✓ Timing fields successfully captured!")
        print("\nThese fields enable RTP timestamp → wall clock conversion:")
        print("  wall_time = gps_time + (rtp_timestamp - rtp_timesnap) / sample_rate")
    else:
        print("⚠ No timing fields found in any channel")
        print("  This may indicate radiod is not sending GPS_TIME/RTP_TIMESNAP")
        print("  or the fields are not being decoded correctly")
    
    return has_timing


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_timing_fields.py <status_address>")
        print("Example: python test_timing_fields.py radiod.local")
        sys.exit(1)
    
    status_address = sys.argv[1]
    success = test_timing_fields(status_address)
    sys.exit(0 if success else 1)
