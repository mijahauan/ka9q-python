# ka9q-python v3.0.0 🎉

## Complete RadioD Feature Exposure

This major release provides **comprehensive control** over all ka9q-radio features through the Python interface. We've exposed **20 new control methods**, covering everything from satellite tracking to spectrum analysis.

### 🚀 What's New

#### 20 New Control Methods

**Satellite & Advanced Tuning**
- 🛰️ `set_doppler()` - Real-time Doppler tracking for satellites
- 📡 `set_first_lo()` - Direct hardware tuner control

**Signal Processing**
- 🔄 `set_pll()` - Phase-locked loop for carrier tracking
- 🔇 `set_squelch()` - SNR-based squelch with hysteresis
- 📻 `set_envelope_detection()` - AM envelope vs synchronous detection
- 🎚️ `set_independent_sideband()` - ISB mode (USB/LSB to L/R)
- 📶 `set_fm_threshold_extension()` - Weak FM signal improvement

**Audio & Output**
- 🔊 `set_output_channels()` - Mono/stereo control
- 🎵 `set_output_encoding()` - Format selection (PCM, Opus)
- 💿 `set_opus_bitrate()` - Opus quality control
- 📦 `set_packet_buffering()` - Latency vs packet rate trade-off
- 🌐 `set_destination()` - Dynamic output routing

**Filtering & Analysis**
- 🎛️ `set_filter2()` - Secondary filter for selectivity
- 📊 `set_spectrum()` - Spectrum analyzer configuration
- 🎯 `set_agc_threshold()` - AGC activation tuning

**System Control**
- ⚙️ `set_status_interval()` - Status reporting rate
- 🔀 `set_demod_type()` - Dynamic mode switching
- 📻 `set_rf_gain()` / `set_rf_attenuation()` - RF hardware control
- 🔬 `set_options()` - Experimental features

### 📚 Documentation

**New Guides:**
- **NEW_FEATURES.md** - Detailed documentation with examples
- **QUICK_REFERENCE.md** - Quick lookup guide
- **examples/advanced_features_demo.py** - Working demo script

### 💡 Example Use Cases

**Satellite Tracking:**
```python
from ka9q import RadiodControl

control = RadiodControl("radiod.local")
control.set_doppler(
    ssrc=12345, 
    doppler_hz=-5000, 
    doppler_rate_hz_per_sec=100
)
```

**Coherent AM Reception:**
```python
# Enable PLL for carrier tracking
control.set_pll(ssrc=12345, enable=True, bandwidth_hz=50)
control.set_envelope_detection(ssrc=12345, enable=False)
```

**ISB Mode (USB & LSB simultaneously):**
```python
control.set_independent_sideband(ssrc=12345, enable=True)
control.set_output_channels(ssrc=12345, channels=2)
```

**High-Quality Opus Streaming:**
```python
from ka9q.types import Encoding

control.set_output_encoding(ssrc=12345, encoding=Encoding.OPUS)
control.set_opus_bitrate(ssrc=12345, bitrate=128000)
```

**Spectrum Analysis:**
```python
control.set_spectrum(
    ssrc=12345, 
    bin_bw_hz=100, 
    bin_count=512,
    kaiser_beta=6.0
)
```

### ✅ Complete Feature Coverage

This release provides **comprehensive coverage** of radiod's TLV command set:

✅ All 35+ radiod commands now supported  
✅ Doppler tracking for satellite reception  
✅ PLL carrier tracking  
✅ SNR squelch with hysteresis  
✅ Independent sideband mode  
✅ FM threshold extension  
✅ Secondary filtering  
✅ Spectrum analyzer  
✅ Output encoding control  
✅ RF hardware controls  
✅ Experimental options  

### 🔄 Backward Compatibility

**100% backward compatible** - All existing code continues to work without modification. All changes are additive.

### 📦 Installation

```bash
pip install ka9q==3.0.0
```

Or upgrade:
```bash
pip install --upgrade ka9q
```

### 🧪 Testing

Run the demo script to see all new features:
```bash
python3 examples/advanced_features_demo.py
```

### 📖 Full Documentation

- **NEW_FEATURES.md** - Complete feature documentation
- **QUICK_REFERENCE.md** - Quick reference with examples
- **CHANGELOG.md** - Detailed changelog
- **RADIOD_FEATURES_SUMMARY.md** - Implementation details

### 🙏 Credits

Thanks to Phil Karn (KA9Q) for creating ka9q-radio and making its source code available for analysis.

### 🐛 Issues & Feedback

Found a bug or have a feature request? Please open an issue on GitHub:
https://github.com/mijahauan/ka9q-python/issues

---

**Full Changelog**: https://github.com/mijahauan/ka9q-python/blob/main/CHANGELOG.md
