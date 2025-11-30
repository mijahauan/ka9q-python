"""
Tests for encode_socket function

This module tests the socket encoding functionality that enables
setting custom RTP destinations for radiod channels.
"""

import struct
import socket
import pytest
from ka9q.control import encode_socket
from ka9q.types import StatusType
from ka9q.exceptions import ValidationError


class TestEncodeSocket:
    """Tests for encode_socket function"""
    
    def test_encode_ipv4_address_default_port(self):
        """Test encoding IPv4 address with default RTP port"""
        buf = bytearray()
        bytes_written = encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.1.2.3")
        
        assert bytes_written == 18  # type(1) + length(1) + data(16)
        assert buf[0] == StatusType.OUTPUT_DATA_DEST_SOCKET  # type
        assert buf[1] == 16  # length
        
        # Decode the socket structure
        family = struct.unpack('>H', buf[2:4])[0]
        port = struct.unpack('>H', buf[4:6])[0]
        addr_bytes = buf[6:10]
        
        assert family == 2  # AF_INET
        assert port == 5004  # Default RTP port
        assert socket.inet_ntoa(addr_bytes) == "239.1.2.3"
    
    def test_encode_ipv4_address_custom_port(self):
        """Test encoding IPv4 address with custom port"""
        buf = bytearray()
        bytes_written = encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.1.2.3", 6789)
        
        assert bytes_written == 18
        
        # Decode port
        port = struct.unpack('>H', buf[4:6])[0]
        assert port == 6789
    
    def test_encode_multicast_address(self):
        """Test encoding typical radiod multicast address"""
        buf = bytearray()
        encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.192.1.1", 5004)
        
        addr_bytes = buf[6:10]
        assert socket.inet_ntoa(addr_bytes) == "239.192.1.1"
    
    def test_encode_localhost(self):
        """Test encoding localhost address"""
        buf = bytearray()
        encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "127.0.0.1", 5004)
        
        addr_bytes = buf[6:10]
        assert socket.inet_ntoa(addr_bytes) == "127.0.0.1"
    
    def test_encode_padding(self):
        """Test that socket structure includes proper padding"""
        buf = bytearray()
        encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.1.2.3", 5004)
        
        # Check padding bytes (last 8 bytes of the 16-byte structure)
        padding = buf[10:18]
        assert padding == b'\x00' * 8
    
    def test_invalid_ip_address(self):
        """Test that invalid IP address raises ValidationError"""
        buf = bytearray()
        
        with pytest.raises(ValidationError, match="Invalid IP address"):
            encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "999.999.999.999")
    
    def test_invalid_port_negative(self):
        """Test that negative port raises ValidationError"""
        buf = bytearray()
        
        with pytest.raises(ValidationError, match="Invalid port"):
            encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.1.2.3", -1)
    
    def test_invalid_port_too_large(self):
        """Test that port > 65535 raises ValidationError"""
        buf = bytearray()
        
        with pytest.raises(ValidationError, match="Invalid port"):
            encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.1.2.3", 65536)
    
    def test_malformed_ip_address(self):
        """Test that malformed IP raises ValidationError"""
        buf = bytearray()
        
        with pytest.raises(ValidationError, match="Invalid IP address"):
            encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "not.an.ip")
    
    def test_empty_address(self):
        """Test that empty address raises ValidationError"""
        buf = bytearray()
        
        with pytest.raises(ValidationError):
            encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "")
    
    def test_roundtrip_decode(self):
        """Test encoding then decoding produces original values"""
        # This test assumes decode_socket exists and works correctly
        from ka9q.control import decode_socket
        
        buf = bytearray()
        encode_socket(buf, StatusType.OUTPUT_DATA_DEST_SOCKET, "239.192.1.100", 5006)
        
        # Skip type and length bytes, decode the socket data
        socket_data = buf[2:]
        result = decode_socket(socket_data, 16)
        
        assert result['family'] == 'IPv4'
        assert result['address'] == '239.192.1.100'
        assert result['port'] == 5006
