
from ka9q.rtp_recorder import rtp_to_wallclock
from ka9q.discovery import ChannelInfo
import time

def test_utc_conversion():
    # Current Leap Seconds (GPS - UTC) = 18 seconds
    LEAP_SECONDS = 18
    GPS_UTC_OFFSET = 315964800
    
    # Pick a known UTC time: 2024-01-01 00:00:00 UTC
    # Unix timestamp: 1704067200
    target_unix_time = 1704067200
    
    # Calculate corresponding GPS time
    # GPS = unix - offset + leap_seconds
    gps_time_seconds = target_unix_time - GPS_UTC_OFFSET + LEAP_SECONDS
    gps_time_ns = gps_time_seconds * 1_000_000_000
    
    print(f"Target Unix Time: {target_unix_time}")
    print(f"Calculated GPS Time (s): {gps_time_seconds}")
    
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
    
    # helper returns float seconds
    calculated_unix_time = rtp_to_wallclock(1000, channel)
    
    print(f"Function Result: {calculated_unix_time}")
    
    diff = calculated_unix_time - target_unix_time
    print(f"Difference (Result - Target): {diff} seconds")
    
    if abs(diff - 18.0) < 0.001:
        print("FAIL: Result is 18 seconds ahead (Missing leap second correction).")
    elif abs(diff) < 0.001:
        print("PASS: Result matches target UTC time.")
    else:
        print(f"FAIL: Unexpected difference: {diff}")

if __name__ == "__main__":
    test_utc_conversion()
