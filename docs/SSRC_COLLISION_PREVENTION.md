# SSRC Collision Prevention and Multi-Client Coordination

**Problem Statement**: How to prevent SSRC/receiver definition collisions when multiple applications share radiod  
**Date**: November 30, 2025  
**Status**: Design Analysis

---

## Table of Contents

1. [Problem Overview](#problem-overview)
2. [Current State Analysis](#current-state-analysis)
3. [Collision Scenarios](#collision-scenarios)
4. [Impact Assessment](#impact-assessment)
5. [Mitigation Strategies](#mitigation-strategies)
6. [Implementation Approaches](#implementation-approaches)
7. [Best Practices](#best-practices)
8. [Recommendations](#recommendations)

---

## Problem Overview

### Two Collision Points

#### Collision Point 1: Multiple ka9q-python Applications
**Scenario**: Multiple applications using ka9q-python or signal-recorder want to create channels on the same radiod instance.

**Risk**:
- App A creates channel with SSRC 14074000
- App B unknowingly creates channel with SSRC 14074000, overwriting App A's configuration
- App C deletes SSRC 14074000, breaking both App A and App B

#### Collision Point 2: Mixed Client Ecosystem
**Scenario**: ka9q-python applications coexist with other radiod clients (C utilities, web interfaces, manual commands).

**Risk**:
- ka9q-python creates channel with SSRC 10000000
- External client (e.g., `control` utility) modifies or deletes SSRC 10000000
- ka9q-python has no way to detect or prevent this interference

---

## Current State Analysis

### Protocol Limitations

**ka9q-radio protocol has NO**:
- ✗ Authentication mechanism
- ✗ Authorization/ACLs
- ✗ Channel ownership tracking
- ✗ Locking mechanism
- ✗ Collision detection
- ✗ Client identification
- ✗ Exclusive access mode

**What radiod DOES**:
- ✓ Accepts commands from any source on multicast network
- ✓ Last write wins (no conflict resolution)
- ✓ Any client can modify/delete any channel
- ✓ STATUS packets broadcast channel state to all listeners

### SSRC Namespace

```python
# SSRC is 32-bit unsigned integer
SSRC_MIN = 0
SSRC_MAX = 0xFFFFFFFF  # 4,294,967,295

# Common convention: frequency in Hz
ssrc = int(14.074e6)  # 14074000
```

**Available namespace**: ~4.3 billion possible SSRCs  
**Typical usage**: Dozens to hundreds of channels  
**Collision probability**: LOW with proper allocation, HIGH with naive approaches

---

## Collision Scenarios

### Scenario 1: Frequency-Based SSRC Collision

**Current Practice**:
```python
# App A - WSPR monitor
ssrc = int(14.0956e6)  # 14095600
control.create_channel(ssrc=ssrc, frequency_hz=14.0956e6, preset="usb")

# App B - FT8 monitor (SAME frequency)
ssrc = int(14.095e6)   # 14095000 (DIFFERENT - truncated)
# OR
ssrc = int(14.0956e6)  # 14095600 (SAME - collision!)
control.create_channel(ssrc=ssrc, frequency_hz=14.0956e6, preset="usb")
```

**Problem**: Multiple apps monitoring same frequency use same SSRC.

**Impact**: Last writer wins, earlier channel configuration overwritten.

### Scenario 2: Application Namespace Collision

**Scenario**:
```python
# signal-recorder using SSRC range 10000000-19999999
signal_recorder_ssrc = 14074000

# Another app using frequency-based SSRCs
other_app_ssrc = int(14.074e6)  # 14074000 - COLLISION!
```

**Problem**: Different allocation strategies collide.

### Scenario 3: External Client Interference

**Scenario**:
```python
# Python application
control.create_channel(ssrc=14074000, frequency_hz=14.074e6, preset="usb")

# Meanwhile, user runs command line:
# $ control -s radiod.local 14074000 radio.frequency=14.095e6
# Channel retuned without Python app's knowledge
```

**Problem**: No ownership or protection mechanism.

### Scenario 4: Channel Deletion Conflict

**Scenario**:
```python
# App A creates and monitors channel
control.create_channel(ssrc=10000, ...)

# App B thinks it owns SSRC 10000
control.remove_channel(ssrc=10000)  # Sets frequency=0

# App A's channel suddenly disappears
```

**Problem**: No way to prevent other apps from removing channels.

### Scenario 5: Configuration Drift

**Scenario**:
```python
# App A creates channel with specific settings
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    gain=10.0
)

# App B modifies settings unknowingly
control.set_gain(ssrc=14074000, gain_db=20.0)

# App A's carefully tuned gain is now wrong
```

**Problem**: Silent configuration changes break assumptions.

---

## Impact Assessment

### Data Loss and Corruption

**Severity**: 🔴 **HIGH**

- Recording applications may lose data during channel reconfiguration
- Sample rate changes cause buffer misalignment
- Frequency changes record wrong signal
- Mode changes corrupt demodulation

### Resource Conflicts

**Severity**: 🟠 **MEDIUM**

- Multiple apps competing for same SSRC waste resources
- Rapid reconfiguration floods radiod with commands
- RTP stream subscribers receive inconsistent data

### Operational Reliability

**Severity**: 🟠 **MEDIUM**

- Applications cannot guarantee channel stability
- Automated systems may enter inconsistent states
- Difficult to debug issues (who changed what?)

### Security Implications

**Severity**: 🟡 **MEDIUM**

- Malicious actors can disrupt operations
- No audit trail for channel modifications
- Denial of service by deleting all channels

---

## Mitigation Strategies

### Strategy 1: SSRC Namespace Partitioning

**Concept**: Divide 32-bit SSRC space into application-specific ranges.

```python
# SSRC Allocation Plan
SSRC_RANGES = {
    'signal-recorder':   (10_000_000, 19_999_999),  # 10M range
    'wspr-monitor':      (20_000_000, 29_999_999),  # 10M range
    'ft8-monitor':       (30_000_000, 39_999_999),  # 10M range
    'satellite-tracker': (40_000_000, 49_999_999),  # 10M range
    'manual-testing':    (90_000_000, 99_999_999),  # 10M range
}

class SSRCAllocator:
    """Allocate SSRCs within application-specific range"""
    def __init__(self, app_name: str):
        if app_name not in SSRC_RANGES:
            raise ValueError(f"Unknown application: {app_name}")
        self.min_ssrc, self.max_ssrc = SSRC_RANGES[app_name]
        self.next_ssrc = self.min_ssrc
    
    def allocate(self) -> int:
        """Allocate next available SSRC"""
        if self.next_ssrc > self.max_ssrc:
            raise RuntimeError(f"SSRC exhausted for {self.app_name}")
        ssrc = self.next_ssrc
        self.next_ssrc += 1
        return ssrc

# Usage
allocator = SSRCAllocator('signal-recorder')
ssrc1 = allocator.allocate()  # 10000000
ssrc2 = allocator.allocate()  # 10000001
```

**Pros**:
- ✅ Simple to implement
- ✅ No coordination required
- ✅ Works with current protocol

**Cons**:
- ❌ Requires coordination at design time
- ❌ No enforcement mechanism
- ❌ Doesn't prevent malicious interference

### Strategy 2: Discovery-Based Collision Avoidance

**Concept**: Check existing channels before allocation.

```python
from ka9q import discover_channels, RadiodControl

class SmartSSRCAllocator:
    """Allocate SSRCs while avoiding collisions"""
    
    def __init__(self, control: RadiodControl, preferred_range: tuple = None):
        self.control = control
        self.preferred_range = preferred_range or (0, 0xFFFFFFFF)
    
    def allocate_avoiding_collisions(self, frequency_hz: float = None) -> int:
        """Allocate SSRC, checking for existing channels"""
        # Discover existing channels
        existing_channels = discover_channels(self.control.status_address)
        existing_ssrcs = set(existing_channels.keys())
        
        # Try frequency-based first (if provided)
        if frequency_hz:
            candidate = int(frequency_hz)
            if candidate not in existing_ssrcs:
                return candidate
        
        # Search for free SSRC in preferred range
        min_ssrc, max_ssrc = self.preferred_range
        for ssrc in range(min_ssrc, max_ssrc):
            if ssrc not in existing_ssrcs:
                return ssrc
        
        raise RuntimeError("No available SSRCs in range")

# Usage
allocator = SmartSSRCAllocator(control, preferred_range=(10_000_000, 20_000_000))
ssrc = allocator.allocate_avoiding_collisions(frequency_hz=14.074e6)
```

**Pros**:
- ✅ Detects existing allocations
- ✅ Works with current protocol
- ✅ Self-healing (finds gaps)

**Cons**:
- ❌ Race condition between discovery and allocation
- ❌ Adds latency (discovery takes 2+ seconds)
- ❌ Doesn't prevent post-allocation conflicts

### Strategy 3: Application Identifier in SSRC

**Concept**: Encode application ID in SSRC structure.

```python
class StructuredSSRC:
    """SSRC with embedded application identifier"""
    
    # SSRC structure: [app_id: 8 bits][instance: 8 bits][channel: 16 bits]
    
    @staticmethod
    def encode(app_id: int, instance_id: int, channel_id: int) -> int:
        """Encode structured SSRC"""
        if not (0 <= app_id < 256):
            raise ValueError("app_id must be 0-255")
        if not (0 <= instance_id < 256):
            raise ValueError("instance_id must be 0-255")
        if not (0 <= channel_id < 65536):
            raise ValueError("channel_id must be 0-65535")
        
        ssrc = (app_id << 24) | (instance_id << 16) | channel_id
        return ssrc
    
    @staticmethod
    def decode(ssrc: int) -> tuple:
        """Decode structured SSRC"""
        app_id = (ssrc >> 24) & 0xFF
        instance_id = (ssrc >> 16) & 0xFF
        channel_id = ssrc & 0xFFFF
        return app_id, instance_id, channel_id

# Application IDs
APP_SIGNAL_RECORDER = 1
APP_WSPR_MONITOR = 2
APP_FT8_MONITOR = 3

# Usage
ssrc = StructuredSSRC.encode(
    app_id=APP_SIGNAL_RECORDER,
    instance_id=0,
    channel_id=1
)
# Result: 0x01000001 = 16777217

# Multiple instances of same app
ssrc_instance_0 = StructuredSSRC.encode(APP_WSPR_MONITOR, 0, 1)
ssrc_instance_1 = StructuredSSRC.encode(APP_WSPR_MONITOR, 1, 1)
```

**Pros**:
- ✅ Self-documenting SSRCs
- ✅ Clear ownership
- ✅ Supports multiple instances

**Cons**:
- ❌ Requires coordination on app_id values
- ❌ Breaks frequency-as-SSRC convention
- ❌ No enforcement (still advisory only)

### Strategy 4: Heartbeat and Ownership Claims

**Concept**: Periodically refresh channel ownership.

```python
import threading
import time
from typing import Set

class ChannelOwnershipManager:
    """Manage channel ownership with heartbeats"""
    
    def __init__(self, control: RadiodControl, heartbeat_interval: float = 5.0):
        self.control = control
        self.heartbeat_interval = heartbeat_interval
        self.owned_ssrcs: Set[int] = set()
        self._heartbeat_thread = None
        self._running = False
    
    def claim_channel(self, ssrc: int, **config):
        """Claim ownership of a channel"""
        # Create/reconfigure channel
        self.control.create_channel(ssrc=ssrc, **config)
        
        # Add to ownership set
        self.owned_ssrcs.add(ssrc)
        
        # Start heartbeat if not running
        if not self._running:
            self.start_heartbeat()
    
    def start_heartbeat(self):
        """Start background heartbeat thread"""
        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self._heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """Periodically verify and refresh owned channels"""
        while self._running:
            time.sleep(self.heartbeat_interval)
            
            # Discover current channels
            channels = discover_channels(self.control.status_address)
            
            # Check each owned SSRC
            for ssrc in list(self.owned_ssrcs):
                if ssrc not in channels:
                    # Channel disappeared - log warning
                    logger.warning(f"Channel {ssrc} disappeared! Recreation needed.")
                    # Could automatically recreate here
                else:
                    # Verify configuration hasn't changed
                    # (would need to store expected config)
                    pass
    
    def release_channel(self, ssrc: int):
        """Release ownership of channel"""
        if ssrc in self.owned_ssrcs:
            self.control.remove_channel(ssrc)
            self.owned_ssrcs.remove(ssrc)
    
    def stop(self):
        """Stop heartbeat and release all channels"""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
        
        # Cleanup all owned channels
        for ssrc in list(self.owned_ssrcs):
            self.release_channel(ssrc)

# Usage
manager = ChannelOwnershipManager(control)
manager.claim_channel(ssrc=14074000, frequency_hz=14.074e6, preset="usb")

# Manager detects if channel is modified/deleted
# Can optionally auto-recreate
```

**Pros**:
- ✅ Detects external interference
- ✅ Can auto-recover
- ✅ Monitors channel health

**Cons**:
- ❌ Adds overhead (periodic discovery)
- ❌ Doesn't prevent conflicts, only detects them
- ❌ Auto-recreation could cause oscillation with competing apps

### Strategy 5: Coordination Service

**Concept**: External service manages SSRC allocation and coordination.

```python
import socket
import json
from typing import Optional

class SSRCCoordinationClient:
    """Client for centralized SSRC coordination service"""
    
    def __init__(self, coordinator_host: str = "localhost", 
                 coordinator_port: int = 9999):
        self.coordinator = (coordinator_host, coordinator_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.coordinator)
        self.app_name = None
    
    def register_application(self, app_name: str, instance_id: int = 0):
        """Register with coordinator"""
        request = {
            'action': 'register',
            'app_name': app_name,
            'instance_id': instance_id
        }
        self._send_request(request)
        self.app_name = app_name
    
    def allocate_ssrc(self, frequency_hz: Optional[float] = None) -> int:
        """Request SSRC allocation from coordinator"""
        request = {
            'action': 'allocate',
            'app_name': self.app_name,
            'frequency_hz': frequency_hz
        }
        response = self._send_request(request)
        return response['ssrc']
    
    def release_ssrc(self, ssrc: int):
        """Release SSRC back to coordinator"""
        request = {
            'action': 'release',
            'ssrc': ssrc
        }
        self._send_request(request)
    
    def _send_request(self, request: dict) -> dict:
        """Send request to coordinator and receive response"""
        msg = json.dumps(request).encode('utf-8')
        self.sock.sendall(msg + b'\n')
        
        response = self.sock.recv(4096)
        return json.loads(response.decode('utf-8'))

# Server-side coordinator (separate process)
class SSRCCoordinationServer:
    """Centralized SSRC coordination service"""
    
    def __init__(self):
        self.allocated_ssrcs = {}  # ssrc -> (app_name, timestamp)
        self.app_ranges = {}       # app_name -> (min, max)
    
    def allocate(self, app_name: str, frequency_hz: Optional[float]) -> int:
        """Allocate SSRC for application"""
        # Get application's range
        if app_name not in self.app_ranges:
            self.app_ranges[app_name] = self._assign_range(app_name)
        
        min_ssrc, max_ssrc = self.app_ranges[app_name]
        
        # Find available SSRC
        for ssrc in range(min_ssrc, max_ssrc):
            if ssrc not in self.allocated_ssrcs:
                self.allocated_ssrcs[ssrc] = (app_name, time.time())
                return ssrc
        
        raise RuntimeError(f"No SSRCs available for {app_name}")
    
    # ... implementation details ...
```

**Pros**:
- ✅ Centralized coordination
- ✅ Prevents collisions completely
- ✅ Audit trail and monitoring
- ✅ Can implement policies

**Cons**:
- ❌ Requires additional infrastructure
- ❌ Single point of failure
- ❌ Adds complexity
- ❌ Network dependency

### Strategy 6: Configuration File Based Allocation

**Concept**: Pre-allocate SSRCs via shared configuration file.

```yaml
# /etc/ka9q/ssrc-allocations.yaml
applications:
  signal-recorder:
    range: [10000000, 19999999]
    channels:
      - ssrc: 14074000
        frequency: 14.074e6
        preset: usb
        owner: signal-recorder-instance-1
      
  wspr-monitor:
    range: [20000000, 29999999]
    channels:
      - ssrc: 20001836
        frequency: 1.8366e6
        preset: usb
        owner: wspr-monitor-main

  manual:
    range: [90000000, 99999999]
    # No pre-allocated channels
```

```python
import yaml
from pathlib import Path

class ConfigBasedSSRCManager:
    """Load SSRC allocations from config file"""
    
    def __init__(self, config_path: Path = Path("/etc/ka9q/ssrc-allocations.yaml")):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
    
    def get_app_range(self, app_name: str) -> tuple:
        """Get SSRC range for application"""
        if app_name not in self.config['applications']:
            raise ValueError(f"Unknown application: {app_name}")
        return tuple(self.config['applications'][app_name]['range'])
    
    def get_allocated_channels(self, app_name: str) -> list:
        """Get pre-allocated channels for application"""
        app_config = self.config['applications'].get(app_name, {})
        return app_config.get('channels', [])
    
    def is_ssrc_available(self, ssrc: int) -> bool:
        """Check if SSRC is not pre-allocated to another app"""
        for app_name, app_config in self.config['applications'].items():
            for channel in app_config.get('channels', []):
                if channel['ssrc'] == ssrc:
                    return False
        return True

# Usage
manager = ConfigBasedSSRCManager()
range_min, range_max = manager.get_app_range('signal-recorder')
allocated = manager.get_allocated_channels('signal-recorder')
```

**Pros**:
- ✅ Human-readable allocation plan
- ✅ Documentation and coordination in one place
- ✅ Can be version controlled
- ✅ Easy to audit

**Cons**:
- ❌ Manual coordination required
- ❌ File must be shared/synchronized
- ❌ No runtime enforcement
- ❌ Stale data possible

---

## Implementation Approaches

### Approach A: Library-Level Support (Recommended)

Add SSRC management directly to ka9q-python:

```python
# ka9q/ssrc_manager.py
class SSRCManager:
    """Centralized SSRC allocation and conflict avoidance"""
    
    def __init__(self, control: RadiodControl, 
                 app_name: str,
                 allocation_strategy: str = 'partitioned'):
        self.control = control
        self.app_name = app_name
        self.strategy = allocation_strategy
        self._allocator = self._create_allocator()
    
    def allocate_ssrc(self, hint: Optional[float] = None) -> int:
        """Allocate SSRC using configured strategy"""
        return self._allocator.allocate(hint)
    
    def create_managed_channel(self, frequency_hz: float, **kwargs) -> int:
        """Create channel with automatic SSRC allocation"""
        ssrc = self.allocate_ssrc(hint=frequency_hz)
        self.control.create_channel(ssrc=ssrc, frequency_hz=frequency_hz, **kwargs)
        return ssrc

# Usage becomes simpler:
from ka9q import RadiodControl, SSRCManager

control = RadiodControl("radiod.local")
manager = SSRCManager(control, app_name='my-app')

# Automatic SSRC allocation with collision avoidance
ssrc = manager.create_managed_channel(frequency_hz=14.074e6, preset="usb")
```

### Approach B: Application-Level Convention

Document conventions and provide examples:

```python
# Best practice template
class MyRadiodApplication:
    """Template for well-behaved radiod client"""
    
    # 1. Choose application-specific SSRC range
    SSRC_BASE = 50_000_000  # Coordinate with other apps
    SSRC_RANGE = 1_000_000  # 1M SSRCs available
    
    def __init__(self):
        self.control = RadiodControl("radiod.local")
        self.next_ssrc = self.SSRC_BASE
        self.owned_channels = {}
    
    def allocate_channel(self, frequency_hz: float, **kwargs) -> int:
        """Allocate channel with automatic SSRC"""
        # Use sequential allocation within range
        ssrc = self.next_ssrc
        self.next_ssrc += 1
        
        if self.next_ssrc >= self.SSRC_BASE + self.SSRC_RANGE:
            raise RuntimeError("SSRC range exhausted")
        
        self.control.create_channel(ssrc=ssrc, frequency_hz=frequency_hz, **kwargs)
        self.owned_channels[ssrc] = {'frequency': frequency_hz, **kwargs}
        return ssrc
    
    def cleanup(self):
        """Clean up all owned channels on exit"""
        for ssrc in self.owned_channels:
            self.control.remove_channel(ssrc)
```

### Approach C: External Coordination Tool

Standalone tool for SSRC management:

```bash
# Command-line SSRC coordinator
$ ka9q-ssrc register --app signal-recorder --range 10000000-19999999
Registered: signal-recorder in range [10000000, 19999999]

$ ka9q-ssrc allocate --app signal-recorder --frequency 14.074e6
Allocated: SSRC 14074000 for signal-recorder

$ ka9q-ssrc list
Current allocations:
  14074000: signal-recorder (14.074 MHz, age: 5m)
  20001836: wspr-monitor (1.8366 MHz, age: 2h)

$ ka9q-ssrc release --ssrc 14074000
Released: SSRC 14074000
```

---

## Best Practices

### Practice 1: SSRC Naming Convention

```python
# RECOMMENDED: Include app identifier in SSRC
def generate_ssrc(app_id: int, channel_id: int) -> int:
    """
    Generate SSRC with embedded application ID
    
    Format: [app_id: 8 bits][reserved: 8 bits][channel_id: 16 bits]
    """
    return (app_id << 24) | (channel_id & 0xFFFF)

# Application IDs (coordinate these!)
APP_ID_SIGNAL_RECORDER = 1
APP_ID_WSPR_MONITOR = 2
APP_ID_FT8_MONITOR = 3

ssrc = generate_ssrc(APP_ID_SIGNAL_RECORDER, channel_id=1)
```

### Practice 2: Always Use Context Managers

```python
# Ensure cleanup even if application crashes
with RadiodControl("radiod.local") as control:
    ssrc = allocate_my_ssrc()
    control.create_channel(ssrc=ssrc, ...)
    
    try:
        # Application logic
        run_my_app()
    finally:
        # Guaranteed cleanup
        control.remove_channel(ssrc)
```

### Practice 3: Check Before Allocate

```python
def safe_allocate_ssrc(control: RadiodControl, preferred_ssrc: int) -> int:
    """Check if SSRC is available before using"""
    channels = discover_channels(control.status_address)
    
    if preferred_ssrc in channels:
        # Collision detected - find alternative
        logger.warning(f"SSRC {preferred_ssrc} already in use")
        return find_alternative_ssrc(channels, preferred_ssrc)
    
    return preferred_ssrc
```

### Practice 4: Document Your SSRC Allocation

```python
# In your application code
"""
SSRC Allocation Strategy
========================

This application uses SSRCs in range: 40,000,000 - 40,999,999

SSRC format: 40_MMM_CCC where:
  - MMM = monitoring station ID (000-999)
  - CCC = channel number (000-999)

Examples:
  - 40_001_000: Station 1, Channel 0
  - 40_001_001: Station 1, Channel 1
  - 40_002_000: Station 2, Channel 0

Coordinate changes with: ops-team@example.com
"""
```

### Practice 5: Monitor for Interference

```python
class DefensiveChannelManager:
    """Detect and handle channel interference"""
    
    def __init__(self, control: RadiodControl):
        self.control = control
        self.expected_config = {}
    
    def create_channel_with_monitoring(self, ssrc: int, **config):
        """Create channel and monitor for changes"""
        self.control.create_channel(ssrc=ssrc, **config)
        self.expected_config[ssrc] = config
    
    def verify_channels(self):
        """Check if channels match expected configuration"""
        channels = discover_channels(self.control.status_address)
        
        for ssrc, expected in self.expected_config.items():
            if ssrc not in channels:
                logger.error(f"Channel {ssrc} disappeared!")
                # Recreate or alert
                continue
            
            actual = channels[ssrc]
            if abs(actual.frequency - expected['frequency_hz']) > 1.0:
                logger.error(
                    f"Channel {ssrc} frequency changed! "
                    f"Expected {expected['frequency_hz']}, got {actual.frequency}"
                )
```

---

## Recommendations

### Immediate Actions (High Priority)

1. **Document SSRC Allocation Strategy**
   - Add section to README.md
   - Explain collision risks
   - Provide allocation examples

2. **Add SSRCManager to ka9q-python**
   - Implement partitioned allocation
   - Discovery-based collision avoidance
   - Provide convenience API

3. **Create Example Applications**
   - Show best practices
   - Demonstrate different strategies
   - Include multi-app scenarios

### Short-Term Improvements

4. **Add Configuration File Support**
   - YAML-based SSRC allocation plans
   - Shared across applications
   - Version controlled

5. **Implement Channel Monitoring**
   - Detect external modifications
   - Optional auto-recovery
   - Alerting/logging

6. **Create Coordination Examples**
   - signal-recorder + other apps
   - Multiple signal-recorder instances
   - Mixed client environments

### Long-Term Solutions

7. **Propose Protocol Extensions to ka9q-radio**
   - Channel ownership field
   - Client identification
   - Optional authentication layer
   - Advisory locking

8. **Build Coordination Service**
   - Centralized SSRC registry
   - Real-time conflict detection
   - REST API for allocation

9. **Community Coordination**
   - Publish SSRC allocation registry
   - Community coordination for app IDs
   - Best practices document

---

## Example: Multi-Application Deployment

### Scenario

Deployment with three applications:
- signal-recorder (long-term data recording)
- wspr-monitor (WSPR band monitoring)
- manual-testing (ad-hoc testing)

### Allocation Plan

```python
# shared_ssrc_config.py - Shared by all applications

SSRC_ALLOCATIONS = {
    'signal-recorder': {
        'range': (10_000_000, 19_999_999),
        'strategy': 'sequential',
        'description': 'Long-term GRAPE signal recording'
    },
    'wspr-monitor': {
        'range': (20_000_000, 29_999_999),
        'strategy': 'frequency-based',
        'description': 'WSPR propagation monitoring'
    },
    'manual-testing': {
        'range': (90_000_000, 99_999_999),
        'strategy': 'manual',
        'description': 'Ad-hoc testing and development'
    }
}

def get_allocator(app_name: str):
    """Get SSRC allocator for application"""
    if app_name not in SSRC_ALLOCATIONS:
        raise ValueError(f"Unknown application: {app_name}")
    
    config = SSRC_ALLOCATIONS[app_name]
    min_ssrc, max_ssrc = config['range']
    
    return SSRCAllocator(
        app_name=app_name,
        min_ssrc=min_ssrc,
        max_ssrc=max_ssrc,
        strategy=config['strategy']
    )
```

### Usage in Each Application

```python
# In signal-recorder
from shared_ssrc_config import get_allocator

allocator = get_allocator('signal-recorder')
ssrc = allocator.allocate()  # Gets 10000000, 10000001, etc.

# In wspr-monitor
allocator = get_allocator('wspr-monitor')
ssrc = allocator.allocate(hint=1.8366e6)  # Tries to use frequency

# In manual-testing
allocator = get_allocator('manual-testing')
ssrc = allocator.allocate()  # Gets 90000000+
```

---

## Conclusion

**Current State**: No collision protection - last write wins

**Root Cause**: ka9q-radio protocol has no authentication, ownership, or locking

**Mitigation Required**: Application-level coordination strategies

**Recommended Approach**:
1. SSRC namespace partitioning (immediate)
2. Discovery-based collision avoidance (short-term)
3. Shared configuration coordination (short-term)
4. Protocol enhancement proposals (long-term)

**Key Principle**: **Cooperative coordination rather than enforcement**

Since the protocol cannot enforce ownership, applications must:
- Use non-overlapping SSRC ranges
- Document allocation strategies
- Check for collisions before allocation
- Monitor for external interference
- Clean up channels on exit

---

## Next Steps

1. Review and approve SSRC allocation strategy
2. Implement SSRCManager in ka9q-python
3. Update documentation with best practices
4. Create multi-app deployment examples
5. Coordinate with signal-recorder integration

---

**References**:
- [API Reference](API_REFERENCE.md) - SSRC validation
- [Security Documentation](SECURITY.md) - Protocol limitations
- [Architecture](ARCHITECTURE.md) - Design principles

**Version**: 1.0  
**Author**: ka9q-python maintainers  
**License**: MIT
