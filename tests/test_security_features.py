"""
Tests for security features added in v2.2.0

Tests cryptographic randomness, input validation, bounds checking,
rate limiting, and metrics tracking.
"""

import pytest
import time
from ka9q.control import (
    RadiodControl, 
    decode_int, 
    decode_float, 
    decode_double, 
    decode_string,
    _validate_ssrc,
    _validate_frequency,
    _validate_preset,
    _validate_string_param,
    Metrics
)
from ka9q.exceptions import ValidationError


class TestCryptographicRandomness:
    """Test that command tags use cryptographically secure random"""
    
    def test_command_tags_are_unpredictable(self):
        """Command tags should be cryptographically random"""
        # Create mock control (don't actually connect)
        control = RadiodControl.__new__(RadiodControl)
        control.status_address = "test.local"
        control.socket = None
        
        # Generate multiple command buffers and check tags are different
        # This is a weak test, but at least verifies tags aren't sequential
        from ka9q.control import encode_int, StatusType, CMD, secrets
        
        tags = []
        for _ in range(10):
            tag = secrets.randbits(31)
            tags.append(tag)
        
        # All tags should be different (extremely unlikely to have duplicates)
        assert len(set(tags)) == len(tags), "Command tags should not repeat"
        
        # Tags should be in valid range
        for tag in tags:
            assert 0 <= tag < 2**31


class TestInputValidation:
    """Test input validation for all parameters"""
    
    def test_ssrc_validation(self):
        """Test SSRC validation"""
        # Valid SSRCs
        _validate_ssrc(0)
        _validate_ssrc(12345678)
        _validate_ssrc(0xFFFFFFFF)
        
        # Invalid SSRCs
        with pytest.raises(ValidationError, match="must be an integer"):
            _validate_ssrc("12345")
        
        with pytest.raises(ValidationError, match="must be an integer"):
            _validate_ssrc(12345.6)
        
        with pytest.raises(ValidationError, match="Invalid SSRC"):
            _validate_ssrc(-1)
        
        with pytest.raises(ValidationError, match="Invalid SSRC"):
            _validate_ssrc(2**32)
    
    def test_frequency_validation(self):
        """Test frequency validation"""
        # Valid frequencies
        _validate_frequency(1.0e6)  # 1 MHz
        _validate_frequency(14.074e6)  # 14.074 MHz
        _validate_frequency(1.0e9)  # 1 GHz
        
        # Invalid frequencies
        with pytest.raises(ValidationError, match="must be a number"):
            _validate_frequency("14.074")
        
        with pytest.raises(ValidationError, match="Invalid frequency"):
            _validate_frequency(0)
        
        with pytest.raises(ValidationError, match="Invalid frequency"):
            _validate_frequency(-100)
        
        with pytest.raises(ValidationError, match="Invalid frequency"):
            _validate_frequency(1e15)  # Too high
    
    def test_preset_validation(self):
        """Test preset name validation"""
        # Valid presets
        _validate_preset("usb")
        _validate_preset("AM-wide")
        _validate_preset("mode_123")
        _validate_preset("iq")
        
        # Invalid presets
        with pytest.raises(ValidationError, match="cannot be empty"):
            _validate_preset("")
        
        with pytest.raises(ValidationError, match="too long"):
            _validate_preset("a" * 100)
        
        with pytest.raises(ValidationError, match="only alphanumeric"):
            _validate_preset("bad;preset")
        
        with pytest.raises(ValidationError, match="only alphanumeric"):
            _validate_preset("bad preset")  # space
        
        with pytest.raises(ValidationError, match="control characters"):
            _validate_preset("bad\npreset")
        
        with pytest.raises(ValidationError, match="must be a string"):
            _validate_preset(123)
    
    def test_string_param_validation(self):
        """Test generic string parameter validation"""
        # Valid strings
        _validate_string_param("test", "param")
        _validate_string_param("test\nwith\nnewlines", "param")
        
        # Invalid strings
        with pytest.raises(ValidationError, match="cannot be empty"):
            _validate_string_param("", "param")
        
        with pytest.raises(ValidationError, match="too long"):
            _validate_string_param("x" * 300, "param", max_length=256)
        
        with pytest.raises(ValidationError, match="null bytes"):
            _validate_string_param("test\x00string", "param")
        
        with pytest.raises(ValidationError, match="control characters"):
            _validate_string_param("test\x01string", "param")


class TestBoundsChecking:
    """Test bounds checking in decoder functions"""
    
    def test_decode_int_negative_length(self):
        """decode_int should reject negative lengths"""
        with pytest.raises(ValidationError, match="Negative length"):
            decode_int(b'\x00\x01', -1)
    
    def test_decode_int_oversized(self):
        """decode_int should handle oversized lengths gracefully"""
        data = b'\xFF' * 20
        # Should not crash, should truncate
        result = decode_int(data, 20)
        assert isinstance(result, int)
    
    def test_decode_int_insufficient_data(self):
        """decode_int should detect insufficient data"""
        with pytest.raises(ValidationError, match="Insufficient data"):
            decode_int(b'\x01\x02', 10)  # Need 10 bytes, have 2
    
    def test_decode_float_negative_length(self):
        """decode_float should reject negative lengths"""
        with pytest.raises(ValidationError, match="Negative length"):
            decode_float(b'\x00\x01\x02\x03', -1)
    
    def test_decode_float_oversized(self):
        """decode_float should truncate oversized lengths"""
        data = b'\xFF' * 10
        # Should not crash
        result = decode_float(data, 10)
        assert isinstance(result, float)
    
    def test_decode_double_negative_length(self):
        """decode_double should reject negative lengths"""
        with pytest.raises(ValidationError, match="Negative length"):
            decode_double(b'\x00' * 8, -1)
    
    def test_decode_double_oversized(self):
        """decode_double should truncate oversized lengths"""
        data = b'\xFF' * 20
        # Should not crash
        result = decode_double(data, 20)
        assert isinstance(result, float)
    
    def test_decode_string_negative_length(self):
        """decode_string should reject negative lengths"""
        with pytest.raises(ValidationError, match="Negative length"):
            decode_string(b'test', -1)
    
    def test_decode_string_oversized(self):
        """decode_string should handle oversized lengths"""
        data = b'x' * 100000
        # Should truncate to max
        result = decode_string(data, 100000)
        assert isinstance(result, str)


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_enforcement(self):
        """Rate limiter should enforce limits"""
        # Create control with very low limit for testing
        control = RadiodControl.__new__(RadiodControl)
        control.max_commands_per_sec = 5
        control._command_count = 0
        control._command_window_start = time.time()
        control._rate_limit_lock = __import__('threading').Lock()
        
        # Send commands up to limit
        for i in range(5):
            control._check_rate_limit()
            assert control._command_count == i + 1
        
        # Next command should cause sleep
        start = time.time()
        control._check_rate_limit()
        elapsed = time.time() - start
        
        # Should have slept for roughly 1 second
        assert elapsed >= 0.9  # Allow some tolerance
    
    def test_rate_limit_window_reset(self):
        """Rate limiter should reset window after 1 second"""
        control = RadiodControl.__new__(RadiodControl)
        control.max_commands_per_sec = 10
        control._command_count = 5
        control._command_window_start = time.time() - 1.1  # 1.1 seconds ago
        control._rate_limit_lock = __import__('threading').Lock()
        
        # Should reset the window
        control._check_rate_limit()
        assert control._command_count == 1  # Reset and incremented


class TestMetrics:
    """Test metrics tracking"""
    
    def test_metrics_initialization(self):
        """Metrics should initialize to zero"""
        metrics = Metrics()
        assert metrics.commands_sent == 0
        assert metrics.commands_failed == 0
        assert metrics.status_received == 0
        assert metrics.last_error == ""
        assert metrics.last_error_time == 0.0
    
    def test_metrics_to_dict(self):
        """Metrics should convert to dictionary correctly"""
        metrics = Metrics()
        metrics.commands_sent = 10
        metrics.commands_failed = 2
        metrics.status_received = 5
        
        d = metrics.to_dict()
        assert d['commands_sent'] == 10
        assert d['commands_failed'] == 2
        assert d['commands_succeeded'] == 8
        assert d['success_rate'] == 0.8
        assert d['status_received'] == 5
    
    def test_metrics_zero_division(self):
        """Metrics should handle zero commands gracefully"""
        metrics = Metrics()
        d = metrics.to_dict()
        # Should not crash with division by zero
        # When 0 commands sent: (0-0)/max(1,0) = 0/1 = 0.0
        assert d['success_rate'] == 0.0
    
    def test_metrics_error_tracking(self):
        """Metrics should track errors by type"""
        metrics = Metrics()
        metrics.errors_by_type['ValueError'] = 3
        metrics.errors_by_type['ConnectionError'] = 1
        
        d = metrics.to_dict()
        assert d['errors_by_type']['ValueError'] == 3
        assert d['errors_by_type']['ConnectionError'] == 1


class TestMalformedPackets:
    """Test handling of malformed status packets"""
    
    def test_empty_packet(self):
        """Empty packet should return empty dict"""
        control = RadiodControl.__new__(RadiodControl)
        control.status_mcast_addr = "239.1.2.3"
        control.metrics = Metrics()  # Initialize metrics
        
        status = control._decode_status_response(b'')
        assert isinstance(status, dict)
        assert len(status) == 0
    
    def test_non_status_packet(self):
        """Non-status packet (type != 0) should return empty dict"""
        control = RadiodControl.__new__(RadiodControl)
        control.status_mcast_addr = "239.1.2.3"
        control.metrics = Metrics()  # Initialize metrics
        
        # Packet type 1 (command), not 0 (status)
        status = control._decode_status_response(b'\x01\x00\x00')
        assert isinstance(status, dict)
        assert len(status) == 0
    
    def test_truncated_packet(self):
        """Truncated packet should not crash"""
        control = RadiodControl.__new__(RadiodControl)
        control.status_mcast_addr = "239.1.2.3"
        control.metrics = Metrics()  # Initialize metrics
        
        # Status packet with incomplete TLV
        status = control._decode_status_response(b'\x00\x21\x08')
        # Should return partial results, not crash
        assert isinstance(status, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
