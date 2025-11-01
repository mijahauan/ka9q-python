"""
ka9q: Python interface for ka9q-radio

A general-purpose library for controlling ka9q-radio channels and streams.
No assumptions about your application - works for everything from AM radio
listening to SuperDARN radar monitoring.

Basic usage:
    from ka9q import RadiodControl
    
    control = RadiodControl("radiod.local")
    control.create_channel(
        ssrc=10000000,
        frequency_hz=10.0e6,
        preset="am",
        sample_rate=12000
    )
"""

__version__ = '1.0.0'
__author__ = 'GRAPE Signal Recorder Project'

from .control import RadiodControl
from .discovery import discover_channels, discover_radiod_services, ChannelInfo
from .types import StatusType
from .exceptions import Ka9qError, ConnectionError, CommandError

__all__ = [
    'RadiodControl',
    'discover_channels',
    'discover_radiod_services',
    'ChannelInfo',
    'StatusType',
    'Ka9qError',
    'ConnectionError',
    'CommandError',
]
