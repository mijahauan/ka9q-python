# Critical Fixes Checklist - ka9q-python

Use this checklist to track the most important fixes from the code review.

## 🔴 Priority 1: Do First (1-2 hours)

### [ ] Fix #1: Documentation Method Name Mismatch
**Impact:** Users get `AttributeError` following documentation  
**Files to change:**
- [ ] `README.md` line 41, 81-86, 111-122
- [ ] `INSTALLATION.md` line 81-86
- [ ] `ka9q/__init__.py` line 12 (example in docstring)

**Options:**
1. Rename method in `control.py` from `create_and_configure_channel()` to `create_channel()`
2. Update all documentation to use `create_and_configure_channel()`
3. Add both names (alias)

**Recommended:** Option 1 (simpler for users)

---

### [ ] Fix #2: Add Input Validation
**Impact:** Prevent crashes from invalid input  
**File:** `ka9q/control.py`

Add these validation functions:
```python
def _validate_ssrc(ssrc: int) -> None:
    if not isinstance(ssrc, int) or not (0 <= ssrc <= 0xFFFFFFFF):
        raise ValidationError(f"Invalid SSRC: {ssrc} (must be 0-4294967295)")

def _validate_frequency(freq_hz: float) -> None:
    if not (0 < freq_hz < 10e12):
        raise ValidationError(f"Invalid frequency: {freq_hz} Hz")

def _validate_sample_rate(rate: int) -> None:
    if not isinstance(rate, int) or rate <= 0:
        raise ValidationError(f"Invalid sample rate: {rate} (must be positive integer)")

def _validate_timeout(timeout: float) -> None:
    if timeout <= 0:
        raise ValidationError(f"Timeout must be positive: {timeout}")
```

Apply to methods:
- [ ] `create_and_configure_channel()` - validate ssrc, frequency_hz, sample_rate
- [ ] `set_frequency()` - validate frequency_hz
- [ ] `set_sample_rate()` - validate sample_rate
- [ ] `tune()` - validate ssrc, timeout
- [ ] `set_gain()` - validate gain_db range
- [ ] `set_agc()` - validate numeric parameters

---

### [ ] Fix #3: Improve Exception Handling
**Impact:** Better debugging, clearer errors  
**Files:** `ka9q/control.py`, `ka9q/discovery.py`

**control.py line 355-357:**
```python
# BEFORE:
except Exception as e:
    logger.error(f"Failed to connect to radiod: {e}")
    raise

# AFTER:
except socket.error as e:
    raise ConnectionError(f"Socket error: {e}") from e
except subprocess.TimeoutExpired as e:
    raise ConnectionError(f"Resolution timeout: {e}") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise ConnectionError(f"Failed to connect: {e}") from e
```

**control.py line 372-374:**
```python
# BEFORE:
except Exception as e:
    logger.error(f"Failed to send command: {e}")
    raise

# AFTER:
except socket.error as e:
    raise CommandError(f"Socket error sending command: {e}") from e
except Exception as e:
    logger.error(f"Unexpected error sending command: {e}", exc_info=True)
    raise CommandError(f"Failed to send command: {e}") from e
```

---

## 🟡 Priority 2: Do Soon (1 day)

### [ ] Fix #4: Add Context Manager Support
**Impact:** Automatic cleanup, prevent resource leaks  
**File:** `ka9q/control.py`

Add to `RadiodControl` class:
```python
def __enter__(self):
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    try:
        self.close()
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")
    return False
```

---

### [ ] Fix #5: Robust Socket Cleanup
**Impact:** Prevent resource leaks  
**File:** `ka9q/control.py` line 979-989

Replace `close()` method:
```python
def close(self):
    """Close all sockets with error handling"""
    errors = []
    
    if self.socket:
        try:
            self.socket.close()
        except Exception as e:
            errors.append(f"control: {e}")
        finally:
            self.socket = None
    
    if self._status_sock:
        try:
            self._status_sock.close()
        except Exception as e:
            errors.append(f"status: {e}")
        finally:
            self._status_sock = None
    
    if errors:
        logger.warning(f"Errors closing sockets: {'; '.join(errors)}")
```

---

### [ ] Fix #6: Fix Integer Encoding Overflow
**Impact:** Prevent crash on negative integers  
**File:** `ka9q/control.py` line 39-66

Add validation to `encode_int64()`:
```python
def encode_int64(buf: bytearray, type_val: int, x: int) -> int:
    """Encode a 64-bit integer in TLV format"""
    if x < 0:
        raise ValidationError(f"Cannot encode negative integer: {x}")
    if x >= 2**64:
        raise ValidationError(f"Integer too large: {x}")
    
    buf.append(type_val)
    # ... rest of function
```

---

### [ ] Fix #7: Add Thread Safety
**Impact:** Safe for multi-threaded use  
**File:** `ka9q/control.py`

Add locks:
```python
import threading

class RadiodControl:
    def __init__(self, status_address: str):
        self.status_address = status_address
        self.socket = None
        self._status_sock = None
        self._status_sock_lock = threading.RLock()
        self._socket_lock = threading.RLock()  # NEW
        self._connect()
    
    def send_command(self, cmdbuffer: bytearray):
        """Thread-safe command sending"""
        with self._socket_lock:  # NEW
            if not self.socket:
                raise RuntimeError("Not connected")
            # ... rest of function
```

---

## 🟢 Priority 3: Nice to Have (1 week)

### [ ] Enhancement #1: Add Retry Logic
**File:** `ka9q/control.py`

See `CODE_REVIEW_RECOMMENDATIONS.md` section 7

---

### [ ] Enhancement #2: Refactor Shared Code
**New file:** `ka9q/utils.py`

See `CODE_REVIEW_RECOMMENDATIONS.md` section 9

---

### [ ] Enhancement #3: Improve Documentation
**Files:** All markdown files

See `CODE_REVIEW_RECOMMENDATIONS.md` section 10

---

## 📝 Testing After Each Fix

After each fix, run:
```bash
# Unit tests
pytest tests/

# Specific integration tests
pytest tests/test_integration.py -v

# Example scripts
python examples/simple_am_radio.py
python examples/discover_example.py
```

---

## ✅ Verification Checklist

After completing Priority 1 & 2 fixes:

- [ ] All examples in README.md work without errors
- [ ] Invalid inputs raise clear `ValidationError` exceptions
- [ ] Context manager works: `with RadiodControl(...) as control:`
- [ ] No resource leaks (check with `lsof` or similar)
- [ ] Multi-threaded usage doesn't crash
- [ ] All existing tests still pass
- [ ] Error messages are clear and actionable

---

## 📊 Progress Tracking

| Fix | Priority | Estimated Time | Status | Notes |
|-----|----------|----------------|--------|-------|
| #1 Doc fix | P1 | 30 min | ⬜ | Choose method name first |
| #2 Validation | P1 | 1 hour | ⬜ | Start with critical params |
| #3 Exceptions | P1 | 30 min | ⬜ | Replace generic catches |
| #4 Context mgr | P2 | 15 min | ⬜ | Simple addition |
| #5 Socket cleanup | P2 | 20 min | ⬜ | Test thoroughly |
| #6 Int overflow | P2 | 15 min | ⬜ | Add bounds check |
| #7 Thread safety | P2 | 1 hour | ⬜ | Test with threads |

**Total P1 Time:** ~2 hours  
**Total P1+P2 Time:** ~4 hours

---

## 🚀 Quick Start (First 30 Minutes)

1. **Decide on method name** (5 min)
   - Keep `create_and_configure_channel()` and update docs? OR
   - Rename to `create_channel()`? (recommended)

2. **Fix documentation** (20 min)
   - Update README.md
   - Update INSTALLATION.md
   - Update __init__.py docstring

3. **Add basic validation** (5 min)
   - Add `_validate_ssrc()` function
   - Call it from `create_and_configure_channel()`
   - Test: `control.create_channel(ssrc=-1, ...)` should raise error

✅ **After 30 min:** Documentation matches code, basic safety added

---

## 📞 Questions to Decide

Before starting fixes:

1. **Method name:** Keep `create_and_configure_channel()` or rename to `create_channel()`?
2. **Validation strictness:** Strict (raise errors) or lenient (log warnings)?
3. **Thread safety:** Required for your use case or can defer?
4. **Breaking changes:** OK to change exceptions types in minor version?

---

*Last updated from code review on 2025-11-11*
