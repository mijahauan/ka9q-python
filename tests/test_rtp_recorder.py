"""
Tests for RTP recorder functionality
"""
import pytest
from ka9q.rtp_recorder import rtp_to_wallclock
from ka9q.discovery import ChannelInfo

def test_rtp_to_wallclock():
    """Test GPS time to Unix time conversion"""
    # Channel info with mocked timing
    # GPS Time: 1234567890000000000 ns (random recent-ish GPS time)
    # This corresponds to some time around 2019
    gps_time_ns = 1234567890000000000 
    
    # Constants from code
    GPS_UTC_OFFSET = 315964800
    BILLION = 1_000_000_000
    
    channel = ChannelInfo(
        ssrc=1234,
        preset="test",
        sample_rate=48000,
        frequency=100.0,
        snr=0.0,
        multicast_address="239.1.2.3",
        port=5004,
        gps_time=gps_time_ns,
        rtp_timesnap=1000
    )
    
    # Case 1: Same RTP timestamp as snapshot
    # Result should be exactly GPS time + offset
    # Expected Unix time = GPS time + Offset - Leap Seconds
    expected_unix_ns = gps_time_ns + (BILLION * (GPS_UTC_OFFSET - 18))
    expected_unix_sec = expected_unix_ns / BILLION
    
    assert rtp_to_wallclock(1000, channel) == pytest.approx(expected_unix_sec)
    
    # Case 2: One second later
    # 48000 samples later
    assert rtp_to_wallclock(1000 + 48000, channel) == pytest.approx(expected_unix_sec + 1.0)
