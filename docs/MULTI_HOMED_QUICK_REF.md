# Multi-Homed Systems - Quick Reference

## What is a Multi-Homed System?

A computer with **multiple network interfaces** (NICs), such as:
- Desktop with Ethernet + Wi-Fi
- Server with multiple Ethernet ports
- VM with multiple virtual NICs
- Laptop with Wi-Fi + Ethernet + VPN

## The Problem

Multicast traffic must be sent/received on a **specific network interface**. Using `0.0.0.0` (INADDR_ANY) lets the OS choose, which may select the wrong interface.

## Current Status in ka9q-python

### ✅ What Works
```python
# Native discovery with interface parameter
from ka9q import discover_channels_native

channels = discover_channels_native(
    "radiod.local",
    interface="192.168.1.100"  # ✅ Specify interface
)
```

### ❌ What Doesn't Work Yet
```python
# Main discovery function - no interface parameter
from ka9q import discover_channels

channels = discover_channels(
    "radiod.local"
    # ❌ Can't specify interface
)

# RadiodControl - no interface parameter  
from ka9q import RadiodControl

control = RadiodControl(
    "radiod.local"
    # ❌ Can't specify interface
)
```

## How to Find Your Interface IP

### Linux
```bash
ip addr show
# or
ifconfig
```

### macOS
```bash
ifconfig
# or
networksetup -listallhardwareports
```

### Windows
```cmd
ipconfig
```

### Python Script
```python
import socket
import netifaces  # pip install netifaces

# List all interfaces
for iface in netifaces.interfaces():
    addrs = netifaces.ifaddresses(iface)
    if netifaces.AF_INET in addrs:
        ip = addrs[netifaces.AF_INET][0]['addr']
        print(f"{iface}: {ip}")
```

## Code Changes Required

### File: `ka9q/control.py`

**Before:**
```python
class RadiodControl:
    def __init__(self, status_address: str, max_commands_per_sec: int = 100):
        self.status_address = status_address
        # ...
    
    def _connect(self):
        # Hardcoded:
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 
                             socket.inet_aton('0.0.0.0'))  # ❌
        
        mreq = struct.pack('=4s4s', 
                          socket.inet_aton(mcast_addr),
                          socket.inet_aton('0.0.0.0'))  # ❌
```

**After:**
```python
class RadiodControl:
    def __init__(self, status_address: str, 
                 max_commands_per_sec: int = 100,
                 interface: Optional[str] = None):  # ✅ ADD
        self.status_address = status_address
        self.interface = interface  # ✅ ADD
        # ...
    
    def _connect(self):
        # Use interface if provided:
        interface_addr = self.interface if self.interface else '0.0.0.0'  # ✅
        
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 
                             socket.inet_aton(interface_addr))  # ✅
        
        mreq = struct.pack('=4s4s', 
                          socket.inet_aton(mcast_addr),
                          socket.inet_aton(interface_addr))  # ✅
```

### File: `ka9q/discovery.py`

**Before:**
```python
def discover_channels(status_address: str, 
                      listen_duration: float = 2.0,
                      use_native: bool = True):  # ❌ No interface
    if use_native:
        channels = discover_channels_native(status_address, listen_duration)  # ❌
```

**After:**
```python
def discover_channels(status_address: str, 
                      listen_duration: float = 2.0,
                      use_native: bool = True,
                      interface: Optional[str] = None):  # ✅ ADD
    if use_native:
        channels = discover_channels_native(
            status_address, listen_duration, interface)  # ✅ PASS IT
```

### File: `ka9q/utils.py`

**Before:**
```python
def create_multicast_socket(multicast_addr: str, port: int = 5006, 
                            bind_addr: str = '0.0.0.0'):  # ❌ No interface
    # ...
    mreq = struct.pack('=4s4s',
                      socket.inet_aton(multicast_addr),
                      socket.inet_aton('0.0.0.0'))  # ❌
```

**After:**
```python
def create_multicast_socket(multicast_addr: str, port: int = 5006, 
                            bind_addr: str = '0.0.0.0',
                            interface: Optional[str] = None):  # ✅ ADD
    # ...
    interface_addr = interface if interface else '0.0.0.0'  # ✅
    mreq = struct.pack('=4s4s',
                      socket.inet_aton(multicast_addr),
                      socket.inet_aton(interface_addr))  # ✅
```

## Expected Usage After Implementation

### Single-Homed System (no change required)
```python
from ka9q import RadiodControl, discover_channels

# Works as before (defaults to 0.0.0.0)
control = RadiodControl("radiod.local")
channels = discover_channels("radiod.local")
```

### Multi-Homed System (new capability)
```python
from ka9q import RadiodControl, discover_channels

# Specify which interface to use
MY_INTERFACE = "192.168.1.100"

control = RadiodControl("radiod.local", interface=MY_INTERFACE)
channels = discover_channels("radiod.local", interface=MY_INTERFACE)

# Create channel using specific interface
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000
)
```

## Troubleshooting

### Problem: "No channels found"

**Single-homed system:**
```python
# This should work
channels = discover_channels("radiod.local")
```

**Multi-homed system:**
```python
# Try specifying interface explicitly
channels = discover_channels("radiod.local", interface="192.168.1.100")
```

### Problem: "Wrong interface being used"

**Check routing:**
```bash
# Linux
ip route show

# macOS  
netstat -rn
```

**Force specific interface:**
```python
control = RadiodControl("radiod.local", interface="192.168.1.100")
```

### Problem: "How do I know which interface to use?"

The interface must be on the **same network** as the multicast traffic:
- If radiod is at `192.168.1.50`
- Use interface like `192.168.1.100` (same subnet)
- Don't use interface on different subnet like `10.0.0.100`

## Implementation Checklist

- [ ] Update `RadiodControl.__init__()` with interface parameter
- [ ] Update `RadiodControl._connect()` to use interface
- [ ] Update `RadiodControl._setup_status_listener()` to use interface
- [ ] Update `discover_channels()` with interface parameter
- [ ] Update `create_multicast_socket()` with interface parameter
- [ ] Test backward compatibility (interface=None)
- [ ] Test multi-homed scenario (interface="192.168.1.100")
- [ ] Update documentation
- [ ] Add examples

## Related Documentation

- **Full Review**: `docs/development/MULTI_HOMED_SUPPORT_REVIEW.md`
- **Action Plan**: `docs/development/MULTI_HOMED_ACTION_PLAN.md`
- **Native Discovery**: `docs/NATIVE_DISCOVERY.md`
- **API Reference**: `docs/API_REFERENCE.md`

## Technical Background

### Socket Options Explained

**IP_ADD_MEMBERSHIP** - Join a multicast group on a specific interface
```python
# Second parameter = interface to join on
mreq = struct.pack('=4s4s', 
                  socket.inet_aton('239.251.200.193'),  # multicast group
                  socket.inet_aton('192.168.1.100'))    # interface IP
socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
```

**IP_MULTICAST_IF** - Set interface for sending multicast packets
```python
# Parameter = interface to send from
socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                 socket.inet_aton('192.168.1.100'))  # interface IP
```

**Bind Address** - Which address/port to bind socket to
```python
# Usually '0.0.0.0' to receive on all interfaces
# But multicast group membership determines which interface actually receives
socket.bind(('0.0.0.0', 5006))  # ✅ This is correct
```

### Common Misconception

❌ **Wrong**: "I need to bind to my interface IP"
```python
socket.bind(('192.168.1.100', 5006))  # ❌ Not necessary
```

✅ **Right**: "I need to join multicast group on my interface"
```python
socket.bind(('0.0.0.0', 5006))  # ✅ Bind to any
# Then join multicast on specific interface:
mreq = struct.pack('=4s4s', 
                  socket.inet_aton(multicast_group),
                  socket.inet_aton('192.168.1.100'))  # ✅ Specify interface here
```

## Summary

**Current**: `0.0.0.0` hardcoded → works on single-homed only  
**Goal**: Optional `interface` parameter → works on both single and multi-homed  
**Implementation**: ~2.5 hours, low risk, backward compatible
