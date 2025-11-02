"""
Tests for TLV encode functions
"""
import struct
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q.control import (
    encode_int, encode_int64, encode_float, encode_double, 
    encode_string, encode_eol
)
from ka9q.types import StatusType


class TestEncodeInt:
    """Tests for encode_int and encode_int64 functions"""
    
    def test_encode_zero(self):
        """Test encoding zero (compressed to zero length)"""
        buf = bytearray()
        length = encode_int(buf, StatusType.OUTPUT_SSRC, 0)
        assert length == 2  # type + length
        assert buf[0] == StatusType.OUTPUT_SSRC
        assert buf[1] == 0  # zero length
    
    def test_encode_single_byte(self):
        """Test encoding single-byte value"""
        buf = bytearray()
        length = encode_int(buf, StatusType.OUTPUT_SSRC, 42)
        assert length == 3  # type + length + value
        assert buf[0] == StatusType.OUTPUT_SSRC
        assert buf[1] == 1  # length = 1
        assert buf[2] == 42
    
    def test_encode_two_bytes(self):
        """Test encoding two-byte value"""
        buf = bytearray()
        length = encode_int(buf, StatusType.OUTPUT_SSRC, 0x1234)
        assert length == 4  # type + length + 2 value bytes
        assert buf[0] == StatusType.OUTPUT_SSRC
        assert buf[1] == 2
        assert buf[2:4] == b'\x12\x34'
    
    def test_encode_four_bytes(self):
        """Test encoding four-byte value"""
        buf = bytearray()
        length = encode_int(buf, StatusType.OUTPUT_SSRC, 0x12345678)
        assert length == 6  # type + length + 4 value bytes
        assert buf[0] == StatusType.OUTPUT_SSRC
        assert buf[1] == 4
        assert buf[2:6] == b'\x12\x34\x56\x78'
    
    def test_encode_leading_zeros_stripped(self):
        """Test that leading zeros are stripped"""
        buf = bytearray()
        # Value 0x0042 should encode as single byte 0x42
        length = encode_int(buf, StatusType.OUTPUT_SSRC, 0x0042)
        assert buf[1] == 1  # length = 1 (leading zero stripped)
        assert buf[2] == 0x42
    
    def test_encode_ssrc_values(self):
        """Test encoding typical SSRC values"""
        ssrc_values = [10000000, 14074000, 0x12345678]
        for ssrc in ssrc_values:
            buf = bytearray()
            encode_int(buf, StatusType.OUTPUT_SSRC, ssrc)
            # Verify type is correct
            assert buf[0] == StatusType.OUTPUT_SSRC


class TestEncodeFloat:
    """Tests for encode_float function"""
    
    def test_encode_zero(self):
        """Test encoding zero as float"""
        buf = bytearray()
        length = encode_float(buf, StatusType.GAIN, 0.0)
        assert buf[0] == StatusType.GAIN
        # Zero float should be compressed
        assert length >= 2
    
    def test_encode_positive_float(self):
        """Test encoding positive float"""
        buf = bytearray()
        test_value = 15.5
        length = encode_float(buf, StatusType.GAIN, test_value)
        assert buf[0] == StatusType.GAIN
        # Verify we can decode it back
        value_length = buf[1]
        if value_length & 0x80:
            # Extended length - not expected for float
            pytest.fail("Unexpected extended length for float")
        value_bytes = b'\x00' * (4 - value_length) + bytes(buf[2:2+value_length])
        decoded = struct.unpack('>f', value_bytes)[0]
        assert abs(decoded - test_value) < 0.001
    
    def test_encode_negative_float(self):
        """Test encoding negative float"""
        buf = bytearray()
        test_value = -20.0
        encode_float(buf, StatusType.GAIN, test_value)
        # Verify type
        assert buf[0] == StatusType.GAIN
        # Negative floats won't have leading zero compression
        value_length = buf[1]
        assert value_length <= 4
    
    def test_encode_frequency_offsets(self):
        """Test encoding filter edge frequencies"""
        offsets = [1500.0, -1500.0, 2400.0, -2400.0]
        for offset in offsets:
            buf = bytearray()
            encode_float(buf, StatusType.LOW_EDGE, offset)
            assert buf[0] == StatusType.LOW_EDGE


class TestEncodeDouble:
    """Tests for encode_double function"""
    
    def test_encode_zero(self):
        """Test encoding zero as double"""
        buf = bytearray()
        length = encode_double(buf, StatusType.RADIO_FREQUENCY, 0.0)
        assert buf[0] == StatusType.RADIO_FREQUENCY
        # Zero should be compressed to zero length
        assert buf[1] == 0
    
    def test_encode_frequency(self):
        """Test encoding typical radio frequencies"""
        buf = bytearray()
        test_freq = 14.074e6  # 14.074 MHz
        length = encode_double(buf, StatusType.RADIO_FREQUENCY, test_freq)
        assert buf[0] == StatusType.RADIO_FREQUENCY
        # Verify we can decode it back
        value_length = buf[1]
        if value_length & 0x80:
            pytest.fail("Unexpected extended length for double")
        value_bytes = b'\x00' * (8 - value_length) + bytes(buf[2:2+value_length])
        decoded = struct.unpack('>d', value_bytes)[0]
        assert abs(decoded - test_freq) < 1.0  # Within 1 Hz
    
    def test_encode_various_frequencies(self):
        """Test encoding various amateur radio frequencies"""
        frequencies = [
            1.8e6,      # 160m band
            3.5e6,      # 80m band
            7.0e6,      # 40m band
            14.0e6,     # 20m band
            28.0e6,     # 10m band
            50.0e6,     # 6m band
            144.0e6,    # 2m band
            440.0e6,    # 70cm band
            1296.0e6,   # 23cm band
        ]
        for freq in frequencies:
            buf = bytearray()
            encode_double(buf, StatusType.RADIO_FREQUENCY, freq)
            assert buf[0] == StatusType.RADIO_FREQUENCY
            assert len(buf) >= 2
    
    def test_encode_precision(self):
        """Test that doubles maintain precision"""
        buf = bytearray()
        test_value = 14.074123456789
        encode_double(buf, StatusType.RADIO_FREQUENCY, test_value)
        value_length = buf[1]
        value_bytes = b'\x00' * (8 - value_length) + bytes(buf[2:2+value_length])
        decoded = struct.unpack('>d', value_bytes)[0]
        # Should maintain double precision
        assert abs(decoded - test_value) < 1e-9


class TestEncodeString:
    """Tests for encode_string function"""
    
    def test_encode_empty_string(self):
        """Test encoding empty string"""
        buf = bytearray()
        length = encode_string(buf, StatusType.PRESET, "")
        assert length == 2  # type + length
        assert buf[0] == StatusType.PRESET
        assert buf[1] == 0
    
    def test_encode_short_string(self):
        """Test encoding short string"""
        buf = bytearray()
        test_str = "usb"
        length = encode_string(buf, StatusType.PRESET, test_str)
        assert buf[0] == StatusType.PRESET
        assert buf[1] == len(test_str)
        assert buf[2:2+len(test_str)].decode('utf-8') == test_str
    
    def test_encode_preset_names(self):
        """Test encoding common preset names"""
        presets = ["iq", "usb", "lsb", "am", "fm", "cw", "cwu", "cwl"]
        for preset in presets:
            buf = bytearray()
            encode_string(buf, StatusType.PRESET, preset)
            assert buf[0] == StatusType.PRESET
            encoded_length = buf[1]
            assert encoded_length == len(preset)
            assert buf[2:2+encoded_length].decode('utf-8') == preset
    
    def test_encode_unicode_string(self):
        """Test encoding UTF-8 string"""
        buf = bytearray()
        test_str = "Test™"
        length = encode_string(buf, StatusType.PRESET, test_str)
        assert buf[0] == StatusType.PRESET
        # UTF-8 encoding of ™ is 3 bytes
        expected_byte_length = len(test_str.encode('utf-8'))
        assert buf[1] == expected_byte_length
    
    def test_encode_string_single_byte_length(self):
        """Test encoding string with length < 128 (single byte length)"""
        buf = bytearray()
        test_str = "a" * 100
        length = encode_string(buf, StatusType.PRESET, test_str)
        assert buf[0] == StatusType.PRESET
        assert buf[1] == 100  # Single byte length
        assert length == 102  # type + length + data
    
    def test_encode_string_multi_byte_length(self):
        """Test encoding string with length >= 128 (multi-byte length)"""
        buf = bytearray()
        test_str = "a" * 200
        length = encode_string(buf, StatusType.PRESET, test_str)
        assert buf[0] == StatusType.PRESET
        # Multi-byte length encoding: 0x80 | (length >> 8), length & 0xff
        assert buf[1] & 0x80  # High bit set for multi-byte length
        # Decode the length
        high_byte = buf[1] & 0x7f
        low_byte = buf[2]
        decoded_length = (high_byte << 8) | low_byte
        assert decoded_length == 200
    
    def test_encode_string_too_long(self):
        """Test that very long strings raise an error"""
        buf = bytearray()
        # String longer than 65535 bytes should raise ValueError
        test_str = "a" * 70000
        with pytest.raises(ValueError, match="String too long"):
            encode_string(buf, StatusType.PRESET, test_str)


class TestEncodeEOL:
    """Tests for encode_eol function"""
    
    def test_encode_eol(self):
        """Test encoding end-of-list marker"""
        buf = bytearray()
        length = encode_eol(buf)
        assert length == 1
        assert buf[0] == StatusType.EOL
        assert len(buf) == 1


class TestEncodeDecodeRoundTrip:
    """Test that encode/decode operations are symmetric"""
    
    def test_roundtrip_int(self):
        """Test encoding and decoding integers"""
        from ka9q.control import decode_int
        
        test_values = [0, 1, 42, 255, 256, 65535, 0x12345678]
        for value in test_values:
            buf = bytearray()
            encode_int(buf, StatusType.OUTPUT_SSRC, value)
            # Extract value bytes (skip type and length)
            length = buf[1]
            value_bytes = buf[2:2+length]
            decoded = decode_int(value_bytes, length)
            assert decoded == value, f"Round-trip failed for {value}"
    
    def test_roundtrip_float(self):
        """Test encoding and decoding floats"""
        from ka9q.control import decode_float
        
        test_values = [0.0, 1.5, -20.0, 123.456, -999.999]
        for value in test_values:
            buf = bytearray()
            encode_float(buf, StatusType.GAIN, value)
            length = buf[1]
            value_bytes = buf[2:2+length]
            decoded = decode_float(value_bytes, length)
            assert abs(decoded - value) < 0.001, f"Round-trip failed for {value}"
    
    def test_roundtrip_double(self):
        """Test encoding and decoding doubles"""
        from ka9q.control import decode_double
        
        test_values = [0.0, 14.074e6, 7.040e6, 146.52e6, 1.296e9]
        for value in test_values:
            buf = bytearray()
            encode_double(buf, StatusType.RADIO_FREQUENCY, value)
            length = buf[1]
            value_bytes = buf[2:2+length]
            decoded = decode_double(value_bytes, length)
            assert abs(decoded - value) < 1.0, f"Round-trip failed for {value}"
    
    def test_roundtrip_string(self):
        """Test encoding and decoding strings"""
        from ka9q.control import decode_string
        
        test_values = ["", "usb", "lsb", "iq", "test string"]
        for value in test_values:
            buf = bytearray()
            encode_string(buf, StatusType.PRESET, value)
            # Handle multi-byte length
            length_byte = buf[1]
            if length_byte & 0x80:
                # Multi-byte length
                high = length_byte & 0x7f
                low = buf[2]
                length = (high << 8) | low
                value_bytes = buf[3:3+length]
            else:
                length = length_byte
                value_bytes = buf[2:2+length]
            decoded = decode_string(value_bytes, length)
            assert decoded == value, f"Round-trip failed for '{value}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
