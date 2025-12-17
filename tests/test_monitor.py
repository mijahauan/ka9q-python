import unittest
from unittest.mock import MagicMock, patch
import time
from ka9q.monitor import ChannelMonitor
from ka9q.discovery import ChannelInfo

class TestChannelMonitor(unittest.TestCase):
    def setUp(self):
        self.control = MagicMock()
        # Mock ensure_channel to return a ChannelInfo object
        self.control.ensure_channel.return_value = ChannelInfo(
            ssrc=12345,
            preset="usb",
            sample_rate=12000,
            frequency=14.074e6,
            snr=30.0,
            multicast_address="239.1.1.1",
            port=5004
        )
        self.monitor = ChannelMonitor(self.control, check_interval=0.1)

    def tearDown(self):
        self.monitor.stop()

    def test_monitor_registration(self):
        """Verify channels are registered for monitoring"""
        ssrc = self.monitor.monitor_channel(frequency_hz=14.074e6, preset="usb")
        
        self.assertEqual(ssrc, 12345)
        self.assertIn(12345, self.monitor._monitored_channels)
        self.assertEqual(
            self.monitor._monitored_channels[12345],
            {'frequency_hz': 14.074e6, 'preset': 'usb'}
        )
        
        # Verify ensure_channel was called
        self.control.ensure_channel.assert_called_with(frequency_hz=14.074e6, preset="usb")

    def test_unmonitor(self):
        """Verify unmonitoring works"""
        ssrc = self.monitor.monitor_channel(frequency_hz=14.074e6)
        self.monitor.unmonitor_channel(ssrc)
        self.assertNotIn(ssrc, self.monitor._monitored_channels)

    @patch('ka9q.monitor.discover_channels')
    def test_recovery(self, mock_discover):
        """Verify recovery triggers when channel is missing"""
        # Register channel
        self.monitor.monitor_channel(frequency_hz=14.074e6, preset="usb")
        self.control.ensure_channel.reset_mock()
        
        # Scenario 1: Channel exists
        mock_discover.return_value = {
            12345: ChannelInfo(
                ssrc=12345, frequency=14.074e6, preset="usb", sample_rate=12000, 
                snr=0, multicast_address="239.1.1.1", port=5004
            )
        }
        
        # Run one loop cycle
        self.monitor._check_and_recover()
        
        # Should NOT call ensure_channel
        self.control.ensure_channel.assert_not_called()
        
        # Scenario 2: Channel missing (radiod restarted)
        mock_discover.return_value = {}  # Empty discovery
        
        # Run one loop cycle
        self.monitor._check_and_recover()
        
        # Should call ensure_channel to restore it
        self.control.ensure_channel.assert_called_with(frequency_hz=14.074e6, preset="usb")

if __name__ == '__main__':
    unittest.main()
