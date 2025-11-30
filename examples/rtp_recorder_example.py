#!/usr/bin/env python3
"""
Example: RTP Recorder with Timing

Demonstrates using the generic RTP recorder to:
- Receive RTP packets with precise timing
- Display packet information in real-time
- Handle state transitions
- Track recording metrics
"""

import sys
import time
import signal
import logging
from datetime import datetime
from ka9q import discover_channels
from ka9q.rtp_recorder import RTPRecorder, RecorderState, RTPHeader, RecordingMetrics

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleRecorder:
    """Example recorder that prints packet info"""
    
    def __init__(self):
        self.packet_count = 0
        self.start_time = None
    
    def on_packet(self, header: RTPHeader, payload: bytes, wallclock: float):
        """Called for each received packet"""
        self.packet_count += 1
        
        # Print every 100th packet
        if self.packet_count % 100 == 0:
            ts = datetime.fromtimestamp(wallclock).strftime('%H:%M:%S.%f')[:-3]
            logger.info(
                f"Packet #{self.packet_count}: "
                f"seq={header.sequence}, "
                f"ts={header.timestamp}, "
                f"size={len(payload)}, "
                f"time={ts}"
            )
    
    def on_state_change(self, old_state: RecorderState, new_state: RecorderState):
        """Called when recorder state changes"""
        logger.info(f"📊 State changed: {old_state.value} → {new_state.value}")
        
        if new_state == RecorderState.RESYNC:
            logger.warning("⚠️  Lost sync - attempting recovery")
    
    def on_recording_start(self):
        """Called when recording starts"""
        self.start_time = time.time()
        self.packet_count = 0
        logger.info("🔴 RECORDING STARTED")
    
    def on_recording_stop(self, metrics: RecordingMetrics):
        """Called when recording stops"""
        logger.info("⏹️  RECORDING STOPPED")
        logger.info("\nRecording Metrics:")
        logger.info(f"  Packets received:     {metrics.packets_received:,}")
        logger.info(f"  Packets dropped:      {metrics.packets_dropped:,}")
        logger.info(f"  Sequence errors:      {metrics.sequence_errors}")
        logger.info(f"  Timestamp jumps:      {metrics.timestamp_jumps}")
        logger.info(f"  Bytes received:       {metrics.bytes_received:,}")
        
        if metrics.recording_start_time and metrics.recording_stop_time:
            duration = metrics.recording_stop_time - metrics.recording_start_time
            logger.info(f"  Duration:             {duration:.2f}s")
            
            if duration > 0:
                rate = metrics.packets_received / duration
                logger.info(f"  Packet rate:          {rate:.1f} pkt/s")


def main(status_address: str, ssrc: int = None, duration: float = 30.0):
    """
    Run RTP recorder example
    
    Args:
        status_address: radiod status address (e.g., "radiod.local")
        ssrc: SSRC to record (if None, uses first discovered channel)
        duration: How long to record in seconds
    """
    print(f"\nDiscovering channels from {status_address}...")
    channels = discover_channels(status_address, listen_duration=3.0)
    
    if not channels:
        print("❌ No channels found")
        return 1
    
    # Select channel
    if ssrc is None:
        ssrc = list(channels.keys())[0]
        logger.info(f"No SSRC specified, using first channel: {ssrc}")
    
    if ssrc not in channels:
        print(f"❌ Channel SSRC {ssrc} not found")
        print(f"Available channels: {list(channels.keys())}")
        return 1
    
    channel = channels[ssrc]
    
    # Display channel info
    print("\n" + "=" * 80)
    print(f"Recording from channel:")
    print(f"  SSRC:         {channel.ssrc}")
    print(f"  Frequency:    {channel.frequency/1e6:.6f} MHz")
    print(f"  Sample Rate:  {channel.sample_rate:,} Hz")
    print(f"  Preset:       {channel.preset}")
    print(f"  Destination:  {channel.multicast_address}:{channel.port}")
    
    # Check timing fields
    if channel.gps_time and channel.rtp_timesnap:
        print(f"  GPS Time:     {channel.gps_time:,} ns")
        print(f"  RTP Timesnap: {channel.rtp_timesnap:,}")
        print("  ✓ Timing fields available")
    else:
        print("  ⚠️  Timing fields not available")
    
    print("=" * 80 + "\n")
    
    # Create recorder
    app = SimpleRecorder()
    recorder = RTPRecorder(
        channel=channel,
        on_packet=app.on_packet,
        on_state_change=app.on_state_change,
        on_recording_start=app.on_recording_start,
        on_recording_stop=app.on_recording_stop,
        max_packet_gap=10,
        resync_threshold=5
    )
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n\nInterrupted by user")
        recorder.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start receiving
        recorder.start()
        print(f"Recorder armed. Starting recording in 2 seconds...")
        time.sleep(2.0)
        
        # Start recording
        recorder.start_recording()
        
        # Record for specified duration
        print(f"Recording for {duration} seconds...")
        print("(Press Ctrl+C to stop early)\n")
        time.sleep(duration)
        
        # Stop recording
        recorder.stop_recording()
        time.sleep(1.0)
        
        # Stop receiver
        recorder.stop()
        
        # Display final metrics
        metrics = recorder.get_metrics()
        print("\nFinal Metrics:")
        for key, value in metrics.items():
            if value is not None:
                print(f"  {key:25s}: {value}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        recorder.stop()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rtp_recorder_example.py <status_address> [ssrc] [duration]")
        print("Example: python rtp_recorder_example.py radiod.local")
        print("Example: python rtp_recorder_example.py radiod.local 14074000 60")
        sys.exit(1)
    
    status_addr = sys.argv[1]
    ssrc_arg = int(sys.argv[2]) if len(sys.argv) > 2 else None
    duration_arg = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
    
    sys.exit(main(status_addr, ssrc_arg, duration_arg))
