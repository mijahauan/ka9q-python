#!/usr/bin/env python3
"""
Example: Using RadiodStream for Continuous Sample Delivery

This example demonstrates the new high-level stream API that provides:
- Continuous sample stream with gap filling
- Quality metrics (StreamQuality) with every callback
- Automatic resequencing of out-of-order packets

Usage:
    # First discover available channels
    python3 examples/discover_example.py
    
    # Then stream from a channel (use SSRC from discovery)
    python3 examples/stream_example.py --ssrc 10000 --multicast 239.x.x.x --port 5004

For GRAPE/WWV recording at 10 MHz:
    python3 examples/stream_example.py --ssrc 10000 --duration 60
"""

import argparse
import logging
import time
import numpy as np
from datetime import datetime

# Add parent to path for development
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import (
    RadiodStream,
    StreamQuality,
    GapSource,
    discover_channels,
    ChannelInfo,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SampleCounter:
    """Simple callback handler that counts samples and reports quality."""
    
    def __init__(self):
        self.total_samples = 0
        self.total_callbacks = 0
        self.total_gaps = 0
        self.last_report = time.time()
        self.report_interval = 5.0  # seconds
    
    def on_samples(self, samples: np.ndarray, quality: StreamQuality):
        """Called for each batch of samples."""
        self.total_samples += len(samples)
        self.total_callbacks += 1
        self.total_gaps += len(quality.batch_gaps)
        
        # Log any gaps
        for gap in quality.batch_gaps:
            logger.warning(
                f"Gap: {gap.source.value}, {gap.duration_samples} samples "
                f"({gap.duration_samples / 16000 * 1000:.1f}ms)"
            )
        
        # Periodic report
        now = time.time()
        if now - self.last_report >= self.report_interval:
            self._report(quality)
            self.last_report = now
    
    def _report(self, quality: StreamQuality):
        """Print periodic status report."""
        print(f"\n{'='*60}")
        print(f"Stream Status @ {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"  Samples delivered: {quality.total_samples_delivered:,}")
        print(f"  Completeness:      {quality.completeness_pct:.2f}%")
        print(f"  Gap events:        {quality.total_gap_events}")
        print(f"  Gaps filled:       {quality.total_gaps_filled:,} samples")
        print(f"  RTP packets:       {quality.rtp_packets_received:,}")
        print(f"  RTP lost:          {quality.rtp_packets_lost}")
        print(f"  RTP resequenced:   {quality.rtp_packets_resequenced}")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Stream samples from radiod with quality tracking'
    )
    parser.add_argument(
        '--ssrc', type=int, required=True,
        help='SSRC of the channel to stream (from discovery)'
    )
    parser.add_argument(
        '--multicast', type=str, default='239.113.49.249',
        help='Multicast address (default: 239.113.49.249)'
    )
    parser.add_argument(
        '--port', type=int, default=5004,
        help='UDP port (default: 5004)'
    )
    parser.add_argument(
        '--sample-rate', type=int, default=16000,
        help='Sample rate in Hz (default: 16000)'
    )
    parser.add_argument(
        '--duration', type=int, default=30,
        help='Duration to stream in seconds (default: 30)'
    )
    parser.add_argument(
        '--discover', action='store_true',
        help='Discover channels first and use specified SSRC'
    )
    
    args = parser.parse_args()
    
    # Create ChannelInfo (normally from discover_channels)
    if args.discover:
        print("Discovering channels...")
        channels = discover_channels(timeout=3.0)
        channel = None
        for ch in channels:
            if ch.ssrc == args.ssrc:
                channel = ch
                break
        
        if channel is None:
            print(f"SSRC {args.ssrc} not found in discovered channels")
            print(f"Available SSRCs: {[ch.ssrc for ch in channels]}")
            return 1
        
        print(f"Found channel: {channel.frequency/1e6:.3f} MHz, {channel.sample_rate} Hz")
    else:
        # Create minimal ChannelInfo
        channel = ChannelInfo(
            ssrc=args.ssrc,
            multicast_address=args.multicast,
            port=args.port,
            sample_rate=args.sample_rate,
            frequency=args.ssrc * 1000,  # Guess from SSRC
            preset='iq',
            snr=0.0,
        )
    
    # Create sample counter
    counter = SampleCounter()
    
    # Create and start stream
    print(f"\nStarting stream: SSRC={args.ssrc}, duration={args.duration}s")
    print(f"Multicast: {channel.multicast_address}:{channel.port}")
    print("-" * 60)
    
    stream = RadiodStream(
        channel=channel,
        on_samples=counter.on_samples,
        samples_per_packet=320,  # 320 samples @ 16kHz = 20ms per packet
    )
    
    stream.start()
    
    try:
        # Run for specified duration
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    # Stop and get final quality
    final_quality = stream.stop()
    
    # Final report
    print(f"\n{'='*60}")
    print("FINAL STATISTICS")
    print(f"{'='*60}")
    print(f"  Duration:          {args.duration}s")
    print(f"  Callbacks:         {counter.total_callbacks}")
    print(f"  Samples delivered: {final_quality.total_samples_delivered:,}")
    print(f"  Completeness:      {final_quality.completeness_pct:.2f}%")
    print(f"  Gap events:        {final_quality.total_gap_events}")
    print(f"  Total gap samples: {final_quality.total_gaps_filled:,}")
    print(f"  RTP packets:       {final_quality.rtp_packets_received:,}")
    print(f"  RTP lost:          {final_quality.rtp_packets_lost}")
    print(f"  RTP duplicates:    {final_quality.rtp_packets_duplicate}")
    print(f"  RTP resequenced:   {final_quality.rtp_packets_resequenced}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
