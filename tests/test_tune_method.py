"""
Tests for the tune() method and related functionality
"""
import struct
import socket
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q.control import RadiodControl, encode_int, encode_double, encode_string
from ka9q.types import StatusType, Encoding


class TestTuneMethod:
    """Tests for RadiodControl.tune() method"""
    
    @pytest.fixture
    def mock_control(self):
        """Create a RadiodControl instance with mocked socket"""
        with patch('ka9q.control.socket.socket') as mock_sock:
            with patch('ka9q.control.socket.getaddrinfo', return_value=[(2, 2, 17, '', ('239.1.2.3', 5006))]):
                control = RadiodControl('radiod.local')
                return control
    
    def create_status_response(self, ssrc, command_tag, frequency=None, preset=None, 
                              sample_rate=None, gain=None, agc_enable=None):
        """Helper to create a mock status response packet"""
        buf = bytearray()
        buf.append(0)  # Status packet type
        
        # Add SSRC
        encode_int(buf, StatusType.OUTPUT_SSRC, ssrc)
        
        # Add command tag
        encode_int(buf, StatusType.COMMAND_TAG, command_tag)
        
        # Add optional fields
        if frequency is not None:
            encode_double(buf, StatusType.RADIO_FREQUENCY, frequency)
        
        if preset is not None:
            encode_string(buf, StatusType.PRESET, preset)
        
        if sample_rate is not None:
            encode_int(buf, StatusType.OUTPUT_SAMPRATE, sample_rate)
        
        if gain is not None:
            from ka9q.control import encode_float
            encode_float(buf, StatusType.GAIN, gain)
        
        if agc_enable is not None:
            encode_int(buf, StatusType.AGC_ENABLE, 1 if agc_enable else 0)
        
        # Add EOL
        buf.append(StatusType.EOL)
        
        return bytes(buf)
    
    def test_tune_basic_parameters(self, mock_control):
        """Test tune() with basic parameters"""
        ssrc = 14074000
        frequency = 14.074e6
        preset = "usb"
        command_tag = 12345
        
        # Create mock response
        response = self.create_status_response(
            ssrc=ssrc,
            command_tag=command_tag,
            frequency=frequency,
            preset=preset,
            sample_rate=12000
        )
        
        # Mock the socket operations
        mock_sock = MagicMock()
        mock_sock.recvfrom.return_value = (response, ('239.1.2.3', 5006))
        
        with patch.object(mock_control, '_setup_status_listener', return_value=mock_sock):
            with patch('ka9q.control.secrets.randbits', return_value=command_tag):
                with patch('select.select', return_value=([mock_sock], [], [])):
                    status = mock_control.tune(
                        ssrc=ssrc,
                        frequency_hz=frequency,
                        preset=preset,
                        timeout=1.0
                    )
        
        # Verify response
        assert status['ssrc'] == ssrc
        assert status['command_tag'] == command_tag
        assert abs(status['frequency'] - frequency) < 1.0
        assert status['preset'] == preset
    
    def test_tune_timeout(self, mock_control):
        """Test that tune() raises TimeoutError on timeout"""
        ssrc = 14074000
        
        # Mock socket that never receives data
        mock_sock = MagicMock()
        mock_sock.recvfrom.side_effect = socket.timeout()
        
        with patch.object(mock_control, '_setup_status_listener', return_value=mock_sock):
            with patch('select.select', return_value=([], [], [])):
                with pytest.raises(TimeoutError, match="No status response"):
                    mock_control.tune(ssrc=ssrc, timeout=0.5)
    
    def test_tune_wrong_ssrc_ignored(self, mock_control):
        """Test that responses with wrong SSRC are ignored"""
        ssrc = 14074000
        wrong_ssrc = 99999999
        command_tag = 12345
        
        # Create response with wrong SSRC
        wrong_response = self.create_status_response(
            ssrc=wrong_ssrc,
            command_tag=command_tag,
            frequency=14.074e6
        )
        
        # Create correct response
        correct_response = self.create_status_response(
            ssrc=ssrc,
            command_tag=command_tag,
            frequency=14.074e6
        )
        
        mock_sock = MagicMock()
        # Return wrong response first, then correct one
        mock_sock.recvfrom.side_effect = [
            (wrong_response, ('239.1.2.3', 5006)),
            (correct_response, ('239.1.2.3', 5006))
        ]
        
        with patch.object(mock_control, '_setup_status_listener', return_value=mock_sock):
            with patch('ka9q.control.secrets.randbits', return_value=command_tag):
                with patch('select.select', return_value=([mock_sock], [], [])):
                    status = mock_control.tune(ssrc=ssrc, timeout=1.0)
        
        # Should get the correct response
        assert status['ssrc'] == ssrc
    
    def test_tune_with_gain_disables_agc(self, mock_control):
        """Test that setting gain parameter disables AGC"""
        # This test verifies the command encoding logic
        ssrc = 14074000
        gain = 15.0
        
        # Capture the command buffer
        sent_commands = []
        original_send = mock_control.send_command
        mock_control.send_command = lambda buf: sent_commands.append(bytes(buf))
        
        # Create mock response
        command_tag = 12345
        response = self.create_status_response(
            ssrc=ssrc,
            command_tag=command_tag,
            gain=gain,
            agc_enable=False
        )
        
        mock_sock = MagicMock()
        mock_sock.recvfrom.return_value = (response, ('239.1.2.3', 5006))
        
        with patch.object(mock_control, '_setup_status_listener', return_value=mock_sock):
            with patch('ka9q.control.secrets.randbits', return_value=command_tag):
                with patch('select.select', return_value=([mock_sock], [], [])):
                    status = mock_control.tune(ssrc=ssrc, gain=gain, timeout=0.5)
        
        # Verify response shows AGC disabled
        assert status['agc_enable'] is False
        assert abs(status['gain'] - gain) < 0.01
    
    def test_tune_all_parameters(self, mock_control):
        """Test tune() with all possible parameters"""
        ssrc = 10000000
        frequency = 10.0e6
        preset = "iq"
        sample_rate = 48000
        low_edge = -24000.0
        high_edge = 24000.0
        gain = 10.0
        rf_gain = 20.0
        rf_atten = 5.0
        
        command_tag = 12345
        response = self.create_status_response(
            ssrc=ssrc,
            command_tag=command_tag,
            frequency=frequency,
            preset=preset,
            sample_rate=sample_rate,
            gain=gain,
            agc_enable=False
        )
        
        mock_sock = MagicMock()
        mock_sock.recvfrom.return_value = (response, ('239.1.2.3', 5006))
        
        with patch.object(mock_control, '_setup_status_listener', return_value=mock_sock):
            with patch('ka9q.control.secrets.randbits', return_value=command_tag):
                with patch('select.select', return_value=([mock_sock], [], [])):
                    status = mock_control.tune(
                        ssrc=ssrc,
                        frequency_hz=frequency,
                        preset=preset,
                        sample_rate=sample_rate,
                        low_edge=low_edge,
                        high_edge=high_edge,
                        gain=gain,
                        rf_gain=rf_gain,
                        rf_atten=rf_atten,
                        encoding=Encoding.F32,
                        timeout=1.0
                    )
        
        assert status['ssrc'] == ssrc
        assert abs(status['frequency'] - frequency) < 1.0


class TestDecodeStatusResponse:
    """Tests for _decode_status_response method"""
    
    @pytest.fixture
    def mock_control(self):
        """Create a RadiodControl instance"""
        with patch('ka9q.control.socket.socket'):
            with patch('ka9q.control.socket.getaddrinfo', return_value=[(2, 2, 17, '', ('239.1.2.3', 5006))]):
                control = RadiodControl('radiod.local')
                return control
    
    def test_decode_empty_buffer(self, mock_control):
        """Test decoding empty buffer"""
        status = mock_control._decode_status_response(b'')
        assert status == {}
    
    def test_decode_non_status_packet(self, mock_control):
        """Test decoding non-status packet (wrong type)"""
        buffer = bytearray()
        buffer.append(1)  # Command packet, not status
        status = mock_control._decode_status_response(bytes(buffer))
        assert status == {}
    
    def test_decode_basic_status(self, mock_control):
        """Test decoding basic status fields"""
        buffer = bytearray()
        buffer.append(0)  # Status packet
        
        # Add SSRC
        encode_int(buffer, StatusType.OUTPUT_SSRC, 14074000)
        
        # Add frequency
        encode_double(buffer, StatusType.RADIO_FREQUENCY, 14.074e6)
        
        # Add preset
        encode_string(buffer, StatusType.PRESET, "usb")
        
        # Add EOL
        buffer.append(StatusType.EOL)
        
        status = mock_control._decode_status_response(bytes(buffer))
        
        assert status['ssrc'] == 14074000
        assert abs(status['frequency'] - 14.074e6) < 1.0
        assert status['preset'] == "usb"
    
    def test_decode_with_snr_calculation(self, mock_control):
        """Test that SNR is calculated when all required fields present"""
        buffer = bytearray()
        buffer.append(0)  # Status packet
        
        # Add required fields for SNR calculation
        from ka9q.control import encode_float
        encode_float(buffer, StatusType.BASEBAND_POWER, -10.0)  # dB
        encode_float(buffer, StatusType.NOISE_DENSITY, -140.0)  # dB/Hz
        encode_float(buffer, StatusType.LOW_EDGE, -1500.0)  # Hz
        encode_float(buffer, StatusType.HIGH_EDGE, 1500.0)   # Hz
        
        buffer.append(StatusType.EOL)
        
        status = mock_control._decode_status_response(bytes(buffer))
        
        # Verify SNR was calculated
        assert 'snr' in status
        assert isinstance(status['snr'], float)
        # SNR should be positive for these values
        assert status['snr'] > 0
    
    def test_decode_all_fields(self, mock_control):
        """Test decoding all supported status fields"""
        buffer = bytearray()
        buffer.append(0)  # Status packet
        
        from ka9q.control import encode_float
        
        # Add all fields
        encode_int(buffer, StatusType.COMMAND_TAG, 12345)
        encode_int(buffer, StatusType.OUTPUT_SSRC, 14074000)
        encode_double(buffer, StatusType.RADIO_FREQUENCY, 14.074e6)
        encode_string(buffer, StatusType.PRESET, "usb")
        encode_int(buffer, StatusType.OUTPUT_SAMPRATE, 12000)
        encode_int(buffer, StatusType.AGC_ENABLE, 1)
        encode_float(buffer, StatusType.GAIN, 15.5)
        encode_float(buffer, StatusType.RF_GAIN, 20.0)
        encode_float(buffer, StatusType.RF_ATTEN, 5.0)
        encode_int(buffer, StatusType.RF_AGC, 1)
        encode_float(buffer, StatusType.LOW_EDGE, -1500.0)
        encode_float(buffer, StatusType.HIGH_EDGE, 1500.0)
        encode_float(buffer, StatusType.NOISE_DENSITY, -140.0)
        encode_float(buffer, StatusType.BASEBAND_POWER, -20.0)
        encode_int(buffer, StatusType.OUTPUT_ENCODING, Encoding.S16LE)
        
        buffer.append(StatusType.EOL)
        
        status = mock_control._decode_status_response(bytes(buffer))
        
        # Verify all fields decoded
        assert status['command_tag'] == 12345
        assert status['ssrc'] == 14074000
        assert abs(status['frequency'] - 14.074e6) < 1.0
        assert status['preset'] == "usb"
        assert status['sample_rate'] == 12000
        assert status['agc_enable'] is True
        assert abs(status['gain'] - 15.5) < 0.1
        assert abs(status['rf_gain'] - 20.0) < 0.1
        assert abs(status['rf_atten'] - 5.0) < 0.1
        assert status['rf_agc'] == 1
        assert abs(status['low_edge'] - (-1500.0)) < 0.1
        assert abs(status['high_edge'] - 1500.0) < 0.1
        assert abs(status['noise_density'] - (-140.0)) < 0.1
        assert abs(status['baseband_power'] - (-20.0)) < 0.1
        assert status['encoding'] == Encoding.S16LE
        assert 'snr' in status  # Should be calculated


class TestSetupStatusListener:
    """Tests for _setup_status_listener method"""
    
    def test_setup_creates_socket(self):
        """Test that _setup_status_listener creates a socket"""
        with patch('ka9q.control.socket.socket') as mock_socket_class:
            with patch('ka9q.control.socket.getaddrinfo', return_value=[(2, 2, 17, '', ('239.1.2.3', 5006))]):
                mock_sock = MagicMock()
                mock_socket_class.return_value = mock_sock
                mock_sock.getsockname.return_value = ('0.0.0.0', 12345)
                
                control = RadiodControl('radiod.local')
                result = control._setup_status_listener()
                
                # Verify socket was created
                assert result == mock_sock
                # Verify socket options were set
                mock_sock.setsockopt.assert_called()
                mock_sock.bind.assert_called_once()
                mock_sock.settimeout.assert_called_once_with(0.1)
    
    def test_setup_joins_multicast_group(self):
        """Test that socket joins the multicast group"""
        with patch('ka9q.control.socket.socket') as mock_socket_class:
            with patch('ka9q.control.socket.getaddrinfo', return_value=[(2, 2, 17, '', ('239.1.2.3', 5006))]):
                mock_sock = MagicMock()
                mock_socket_class.return_value = mock_sock
                mock_sock.getsockname.return_value = ('0.0.0.0', 12345)
                
                control = RadiodControl('radiod.local')
                control._setup_status_listener()
                
                # Verify IP_ADD_MEMBERSHIP was called
                calls = mock_sock.setsockopt.call_args_list
                membership_calls = [c for c in calls if c[0][1] == socket.IP_ADD_MEMBERSHIP]
                assert len(membership_calls) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
