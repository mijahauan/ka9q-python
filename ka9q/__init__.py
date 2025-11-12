"""
ka9q: Python interface for ka9q-radio

A general-purpose library for controlling ka9q-radio channels and streams.
No assumptions about your application - works for everything from AM radio
listening to SuperDARN radar monitoring.

Basic usage:
    from ka9q import RadiodControl
    
    # Use context manager for automatic cleanup
    with RadiodControl("radiod.local") as control:
        control.create_channel(
            ssrc=10000000,
            frequency_hz=10.0e6,
            preset="am",
            sample_rate=12000
        )
"""

__version__ = '2.0.0'
__author__ = 'Michael J. Hauan'

from .control import RadiodControl
from .discovery import (
    discover_channels,
    discover_channels_native,
    discover_channels_via_control,
    discover_radiod_services,
    ChannelInfo
)
from .types import StatusType, Encoding
from .exceptions import Ka9qError, ConnectionError, CommandError, ValidationError

__all__ = [
    'RadiodControl',
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
]
