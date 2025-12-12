"""
ka9q: Python interface for ka9q-radio

A general-purpose library for controlling ka9q-radio channels and streams.
No assumptions about your application - works for everything from AM radio
listening to SuperDARN radar monitoring.

Basic usage:
    from ka9q import RadiodControl, allocate_ssrc
    
    # Use context manager for automatic cleanup
    with RadiodControl("radiod.local") as control:
        # SSRC-free API (recommended) - SSRC auto-allocated
        ssrc = control.create_channel(
            frequency_hz=10.0e6,
            preset="am",
            sample_rate=12000
        )
        print(f"Created channel with SSRC: {ssrc}")
        
        # Or use allocate_ssrc() directly for coordination
        ssrc = allocate_ssrc(10.0e6, "iq", 16000)
"""

__version__ = '3.2.1'
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
]
