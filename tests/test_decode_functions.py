"""
Tests for TLV decode functions
"""
import struct
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q.control import (
    decode_int, decode_int32, decode_float, decode_double,
    decode_bool, decode_string, decode_socket
)


class TestDecodeInt:
    """Tests for decode_int and decode_int32 functions"""
    
    def test_decode_zero(self):
        """Test decoding zero"""
        result = decode_int(b'', 0)
        assert result == 0
    
    def test_decode_single_byte(self):
        """Test decoding a single byte"""
        result = decode_int(b'\x42', 1)
        assert result == 0x42
    
    def test_decode_two_bytes(self):
        """Test decoding two bytes (big-endian)"""
        result = decode_int(b'\x12\x34', 2)
        assert result == 0x1234
    
    def test_decode_four_bytes(self):
        """Test decoding four bytes"""
        result = decode_int(b'\x12\x34\x56\x78', 4)
        assert result == 0x12345678
    
    def test_decode_int32_alias(self):
        """Test that decode_int32 works the same as decode_int"""
        data = b'\x12\x34\x56\x78'
        assert decode_int32(data, 4) == decode_int(data, 4)
    
    def test_decode_large_number(self):
        """Test decoding a large number"""
        # Test with 8 bytes (max for typical TLV)
        data = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        result = decode_int(data, 8)
        assert result == 0x0102030405060708


class TestDecodeFloat:
    """Tests for decode_float function"""
    
    def test_decode_zero(self):
        """Test decoding zero as float"""
        data = struct.pack('>f', 0.0)
        result = decode_float(data, 4)
        assert result == 0.0
    
    def test_decode_positive_float(self):
        """Test decoding positive float"""
        test_value = 3.14159
        data = struct.pack('>f', test_value)
        result = decode_float(data, 4)
        assert abs(result - test_value) < 0.0001
    
    def test_decode_negative_float(self):
        """Test decoding negative float"""
        test_value = -123.456
        data = struct.pack('>f', test_value)
        result = decode_float(data, 4)
        assert abs(result - test_value) < 0.001
    
    def test_decode_compressed_float(self):
        """Test decoding float with leading zeros stripped"""
        # Simulate compressed encoding (e.g., 3 bytes instead of 4)
        test_value = 1.5
        full_data = struct.pack('>f', test_value)
        # Skip leading zero byte if present
        if full_data[0] == 0:
            compressed_data = full_data[1:]
            result = decode_float(compressed_data, 3)
            assert abs(result - test_value) < 0.0001
    
    def test_decode_scientific_values(self):
        """Test decoding very large and small floats"""
        for test_value in [1e6, 1e-6, 123.456e3]:
            data = struct.pack('>f', test_value)
            result = decode_float(data, 4)
            assert abs((result - test_value) / test_value) < 0.0001


class TestDecodeDouble:
    """Tests for decode_double function"""
    
    def test_decode_zero(self):
        """Test decoding zero as double"""
        data = struct.pack('>d', 0.0)
        result = decode_double(data, 8)
        assert result == 0.0
    
    def test_decode_positive_double(self):
        """Test decoding positive double"""
        test_value = 3.14159265358979
        data = struct.pack('>d', test_value)
        result = decode_double(data, 8)
        assert abs(result - test_value) < 1e-10
    
    def test_decode_negative_double(self):
        """Test decoding negative double"""
        test_value = -123.456789012345
        data = struct.pack('>d', test_value)
        result = decode_double(data, 8)
        assert abs(result - test_value) < 1e-10
    
    def test_decode_frequency(self):
        """Test decoding typical radio frequencies"""
        frequencies = [14.074e6, 7.040e6, 146.52e6, 1.2e9]
        for freq in frequencies:
            data = struct.pack('>d', freq)
            result = decode_double(data, 8)
            assert abs(result - freq) < 0.01
    
    def test_decode_compressed_double(self):
        """Test decoding double with leading zeros stripped"""
        test_value = 100.0
        full_data = struct.pack('>d', test_value)
        # Find first non-zero byte
        start = 0
        while start < len(full_data) and full_data[start] == 0:
            start += 1
        if start > 0:
            compressed_data = full_data[start:]
            result = decode_double(compressed_data, len(compressed_data))
            assert abs(result - test_value) < 1e-10


class TestDecodeBool:
    """Tests for decode_bool function"""
    
    def test_decode_false_zero_length(self):
        """Test decoding false from zero-length data"""
        result = decode_bool(b'', 0)
        assert result is False
    
    def test_decode_false_explicit_zero(self):
        """Test decoding false from explicit zero byte"""
        result = decode_bool(b'\x00', 1)
        assert result is False
    
    def test_decode_true_one(self):
        """Test decoding true from value 1"""
        result = decode_bool(b'\x01', 1)
        assert result is True
    
    def test_decode_true_any_nonzero(self):
        """Test that any non-zero value is true"""
        for value in [1, 2, 42, 255]:
            data = bytes([value])
            result = decode_bool(data, 1)
            assert result is True


class TestDecodeString:
    """Tests for decode_string function"""
    
    def test_decode_empty_string(self):
        """Test decoding empty string"""
        result = decode_string(b'', 0)
        assert result == ''
    
    def test_decode_ascii_string(self):
        """Test decoding ASCII string"""
        test_str = "usb"
        data = test_str.encode('utf-8')
        result = decode_string(data, len(data))
        assert result == test_str
    
    def test_decode_preset_names(self):
        """Test decoding common preset names"""
        presets = ["iq", "usb", "lsb", "am", "fm", "cw"]
        for preset in presets:
            data = preset.encode('utf-8')
            result = decode_string(data, len(data))
            assert result == preset
    
    def test_decode_unicode_string(self):
        """Test decoding UTF-8 string with unicode characters"""
        test_str = "Test™"
        data = test_str.encode('utf-8')
        result = decode_string(data, len(data))
        assert result == test_str
    
    def test_decode_with_replacement_char(self):
        """Test that invalid UTF-8 is handled gracefully"""
        # Invalid UTF-8 sequence
        data = b'\xff\xfe'
        result = decode_string(data, len(data))
        # Should return something (replacement characters)
        assert isinstance(result, str)


class TestDecodeSocket:
    """Tests for decode_socket function"""
    
    def test_decode_too_short(self):
        """Test decoding socket with insufficient data"""
        result = decode_socket(b'\x00\x00', 2)
        assert result['family'] == 'unknown'
        assert result['address'] == ''
        assert result['port'] == 0
    
    def test_decode_ipv4_socket(self):
        """Test decoding IPv4 socket address"""
        # Family=2 (AF_INET), Port=5004, Address=239.1.2.3
        data = struct.pack('>HH4s', 2, 5004, b'\xef\x01\x02\x03')
        result = decode_socket(data, 8)
        assert result['family'] == 'IPv4'
        assert result['address'] == '239.1.2.3'
        assert result['port'] == 5004
    
    def test_decode_localhost_socket(self):
        """Test decoding localhost socket"""
        # Family=2 (AF_INET), Port=12345, Address=127.0.0.1
        data = struct.pack('>HH4s', 2, 12345, b'\x7f\x00\x00\x01')
        result = decode_socket(data, 8)
        assert result['family'] == 'IPv4'
        assert result['address'] == '127.0.0.1'
        assert result['port'] == 12345
    
    def test_decode_multicast_socket(self):
        """Test decoding multicast socket address"""
        # Typical ka9q-radio multicast address
        data = struct.pack('>HH4s', 2, 5006, b'\xef\x01\x01\x01')
        result = decode_socket(data, 8)
        assert result['family'] == 'IPv4'
        assert result['address'] == '239.1.1.1'
        assert result['port'] == 5006
    
    def test_decode_unknown_family(self):
        """Test decoding socket with unknown address family"""
        # Family=99 (unknown), Port=1234
        data = struct.pack('>HH4s', 99, 1234, b'\x00\x00\x00\x00')
        result = decode_socket(data, 8)
        assert 'unknown' in result['family']
        assert result['port'] == 1234


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
