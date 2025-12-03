# Control Command Comparison: control.c vs ka9q-python

## Commands Sent by control.c

Based on analysis of `/home/mjh/git/ka9q-radio/src/control.c`, here are all the TLV commands the interactive `control` utility can send:

### Tuning & Frequency
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Radio frequency | `RADIO_FREQUENCY` | `f` | `set_frequency()` | ✅ |
| Shift frequency | `SHIFT_FREQUENCY` | arrow keys | `set_shift_frequency()` | ✅ |

### Demodulation & Mode
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Preset/Mode | `PRESET` | `p`, `m` | `set_preset()` | ✅ |
| Demod type | `DEMOD_TYPE` | (implicit) | `create_channel()` | ✅ |

### Filter & Bandwidth
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Low edge | `LOW_EDGE` | arrow keys | `set_filter()` | ✅ |
| High edge | `HIGH_EDGE` | arrow keys | `set_filter()` | ✅ |
| Kaiser beta | `KAISER_BETA` | `k` | `set_filter()` | ✅ |
| Filter2 Kaiser beta | `FILTER2_KAISER_BETA` | `K` | ❌ **MISSING** | ❌ |
| Spectrum Kaiser beta | `SPECTRUM_KAISER_BETA` | `w` | ❌ **MISSING** | ❌ |
| Filter2 blocksize | `FILTER2` | `F` | ❌ **MISSING** | ❌ |
| Spectrum crossover | `CROSSOVER` | `C` | ❌ **MISSING** | ❌ |

### AGC & Gain
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| AGC enable | `AGC_ENABLE` | `o` (agc) | `set_agc()` | ✅ |
| AGC hangtime | `AGC_HANGTIME` | `T` | `set_agc()` | ✅ |
| AGC threshold | `AGC_THRESHOLD` | `L` | `set_agc()` | ✅ |
| AGC recovery rate | `AGC_RECOVERY_RATE` | `R` | `set_agc()` | ✅ |
| AGC attack rate | `AGC_ATTACK_RATE` | (none) | `set_agc()` | ✅ |
| Headroom | `HEADROOM` | `H` | `set_agc()` | ✅ |
| Manual gain | `GAIN` | `g` | `set_gain()` | ✅ |
| RF gain | `RF_GAIN` | `G` | `tune()` | ✅ |
| RF attenuation | `RF_ATTEN` | `A` | `tune()` | ✅ |

### Output Configuration
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Output sample rate | `OUTPUT_SAMPRATE` | `S` | `set_sample_rate()` | ✅ |
| Output encoding | `OUTPUT_ENCODING` | `e` | `tune()` | ✅ |
| Output channels (mono/stereo) | `OUTPUT_CHANNELS` | `o` (mono/stereo) | ❌ **MISSING** | ❌ |
| Output destination | `OUTPUT_DATA_DEST_SOCKET` | `D` | `tune()`, `create_channel()` | ✅ |
| Output level | `OUTPUT_LEVEL` | (none) | `set_output_level()` | ✅ |
| Status interval | `STATUS_INTERVAL` | `u` | ❌ **MISSING** | ❌ |

### Squelch
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Squelch open threshold | `SQUELCH_OPEN` | `s` | ❌ **MISSING** | ❌ |
| Squelch close threshold | `SQUELCH_CLOSE` | `s` | ❌ **MISSING** | ❌ |
| SNR squelch enable | `SNR_SQUELCH` | mouse clicks | ❌ **MISSING** | ❌ |

### PLL (Phase-Locked Loop)
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| PLL enable | `PLL_ENABLE` | `o` (pll) | ❌ **MISSING** | ❌ |
| PLL square | `PLL_SQUARE` | `o` (square) | ❌ **MISSING** | ❌ |
| PLL bandwidth | `PLL_BW` | `P` | ❌ **MISSING** | ❌ |

### Advanced Options
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Independent sideband | `INDEPENDENT_SIDEBAND` | `o` (isb) | ❌ **MISSING** | ❌ |
| Envelope detection | `ENVELOPE` | mouse clicks | ❌ **MISSING** | ❌ |
| Threshold extend (FM) | `THRESH_EXTEND` | mouse clicks | ❌ **MISSING** | ❌ |
| Set options | `SETOPTS` | `O` | ❌ **MISSING** | ❌ |
| Clear options | `CLEAROPTS` | `O` | ❌ **MISSING** | ❌ |

### Codec-Specific
| Command | StatusType | control.c Key | ka9q-python Method | Status |
|---------|-----------|---------------|-------------------|--------|
| Opus bit rate | `OPUS_BIT_RATE` | `b` | ❌ **MISSING** | ❌ |
| Minimum packet buffering | `MINPACKET` | `B` | ❌ **MISSING** | ❌ |

## Summary Statistics

- **Total commands in control.c**: ~40
- **Implemented in ka9q-python**: 21 (52.5%)
- **Missing from ka9q-python**: 19 (47.5%)

## Priority Assessment

### High Priority (Core Functionality)
These are commonly used and should be implemented:

1. **`OUTPUT_CHANNELS`** (mono/stereo) - Basic audio configuration
2. **`SQUELCH_OPEN`** / **`SQUELCH_CLOSE`** - Essential for automated operation
3. **`PLL_ENABLE`** / **`PLL_BW`** - Important for weak signal work
4. **`INDEPENDENT_SIDEBAND`** - Useful for HF operations
5. **`OPUS_BIT_RATE`** - Codec tuning for network conditions

### Medium Priority (Advanced Features)
Less commonly used but still valuable:

6. **`FILTER2_KAISER_BETA`** / **`FILTER2`** - Advanced filtering
7. **`SPECTRUM_KAISER_BETA`** / **`CROSSOVER`** - Spectrum display tuning
8. **`STATUS_INTERVAL`** - Control status update rate
9. **`SNR_SQUELCH`** - SNR-based squelch control
10. **`ENVELOPE`** - AM envelope detection mode

### Low Priority (Specialized)
Rarely used or for specific scenarios:

11. **`PLL_SQUARE`** - Squaring PLL (specialized)
12. **`THRESH_EXTEND`** - FM threshold extension
13. **`SETOPTS`** / **`CLEAROPTS`** - Low-level bit manipulation
14. **`MINPACKET`** - Network packet buffering tuning

## Recommended Implementation Order

### Phase 1: Core Audio & Squelch
```python
def set_output_channels(self, ssrc: int, channels: int)
def set_squelch(self, ssrc: int, open_threshold: float, close_threshold: float = None)
def set_snr_squelch(self, ssrc: int, enable: bool)
```

### Phase 2: PLL & Advanced Demod
```python
def set_pll(self, ssrc: int, enable: bool, bandwidth: float = None, square: bool = False)
def set_independent_sideband(self, ssrc: int, enable: bool)
def set_envelope_detection(self, ssrc: int, enable: bool)
```

### Phase 3: Advanced Filtering
```python
def set_filter2(self, ssrc: int, blocksize: int = None, kaiser_beta: float = None)
def set_spectrum(self, ssrc: int, crossover: float = None, kaiser_beta: float = None)
```

### Phase 4: Codec & Network Tuning
```python
def set_opus(self, ssrc: int, bitrate: int, min_packet: int = None)
def set_status_interval(self, ssrc: int, interval: int)
```

## Usage Examples for Missing Features

### Example 1: Squelch Control
```python
# What we SHOULD be able to do:
control.set_squelch(
    ssrc=14074000,
    open_threshold=-10.0,  # dB SNR to open
    close_threshold=-11.0   # dB SNR to close (hysteresis)
)
```

### Example 2: Stereo/Mono Control
```python
# What we SHOULD be able to do:
control.set_output_channels(ssrc=14074000, channels=2)  # Stereo
control.set_output_channels(ssrc=14074000, channels=1)  # Mono
```

### Example 3: PLL for Weak Signals
```python
# What we SHOULD be able to do:
control.set_pll(
    ssrc=7074000,
    enable=True,
    bandwidth=20.0  # Hz, narrow for weak CW signals
)
```

### Example 4: Independent Sideband (ISB)
```python
# What we SHOULD be able to do:
control.set_independent_sideband(ssrc=14074000, enable=True)
```

## Implementation Notes

### Why These Are Missing

1. **Not in tune.c**: The `tune` utility (which ka9q-python was initially modeled after) is simpler than `control` and doesn't support all features
2. **Focus on automation**: Initial development focused on programmatic channel creation, not interactive tuning
3. **Display-related**: Some features (like spectrum settings) are more relevant to the interactive `control` UI

### Implementation Strategy

1. **Add encode functions** for new parameter types if needed
2. **Create setter methods** following existing patterns
3. **Add to `tune()` method** for parameters that make sense to set atomically
4. **Test with radiod** to verify parameter acceptance and effect
5. **Document** with clear examples and parameter ranges

## Next Steps

1. Review priority list with user to determine which features are most needed
2. Implement Phase 1 (core audio & squelch) features
3. Add comprehensive tests for new functions
4. Update API documentation
5. Consider adding to `tune()` method for atomic multi-parameter updates
