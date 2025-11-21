# Multi-Homed Support - Action Plan

## Quick Summary

**Current Status**: ✅ Partial Support  
**What Works**: `discover_channels_native()` with `interface` parameter  
**What's Missing**: `RadiodControl`, `discover_channels()`, and utilities all use hardcoded `0.0.0.0`

---

## Key Findings

### 1. The Good News ✅
- `ka9q/discovery.py` already has proper interface support in `discover_channels_native()`
- Architecture is sound and extensible
- Backward compatibility is easy to maintain
- Implementation is straightforward

### 2. The Gaps ❌

| Component | Status | Line References |
|-----------|--------|-----------------|
| `discovery.py` → `_create_status_listener_socket()` | ✅ Has interface param | Line 35, 71-76 |
| `discovery.py` → `discover_channels_native()` | ✅ Has interface param | Line 84-97 |
| `discovery.py` → `discover_channels()` | ❌ Missing interface param | Line 302-318 |
| `control.py` → `RadiodControl.__init__()` | ❌ No interface support | - |
| `control.py` → `_connect()` | ❌ Hardcoded 0.0.0.0 | Lines 591, 597 |
| `control.py` → `_setup_status_listener()` | ❌ Hardcoded 0.0.0.0 | Lines 1110, 1121 |
| `utils.py` → `create_multicast_socket()` | ❌ Hardcoded 0.0.0.0 | Line 147 |

---

## Critical Code Locations

### Files Requiring Changes

1. **`ka9q/discovery.py`**
   - Line 302-318: Add `interface` parameter to `discover_channels()`
   - Pass through to `discover_channels_native()` at line 322

2. **`ka9q/control.py`** (Most important)
   - Constructor: Add `interface` parameter
   - Line 591: Replace `'0.0.0.0'` with interface logic for IP_MULTICAST_IF
   - Line 597: Replace `'0.0.0.0'` with interface logic for IP_ADD_MEMBERSHIP
   - Line 1110: Keep `'0.0.0.0'` for bind (correct)
   - Line 1121: Replace `'0.0.0.0'` with interface logic for IP_ADD_MEMBERSHIP

3. **`ka9q/utils.py`**
   - Line 97: Add `interface` parameter to function signature
   - Line 147: Replace `'0.0.0.0'` with interface logic

---

## Minimum Viable Implementation

### Step 1: Update `RadiodControl` (20 minutes)

```python
# In ka9q/control.py

class RadiodControl:
    def __init__(self, status_address: str, 
                 max_commands_per_sec: int = 100,
                 interface: Optional[str] = None):  # ADD THIS
        """
        Args:
            ...
            interface: IP address of network interface for multicast (e.g., '192.168.1.100').
                      Required on multi-homed systems. If None, uses INADDR_ANY (0.0.0.0).
        """
        self.status_address = status_address
        self.max_commands_per_sec = max_commands_per_sec
        self.interface = interface  # ADD THIS
        # ... rest of init
```

### Step 2: Update `_connect()` Method (10 minutes)

```python
# In ka9q/control.py, around line 588-598

def _connect(self):
    # ... socket creation ...
    
    # Determine interface address (None -> 0.0.0.0)
    interface_addr = self.interface if self.interface else '0.0.0.0'
    
    # Set multicast interface
    self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 
                         socket.inet_aton(interface_addr))
    logger.debug(f"Set IP_MULTICAST_IF to {interface_addr}")
    
    # Join multicast group on specified interface
    mreq = struct.pack('=4s4s', 
                      socket.inet_aton(mcast_addr),
                      socket.inet_aton(interface_addr))
    # ... rest
```

### Step 3: Update `_setup_status_listener()` Method (5 minutes)

```python
# In ka9q/control.py, around line 1119-1122

def _setup_status_listener(self):
    # ... socket setup ...
    
    # Join multicast group on specified interface
    interface_addr = self.interface if self.interface else '0.0.0.0'
    mreq = struct.pack('=4s4s', 
                      socket.inet_aton(self.status_mcast_addr),
                      socket.inet_aton(interface_addr))
    # ... rest
```

### Step 4: Update `discover_channels()` (5 minutes)

```python
# In ka9q/discovery.py, around line 302-318

def discover_channels(status_address: str, 
                      listen_duration: float = 2.0,
                      use_native: bool = True,
                      interface: Optional[str] = None) -> Dict[int, ChannelInfo]:  # ADD THIS
    """
    ...
    Args:
        status_address: Status multicast address
        listen_duration: Duration to listen
        use_native: Use native Python listener
        interface: IP address of network interface (e.g., '192.168.1.100').
                  Required on multi-homed systems.
    """
    if use_native:
        try:
            channels = discover_channels_native(status_address, listen_duration, interface)  # PASS IT
            # ... rest
```

### Step 5: Update `create_multicast_socket()` (5 minutes)

```python
# In ka9q/utils.py, around line 96-147

def create_multicast_socket(multicast_addr: str, port: int = 5006, 
                            bind_addr: str = '0.0.0.0',
                            interface: Optional[str] = None) -> socket.socket:  # ADD THIS
    """
    Args:
        ...
        interface: IP address of network interface for multicast membership.
                  If None, uses INADDR_ANY (0.0.0.0).
    """
    # ... socket setup ...
    
    # Join multicast group on specified interface
    interface_addr = interface if interface else '0.0.0.0'
    mreq = struct.pack('=4s4s',
                      socket.inet_aton(multicast_addr),
                      socket.inet_aton(interface_addr))
    # ... rest
```

---

## Time Estimate

- **Core Implementation**: 45 minutes
- **Testing**: 30 minutes
- **Documentation**: 1 hour
- **Examples**: 30 minutes

**Total**: ~2.5 hours for complete implementation

---

## Testing Checklist

### Backward Compatibility Tests
- [ ] `RadiodControl("radiod.local")` still works (no interface specified)
- [ ] `discover_channels("radiod.local")` still works
- [ ] All existing examples run without modification

### Multi-Homed Tests  
- [ ] `RadiodControl("radiod.local", interface="192.168.1.100")` works
- [ ] `discover_channels("radiod.local", interface="192.168.1.100")` works
- [ ] Discovery finds channels on correct interface
- [ ] Commands sent via correct interface

### Error Handling
- [ ] Invalid interface IP raises clear error
- [ ] Non-existent interface handled gracefully
- [ ] Logging shows which interface is used

---

## Documentation Updates Required

### High Priority
1. **API Reference** (`docs/API_REFERENCE.md`)
   - Add `interface` parameter to `RadiodControl`
   - Add `interface` parameter to `discover_channels()`
   - Document single-homed vs multi-homed usage

2. **README** (`README.md`)
   - Add Quick Start example with interface
   - Mention multi-homed support in features

### Medium Priority
3. **Native Discovery Doc** (`docs/NATIVE_DISCOVERY.md`)
   - Add multi-homed examples
   - Update "Future Enhancements" section

4. **New Multi-Homed Guide** (`docs/MULTI_HOMED_USAGE.md`)
   - How to determine your interface IP
   - Platform-specific notes (Linux/macOS/Windows)
   - Troubleshooting guide

### Low Priority
5. **Examples** (`examples/discover_example.py`)
   - Add Method 4: Multi-homed discovery
   - Create `examples/multihomed_example.py`

---

## Sample Code After Implementation

### Before (Current - Works only on single-homed)
```python
from ka9q import RadiodControl, discover_channels

control = RadiodControl("radiod.local")
channels = discover_channels("radiod.local")
```

### After (Works on both single and multi-homed)
```python
from ka9q import RadiodControl, discover_channels

# Single-homed (same as before)
control = RadiodControl("radiod.local")
channels = discover_channels("radiod.local")

# Multi-homed (specify interface)
control = RadiodControl("radiod.local", interface="192.168.1.100")
channels = discover_channels("radiod.local", interface="192.168.1.100")
```

---

## Next Steps

### Immediate Action
1. Review this action plan
2. Implement Step 1-5 (core changes)
3. Test backward compatibility
4. Test on multi-homed system

### Follow-up
1. Update documentation (API Reference, README)
2. Add examples
3. Create test cases
4. Consider auto-detection enhancement

---

## Questions to Consider

1. **Interface Validation**: Should we validate that the interface IP exists on the system?
2. **Error Messages**: What error message for invalid interface?
3. **Logging**: Log which interface is being used (INFO or DEBUG level)?
4. **Auto-Detection**: Should we attempt to auto-detect in future version?
5. **IPv6**: Should we plan for IPv6 support now or later?

---

## Risk Assessment

**Low Risk** - All changes are:
- ✅ Backward compatible (optional parameters with safe defaults)
- ✅ Non-breaking (existing code continues to work)
- ✅ Localized (changes in specific functions)
- ✅ Well-tested pattern (already used in `discover_channels_native()`)

---

## Success Criteria

Implementation is complete when:
- [ ] `RadiodControl` accepts `interface` parameter
- [ ] `discover_channels()` accepts `interface` parameter  
- [ ] All multicast joins use specified interface
- [ ] Backward compatibility maintained
- [ ] Documentation updated
- [ ] At least one multi-homed example provided
- [ ] Basic tests passing

---

## Contact

For questions or clarifications on this action plan, refer to:
- Full analysis: `docs/development/MULTI_HOMED_SUPPORT_REVIEW.md`
- Code locations: See "Critical Code Locations" section above
