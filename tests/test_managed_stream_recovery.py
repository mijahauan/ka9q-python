#!/usr/bin/env python3
"""
Test ManagedStream drop detection and automatic recovery.

Run this script, then stop and restart radiod to test recovery:
    sudo systemctl stop radiod
    # wait a few seconds
    sudo systemctl start radiod

The script should detect the drop and automatically restore the stream.

Usage:
    python tests/test_managed_stream_recovery.py [status_address]
    
    status_address: radiod status multicast address (default: sdr.local)
"""

import sys
import time
import logging
from datetime import datetime

# Add parent directory to path for development
sys.path.insert(0, '.')

from ka9q import RadiodControl, ManagedStream, StreamState

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Reduce noise from ka9q internals
logging.getLogger('ka9q.control').setLevel(logging.WARNING)
logging.getLogger('ka9q.discovery').setLevel(logging.WARNING)
logging.getLogger('ka9q.stream').setLevel(logging.WARNING)
logging.getLogger('ka9q.managed_stream').setLevel(logging.INFO)


class StreamTester:
    """Test harness for ManagedStream recovery"""
    
    def __init__(self):
        self.packets_received = 0
        self.samples_received = 0
        self.drops_detected = 0
        self.restorations = 0
        self.last_sample_time = None
    
    def on_samples(self, samples, quality):
        """Called when samples are received"""
        self.packets_received += 1
        self.samples_received += len(samples)
        self.last_sample_time = datetime.now()
        
        # Print status every 50 packets (~1 second at typical rates)
        if self.packets_received % 50 == 0:
            logger.info(
                f"Receiving: {self.samples_received:,} samples, "
                f"{quality.completeness_pct:.1f}% complete"
            )
    
    def on_stream_dropped(self, reason):
        """Called when stream drop is detected"""
        self.drops_detected += 1
        logger.warning(f"🔴 STREAM DROPPED #{self.drops_detected}: {reason}")
        print(f"\n{'='*60}")
        print(f"STREAM DROPPED: {reason}")
        print(f"Total drops: {self.drops_detected}")
        print(f"Attempting automatic restoration...")
        print(f"{'='*60}\n")
    
    def on_stream_restored(self, channel):
        """Called when stream is restored"""
        self.restorations += 1
        logger.info(
            f"🟢 STREAM RESTORED #{self.restorations}: "
            f"SSRC={channel.ssrc}, {channel.frequency/1e6:.3f} MHz"
        )
        print(f"\n{'='*60}")
        print(f"STREAM RESTORED!")
        print(f"  SSRC: {channel.ssrc}")
        print(f"  Frequency: {channel.frequency/1e6:.3f} MHz")
        print(f"  Address: {channel.multicast_address}:{channel.port}")
        print(f"Total restorations: {self.restorations}")
        print(f"{'='*60}\n")


def main():
    # Get status address from command line or use default
    status_address = sys.argv[1] if len(sys.argv) > 1 else "sdr.local"
    
    # Test parameters - adjust as needed for your setup
    frequency_hz = 10.0e6  # 10 MHz WWV
    preset = "am"
    sample_rate = 12000
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         ManagedStream Recovery Test                          ║
╠══════════════════════════════════════════════════════════════╣
║  This test demonstrates automatic stream recovery.           ║
║                                                              ║
║  While this script is running, try:                          ║
║    sudo systemctl stop radiod                                ║
║    (wait 5 seconds)                                          ║
║    sudo systemctl start radiod                               ║
║                                                              ║
║  The stream should automatically detect the drop and         ║
║  restore itself when radiod comes back.                      ║
║                                                              ║
║  Press Ctrl+C to stop the test.                              ║
╚══════════════════════════════════════════════════════════════╝

Configuration:
  Status address: {status_address}
  Frequency: {frequency_hz/1e6:.3f} MHz
  Preset: {preset}
  Sample rate: {sample_rate} Hz
  Drop timeout: 3.0 seconds

""")
    
    tester = StreamTester()
    
    try:
        with RadiodControl(status_address) as control:
            logger.info(f"Connected to radiod at {status_address}")
            
            # Create managed stream with recovery callbacks
            stream = ManagedStream(
                control=control,
                frequency_hz=frequency_hz,
                preset=preset,
                sample_rate=sample_rate,
                on_samples=tester.on_samples,
                on_stream_dropped=tester.on_stream_dropped,
                on_stream_restored=tester.on_stream_restored,
                drop_timeout_sec=3.0,      # Detect drop after 3s of silence
                restore_interval_sec=1.0,  # Retry restoration every 1s
            )
            
            # Start the stream
            channel = stream.start()
            logger.info(
                f"Stream started: SSRC={channel.ssrc}, "
                f"{channel.frequency/1e6:.3f} MHz @ {channel.sample_rate} Hz"
            )
            print(f"Stream is HEALTHY. Waiting for samples...\n")
            
            # Run until interrupted
            last_status_time = time.time()
            while True:
                time.sleep(1.0)
                
                # Print periodic status
                if time.time() - last_status_time >= 10.0:
                    stats = stream.get_stats()
                    state_emoji = {
                        StreamState.HEALTHY: "🟢",
                        StreamState.DROPPED: "🔴",
                        StreamState.RESTORING: "🟡",
                        StreamState.STARTING: "🟡",
                        StreamState.STOPPED: "⚫",
                    }.get(stats.state, "❓")
                    
                    print(f"\n--- Status Update ---")
                    print(f"  State: {state_emoji} {stats.state.value}")
                    print(f"  Samples received: {tester.samples_received:,}")
                    print(f"  Total drops: {stats.total_drops}")
                    print(f"  Total restorations: {stats.total_restorations}")
                    print(f"  Healthy duration: {stats.total_healthy_duration_sec:.1f}s")
                    print(f"  Dropped duration: {stats.total_dropped_duration_sec:.1f}s")
                    print()
                    
                    last_status_time = time.time()
    
    except KeyboardInterrupt:
        print("\n\nStopping test...")
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    
    finally:
        # Print final summary
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                     Test Summary                             ║
╠══════════════════════════════════════════════════════════════╣
║  Samples received:    {tester.samples_received:>10,}                         ║
║  Drops detected:      {tester.drops_detected:>10}                         ║
║  Restorations:        {tester.restorations:>10}                         ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
