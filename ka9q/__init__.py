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

__version__ = '3.1.0'
__author__ = 'Michael J. Hauan'

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

__all__ = [
    'RadiodControl',
    'allocate_ssrc',
    'discover_channels',
    'discover_channels_native',
    'discover_channels_via_control',
    'discover_radiod_services',
    'ChannelInfo',
    'StatusType',
    'Encoding',
    'Ka9qError',
    'ConnectionError',
    'CommandError',
    'ValidationError',
    'RTPRecorder',
    'RecorderState',
    'RTPHeader',
    'RecordingMetrics',
    'parse_rtp_header',
    'rtp_to_wallclock',
]
