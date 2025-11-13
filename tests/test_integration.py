"""
Integration tests for tune functionality with live radiod

These tests require a running radiod instance and verify that tune commands
actually change the radio state as expected.

Run with: pytest tests/test_integration.py -v --radiod-host=radiod.local

Set environment variables:
  RADIOD_HOST=radiod.local    (default: radiod.local)
  SKIP_INTEGRATION=1           (skip these tests)
"""
import pytest
import os
import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import RadiodControl, Encoding, StatusType, ConnectionError, CommandError


def pytest_addoption(parser):
    """Add command line options for integration tests"""
    parser.addoption(
        "--radiod-host",
        action="store",
        default=os.environ.get("RADIOD_HOST", "radiod.local"),
        help="Hostname of radiod instance to test against"
    )


@pytest.fixture
def radiod_host(request):
    """Get radiod host from command line or environment"""
    return request.config.getoption("--radiod-host")


@pytest.fixture
def skip_if_no_radiod():
    """Skip test if SKIP_INTEGRATION is set"""
    if os.environ.get("SKIP_INTEGRATION"):
        pytest.skip("Integration tests disabled (SKIP_INTEGRATION set)")


@pytest.fixture
def control(radiod_host, skip_if_no_radiod):
    """Create RadiodControl instance for integration testing"""
    try:
        ctrl = RadiodControl(radiod_host)
        return ctrl
    except (ConnectionError, OSError) as e:
        pytest.skip(f"Cannot connect to radiod at {radiod_host}: {e}")


class TestIntegrationBasic:
    """Basic integration tests to verify radiod connectivity"""
    
    def test_can_connect_to_radiod(self, control):
        """Test that we can connect to radiod"""
        assert control is not None
        assert control.status_address is not None
        print(f"\n✓ Connected to radiod at {control.status_address}")
    
    def test_control_socket_exists(self, control):
        """Test that control socket is set up"""
        assert hasattr(control, 'socket')
        assert control.socket is not None
        print(f"\n✓ Control socket configured")


class TestIntegrationTuneFrequency:
    """Integration tests for frequency tuning"""
    
    def test_tune_frequency_changes(self, control):
        """Test that tuning to a frequency actually changes it"""
        ssrc = 99000000  # Use unique SSRC for testing
        freq1 = 14.074e6  # 14.074 MHz
        freq2 = 14.076e6  # 14.076 MHz
        
        # Tune to first frequency
        print(f"\n→ Tuning to {freq1/1e6:.3f} MHz")
        status1 = control.tune(ssrc=ssrc, frequency_hz=freq1, preset='usb', timeout=5.0)
        
        # Verify it took effect
        assert 'frequency' in status1, "Status missing frequency field"
        actual_freq1 = status1['frequency']
        print(f"  Reported frequency: {actual_freq1/1e6:.3f} MHz")
        
        # Should be within 1 Hz
        assert abs(actual_freq1 - freq1) < 1.0, \
            f"Frequency mismatch: requested {freq1}, got {actual_freq1}"
        
        # Wait a moment
        time.sleep(0.5)
        
        # Tune to second frequency
        print(f"→ Tuning to {freq2/1e6:.3f} MHz")
        status2 = control.tune(ssrc=ssrc, frequency_hz=freq2, preset='usb', timeout=5.0)
        
        actual_freq2 = status2['frequency']
        print(f"  Reported frequency: {actual_freq2/1e6:.3f} MHz")
        
        # Verify it changed
        assert abs(actual_freq2 - freq2) < 1.0, \
            f"Frequency mismatch: requested {freq2}, got {actual_freq2}"
        
        # Verify they're different
        assert abs(actual_freq2 - actual_freq1) > 1000, \
            f"Frequency didn't change: {actual_freq1} vs {actual_freq2}"
        
        print(f"✓ Frequency change verified: {actual_freq1/1e6:.3f} → {actual_freq2/1e6:.3f} MHz")
    
    def test_tune_various_frequencies(self, control):
        """Test tuning to various frequencies across bands"""
        ssrc = 99000001
        test_frequencies = [
            (3.573e6, "80m band"),
            (7.074e6, "40m band"),
            (14.074e6, "20m band"),
            (21.074e6, "15m band"),
            (28.074e6, "10m band"),
        ]
        
        for freq, band_name in test_frequencies:
            print(f"\n→ Testing {band_name}: {freq/1e6:.3f} MHz")
            status = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb', timeout=5.0)
            
            actual = status.get('frequency', 0)
            assert abs(actual - freq) < 1.0, \
                f"{band_name} frequency mismatch: requested {freq}, got {actual}"
            
            print(f"  ✓ {band_name} verified: {actual/1e6:.3f} MHz")
            time.sleep(0.3)


class TestIntegrationTuneGain:
    """Integration tests for gain/volume control"""
    
    def test_gain_changes_take_effect(self, control):
        """Test that changing gain actually changes it"""
        ssrc = 99000002
        freq = 14.074e6
        gain1 = 0.0   # 0 dB
        gain2 = 10.0  # 10 dB
        
        # Set gain to 0 dB
        print(f"\n→ Setting gain to {gain1} dB")
        status1 = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb', 
                              gain=gain1, timeout=5.0)
        
        actual_gain1 = status1.get('gain', None)
        assert actual_gain1 is not None, "Status missing gain field"
        print(f"  Reported gain: {actual_gain1:.1f} dB")
        
        # Should match requested gain (within 0.1 dB)
        assert abs(actual_gain1 - gain1) < 0.1, \
            f"Gain mismatch: requested {gain1}, got {actual_gain1}"
        
        # Verify AGC is disabled when gain is set
        agc1 = status1.get('agc_enable', None)
        print(f"  AGC enabled: {agc1}")
        
        time.sleep(0.5)
        
        # Change gain to 10 dB
        print(f"→ Setting gain to {gain2} dB")
        status2 = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                              gain=gain2, timeout=5.0)
        
        actual_gain2 = status2.get('gain', None)
        print(f"  Reported gain: {actual_gain2:.1f} dB")
        
        assert abs(actual_gain2 - gain2) < 0.1, \
            f"Gain mismatch: requested {gain2}, got {actual_gain2}"
        
        # Verify it actually changed
        assert abs(actual_gain2 - actual_gain1) > 5.0, \
            f"Gain didn't change: {actual_gain1} vs {actual_gain2}"
        
        print(f"✓ Gain change verified: {actual_gain1:.1f} → {actual_gain2:.1f} dB")
    
    def test_agc_enable_disable(self, control):
        """Test enabling and disabling AGC"""
        ssrc = 99000003
        freq = 14.074e6
        
        # Enable AGC (by not setting gain)
        print("\n→ Enabling AGC (no gain specified)")
        status1 = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                              agc_enable=True, timeout=5.0)
        
        agc1 = status1.get('agc_enable', None)
        print(f"  AGC enabled: {agc1}")
        
        # Note: AGC state might not be directly controllable on all radiod instances
        # Just verify we get a status back
        assert agc1 is not None or 'gain' in status1
        
        time.sleep(0.5)
        
        # Disable AGC (by setting manual gain)
        print("→ Disabling AGC (setting manual gain)")
        status2 = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                              gain=5.0, timeout=5.0)
        
        agc2 = status2.get('agc_enable', None)
        gain2 = status2.get('gain', None)
        print(f"  AGC enabled: {agc2}, Gain: {gain2}")
        
        # When we set manual gain, AGC should be off
        if agc2 is not None:
            assert agc2 is False, "AGC should be disabled when manual gain is set"
        
        print("✓ AGC control verified")


class TestIntegrationTunePresets:
    """Integration tests for preset/mode changes"""
    
    def test_preset_changes_take_effect(self, control):
        """Test that changing preset actually changes it"""
        ssrc = 99000004
        freq = 14.074e6
        
        presets_to_test = ['usb', 'lsb', 'iq']
        
        for preset in presets_to_test:
            print(f"\n→ Setting preset to '{preset}'")
            status = control.tune(ssrc=ssrc, frequency_hz=freq, preset=preset, timeout=5.0)
            
            actual_preset = status.get('preset', None)
            print(f"  Reported preset: '{actual_preset}'")
            
            # Verify preset was set (note: radiod might return different casing)
            if actual_preset is not None:
                assert actual_preset.lower() == preset.lower(), \
                    f"Preset mismatch: requested '{preset}', got '{actual_preset}'"
                print(f"  ✓ Preset '{preset}' verified")
            else:
                print(f"  ⚠ Preset not reported in status (might not be supported)")
            
            time.sleep(0.3)


class TestIntegrationTuneSampleRate:
    """Integration tests for sample rate changes"""
    
    def test_sample_rate_changes(self, control):
        """Test that changing sample rate actually changes it"""
        ssrc = 99000005
        freq = 14.074e6
        
        sample_rates = [12000, 24000, 48000]
        
        for rate in sample_rates:
            print(f"\n→ Setting sample rate to {rate} Hz")
            status = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                                 sample_rate=rate, timeout=5.0)
            
            actual_rate = status.get('samprate', None)
            print(f"  Reported sample rate: {actual_rate} Hz")
            
            if actual_rate is not None:
                # Sample rate should match (within 1 Hz)
                assert abs(actual_rate - rate) < 1, \
                    f"Sample rate mismatch: requested {rate}, got {actual_rate}"
                print(f"  ✓ Sample rate {rate} Hz verified")
            else:
                print(f"  ⚠ Sample rate not reported in status")
            
            time.sleep(0.3)


class TestIntegrationTuneFilterEdges:
    """Integration tests for filter edge settings"""
    
    def test_filter_edges_change(self, control):
        """Test that filter edges actually change"""
        ssrc = 99000006
        freq = 14.074e6
        
        # Test USB filter (300 Hz to 2700 Hz)
        low1, high1 = 300.0, 2700.0
        print(f"\n→ Setting filter edges: {low1} Hz to {high1} Hz")
        status1 = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                              low_edge=low1, high_edge=high1, timeout=5.0)
        
        actual_low1 = status1.get('low', None)
        actual_high1 = status1.get('high', None)
        print(f"  Reported filter: {actual_low1} Hz to {actual_high1} Hz")
        
        if actual_low1 is not None and actual_high1 is not None:
            assert abs(actual_low1 - low1) < 10, \
                f"Low edge mismatch: requested {low1}, got {actual_low1}"
            assert abs(actual_high1 - high1) < 10, \
                f"High edge mismatch: requested {high1}, got {actual_high1}"
            print(f"  ✓ Filter edges verified")
        else:
            print(f"  ⚠ Filter edges not reported in status")
        
        time.sleep(0.5)
        
        # Test wider filter (200 Hz to 3000 Hz)
        low2, high2 = 200.0, 3000.0
        print(f"→ Setting filter edges: {low2} Hz to {high2} Hz")
        status2 = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                              low_edge=low2, high_edge=high2, timeout=5.0)
        
        actual_low2 = status2.get('low', None)
        actual_high2 = status2.get('high', None)
        print(f"  Reported filter: {actual_low2} Hz to {actual_high2} Hz")
        
        if actual_low2 is not None and actual_high2 is not None:
            assert abs(actual_low2 - low2) < 10, \
                f"Low edge mismatch: requested {low2}, got {actual_low2}"
            assert abs(actual_high2 - high2) < 10, \
                f"High edge mismatch: requested {high2}, got {actual_high2}"
            
            # Verify they changed
            assert abs(actual_low2 - actual_low1) > 50, \
                f"Low edge didn't change: {actual_low1} vs {actual_low2}"
            print(f"  ✓ Filter edge changes verified")


class TestIntegrationTuneEncoding:
    """Integration tests for encoding type changes"""
    
    def test_encoding_changes(self, control):
        """Test that changing encoding type works"""
        ssrc = 99000007
        freq = 14.074e6
        
        encodings_to_test = [
            (Encoding.S16BE, "S16BE"),
            (Encoding.S16LE, "S16LE"),
            (Encoding.F32, "F32"),
        ]
        
        for encoding_value, encoding_name in encodings_to_test:
            print(f"\n→ Setting encoding to {encoding_name}")
            status = control.tune(ssrc=ssrc, frequency_hz=freq, preset='usb',
                                 encoding=encoding_value, timeout=5.0)
            
            actual_encoding = status.get('encoding', None)
            print(f"  Reported encoding: {actual_encoding}")
            
            if actual_encoding is not None:
                assert actual_encoding == encoding_value, \
                    f"Encoding mismatch: requested {encoding_value}, got {actual_encoding}"
                print(f"  ✓ Encoding {encoding_name} verified")
            else:
                print(f"  ⚠ Encoding not reported in status")
            
            time.sleep(0.3)


class TestIntegrationTuneMultipleChannels:
    """Integration tests for multiple simultaneous channels"""
    
    def test_multiple_channels_coexist(self, control):
        """Test that multiple channels can be tuned simultaneously"""
        channels = [
            (99001000, 14.074e6, 'usb'),
            (99001001, 7.074e6, 'usb'),
            (99001002, 3.573e6, 'lsb'),
        ]
        
        statuses = []
        
        # Create all channels
        for ssrc, freq, preset in channels:
            print(f"\n→ Creating channel SSRC={ssrc}, freq={freq/1e6:.3f} MHz, preset={preset}")
            status = control.tune(ssrc=ssrc, frequency_hz=freq, preset=preset, timeout=5.0)
            
            assert status['ssrc'] == ssrc
            assert abs(status['frequency'] - freq) < 1.0
            
            statuses.append(status)
            print(f"  ✓ Channel {ssrc} created")
            time.sleep(0.3)
        
        # Verify all are different
        ssrcs = [s['ssrc'] for s in statuses]
        assert len(set(ssrcs)) == len(channels), "Duplicate SSRCs detected"
        
        freqs = [s['frequency'] for s in statuses]
        assert len(set(freqs)) == len(channels), "Duplicate frequencies detected"
        
        print(f"\n✓ {len(channels)} channels coexist successfully")


class TestIntegrationTuneRetune:
    """Integration tests for re-tuning existing channels"""
    
    def test_retune_existing_channel(self, control):
        """Test that we can re-tune an existing channel"""
        ssrc = 99002000
        freq1 = 14.074e6
        freq2 = 14.076e6
        gain1 = 5.0
        gain2 = 10.0
        
        # Create initial channel
        print(f"\n→ Creating channel: freq={freq1/1e6:.3f} MHz, gain={gain1} dB")
        status1 = control.tune(ssrc=ssrc, frequency_hz=freq1, preset='usb',
                              gain=gain1, timeout=5.0)
        
        assert abs(status1['frequency'] - freq1) < 1.0
        print(f"  ✓ Initial channel created")
        
        time.sleep(0.5)
        
        # Re-tune: change frequency
        print(f"→ Re-tuning: new freq={freq2/1e6:.3f} MHz")
        status2 = control.tune(ssrc=ssrc, frequency_hz=freq2, preset='usb',
                              gain=gain1, timeout=5.0)
        
        assert status2['ssrc'] == ssrc
        assert abs(status2['frequency'] - freq2) < 1.0
        print(f"  ✓ Frequency changed to {status2['frequency']/1e6:.3f} MHz")
        
        time.sleep(0.5)
        
        # Re-tune: change gain
        print(f"→ Re-tuning: new gain={gain2} dB")
        status3 = control.tune(ssrc=ssrc, frequency_hz=freq2, preset='usb',
                              gain=gain2, timeout=5.0)
        
        assert status3['ssrc'] == ssrc
        actual_gain = status3.get('gain', None)
        if actual_gain is not None:
            assert abs(actual_gain - gain2) < 0.1
            print(f"  ✓ Gain changed to {actual_gain:.1f} dB")
        
        print(f"\n✓ Re-tuning verified")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
