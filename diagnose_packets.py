#!/usr/bin/env python3
"""
Diagnostic script to analyze RTP packet sizes from radiod.

This script captures packets and reports:
- Actual payload sizes received
- Expected vs actual sample counts
- Any variability in packet sizes
"""

import socket
import struct
import sys
import time
from collections import Counter
from ka9q import discover_channels

def parse_rtp_header(data: bytes):
    """Parse RTP header, return (header_len, ssrc, timestamp, sequence)"""
    if len(data) < 12:
        return None
    first_byte = data[0]
    csrc_count = first_byte & 0x0F
    sequence = struct.unpack('>H', data[2:4])[0]
    timestamp = struct.unpack('>I', data[4:8])[0]
    ssrc = struct.unpack('>I', data[8:12])[0]
    header_len = 12 + (4 * csrc_count)
    return header_len, ssrc, timestamp, sequence

def diagnose_stream(radiod_address: str, ssrc: int = None, duration: float = 10.0):
    """
    Capture packets from a radiod stream and analyze sizes.
    
    Args:
        radiod_address: Address of radiod (e.g., 'radiod.local')
        ssrc: Specific SSRC to filter (None = first found)
        duration: How long to capture (seconds)
    """
    print(f"Discovering channels on {radiod_address}...")
    channels = discover_channels(radiod_address, timeout=5.0)
    
    if not channels:
        print("ERROR: No channels found!")
        return
    
    print(f"Found {len(channels)} channel(s):")
    for ch_ssrc, ch in channels.items():
        print(f"  SSRC {ch_ssrc}: {ch.frequency/1e6:.3f} MHz, {ch.preset}, {ch.sample_rate} Hz")
    
    # Select channel
    if ssrc is None:
        ssrc = list(channels.keys())[0]
        print(f"\nUsing first channel: SSRC {ssrc}")
    
    if ssrc not in channels:
        print(f"ERROR: SSRC {ssrc} not found!")
        return
    
    channel = channels[ssrc]
    print(f"\nChannel details:")
    print(f"  Frequency: {channel.frequency/1e6:.6f} MHz")
    print(f"  Preset: {channel.preset}")
    print(f"  Sample rate: {channel.sample_rate} Hz")
    print(f"  Multicast: {channel.multicast_address}:{channel.port}")
    
    # Calculate expected payload size
    is_iq = channel.preset.lower() in ('iq', 'spectrum')
    
    # radiod typically sends 20ms of audio or equivalent IQ
    # At 16kHz audio: 320 samples * 4 bytes = 1280 bytes
    # At 16kHz IQ: 160 complex samples * 8 bytes = 1280 bytes (or 320 floats * 4 = 1280)
    expected_samples_per_20ms = channel.sample_rate // 50  # 20ms worth
    
    if is_iq:
        # IQ: complex64 = 8 bytes per sample
        expected_payload_bytes = expected_samples_per_20ms * 8
        sample_type = "complex64 (IQ)"
    else:
        # Audio: float32 = 4 bytes per sample
        expected_payload_bytes = expected_samples_per_20ms * 4
        sample_type = "float32 (audio)"
    
    print(f"\nExpected packet structure:")
    print(f"  Sample type: {sample_type}")
    print(f"  Samples per 20ms: {expected_samples_per_20ms}")
    print(f"  Expected payload: {expected_payload_bytes} bytes")
    
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', channel.port))
    
    # Join multicast
    mreq = struct.pack('4s4s', 
                       socket.inet_aton(channel.multicast_address),
                       socket.inet_aton('0.0.0.0'))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(1.0)
    
    print(f"\nCapturing packets for {duration} seconds...")
    
    # Collect stats
    payload_sizes = Counter()
    total_packets = 0
    filtered_packets = 0
    timestamps = []
    sequences = []
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            try:
                data, addr = sock.recvfrom(8192)
                total_packets += 1
                
                parsed = parse_rtp_header(data)
                if parsed is None:
                    continue
                
                header_len, pkt_ssrc, timestamp, sequence = parsed
                
                # Filter by SSRC
                if pkt_ssrc != ssrc:
                    continue
                
                filtered_packets += 1
                payload = data[header_len:]
                payload_sizes[len(payload)] += 1
                timestamps.append(timestamp)
                sequences.append(sequence)
                
            except socket.timeout:
                continue
    
    finally:
        sock.close()
    
    # Report results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Total packets received: {total_packets}")
    print(f"Packets for SSRC {ssrc}: {filtered_packets}")
    
    if not payload_sizes:
        print("ERROR: No packets captured for this SSRC!")
        return
    
    print(f"\nPayload size distribution:")
    for size, count in sorted(payload_sizes.items()):
        pct = 100 * count / filtered_packets
        
        # Calculate what this size means
        if is_iq:
            samples = size // 8  # complex64
            floats = size // 4
            interpretation = f"{samples} complex samples ({floats} floats)"
        else:
            samples = size // 4  # float32
            interpretation = f"{samples} float32 samples"
        
        match = "✓ EXPECTED" if size == expected_payload_bytes else "⚠ UNEXPECTED"
        print(f"  {size:5d} bytes: {count:6d} packets ({pct:5.1f}%) - {interpretation} {match}")
    
    # Timestamp analysis
    if len(timestamps) > 1:
        print(f"\nTimestamp analysis:")
        ts_diffs = []
        for i in range(1, len(timestamps)):
            # Handle 32-bit wraparound
            diff = (timestamps[i] - timestamps[i-1]) & 0xFFFFFFFF
            if diff > 0x80000000:
                diff -= 0x100000000
            ts_diffs.append(diff)
        
        ts_diff_counts = Counter(ts_diffs)
        print(f"  Timestamp increments (samples between packets):")
        for diff, count in sorted(ts_diff_counts.items()):
            pct = 100 * count / len(ts_diffs)
            duration_ms = 1000 * diff / channel.sample_rate
            print(f"    {diff:6d} samples ({duration_ms:6.2f} ms): {count:5d} ({pct:5.1f}%)")
    
    # Sequence analysis
    if len(sequences) > 1:
        print(f"\nSequence analysis:")
        seq_gaps = 0
        for i in range(1, len(sequences)):
            expected = (sequences[i-1] + 1) & 0xFFFF
            if sequences[i] != expected:
                seq_gaps += 1
        print(f"  Sequence gaps detected: {seq_gaps}")
    
    print(f"\n{'='*60}")
    if len(payload_sizes) == 1 and list(payload_sizes.keys())[0] == expected_payload_bytes:
        print("✓ All packets have expected size - radiod output looks correct")
    else:
        print("⚠ Variable or unexpected packet sizes detected!")
        print("  This may indicate:")
        print("  - Mismatched samples_per_packet configuration")
        print("  - Different encoding than expected")
        print("  - Multiple streams on same multicast group")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diagnose_packets.py <radiod_address> [ssrc] [duration]")
        print("Example: python diagnose_packets.py radiod.local")
        print("Example: python diagnose_packets.py radiod.local 10000000 30")
        sys.exit(1)
    
    radiod = sys.argv[1]
    ssrc = int(sys.argv[2]) if len(sys.argv) > 2 else None
    duration = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    
    diagnose_stream(radiod, ssrc, duration)
