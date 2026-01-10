import logging
import pytest
from ka9q.control import RadiodControl
from ka9q.types import StatusType
import sys
import ka9q.control
print(f"DEBUG: ka9q.control file: {ka9q.control.__file__}", file=sys.stderr)


class TestTTLWarning:
    def test_ttl_zero_warning(self, caplog):
        """Test that a warning is logged when TTL is 0"""
        import sys
        import ka9q.control
        print(f"DEBUG: ka9q.control file: {ka9q.control.__file__}")
        
        # Constructor might try to resolve address, use loopback
        control = RadiodControl("127.0.0.1")
        
        # Construct a status packet with OUTPUT_TTL = 0
        # First byte must be 0 (STATUS)
        # Type: 19 (OUTPUT_TTL), Length: 1, Value: 0
        data = bytes([0, StatusType.OUTPUT_TTL, 1, 0])
        
        # We need to capture logs from ka9q.control
        with caplog.at_level(logging.DEBUG, logger="ka9q.control"):
            status = control._decode_status_response(data)
            
        # Debug: print captured logs if failure
        print(f"Captured logs: {caplog.text}")
        
        assert status['ttl'] == 0
        assert "Radiod reporting TTL=0" in caplog.text
        assert "localhost loopback only" in caplog.text

    def test_ttl_nonzero_no_warning(self, caplog):
        """Test that NO warning is logged when TTL is > 0"""
        control = RadiodControl("127.0.0.1")
        
        # Type: 19, Length: 1, Value: 2
        # Prepend 0 byte
        data = bytes([0, StatusType.OUTPUT_TTL, 1, 2])
        
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="ka9q.control"):
            status = control._decode_status_response(data)
            
        assert status['ttl'] == 2
        assert "Radiod reporting TTL=0" not in caplog.text
