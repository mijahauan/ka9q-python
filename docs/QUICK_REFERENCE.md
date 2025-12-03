# Quick Reference: New RadioD Features

## Import
```python
from ka9q.control import RadiodControl
from ka9q.types import Encoding
```

## Usage Examples

### Satellite Tracking
```python
control = RadiodControl(control_address="239.101.6.1")
# Set Doppler shift that's changing at 100 Hz/sec
control.set_doppler(ssrc=12345, doppler_hz=-5000, doppler_rate_hz_per_sec=100)
```

### Coherent AM Reception
```python
# Enable PLL for carrier tracking
control.set_pll(ssrc=12345, enable=True, bandwidth_hz=50)
control.set_envelope_detection(ssrc=12345, enable=False)  # Synchronous detection
```

### DSB Suppressed Carrier
```python
# Use squaring PLL for suppressed carrier
control.set_pll(ssrc=12345, enable=True, bandwidth_hz=20, square=True)
```

### SNR Squelch
```python
# Open at 10 dB, close at 8 dB (2 dB hysteresis)
control.set_squelch(ssrc=12345, enable=True, open_snr_db=10, close_snr_db=8)
```

### Independent Sideband (ISB)
```python
# USB on left, LSB on right
control.set_independent_sideband(ssrc=12345, enable=True)
control.set_output_channels(ssrc=12345, channels=2)
```

### FM Stereo
```python
# Enable stereo for WFM mode
control.set_output_channels(ssrc=12345, channels=2)
```

### Extra Selectivity
```python
# Add secondary filter for adjacent channel rejection
control.set_filter2(ssrc=12345, blocksize=5, kaiser_beta=3.5)
```

### Opus Encoding
```python
# Switch to Opus at 64 kbps
control.set_output_encoding(ssrc=12345, encoding=Encoding.OPUS)
control.set_opus_bitrate(ssrc=12345, bitrate=64000)
```

### Spectrum Analyzer
```python
# Configure for 100 Hz resolution, 512 bins
control.set_spectrum(ssrc=12345, bin_bw_hz=100, bin_count=512, kaiser_beta=6.0)
```

### Reduce Packet Rate
```python
# Buffer 2 blocks before sending (40ms at 20ms/block)
control.set_packet_buffering(ssrc=12345, min_blocks=2)
```

### AGC Fine-Tuning
```python
# Set AGC threshold 10 dB above noise floor
control.set_agc_threshold(ssrc=12345, threshold_db=10)
```

### Status Updates
```python
# Send status every 50 frames
control.set_status_interval(ssrc=12345, interval=50)
# Or disable automatic status
control.set_status_interval(ssrc=12345, interval=0)
```

### RF Hardware Control
```python
# Adjust RF gain (hardware-dependent)
control.set_rf_gain(ssrc=12345, gain_db=20)
control.set_rf_attenuation(ssrc=12345, atten_db=10)
```

### Switch Demodulator
```python
# 0=LINEAR, 1=FM, 2=WFM, 3=SPECTRUM
control.set_demod_type(ssrc=12345, demod_type=1)  # Switch to FM
```

### Change Output Format
```python
# Switch from PCM to float
control.set_output_encoding(ssrc=12345, encoding=Encoding.F32)
```

### Redirect Output
```python
# Change multicast destination
control.set_destination(ssrc=12345, address="239.1.2.3", port=5004)
```

### Hardware Tuning
```python
# Tune SDR hardware (affects ALL channels!)
control.set_first_lo(ssrc=12345, frequency_hz=14.1e6)
```

### FM Weak Signals
```python
# Enable threshold extension
control.set_fm_threshold_extension(ssrc=12345, enable=True)
```

### Experimental Features
```python
# Set/clear option bits
control.set_options(ssrc=12345, set_bits=0x01, clear_bits=0x02)
```

## Method Signatures

```python
# Doppler
set_doppler(ssrc, doppler_hz=0.0, doppler_rate_hz_per_sec=0.0)

# PLL
set_pll(ssrc, enable, bandwidth_hz=None, square=False)

# Squelch
set_squelch(ssrc, enable=True, open_snr_db=None, close_snr_db=None)

# Channels
set_output_channels(ssrc, channels)  # 1 or 2

# Linear mode
set_envelope_detection(ssrc, enable)
set_independent_sideband(ssrc, enable)

# FM mode
set_fm_threshold_extension(ssrc, enable)

# AGC
set_agc_threshold(ssrc, threshold_db)

# Encoding
set_output_encoding(ssrc, encoding)
set_opus_bitrate(ssrc, bitrate)

# Filtering
set_filter2(ssrc, blocksize, kaiser_beta=None)

# Spectrum
set_spectrum(ssrc, bin_bw_hz=None, bin_count=None, crossover_hz=None, kaiser_beta=None)

# Buffering
set_packet_buffering(ssrc, min_blocks)  # 0-4

# Status
set_status_interval(ssrc, interval)

# Mode
set_demod_type(ssrc, demod_type)  # 0-3

# Hardware
set_rf_gain(ssrc, gain_db)
set_rf_attenuation(ssrc, atten_db)

# Routing
set_destination(ssrc, address, port=5004)
set_first_lo(ssrc, frequency_hz)

# Options
set_options(ssrc, set_bits=0, clear_bits=0)
```

## Demod Types
- `0` = LINEAR (SSB, CW, AM)
- `1` = FM (Narrowband FM)
- `2` = WFM (Wideband FM, broadcast)
- `3` = SPECTRUM (Spectrum analyzer)

## Encoding Types
```python
from ka9q.types import Encoding

Encoding.NO_ENCODING = 0
Encoding.S16BE = 1      # 16-bit signed big-endian
Encoding.S16LE = 2      # 16-bit signed little-endian
Encoding.F32 = 3        # 32-bit float
Encoding.F16 = 4        # 16-bit float
Encoding.OPUS = 5       # Opus codec
```

## Error Handling
All methods may raise:
- `ValidationError` - Invalid parameters
- `CommandError` - Communication failure after retries

```python
from ka9q.control import ValidationError, CommandError

try:
    control.set_frequency(ssrc=12345, frequency_hz=14.1e6)
except ValidationError as e:
    print(f"Invalid parameter: {e}")
except CommandError as e:
    print(f"Communication error: {e}")
```

## Best Practices

1. **Always check return values** for async operations
2. **Use appropriate timeouts** for status queries
3. **Handle exceptions** for robustness
4. **Log operations** for debugging
5. **Close connections** when done: `control.close()`
6. **Test changes** on non-critical channels first
7. **Be cautious with `set_first_lo()`** - affects all channels
8. **Use appropriate AGC settings** for your signal type
9. **Combine settings logically** (e.g., ISB needs stereo output)
10. **Monitor metrics** with `control.get_metrics()`
