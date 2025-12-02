#!/usr/bin/env python3
"""
Unit tests for native channel discovery

Tests the discover_channels_native() function without requiring a live radiod.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import socket
import struct

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import discover_channels_native, discover_channels, ChannelInfo
from ka9q.discovery import _decode_escape_sequences
from ka9q.types import StatusType


class TestNativeDiscovery(unittest.TestCase):
    """Test native Python discovery implementation"""
    
    def test_import_functions(self):
        """Test that all discovery functions can be imported"""
        from ka9q import (
            discover_channels,
            discover_channels_native,
            discover_channels_via_control
        )
        
        # Verify they're callable
        self.assertTrue(callable(discover_channels))
        self.assertTrue(callable(discover_channels_native))
        self.assertTrue(callable(discover_channels_via_control))
    
    def test_channel_info_structure(self):
        """Test ChannelInfo dataclass structure"""
        channel = ChannelInfo(
            ssrc=12345678,
            preset="usb",
            sample_rate=12000,
            frequency=14.074e6,
            snr=15.5,
            multicast_address="239.1.2.3",
            port=5004
        )
        
        self.assertEqual(channel.ssrc, 12345678)
        self.assertEqual(channel.preset, "usb")
        self.assertEqual(channel.sample_rate, 12000)
        self.assertEqual(channel.frequency, 14.074e6)
        self.assertEqual(channel.snr, 15.5)
        self.assertEqual(channel.multicast_address, "239.1.2.3")
        self.assertEqual(channel.port, 5004)
    
    @patch('ka9q.control.RadiodControl')
    @patch('ka9q.discovery.resolve_multicast_address')
    @patch('ka9q.discovery._create_status_listener_socket')
    def test_native_discovery_no_packets(self, mock_create_socket, mock_resolve, mock_control_class):
        """Test native discovery when no packets are received"""
        # Mock address resolution
        mock_resolve.return_value = "239.1.2.3"
        
        # Mock socket that returns no data (times out)
        mock_socket = MagicMock()
        mock_create_socket.return_value = mock_socket
        
        # Mock RadiodControl - configure __new__ to return our mock
        mock_control = MagicMock()
        mock_control.status_mcast_addr = "239.1.2.3"
        mock_control._decode_status_response = MagicMock(return_value={})
        mock_control_class.__new__.return_value = mock_control
        
        # Mock select to always return no data
        with patch('ka9q.discovery.select.select', return_value=([], [], [])):
            channels = discover_channels_native("test.local", listen_duration=0.5)
        
        # Should return empty dict
        self.assertEqual(channels, {})
        
        # Verify cleanup
        mock_socket.close.assert_called_once()
    
    @patch('ka9q.discovery.resolve_multicast_address')
    @patch('ka9q.discovery._create_status_listener_socket')
    @patch('ka9q.discovery.select.select')
    def test_native_discovery_with_valid_packet(self, mock_select, mock_create_socket, mock_resolve):
        """Test native discovery with a valid status packet"""
        # Mock address resolution
        mock_resolve.return_value = "239.1.2.3"
        
        # Mock socket
        mock_socket = MagicMock()
        mock_create_socket.return_value = mock_socket
        
        # Use real RadiodControl but intercept decode
        from ka9q.control import RadiodControl
        original_decode = RadiodControl._decode_status_response
        
        # Create a mock status packet
        status_dict = {
            'ssrc': 14074000,
            'frequency': 14.074e6,
            'preset': 'usb',
            'sample_rate': 12000,
            'snr': 12.5,
            'destination': {'address': '239.1.2.3', 'port': 5004}
        }
        
        # Mock socket.recvfrom to return a status packet (type=0)
        mock_packet = b'\x00' + b'\x00' * 50  # Status packet (type 0)
        mock_socket.recvfrom.return_value = (mock_packet, ('239.1.2.3', 5006))
        
        # Mock select to return data once, then timeout
        call_count = [0]
        def mock_select_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return ([mock_socket], [], [])  # Data available
            else:
                return ([], [], [])  # No more data (timeout loop)
        
        mock_select.side_effect = mock_select_side_effect
        
        # Run discovery with short duration
        # Mock time to control loop - need enough values for all time.time() calls
        time_values = [0.0, 0.1, 0.2, 1.0, 1.0, 1.0, 1.0]  # Enough for loop + logging
        with patch.object(RadiodControl, '_decode_status_response', return_value=status_dict):
            with patch('ka9q.discovery.time.time', side_effect=time_values):
                channels = discover_channels_native("test.local", listen_duration=0.5)
        
        # Should find one channel
        self.assertEqual(len(channels), 1)
        self.assertIn(14074000, channels)
        
        channel = channels[14074000]
        self.assertEqual(channel.frequency, 14.074e6)
        self.assertEqual(channel.preset, 'usb')
        self.assertEqual(channel.sample_rate, 12000)
        self.assertAlmostEqual(channel.snr, 12.5)
    
    @patch('ka9q.control.RadiodControl')
    @patch('ka9q.discovery.select.select')
    def test_native_discovery_skips_non_status_packets(self, mock_select, mock_control_class):
        """Test that non-status packets are skipped"""
        # Mock RadiodControl instance
        mock_control = MagicMock()
        mock_control_class.return_value = mock_control
        
        # Mock socket
        mock_socket = MagicMock()
        mock_control._setup_status_listener.return_value = mock_socket
        
        # Mock socket.recvfrom to return command packets (type=1)
        mock_packet = b'\x01' + b'\x00' * 50  # Command packet (type 1), not status
        mock_socket.recvfrom.return_value = (mock_packet, ('239.1.2.3', 5006))
        
        # Mock select to return data once
        mock_select.return_value = ([mock_socket], [], [])
        
        # Run discovery with very short duration
        with patch('ka9q.discovery.time.time', side_effect=[0, 1.0]):
            channels = discover_channels_native("test.local", listen_duration=0.1)
        
        # Should find no channels (packet skipped)
        self.assertEqual(len(channels), 0)
        
        # Verify decode was never called (packet was skipped)
        mock_control._decode_status_response.assert_not_called()
    
    @patch('ka9q.discovery.discover_channels_native')
    @patch('ka9q.discovery.discover_channels_via_control')
    def test_discover_channels_fallback(self, mock_control, mock_native):
        """Test that discover_channels falls back to control utility"""
        # Native returns empty
        mock_native.return_value = {}
        
        # Control returns channels
        mock_control.return_value = {
            12345: ChannelInfo(12345, 'usb', 12000, 14.0e6, 10.0, '239.1.2.3', 5004)
        }
        
        # Call with native enabled (default)
        channels = discover_channels("test.local", use_native=True)
        
        # Should have called both
        mock_native.assert_called_once()
        mock_control.assert_called_once()
        
        # Should return control utility results
        self.assertEqual(len(channels), 1)
    
    @patch('ka9q.discovery.discover_channels_native')
    @patch('ka9q.discovery.discover_channels_via_control')
    def test_discover_channels_no_fallback_if_found(self, mock_control, mock_native):
        """Test that discover_channels doesn't fall back if native finds channels"""
        # Native returns channels
        mock_native.return_value = {
            12345: ChannelInfo(12345, 'usb', 12000, 14.0e6, 10.0, '239.1.2.3', 5004)
        }
        
        # Call with native enabled
        channels = discover_channels("test.local", use_native=True)
        
        # Should only call native
        mock_native.assert_called_once()
        mock_control.assert_not_called()
        
        # Should return native results
        self.assertEqual(len(channels), 1)
    
    @patch('ka9q.discovery.discover_channels_via_control')
    def test_discover_channels_force_control(self, mock_control):
        """Test forcing control utility (skipping native)"""
        mock_control.return_value = {}
        
        # Call with native disabled
        channels = discover_channels("test.local", use_native=False)
        
        # Should only call control utility
        mock_control.assert_called_once()
    
    def test_discover_channels_parameters(self):
        """Test that parameters are passed correctly"""
        # This just tests the function signature
        try:
            # Should accept these parameters without error
            from ka9q import discover_channels
            
            # Test parameter types
            self.assertTrue(callable(discover_channels))
            
            # Check function signature has expected parameters
            import inspect
            sig = inspect.signature(discover_channels)
            params = list(sig.parameters.keys())
            
            self.assertIn('status_address', params)
            self.assertIn('listen_duration', params)
            self.assertIn('use_native', params)
            
        except Exception as e:
            self.fail(f"Parameter check failed: {e}")
    
    def test_decode_escape_sequences_decimal(self):
        """Test decoding of decimal escape sequences from avahi-browse"""
        # Test decimal 032 (space character, ASCII 32)
        result = _decode_escape_sequences(r"ACO G\032test")
        self.assertEqual(result, "ACO G test")
        
        # Test decimal 064 (@ character, ASCII 64)
        result = _decode_escape_sequences(r"ACO\064test")
        self.assertEqual(result, "ACO@test")
        
        # Test multiple escape sequences
        result = _decode_escape_sequences(r"ACO G\032\064EM38ww\032with\032SAS2")
        self.assertEqual(result, "ACO G @EM38ww with SAS2")
    
    def test_decode_escape_sequences_real_world(self):
        """Test with real-world service names from avahi-browse"""
        test_cases = [
            (r"ACO G\032\064EM38ww\032with\032SAS2", "ACO G @EM38ww with SAS2"),
            (r"ACO G\032\064EM38ww\032with\032T3FD", "ACO G @EM38ww with T3FD"),
            (r"ACO G\032\064EM38ww\032with\032airspy", "ACO G @EM38ww with airspy"),
            (r"ACO G\032\064EM38ww\032with\032airspyhf", "ACO G @EM38ww with airspyhf"),
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input=input_str):
                result = _decode_escape_sequences(input_str)
                self.assertEqual(result, expected)
    
    def test_decode_escape_sequences_no_escapes(self):
        """Test that strings without escapes are unchanged"""
        test_strings = [
            "normal_string",
            "string with spaces",
            "string-with-dashes",
            "radiod.local",
        ]
        
        for test_str in test_strings:
            with self.subTest(input=test_str):
                result = _decode_escape_sequences(test_str)
                self.assertEqual(result, test_str)
    
    def test_decode_escape_sequences_control_chars(self):
        """Test that control characters are replaced with spaces"""
        # Test various control characters (< 32) - using decimal values
        result = _decode_escape_sequences(r"\000\001\010\031")
        # All control chars should become spaces
        self.assertEqual(result, "    ")
        
        # Test DEL character (127 decimal)
        result = _decode_escape_sequences(r"\127")
        self.assertEqual(result, " ")


class TestDiscoveryIntegration(unittest.TestCase):
    """Integration tests that can run without radiod"""
    
    def test_no_radiod_doesnt_crash(self):
        """Test that discovery doesn't crash when radiod isn't available"""
        try:
            # This should not raise an exception, just return empty
            channels = discover_channels_native("nonexistent.local", listen_duration=0.1)
            # Should return empty dict or raise controlled exception
            self.assertIsInstance(channels, dict)
        except Exception as e:
            # If it raises, should be a connection error
            self.assertIn("radiod", str(e).lower())
    
    def test_invalid_address_handling(self):
        """Test handling of invalid addresses"""
        try:
            channels = discover_channels_native("invalid..address", listen_duration=0.1)
            # Should handle gracefully
            self.assertIsInstance(channels, dict)
        except Exception:
            # Exception is acceptable for invalid address
            pass


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestNativeDiscovery))
    suite.addTests(loader.loadTestsFromTestCase(TestDiscoveryIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
