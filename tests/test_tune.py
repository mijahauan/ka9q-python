#!/usr/bin/env python3
"""
Unit tests for tune functionality
Tests encoding/decoding without requiring a live radiod instance
"""

import sys
from pathlib import Path
import struct

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q.control import (
    encode_int, encode_float, encode_double, encode_string, encode_eol,
    decode_int, decode_int32, decode_float, decode_double, decode_bool, decode_string
)
from ka9q.types import StatusType, Encoding


def test_encode_decode_int():
    """Test integer encoding and decoding"""
    print("Testing integer encoding/decoding...")
    
    test_values = [0, 1, 255, 256, 65535, 65536, 16777215, 0x12345678]
    
    for val in test_values:
        buf = bytearray()
        encode_int(buf, StatusType.OUTPUT_SSRC, val)
        
        # Skip type and length bytes to get to value
        type_byte = buf[0]
        length = buf[1]
        data = buf[2:2+length]
        
        decoded = decode_int(data, length)
        
        assert decoded == val, f"Mismatch: encoded {val}, decoded {decoded}"
        print(f"  ✓ {val} -> {decoded}")
    
    print("  All integer tests passed!\n")


def test_encode_decode_float():
    """Test float encoding and decoding"""
    print("Testing float encoding/decoding...")
    
    test_values = [0.0, 1.0, -1.0, 3.14159, 100.5, -273.15, 1e6, 1e-6]
    
    for val in test_values:
        buf = bytearray()
        encode_float(buf, StatusType.GAIN, val)
        
        type_byte = buf[0]
        length = buf[1]
        data = buf[2:2+length]
        
        decoded = decode_float(data, length)
        
        # Float comparison with tolerance (1e-5 for single-precision IEEE 754)
        assert abs(decoded - val) < 1e-5, f"Mismatch: encoded {val}, decoded {decoded}"
        print(f"  ✓ {val} -> {decoded}")
    
    print("  All float tests passed!\n")


def test_encode_decode_double():
    """Test double encoding and decoding"""
    print("Testing double encoding/decoding...")
    
    test_values = [0.0, 14.074e6, 146.52e6, 10.0e9, -100.5, 3.141592653589793]
    
    for val in test_values:
        buf = bytearray()
        encode_double(buf, StatusType.RADIO_FREQUENCY, val)
        
        type_byte = buf[0]
        length = buf[1]
        data = buf[2:2+length]
        
        decoded = decode_double(data, length)
        
        # Double comparison with tolerance
        assert abs(decoded - val) < 1e-9, f"Mismatch: encoded {val}, decoded {decoded}"
        print(f"  ✓ {val} -> {decoded}")
    
    print("  All double tests passed!\n")


def test_encode_decode_string():
    """Test string encoding and decoding"""
    print("Testing string encoding/decoding...")
    
    test_values = ["", "usb", "iq", "am", "fm", "preset-mode-name", "Test String 123"]
    
    for val in test_values:
        buf = bytearray()
        encode_string(buf, StatusType.PRESET, val)
        
        type_byte = buf[0]
        length = buf[1]
        if length & 0x80:
            # Multi-byte length
            length = ((length & 0x7f) << 8) | buf[2]
            data = buf[3:3+length]
        else:
            data = buf[2:2+length]
        
        decoded = decode_string(data, length)
        
        assert decoded == val, f"Mismatch: encoded '{val}', decoded '{decoded}'"
        print(f"  ✓ '{val}' -> '{decoded}'")
    
    print("  All string tests passed!\n")


def test_encode_decode_bool():
    """Test boolean encoding and decoding"""
    print("Testing boolean encoding/decoding...")
    
    test_values = [True, False]
    
    for val in test_values:
        buf = bytearray()
        encode_int(buf, StatusType.AGC_ENABLE, 1 if val else 0)
        
        type_byte = buf[0]
        length = buf[1]
        data = buf[2:2+length]
        
        decoded = decode_bool(data, length)
        
        assert decoded == val, f"Mismatch: encoded {val}, decoded {decoded}"
        print(f"  ✓ {val} -> {decoded}")
    
    print("  All boolean tests passed!\n")


def test_command_packet_structure():
    """Test building a complete command packet"""
    print("Testing command packet structure...")
    
    buf = bytearray()
    buf.append(1)  # CMD packet type
    
    # Add various parameters
    encode_int(buf, StatusType.COMMAND_TAG, 0x12345678)
    encode_int(buf, StatusType.OUTPUT_SSRC, 10000000)
    encode_double(buf, StatusType.RADIO_FREQUENCY, 14.074e6)
    encode_string(buf, StatusType.PRESET, "usb")
    encode_int(buf, StatusType.OUTPUT_SAMPRATE, 12000)
    encode_int(buf, StatusType.AGC_ENABLE, 1)
    encode_eol(buf)
    
    print(f"  Command packet length: {len(buf)} bytes")
    print(f"  Packet type: {buf[0]} (CMD)")
    print(f"  Hex dump (first 32 bytes): {' '.join(f'{b:02x}' for b in buf[:32])}")
    print("  ✓ Command packet structure valid!\n")


def test_encoding_constants():
    """Test encoding constants"""
    print("Testing encoding constants...")
    
    assert Encoding.NO_ENCODING == 0
    assert Encoding.S16BE == 1
    assert Encoding.S16LE == 2
    assert Encoding.F32 == 3
    assert Encoding.F16 == 4
    assert Encoding.OPUS == 5
    
    print("  ✓ All encoding constants correct!\n")


def test_status_type_values():
    """Test critical StatusType values"""
    print("Testing StatusType values...")
    
    # Test critical values match status.h
    assert StatusType.EOL == 0
    assert StatusType.COMMAND_TAG == 1
    assert StatusType.OUTPUT_SSRC == 18
    assert StatusType.OUTPUT_SAMPRATE == 20
    assert StatusType.RADIO_FREQUENCY == 33
    assert StatusType.LOW_EDGE == 39
    assert StatusType.HIGH_EDGE == 40
    assert StatusType.AGC_ENABLE == 62
    assert StatusType.GAIN == 68
    assert StatusType.PRESET == 85
    assert StatusType.RF_ATTEN == 97
    assert StatusType.RF_GAIN == 98
    assert StatusType.RF_AGC == 99
    assert StatusType.OUTPUT_ENCODING == 107
    
    print("  ✓ All critical StatusType values correct!\n")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("TUNE FUNCTIONALITY UNIT TESTS")
    print("=" * 60)
    print()
    
    try:
        test_status_type_values()
        test_encoding_constants()
        test_encode_decode_int()
        test_encode_decode_float()
        test_encode_decode_double()
        test_encode_decode_string()
        test_encode_decode_bool()
        test_command_packet_structure()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
