#!/usr/bin/env python3
"""
Example: GRAPE-style Recording with RadiodStream

Demonstrates how GRAPE recorder can use the RadiodStream API:
1. Startup phase: Buffer samples for tone detection → time_snap
2. Recording phase: Write 1-minute NPZ segments with quality metadata

This is a simplified example. The full GRAPE recorder would add:
- Tone detection for time_snap
- NPZ file writing
- Periodic tone re-validation
"""

import time
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import (
    discover_channels,
    RadiodStream,
    StreamQuality,
    GapEvent,
    ChannelInfo,
)


@dataclass
class TimeSnap:
    """Simplified time_snap for this example"""
    rtp_timestamp: int
    utc_timestamp: float
    sample_rate: int
    source: str  # 'tone', 'ntp', 'wall_clock'
    
    def rtp_to_utc(self, rtp: int) -> float:
        """Convert RTP timestamp to UTC"""
        rtp_diff = rtp - self.rtp_timestamp
        if rtp_diff > 0x80000000:
            rtp_diff -= 0x100000000
        elapsed = rtp_diff / self.sample_rate
        return self.utc_timestamp + elapsed


class GrapeRecorderExample:
    """
    Example GRAPE recorder using RadiodStream.
    
    Shows the two-phase architecture:
    - Phase 1: Buffer samples for tone detection
    - Phase 2: Write minute segments with quality
    """
    
    def __init__(
        self,
        channel: ChannelInfo,
        output_dir: Path,
        startup_buffer_sec: float = 10.0,  # Shortened for demo
    ):
        self.channel = channel
        self.output_dir = output_dir
        self.startup_buffer_sec = startup_buffer_sec
        
        self.stream: Optional[RadiodStream] = None
        self.time_snap: Optional[TimeSnap] = None
        
        # Startup phase
        self._startup_samples: List[np.ndarray] = []
        self._startup_gaps: List[GapEvent] = []
        self._startup_start: float = 0
        self._startup_complete = False
        
        # Recording phase
        self._minute_buffer: List[np.ndarray] = []
        self._minute_gaps: List[GapEvent] = []
        self._minute_start_rtp: int = 0
        self._samples_per_minute: int = channel.sample_rate * 60
        
        # Stats
        self.segments_written = 0
    
    def start(self):
        """Start the recorder"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stream = RadiodStream(
            channel=self.channel,
            on_samples=self._on_samples,
            samples_per_packet=320,
        )
        
        self._startup_start = time.time()
        self.stream.start()
        print(f"Started GRAPE recorder for {self.channel.frequency/1e6:.3f} MHz")
        print(f"Startup buffer: {self.startup_buffer_sec}s")
    
    def stop(self) -> StreamQuality:
        """Stop and return final quality"""
        if self.stream:
            quality = self.stream.stop()
            print(f"\nStopped. Segments written: {self.segments_written}")
            print(f"Final completeness: {quality.completeness_pct:.1f}%")
            return quality
        return StreamQuality()
    
    def _on_samples(self, samples: np.ndarray, quality: StreamQuality):
        """Handle incoming samples"""
        if not self._startup_complete:
            self._handle_startup(samples, quality)
        else:
            self._handle_recording(samples, quality)
    
    def _handle_startup(self, samples: np.ndarray, quality: StreamQuality):
        """Startup phase: buffer for tone detection"""
        self._startup_samples.append(samples)
        self._startup_gaps.extend(quality.batch_gaps)
        
        elapsed = time.time() - self._startup_start
        if elapsed >= self.startup_buffer_sec:
            self._complete_startup(quality)
    
    def _complete_startup(self, quality: StreamQuality):
        """Complete startup: establish time_snap"""
        print(f"\nStartup buffer complete ({len(self._startup_samples)} batches)")
        
        # In real GRAPE: run tone detection on buffered samples
        # For this example: create time_snap from first RTP timestamp
        all_samples = np.concatenate(self._startup_samples)
        print(f"  Buffered {len(all_samples):,} samples")
        
        # Create time_snap (simplified - real GRAPE uses tone detection)
        self.time_snap = TimeSnap(
            rtp_timestamp=quality.first_rtp_timestamp,
            utc_timestamp=time.time() - (len(all_samples) / quality.sample_rate),
            sample_rate=quality.sample_rate,
            source='wall_clock',  # Real GRAPE would use 'tone' or 'ntp'
        )
        print(f"  time_snap established: {self.time_snap.source}")
        
        # Initialize first minute
        self._minute_start_rtp = quality.first_rtp_timestamp
        
        # Process buffered samples
        print(f"  Processing buffered samples into segments...")
        self._process_buffered_startup(all_samples, self._startup_gaps)
        
        self._startup_complete = True
        self._startup_samples = []
        self._startup_gaps = []
        print("  Recording phase started\n")
    
    def _process_buffered_startup(self, samples: np.ndarray, gaps: List[GapEvent]):
        """Write buffered startup samples as segments"""
        offset = 0
        while offset < len(samples):
            chunk_size = min(self._samples_per_minute, len(samples) - offset)
            self._minute_buffer.append(samples[offset:offset + chunk_size])
            
            # Check if we have a full minute
            total = sum(len(s) for s in self._minute_buffer)
            if total >= self._samples_per_minute:
                self._write_minute_segment()
            
            offset += chunk_size
    
    def _handle_recording(self, samples: np.ndarray, quality: StreamQuality):
        """Recording phase: accumulate and write minute segments"""
        self._minute_buffer.append(samples)
        self._minute_gaps.extend(quality.batch_gaps)
        
        # Check if we have a full minute
        total = sum(len(s) for s in self._minute_buffer)
        if total >= self._samples_per_minute:
            self._write_minute_segment()
    
    def _write_minute_segment(self):
        """Write accumulated samples as a minute segment"""
        # Concatenate samples
        all_samples = np.concatenate(self._minute_buffer)
        
        # Take exactly one minute worth
        segment_samples = all_samples[:self._samples_per_minute]
        remainder = all_samples[self._samples_per_minute:]
        
        # Calculate timestamp
        utc = self.time_snap.rtp_to_utc(self._minute_start_rtp)
        dt = datetime.fromtimestamp(utc, timezone.utc)
        
        # Create filename (GRAPE format)
        filename = self.output_dir / f"{dt.strftime('%Y%m%d_%H%M%S')}.npz"
        
        # In real GRAPE: save NPZ with all metadata
        # For this example: just print and count
        gap_samples = sum(g.duration_samples for g in self._minute_gaps)
        completeness = 100.0 * (len(segment_samples) - gap_samples) / len(segment_samples)
        
        print(f"  Segment: {dt.strftime('%H:%M:%S')} | "
              f"{len(segment_samples):,} samples | "
              f"{len(self._minute_gaps)} gaps | "
              f"{completeness:.1f}% complete")
        
        self.segments_written += 1
        
        # Reset for next minute
        self._minute_buffer = [remainder] if len(remainder) > 0 else []
        self._minute_gaps = []
        self._minute_start_rtp += self._samples_per_minute * 2  # *2 for IQ mode RTP


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GRAPE-style recording example')
    parser.add_argument('--ssrc', type=int, default=10000000, help='Channel SSRC')
    parser.add_argument('--duration', type=int, default=180, help='Recording duration (sec)')
    parser.add_argument('--output', type=str, default='/tmp/grape_example', help='Output dir')
    args = parser.parse_args()
    
    # Discover channel
    print("Discovering channels...")
    channels = discover_channels('bee1-hf-status.local', listen_duration=2.0)
    channel = channels.get(args.ssrc)
    
    if not channel:
        print(f"SSRC {args.ssrc} not found")
        return 1
    
    print(f"Found: {channel.frequency/1e6:.3f} MHz @ {channel.sample_rate} Hz")
    
    # Create and run recorder
    recorder = GrapeRecorderExample(
        channel=channel,
        output_dir=Path(args.output),
        startup_buffer_sec=10.0,  # Shortened for demo
    )
    
    recorder.start()
    
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("\nInterrupted")
    
    recorder.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
