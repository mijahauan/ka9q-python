# Quick Action Items - ka9q-python Security & Design

## Immediate Fixes (Can be done today)

### 1. Fix Weak Cryptographic Randomness (CRITICAL)
**File**: `ka9q/control.py` lines 708, 814, 984

**Change from**:
```python
encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
```

**Change to**:
```python
import secrets
encode_int(cmdbuffer, StatusType.COMMAND_TAG, secrets.randbits(31))
```

---

### 2. Add Bounds Checking to Decoders (HIGH)
**File**: `ka9q/control.py` lines 297-327

**Add validation**:
```python
def decode_double(data: bytes, length: int) -> float:
    if length > 8:
        logger.warning(f"Invalid double length {length}, truncating to 8")
        length = 8
    if length < 0:
        raise ValidationError(f"Negative length: {length}")
    value_bytes = b'\x00' * (8 - length) + data[:length]
    return struct.unpack('>d', value_bytes)[0]

def decode_float(data: bytes, length: int) -> float:
    if length > 4:
        logger.warning(f"Invalid float length {length}, truncating to 4")
        length = 4
    if length < 0:
        raise ValidationError(f"Negative length: {length}")
    value_bytes = b'\x00' * (4 - length) + data[:length]
    return struct.unpack('>f', value_bytes)[0]
```

---

### 3. Fix Socket Leak in Discovery (MEDIUM)
**File**: `ka9q/discovery.py` line 186

**Ensure proper cleanup**:
```python
def discover_channels_native(status_address: str, listen_duration: float = 2.0):
    status_sock = None  # Initialize outside try
    temp_control = None
    
    try:
        # ... existing code ...
    except Exception as e:
        logger.error(f"Error during native channel discovery: {e}")
        raise
    finally:
        # Always cleanup, even on exception
        if status_sock:
            try:
                status_sock.close()
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
```

---

### 4. Add String Input Validation (HIGH)
**File**: `ka9q/control.py` - add new validation function

**Add after other validation functions** (around line 88):
```python
import re

def _validate_preset(preset: str) -> None:
    """Validate preset name is safe"""
    if not preset:
        raise ValidationError("Preset name cannot be empty")
    if len(preset) > 32:
        raise ValidationError(f"Preset too long: {len(preset)} chars (max 32)")
    if not re.match(r'^[a-zA-Z0-9_-]+$', preset):
        raise ValidationError(f"Invalid preset characters: {preset}")
    # Reject control characters
    if any(ord(c) < 32 for c in preset):
        raise ValidationError("Preset contains control characters")
```

**Then use it in** `create_channel()` around line 787:
```python
# After: encode_string(cmdbuffer, StatusType.PRESET, preset)
# Add before it:
_validate_preset(preset)
encode_string(cmdbuffer, StatusType.PRESET, preset)
```

---

## Quick Wins (1-2 hours)

### 5. Extract Decoder Module (Resolves TODO)
**File**: `ka9q/discovery.py` line 110

**Create new file** `ka9q/protocol.py`:
```python
"""
Protocol encoding/decoding functions for ka9q-radio TLV format
"""

def decode_status_packet(buffer: bytes, status_mcast_addr: str = None) -> dict:
    """
    Decode a status response packet from radiod
    
    Args:
        buffer: Raw response bytes
        status_mcast_addr: Optional multicast address for context
        
    Returns:
        Dictionary containing decoded status fields
    """
    from .control import (decode_int, decode_int32, decode_bool, 
                          decode_float, decode_double, decode_string, 
                          decode_socket)
    from .types import StatusType
    
    status = {}
    
    if len(buffer) == 0 or buffer[0] != 0:
        return status  # Not a status response
    
    # ... move entire _decode_status_response implementation here ...
    
    return status
```

**Then update** `discovery.py`:
```python
from .protocol import decode_status_packet

def discover_channels_native(status_address: str, listen_duration: float = 2.0):
    # ...
    # REMOVE these lines (109-112):
    # temp_control = RadiodControl.__new__(RadiodControl)
    # temp_control.status_mcast_addr = multicast_addr
    
    # REPLACE with:
    status = decode_status_packet(buffer, multicast_addr)
```

---

### 6. Add Security Documentation
**File**: `README.md` - add new section after "Requirements"

```markdown
## Security Considerations

⚠️ **IMPORTANT**: ka9q-radio uses an unauthenticated multicast protocol.

### Deployment Recommendations
- **Network Isolation**: Deploy on private/isolated network segments
- **Firewall Rules**: Restrict UDP port 5006 to trusted sources
- **Access Control**: Use VPN for remote access
- **Monitoring**: Log and monitor for unauthorized command traffic

### Threat Model
This library is designed for **trusted network environments**:
- ✅ Private LANs behind firewalls
- ✅ Laboratory/research networks  
- ✅ Home networks for amateur radio
- ❌ Public internet exposure
- ❌ Multi-tenant/shared environments
- ❌ Security-critical applications

For high-security requirements, consider deploying additional network-level authentication (VPN, mTLS proxy, etc.).

### What We Validate
- All numeric parameters are range-checked
- String inputs are length-limited and sanitized
- TLV encoding follows protocol specification
- Thread-safe operation guaranteed
```

---

## Medium Priority (This Week)

### 7. Add Simple Rate Limiting
**File**: `ka9q/control.py` - add to RadiodControl class

```python
class RadiodControl:
    def __init__(self, status_address: str, max_commands_per_sec: int = 100):
        # ... existing init ...
        self.max_commands_per_sec = max_commands_per_sec
        self._command_count = 0
        self._command_window_start = time.time()
        self._rate_limit_lock = threading.Lock()
    
    def _check_rate_limit(self):
        """Simple rate limiting check"""
        with self._rate_limit_lock:
            now = time.time()
            
            # Reset window every second
            if now - self._command_window_start >= 1.0:
                self._command_count = 0
                self._command_window_start = now
            
            # Check limit
            if self._command_count >= self.max_commands_per_sec:
                sleep_time = 1.0 - (now - self._command_window_start)
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached, sleeping {sleep_time:.3f}s")
                    time.sleep(sleep_time)
                    self._command_count = 0
                    self._command_window_start = time.time()
            
            self._command_count += 1
    
    def send_command(self, cmdbuffer: bytearray, **kwargs):
        self._check_rate_limit()  # Add this line at start
        # ... rest of existing code ...
```

---

### 8. Add Basic Metrics
**File**: `ka9q/control.py` - add simple metrics tracking

```python
@dataclass
class Metrics:
    """Simple metrics tracking"""
    commands_sent: int = 0
    commands_failed: int = 0
    last_error: str = ""
    
    def to_dict(self) -> dict:
        return {
            'commands_sent': self.commands_sent,
            'commands_failed': self.commands_failed,
            'success_rate': (self.commands_sent - self.commands_failed) / max(1, self.commands_sent),
            'last_error': self.last_error
        }

class RadiodControl:
    def __init__(self, status_address: str):
        # ... existing init ...
        self.metrics = Metrics()
    
    def send_command(self, cmdbuffer: bytearray, **kwargs):
        try:
            # ... existing code ...
            self.metrics.commands_sent += 1
        except Exception as e:
            self.metrics.commands_failed += 1
            self.metrics.last_error = str(e)
            raise
    
    def get_metrics(self) -> dict:
        """Get metrics dictionary"""
        return self.metrics.to_dict()
```

---

## Testing Additions (This Week)

### 9. Add Security Tests
**File**: `tests/test_security.py` (new file)

```python
import pytest
from ka9q.control import RadiodControl, decode_double, decode_float
from ka9q.exceptions import ValidationError

def test_decode_oversized_double():
    """Test double decoder with oversized input"""
    # Should not crash, should truncate
    data = b'\xFF' * 20  # Way too large
    result = decode_double(data, 20)
    # Should handle gracefully

def test_decode_negative_length():
    """Test negative length handling"""
    with pytest.raises(ValidationError):
        decode_double(b'\x00', -1)

def test_malformed_status_packets():
    """Test malformed packet handling"""
    control = RadiodControl.__new__(RadiodControl)
    control.status_mcast_addr = "239.1.2.3"
    
    malformed = [
        b'',  # Empty
        b'\x00',  # Only type
        b'\x00\x21\x08',  # Incomplete
        b'\xFF' * 1000,  # Garbage
    ]
    
    for packet in malformed:
        # Should not crash
        status = control._decode_status_response(packet)
        assert isinstance(status, dict)

def test_preset_validation():
    """Test preset name validation"""
    from ka9q.control import _validate_preset
    
    # Valid presets
    _validate_preset("usb")
    _validate_preset("AM-wide")
    _validate_preset("mode_123")
    
    # Invalid presets
    with pytest.raises(ValidationError):
        _validate_preset("")  # Empty
    
    with pytest.raises(ValidationError):
        _validate_preset("a" * 100)  # Too long
    
    with pytest.raises(ValidationError):
        _validate_preset("bad;preset")  # Invalid char
    
    with pytest.raises(ValidationError):
        _validate_preset("bad\npreset")  # Control char
```

---

## Summary of Changes

| Priority | Item | File | Lines Changed | Risk |
|----------|------|------|---------------|------|
| 🔴 CRITICAL | Cryptographic random | control.py | 3 | Low |
| 🟠 HIGH | Bounds checking | control.py | 10 | Low |
| 🟠 HIGH | Socket leak fix | discovery.py | 5 | Low |
| 🟠 HIGH | String validation | control.py | 20 | Medium |
| 🟡 MEDIUM | Extract decoder | protocol.py (new) | 50 | Medium |
| 🟡 MEDIUM | Security docs | README.md | 30 | Low |
| 🟡 MEDIUM | Rate limiting | control.py | 30 | Low |
| 🟡 MEDIUM | Metrics | control.py | 20 | Low |
| 🟢 LOW | Security tests | test_security.py (new) | 60 | Low |

**Total effort**: ~4-6 hours for all immediate and quick wins

---

## How to Apply

1. **Immediate fixes** can be done in any order
2. **Quick wins** should be done after immediate fixes
3. **Test additions** should be done alongside code changes
4. Run test suite after each change: `pytest tests/`
5. Update version number when complete
6. Add to CHANGELOG.md

---

## Before Committing

- [ ] All tests pass (`pytest`)
- [ ] Code style consistent (`black ka9q/`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped (suggest 2.2.0 for security fixes)
