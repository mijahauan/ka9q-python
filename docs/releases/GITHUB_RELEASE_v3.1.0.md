# ka9q-python v3.1.0 🎯

## SSRC Abstraction - Simplified Channel Creation

This release removes SSRC from application concerns. Applications now specify **what they want** (frequency, mode, sample rate) and the system handles SSRC allocation internally.

### 🚀 What's New

#### SSRC-Free API

**No more manual SSRC management!** The `create_channel()` method now automatically allocates SSRCs when not specified:

```python
from ka9q import RadiodControl

# New simplified API (recommended)
with RadiodControl("radiod.local") as control:
    ssrc = control.create_channel(
        frequency_hz=14.074e6,
        preset="usb",
        sample_rate=12000
    )
    print(f"Created channel with SSRC: {ssrc}")
```

**Key Features:**
- 🎯 **Optional SSRC** - Method returns the SSRC (useful when auto-allocated)
- 🔄 **Deterministic allocation** - Same parameters always produce the same SSRC
- 🤝 **Cross-library compatibility** - Matches signal-recorder's allocation algorithm
- 📡 **Stream sharing** - Multiple apps can share the same stream automatically

#### New `allocate_ssrc()` Function

For advanced use cases requiring coordination:

```python
from ka9q import allocate_ssrc

# Pre-allocate SSRC for coordination
ssrc = allocate_ssrc(
    frequency_hz=10.0e6,
    preset="iq",
    sample_rate=16000
)
# Use with create_channel() or share with other apps
```

### 🔄 API Changes

**`create_channel()` signature updated:**
- `frequency_hz` is now the **first required parameter**
- `ssrc` moved to the end and made **optional**
- Method now **returns the SSRC** (int) instead of None

**Before (v3.0.0):**
```python
control.create_channel(ssrc=12345, frequency_hz=14.074e6, preset="usb")
```

**After (v3.1.0):**
```python
# Auto-allocate (recommended)
ssrc = control.create_channel(frequency_hz=14.074e6, preset="usb")

# Or specify manually (still supported)
ssrc = control.create_channel(frequency_hz=14.074e6, preset="usb", ssrc=12345)
```

### 🤝 Cross-Library Compatibility

The SSRC allocation algorithm matches `signal-recorder`'s `StreamSpec.ssrc_hash()`:

```python
key = (round(frequency_hz), preset.lower(), sample_rate, agc, round(gain, 1))
return hash(key) & 0x7FFFFFFF
```

**Benefits:**
- Same parameters → same SSRC in both libraries
- Automatic stream sharing across applications
- No coordination overhead needed

### 💡 Use Cases

**Simple Channel Creation:**
```python
# Just specify what you want - SSRC handled automatically
ssrc = control.create_channel(14.074e6, "usb", 12000)
```

**Stream Sharing Between Apps:**
```python
# App 1: Creates channel
ssrc1 = control.create_channel(7.074e6, "usb", 12000)

# App 2: Same parameters → same SSRC → shared stream
ssrc2 = control.create_channel(7.074e6, "usb", 12000)
# ssrc1 == ssrc2 (stream is shared!)
```

**Coordinated Recording:**
```python
# Both ka9q-python and signal-recorder use the same SSRC
ssrc = allocate_ssrc(14.074e6, "usb", 12000)
# Now both apps receive the same RTP stream
```

### ✅ Backward Compatibility

**100% backward compatible** - Existing code with explicit SSRCs continues to work without modification. The SSRC parameter is still supported, just optional.

### 📦 Installation

```bash
pip install ka9q==3.1.0
```

Or upgrade:
```bash
pip install --upgrade ka9q
```

### 📖 Documentation

- **CHANGELOG.md** - Complete version history
- **README.md** - Updated with new API examples

### 🙏 Credits

SSRC allocation algorithm inspired by Phil Karn's ka9q-radio project.

### 🐛 Issues & Feedback

Found a bug or have a feature request? Please open an issue on GitHub:
https://github.com/mijahauan/ka9q-python/issues

---

**Full Changelog**: https://github.com/mijahauan/ka9q-python/blob/main/CHANGELOG.md
