"""
ka9q: Python interface for ka9q-radio

A general-purpose library for controlling ka9q-radio channels and streams.
No assumptions about your application - works for everything from AM radio
listening to SuperDARN radar monitoring.

Recommended usage (high-level API):
    from ka9q import RadiodControl, RadiodStream
    
    with RadiodControl("radiod.local") as control:
        # Request a channel with specific characteristics
        # ka9q-python handles discovery, creation, and verification
        channel = control.ensure_channel(
            frequency_hz=14.074e6,
            preset="usb",
            sample_rate=12000
        )
        # Channel is verified and ready for streaming
        print(f"Channel ready: {channel.frequency/1e6:.3f} MHz")
        
        # Start receiving samples
        stream = RadiodStream(channel, on_samples=my_callback)
        stream.start()

Lower-level usage (explicit control):
    from ka9q import RadiodControl, allocate_ssrc
    
    with RadiodControl("radiod.local") as control:
        # SSRC-free API - SSRC auto-allocated
        ssrc = control.create_channel(
            frequency_hz=10.0e6,
            preset="am",
            sample_rate=12000
        )
        print(f"Created channel with SSRC: {ssrc}")
        
        # Or use allocate_ssrc() directly for coordination
        ssrc = allocate_ssrc(10.0e6, "iq", 16000)
"""
__version__ = '3.2.7'
__author__ = 'Michael Hauan AC0G'

from .control import RadiodControl, allocate_ssrc
from .discovery import (
    discover_channels,
    discover_channels_native,
    discover_channels_via_control,
    discover_radiod_services,
    ChannelInfo
)
from .types import StatusType, Encoding
from .exceptions import Ka9qError, ConnectionError, CommandError, ValidationError
from .rtp_recorder import (
    RTPRecorder,
    RecorderState,
    RTPHeader,
    RecordingMetrics,
    parse_rtp_header,
    rtp_to_wallclock
)
from .stream_quality import (
    GapSource,
    GapEvent,
    StreamQuality,
)
from .resequencer import (
    PacketResequencer,
    RTPPacket,
    ResequencerStats,
)
from .stream import (
    RadiodStream,
)

__all__ = [
    # Control
    'RadiodControl',
    'allocate_ssrc',
    
    # Discovery
    'discover_channels',
    'discover_channels_native',
    'discover_channels_via_control',
    'discover_radiod_services',
    'ChannelInfo',
    
    # Types
    'StatusType',
    'Encoding',
    
    # Exceptions
    'Ka9qError',
    'ConnectionError',
    'CommandError',
    'ValidationError',
    
    # Low-level RTP (packet-oriented)
    'RTPRecorder',
    'RecorderState',
    'RTPHeader',
    'RecordingMetrics',
    'parse_rtp_header',
    'rtp_to_wallclock',
    
    # Stream API (sample-oriented) - NEW
    'RadiodStream',
    'StreamQuality',
    'GapSource',
    'GapEvent',
    'PacketResequencer',
    'RTPPacket',
    'ResequencerStats',
    'generate_multicast_ip',
    'ChannelMonitor',
]

from .addressing import generate_multicast_ip
from .monitor import ChannelMonitor
