# GitHub Release for v2.4.0

## Web UI and Release Creation

The GitHub release for v2.4.0 has already been created automatically via `git push origin v2.4.0`.

To view or edit the release, visit:
https://github.com/mijahauan/ka9q-python/releases/tag/v2.4.0

## Release Summary

**Tag:** v2.4.0  
**Title:** Release v2.4.0: RTP Destination Control + Web UI  
**Date:** November 29, 2025

### Key Features

1. **Per-Channel RTP Destination Control**
   - `encode_socket()` function for socket address encoding
   - `destination` parameter in `create_channel()` and `tune()`
   - Full `OUTPUT_DATA_DEST_SOCKET` TLV command support

2. **Complete Web UI**
   - Flask-based REST API backend
   - Modern responsive interface
   - Real-time channel monitoring
   - Auto-discovery of radiod instances

3. **Discovery Improvements**
   - Fixed duplicate radiod instances
   - Deduplication by IP address

### Statistics

- **17 files changed**
- **3,155 insertions(+), 286 deletions(-)**
- **~1,100 lines** of web UI code
- **~2,000 lines** of documentation

### Documentation

- `RTP_DESTINATION_FEATURE.md`
- `CONTROL_COMPARISON.md`
- `IMPLEMENTATION_STATUS.md`
- `WEBUI_SUMMARY.md`
- `CHANGELOG.md`
- `webui/README.md`

## Release Description (for GitHub UI)

If editing the release on GitHub, use this description:

---

# Release v2.4.0: RTP Destination Control + Web UI

**Release Date:** November 29, 2025  
**Type:** Major Feature Release  
**Compatibility:** Fully backward compatible with v2.3.0

---

## 🎉 What's New

### 1. Per-Channel RTP Destination Control

Control exactly where each channel's RTP stream goes:

```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")

# Specify unique destination for this channel
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    destination="239.1.2.3:5004"  # NEW!
)

# Works with hostnames too
control.tune(ssrc=7074000, destination="wspr.local")
```

**Features:**
- Per-channel RTP multicast destinations
- Supports IP addresses and DNS names
- Port specification (defaults to 5004)
- Full `OUTPUT_DATA_DEST_SOCKET` TLV command support

### 2. Web UI for Radiod Monitoring

Complete browser-based interface for monitoring radiod:

```bash
cd webui
./start.sh
# Open http://localhost:5000
```

**Features:**
- 📡 Auto-discovery of radiod instances
- 📊 Real-time channel monitoring (1-second updates)
- 📱 Responsive design (desktop/tablet/mobile)
- 🎨 Modern dark theme
- ⚡ Live SNR, power, noise measurements
- 🔄 Auto-refresh with error handling
- 🚫 No framework dependencies (vanilla JS)

**Layout:**
- 4-column display: Tuning, Filter, Output, Signal
- Full-width Gain & AGC section
- Mobile-friendly responsive design

### 3. Discovery Improvements

Fixed duplicate entries in radiod service discovery:
- Deduplicates by IP address
- Alphabetical sorting
- Handles multiple avahi-browse results

---

## 📦 Installation

```bash
pip install git+https://github.com/mijahauan/ka9q-python.git@v2.4.0
```

Or clone and install:

```bash
git clone https://github.com/mijahauan/ka9q-python.git
cd ka9q-python
git checkout v2.4.0
pip install -e .
```

---

## 🚀 Quick Start

### RTP Destination Control

```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")

# Create channel with specific destination
control.create_channel(
    ssrc=14074000,
    frequency_hz=14.074e6,
    preset="usb",
    sample_rate=12000,
    destination="239.1.2.3:5004"
)
```

### Web UI

```bash
cd webui
pip install -r requirements.txt
./start.sh
```

Then open http://localhost:5000 in your browser.

---

## 📊 Implementation Status

- ✅ **100% coverage** of tune.c commands
- ✅ **52.5% coverage** of control.c commands (all core features)
- ✅ All tuning, filtering, gain, AGC, and output controls
- ✅ **NEW:** RTP destination control

**What You Can Control:**
- Frequency, Mode, Filters (Low/High edges, Kaiser beta)
- Gain (Manual, RF gain, RF atten, Headroom)
- AGC (Enable, Hangtime, Threshold, Recovery rate)
- Output (Sample rate, Encoding, **Destination**, Channels)

---

## 📝 Documentation

**New Documentation:**
- [RTP_DESTINATION_FEATURE.md](../RTP_DESTINATION_FEATURE.md) - Complete feature guide
- [CONTROL_COMPARISON.md](../CONTROL_COMPARISON.md) - Command comparison
- [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) - Implementation status
- [WEBUI_SUMMARY.md](../WEBUI_SUMMARY.md) - Web UI architecture
- [CHANGELOG.md](../CHANGELOG.md) - Complete changelog
- [webui/README.md](../../webui/README.md) - Web UI usage guide

**Release Notes:**
- [RELEASE_NOTES_v2.4.0.md](RELEASE_NOTES_v2.4.0.md) - Comprehensive release notes

---

## 🎯 Use Cases

### RTP Destination Control
- Dynamic stream routing per channel
- Multiple destinations for different frequencies
- Network-efficient multicast distribution
- Custom stream organization

### Web UI
- Remote monitoring without SSH
- Multi-user access
- Mobile/tablet monitoring
- Visual signal quality assessment
- Demo/presentation mode

---

## 📈 Statistics

- **17 files changed**
- **3,155 lines added**, 286 lines deleted
- **Web UI:** 1,100+ lines of production code
- **Documentation:** 2,000+ lines across 5 new docs
- **Test suite:** Comprehensive socket encoding tests

---

## 🔄 Backward Compatibility

**100% backward compatible** - All existing code continues to work:

```python
# v2.3.0 code still works in v2.4.0
control = RadiodControl("radiod.local")
control.create_channel(ssrc=14074000, frequency_hz=14.074e6, preset="usb")
```

New features are **optional** - use them when you need them!

---

## 🧪 Testing

Tested on:
- ✅ Single-homed and multi-homed systems
- ✅ Multiple radiod instances
- ✅ Real-time monitoring scenarios
- ✅ Desktop browsers (Chrome, Firefox, Safari, Edge)
- ✅ Mobile browsers (iOS Safari, Android Chrome)

---

## 🔗 Resources

- **Full Release Notes:** [RELEASE_NOTES_v2.4.0.md](RELEASE_NOTES_v2.4.0.md)
- **Changelog:** [CHANGELOG.md](../../CHANGELOG.md)
- **Web UI Guide:** [webui/README.md](../../webui/README.md)
- **Issues:** https://github.com/mijahauan/ka9q-python/issues
- **ka9q-radio:** https://github.com/ka9q/ka9q-radio

---

**Full Changelog:** https://github.com/mijahauan/ka9q-python/blob/main/CHANGELOG.md

---

**Thank you for using ka9q-python!** 📻✨
