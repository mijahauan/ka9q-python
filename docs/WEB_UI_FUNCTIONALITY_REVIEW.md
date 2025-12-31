# Web UI Functionality Review vs Control Program

**Date**: 2024-12-30  
**Reviewer**: Analysis of web-ui against ka9q-radio's ncurses `control` utility

## Executive Summary

The web-ui currently provides **read-only monitoring** of radiod channels with excellent display capabilities. However, it lacks the **full get/set functionality** that the ncurses `control` program provides. The web-ui can display all parameters but **cannot modify most of them**.

### Current State
- ✅ **Display**: Comprehensive read-only view of all channel parameters
- ⚠️ **Control**: Limited to basic tuning only (frequency, preset, sample_rate, filter edges, gain, AGC)
- ❌ **Missing**: 19 out of ~40 control commands from `control.c` (47.5%)

## Detailed Comparison

### 1. What Web-UI Can Display (Read)

The web-ui displays all these parameters from channel status:

#### ✅ Tuning & Frequency
- Frequency (MHz)
- Mode/Preset
- SSRC
- Shift frequency
- Doppler frequency

#### ✅ Filter Parameters
- Low edge
- High edge
- Bandwidth (calculated)
- Kaiser beta
- FFT block size
- FIR filter length

#### ✅ Output Configuration
- Sample rate
- Encoding type
- RTP destination
- Output packets/errors

#### ✅ Gain & AGC
- AGC enable status
- Channel gain
- Headroom
- AGC hang time
- AGC recovery rate
- RF gain
- RF attenuation
- RF AGC status

#### ✅ Signal Measurements
- SNR
- Baseband power
- Noise density
- IF power

#### ✅ Demodulation
- Demod type
- PLL enable/lock status
- PLL bandwidth
- Squelch threshold

#### ✅ Hardware
- LNA gain
- Mixer gain
- IF gain
- First/Second LO frequencies

#### ✅ Statistics
- Data packets
- Metadata packets
- Output errors
- Filter drops

### 2. What Web-UI Can Modify (Write)

Currently implemented in `/api/tune` endpoint:

#### ✅ Basic Tuning (7 parameters)
1. **Frequency** (`frequency_hz`) - ✅ Working
2. **Preset/Mode** (`preset`) - ✅ Working
3. **Sample Rate** (`sample_rate`) - ✅ Working
4. **Low Edge** (`low_edge`) - ✅ Working
5. **High Edge** (`high_edge`) - ✅ Working
6. **Gain** (`gain`) - ✅ Working
7. **AGC Enable** (`agc_enable`) - ✅ Working

### 3. What Web-UI CANNOT Modify (Missing Controls)

Based on `CONTROL_COMPARISON.md`, these 19 commands are **missing from web-ui**:

#### ❌ High Priority (Core Functionality)
1. **Output Channels** (mono/stereo) - `OUTPUT_CHANNELS`
2. **Squelch Open/Close** - `SQUELCH_OPEN`, `SQUELCH_CLOSE`
3. **SNR Squelch** - `SNR_SQUELCH`
4. **PLL Enable/Bandwidth** - `PLL_ENABLE`, `PLL_BW`
5. **PLL Square** - `PLL_SQUARE`
6. **Independent Sideband** - `INDEPENDENT_SIDEBAND`
7. **Opus Bit Rate** - `OPUS_BIT_RATE`

#### ❌ Medium Priority (Advanced Features)
8. **Filter2 Kaiser Beta** - `FILTER2_KAISER_BETA`
9. **Filter2 Blocksize** - `FILTER2`
10. **Spectrum Kaiser Beta** - `SPECTRUM_KAISER_BETA`
11. **Spectrum Crossover** - `CROSSOVER`
12. **Status Interval** - `STATUS_INTERVAL`
13. **Envelope Detection** - `ENVELOPE`
14. **AGC Threshold** - `AGC_THRESHOLD`
15. **Headroom** (read-only, not settable) - `HEADROOM`
16. **AGC Hangtime** (read-only, not settable) - `AGC_HANGTIME`
17. **AGC Recovery Rate** (read-only, not settable) - `AGC_RECOVERY_RATE`

#### ❌ Low Priority (Specialized)
18. **Threshold Extend (FM)** - `THRESH_EXTEND`
19. **Set/Clear Options** - `SETOPTS`, `CLEAROPTS`
20. **Min Packet Buffering** - `MINPACKET`
21. **RF Gain** (read-only, not settable) - `RF_GAIN`
22. **RF Attenuation** (read-only, not settable) - `RF_ATTEN`

## Architecture Analysis

### Backend (`app.py`)

**Current Implementation:**
```python
@app.route('/api/tune/<radiod_address>/<int:ssrc>', methods=['POST'])
def tune_channel(radiod_address, ssrc):
    # Only handles: frequency, preset, sample_rate, low_edge, high_edge, gain, agc_enable
    params = {'ssrc': ssrc}
    if 'frequency' in data:
        params['frequency_hz'] = float(data['frequency'])
    # ... etc
    status = control.tune(**params, timeout=2.0)
```

**What's Missing:**
- No endpoints for squelch control
- No endpoints for PLL configuration
- No endpoints for output channels (mono/stereo)
- No endpoints for codec settings (Opus bitrate)
- No endpoints for advanced AGC parameters (threshold, hangtime, recovery)
- No endpoints for advanced filter settings (filter2, spectrum)

### Frontend (`app.js`, `index.html`)

**Current Implementation:**
- Read-only display of all parameters
- No input controls (sliders, buttons, text fields)
- No forms for parameter modification
- Auto-refresh every 1 second (display only)

**What's Missing:**
- Interactive controls for modifying parameters
- Input validation
- Parameter range checking
- Confirmation dialogs for critical changes
- Undo/reset functionality

### Control Library (`ka9q/control.py`)

**Available Methods (Not Used by Web-UI):**
```python
# Already implemented but NOT exposed in web-ui:
control.set_agc(ssrc, enable, hangtime, headroom, recovery_rate, attack_rate)
control.set_shift_frequency(ssrc, shift_hz)
control.set_output_level(ssrc, level)

# Missing from control.py (need implementation):
control.set_squelch(ssrc, open_threshold, close_threshold)
control.set_pll(ssrc, enable, bandwidth, square)
control.set_output_channels(ssrc, channels)
control.set_opus(ssrc, bitrate)
control.set_independent_sideband(ssrc, enable)
control.set_envelope_detection(ssrc, enable)
control.set_filter2(ssrc, blocksize, kaiser_beta)
control.set_spectrum(ssrc, crossover, kaiser_beta)
```

## Gap Analysis Summary

### Category 1: Backend Methods Exist, Not Exposed in Web-UI
These are **quick wins** - just need API endpoints and UI controls:

1. **AGC Advanced** - `set_agc()` supports hangtime, headroom, recovery_rate
2. **Shift Frequency** - `set_shift_frequency()` exists
3. **Output Level** - `set_output_level()` exists

### Category 2: Backend Methods Missing, Need Implementation
These require **new methods in control.py** first:

1. **Squelch Control** - High priority
2. **PLL Configuration** - High priority
3. **Output Channels** - High priority
4. **Opus Bitrate** - Medium priority
5. **Independent Sideband** - Medium priority
6. **Envelope Detection** - Medium priority
7. **Filter2 Settings** - Medium priority
8. **Spectrum Settings** - Medium priority

### Category 3: Read-Only Hardware Parameters
These are **informational only** and cannot be set via control protocol:

1. LNA/Mixer/IF Gain (hardware-specific)
2. First/Second LO frequencies (derived from tuning)
3. Signal measurements (SNR, power, noise)

## Recommendations

### Phase 1: Expose Existing Backend Methods (Quick Wins)

**Effort**: Low (1-2 days)  
**Impact**: Medium

1. Add API endpoints for:
   - Advanced AGC parameters (hangtime, headroom, recovery_rate)
   - Shift frequency control
   - Output level control

2. Add UI controls:
   - AGC section with sliders/inputs
   - Shift frequency input
   - Output level slider

### Phase 2: Implement High-Priority Missing Features

**Effort**: Medium (3-5 days)  
**Impact**: High

1. **Squelch Control**
   - Implement `set_squelch()` in `control.py`
   - Add `/api/squelch` endpoint
   - Add squelch controls to UI

2. **PLL Configuration**
   - Implement `set_pll()` in `control.py`
   - Add `/api/pll` endpoint
   - Add PLL controls to UI

3. **Output Channels (Mono/Stereo)**
   - Implement `set_output_channels()` in `control.py`
   - Add `/api/output_channels` endpoint
   - Add mono/stereo toggle to UI

### Phase 3: Advanced Features

**Effort**: Medium-High (5-7 days)  
**Impact**: Medium

1. **Codec Settings**
   - Implement `set_opus()` in `control.py`
   - Add codec configuration UI

2. **Advanced Demodulation**
   - Implement ISB, envelope detection
   - Add demod mode controls

3. **Advanced Filtering**
   - Implement filter2, spectrum settings
   - Add advanced filter controls

### Phase 4: UI/UX Enhancements

**Effort**: Medium (3-5 days)  
**Impact**: High (usability)

1. **Interactive Controls**
   - Replace read-only displays with editable inputs
   - Add sliders for continuous parameters
   - Add toggles for boolean parameters
   - Add dropdowns for enumerated parameters

2. **User Experience**
   - Add "Edit Mode" toggle
   - Add parameter validation
   - Add confirmation dialogs
   - Add undo/reset functionality
   - Add preset save/load

3. **Visual Feedback**
   - Highlight changed parameters
   - Show pending changes
   - Indicate successful/failed updates
   - Add loading states

## Proposed UI Mockup

### Current (Read-Only)
```
┌─────────────────────────────────────┐
│ Gain & AGC                          │
├─────────────────────────────────────┤
│ AGC:              ON                │
│ Channel Gain:     -10.5 dB          │
│ Headroom:         5.0 dB            │
│ Hang Time:        2.5 s             │
│ Recovery:         1.0 dB/s          │
└─────────────────────────────────────┘
```

### Proposed (Interactive)
```
┌─────────────────────────────────────┐
│ Gain & AGC                    [Edit]│
├─────────────────────────────────────┤
│ AGC:              [●] ON  [ ] OFF   │
│ Channel Gain:     [-10.5] dB        │
│ Headroom:         [====|===] 5.0 dB │
│ Hang Time:        [====|===] 2.5 s  │
│ Recovery:         [===|====] 1.0 dB/s│
│                   [Apply] [Reset]   │
└─────────────────────────────────────┘
```

## Implementation Priority Matrix

| Feature | Priority | Effort | Impact | Status |
|---------|----------|--------|--------|--------|
| Squelch Control | HIGH | Medium | High | ❌ Not Started |
| PLL Configuration | HIGH | Medium | High | ❌ Not Started |
| Output Channels | HIGH | Low | High | ❌ Not Started |
| Advanced AGC | HIGH | Low | Medium | ⚠️ Backend Ready |
| Interactive UI | HIGH | Medium | High | ❌ Not Started |
| Opus Bitrate | MEDIUM | Medium | Medium | ❌ Not Started |
| ISB/Envelope | MEDIUM | Medium | Low | ❌ Not Started |
| Filter2/Spectrum | LOW | Medium | Low | ❌ Not Started |

## Technical Debt

### Current Issues
1. **No input validation** in frontend
2. **No error handling** for failed parameter changes
3. **No state management** for pending changes
4. **No undo mechanism**
5. **No parameter range checking**

### Security Considerations
1. Add authentication (currently open to LAN)
2. Add rate limiting for parameter changes
3. Add audit logging for configuration changes
4. Validate all inputs server-side

## Conclusion

The web-ui has **excellent read capabilities** but lacks the **write/control functionality** of the ncurses `control` program. To achieve feature parity:

1. **Immediate**: Expose existing backend methods (AGC, shift, output level)
2. **Short-term**: Implement high-priority missing features (squelch, PLL, output channels)
3. **Medium-term**: Add interactive UI controls with proper validation
4. **Long-term**: Implement advanced features and UX enhancements

**Estimated Total Effort**: 15-20 days for full feature parity with `control` program

**Current Capability**: ~20% of control program's functionality (read-only monitoring + basic tuning)  
**Target Capability**: 100% of control program's functionality (full get/set control)
