"""
RadiodStream - High-Level Sample Stream Interface

Provides a continuous sample stream from radiod with quality metadata.
This is the primary interface for applications consuming radio data.

Features:
- Automatic multicast subscription
- RTP packet reception and parsing
- Packet resequencing and gap filling
- Quality tracking (StreamQuality) with every callback
- Cross-platform support (Linux, macOS, Windows)

Usage:
    from ka9q import RadiodStream, StreamQuality
    
    def on_samples(samples: np.ndarray, quality: StreamQuality):
        # Process continuous sample stream
        print(f"Got {len(samples)} samples, completeness: {quality.completeness_pct:.1f}%")
    
    stream = RadiodStream(
        channel=channel_info,
        on_samples=on_samples,
    )
    stream.start()
    # ... run until done ...
    stream.stop()
"""

import socket
import struct
import logging
import threading
import numpy as np
from datetime import datetime, timezone
from typing import Optional, Callable, List

from .discovery import ChannelInfo
from .rtp_recorder import RTPHeader, parse_rtp_header, rtp_to_wallclock
from .resequencer import PacketResequencer, RTPPacket
from .stream_quality import GapSource, GapEvent, StreamQuality

logger = logging.getLogger(__name__)

# Type alias for sample callback
SampleCallback = Callable[[np.ndarray, StreamQuality], None]


class RadiodStream:
    """
    High-level interface to a radiod IQ/audio stream.
    
    Handles all low-level details:
    - Multicast subscription and RTP packet reception
    - Packet resequencing and gap detection
    - Gap filling with zeros for continuous stream
    - Quality tracking with detailed metrics
    
    Delivers to application:
    - Continuous sample stream (np.ndarray, complex64 or float32)
    - StreamQuality metadata with every callback
    """
    
    def __init__(
        self,
        channel: ChannelInfo,
        on_samples: Optional[SampleCallback] = None,
        samples_per_packet: int = 320,
        resequence_buffer_size: int = 64,
        deliver_interval_packets: int = 10,
    ):
        """
        Initialize RadiodStream.
        
        Args:
            channel: ChannelInfo with stream details (from discover_channels)
            on_samples: Callback(samples, quality) for sample delivery
            samples_per_packet: Expected samples per RTP packet (320 @ 16kHz)
            resequence_buffer_size: Packets to buffer for resequencing (64 = ~2s)
            deliver_interval_packets: Deliver to callback every N packets (batching)
        """
        self.channel = channel
        self.on_samples = on_samples
        self.samples_per_packet = samples_per_packet
        self.deliver_interval_packets = deliver_interval_packets
        
        # Resequencer
        self.resequencer = PacketResequencer(
            buffer_size=resequence_buffer_size,
            samples_per_packet=samples_per_packet,
            sample_rate=channel.sample_rate,
        )
        
        # Quality tracking
        self.quality = StreamQuality()
        
        # Sample accumulator for batched delivery
        self._sample_buffer: List[np.ndarray] = []
        self._gap_buffer: List[GapEvent] = []
        self._packets_since_delivery = 0
        
        # Socket and threading
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Detect payload format from channel preset
        # IQ mode: complex64 (interleaved float32 I/Q)
        # Audio modes: float32 (mono or stereo)
        self._is_iq = channel.preset.lower() in ('iq', 'spectrum')
        
        # Payload samples differ from RTP timestamp increment in IQ mode
        # IQ: 160 complex samples per packet, but timestamp advances by 320
        # Audio: samples_per_packet real samples, timestamp advances same
        self._payload_samples_per_packet = samples_per_packet // 2 if self._is_iq else samples_per_packet
    
    def start(self):
        """Start receiving and delivering samples."""
        if self._running:
            logger.warning("Stream already running")
            return
        
        # Initialize quality tracking
        self.quality = StreamQuality(
            stream_start_utc=datetime.now(timezone.utc).isoformat(),
            sample_rate=self.channel.sample_rate,
        )
        
        # Track first RTP timestamp
        self._first_rtp_timestamp: Optional[int] = None
        
        # Reset resequencer
        self.resequencer.reset()
        
        # Start receive thread
        self._running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._thread.start()
        
        logger.info(
            f"RadiodStream started: {self.channel.multicast_address}:{self.channel.port} "
            f"SSRC={self.channel.ssrc}"
        )
    
    def stop(self) -> StreamQuality:
        """
        Stop receiving and return final quality metrics.
        
        Returns:
            Final StreamQuality with complete statistics
        """
        if not self._running:
            return self.quality.copy()
        
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        # Flush resequencer
        final_samples, final_gaps = self.resequencer.flush()
        if len(final_samples) > 0 or final_gaps:
            self._sample_buffer.append(final_samples)
            self._gap_buffer.extend(final_gaps)
            self._deliver_samples()
        
        logger.info(
            f"RadiodStream stopped. Completeness: {self.quality.completeness_pct:.1f}%, "
            f"Gaps: {self.quality.total_gap_events}"
        )
        
        return self.quality.copy()
    
    def _create_socket(self) -> socket.socket:
        """Create and configure multicast receive socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Allow address reuse
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass  # Not supported on all platforms
        
        # Bind to port
        sock.bind(('0.0.0.0', self.channel.port))
        
        # Join multicast group
        mreq = struct.pack(
            '=4s4s',
            socket.inet_aton(self.channel.multicast_address),
            socket.inet_aton('0.0.0.0')
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Timeout for periodic running check
        sock.settimeout(1.0)
        
        logger.debug(
            f"Joined multicast {self.channel.multicast_address}:{self.channel.port}"
        )
        
        return sock
    
    def _receive_loop(self):
        """Main packet receiving loop."""
        try:
            self._socket = self._create_socket()
            
            while self._running:
                try:
                    data, addr = self._socket.recvfrom(8192)
                    self._process_packet(data)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        logger.error(f"Receive error: {e}", exc_info=True)
        
        finally:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass  # Ignore errors during cleanup
                self._socket = None
    
    def _process_packet(self, data: bytes):
        """Process a received RTP packet."""
        # Parse RTP header
        header = parse_rtp_header(data)
        if header is None:
            logger.debug("Invalid RTP packet")
            return
        
        # Filter by SSRC
        if header.ssrc != self.channel.ssrc:
            return  # Wrong stream
        
        # Update RTP stats
        self.quality.rtp_packets_received += 1
        
        # Track first and last RTP timestamps
        if self._first_rtp_timestamp is None:
            self._first_rtp_timestamp = header.timestamp
            self.quality.first_rtp_timestamp = header.timestamp
        self.quality.last_rtp_timestamp = header.timestamp
        
        # Extract payload
        header_len = 12 + (4 * header.csrc_count)
        payload = data[header_len:]
        
        if len(payload) == 0:
            # Empty payload - track as gap source
            self._record_empty_payload(header)
            return
        
        # Parse samples from payload
        samples = self._parse_samples(payload)
        if samples is None:
            return
        
        # Get wallclock time
        wallclock = rtp_to_wallclock(header.timestamp, self.channel)
        
        # Create packet for resequencer
        packet = RTPPacket(
            sequence=header.sequence,
            timestamp=header.timestamp,
            ssrc=header.ssrc,
            samples=samples,
            wallclock=wallclock,
        )
        
        # Process through resequencer
        output_samples, gap_events = self.resequencer.process_packet(packet)
        
        # Accumulate output
        if output_samples is not None:
            self._sample_buffer.append(output_samples)
            self._gap_buffer.extend(gap_events)
            self._packets_since_delivery += 1
            
            # Update gap stats
            for gap in gap_events:
                self.quality.total_gap_events += 1
                self.quality.total_gaps_filled += gap.duration_samples
            
            # Deliver if we've accumulated enough
            if self._packets_since_delivery >= self.deliver_interval_packets:
                self._deliver_samples()
        
        # Update timing
        if wallclock:
            self.quality.last_packet_utc = datetime.fromtimestamp(
                wallclock, tz=timezone.utc
            ).isoformat()
    
    def _parse_samples(self, payload: bytes) -> Optional[np.ndarray]:
        """Parse samples from RTP payload."""
        try:
            if self._is_iq:
                # IQ mode: float32 interleaved I/Q -> complex64
                # 960 bytes = 240 floats = 120 complex samples
                floats = np.frombuffer(payload, dtype=np.float32)
                if len(floats) % 2 != 0:
                    logger.warning(f"Odd number of floats in IQ payload: {len(floats)}")
                    return None
                samples = floats[0::2] + 1j * floats[1::2]
                return samples.astype(np.complex64)
            else:
                # Audio mode: float32 mono
                return np.frombuffer(payload, dtype=np.float32)
                
        except Exception as e:
            logger.error(f"Failed to parse payload: {e}")
            return None
    
    def _record_empty_payload(self, header: RTPHeader):
        """Record an empty payload as a gap event."""
        gap = GapEvent(
            source=GapSource.EMPTY_PAYLOAD,
            position_samples=self.quality.total_samples_delivered,
            duration_samples=self.samples_per_packet,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            packets_affected=1,
        )
        self._gap_buffer.append(gap)
        self.quality.total_gap_events += 1
        self.quality.total_gaps_filled += self.samples_per_packet
    
    def _deliver_samples(self):
        """Deliver accumulated samples to callback."""
        if not self._sample_buffer:
            return
        
        # Combine samples
        samples = np.concatenate(self._sample_buffer)
        gaps = list(self._gap_buffer)
        
        # Update quality for this batch
        batch_start = self.quality.total_samples_delivered
        self.quality.batch_start_sample = batch_start
        self.quality.batch_samples_delivered = len(samples)
        self.quality.batch_gaps = gaps
        self.quality.total_samples_delivered += len(samples)
        
        # Update expected samples (based on actual payload samples per packet)
        self.quality.total_samples_expected = (
            self.quality.rtp_packets_received * self._payload_samples_per_packet
        )
        
        # Update RTP loss stats from resequencer
        reseq_stats = self.resequencer.get_stats()
        self.quality.rtp_packets_lost = reseq_stats.get('gaps_detected', 0)
        self.quality.rtp_packets_resequenced = reseq_stats.get('packets_resequenced', 0)
        self.quality.rtp_packets_duplicate = reseq_stats.get('packets_duplicate', 0)
        
        # Clear buffers
        self._sample_buffer = []
        self._gap_buffer = []
        self._packets_since_delivery = 0
        
        # Deliver to callback
        if self.on_samples:
            try:
                self.on_samples(samples, self.quality.copy())
            except Exception as e:
                logger.error(f"Error in sample callback: {e}", exc_info=True)
    
    @property
    def is_running(self) -> bool:
        """True if stream is actively receiving."""
        return self._running
    
    def get_quality(self) -> StreamQuality:
        """Get current quality metrics (copy)."""
        return self.quality.copy()
    
    def __del__(self):
        """
        Ensure stream is stopped on garbage collection
        
        This provides a safety net for unclosed streams and helps
        detect resource leaks during development.
        """
        try:
            self.stop()
        except Exception:
            pass  # Can't raise exceptions in __del__
