# Newly Exposed RadioD Features in ka9q-python

This document lists all the radiod features that have been newly exposed in the ka9q-python library.

## Summary

Added **17 new control methods** to the `RadiodControl` class, exposing previously unavailable radiod features. All methods follow the existing design patterns with proper validation, logging, and error handling.

## New Control Methods

### 1. Doppler Tracking
**Method:** `set_doppler(ssrc, doppler_hz, doppler_rate_hz_per_sec)`
- **Purpose:** Configure Doppler frequency shift and rate for satellite tracking
- **Use case:** Real-time satellite reception with changing Doppler shifts
- **Parameters:**
  - `doppler_hz`: Doppler frequency shift in Hz
  - `doppler_rate_hz_per_sec`: Rate of Doppler change in Hz/second

### 2. PLL Configuration
**Method:** `set_pll(ssrc, enable, bandwidth_hz, square)`
- **Purpose:** Configure Phase-Locked Loop for carrier tracking in linear modes
- **Use case:** Coherent AM/DSB reception, suppressed carrier signals
- **Parameters:**
  - `enable`: Enable/disable PLL
  - `bandwidth_hz`: PLL loop bandwidth (Hz)
  - `square`: Enable squaring loop for suppressed carrier

### 3. SNR Squelch
**Method:** `set_squelch(ssrc, enable, open_snr_db, close_snr_db)`
- **Purpose:** Configure SNR-based squelch with hysteresis
- **Use case:** Mute audio when signal drops below threshold
- **Parameters:**
  - `enable`: Enable/disable SNR squelch
  - `open_snr_db`: SNR threshold to open squelch
  - `close_snr_db`: SNR threshold to close squelch

### 4. Output Channels
**Method:** `set_output_channels(ssrc, channels)`
- **Purpose:** Set mono (1) or stereo (2) output
- **Use case:** Enable FM stereo decoding in WFM mode, or set mono/stereo for linear modes
- **Parameters:**
  - `channels`: 1 for mono, 2 for stereo

### 5. Envelope Detection
**Method:** `set_envelope_detection(ssrc, enable)`
- **Purpose:** Enable envelope detection for AM reception
- **Use case:** Switch between envelope (AM) and synchronous detection
- **Parameters:**
  - `enable`: True for envelope detection

### 6. Independent Sideband Mode
**Method:** `set_independent_sideband(ssrc, enable)`
- **Purpose:** Enable ISB mode (USB/LSB to separate L/R channels)
- **Use case:** Monitoring two separate channels simultaneously
- **Parameters:**
  - `enable`: True to enable ISB

### 7. FM Threshold Extension
**Method:** `set_fm_threshold_extension(ssrc, enable)`
- **Purpose:** Improve FM reception at weak signal levels
- **Use case:** Weak FM signal reception
- **Parameters:**
  - `enable`: True to enable threshold extension

### 8. AGC Threshold
**Method:** `set_agc_threshold(ssrc, threshold_db)`
- **Purpose:** Set AGC activation threshold above noise floor
- **Use case:** Fine-tune AGC behavior for different signal conditions
- **Parameters:**
  - `threshold_db`: Threshold in dB relative to noise floor

### 9. Opus Bitrate
**Method:** `set_opus_bitrate(ssrc, bitrate)`
- **Purpose:** Configure Opus encoder bitrate
- **Use case:** Trade quality for bandwidth (or vice versa)
- **Parameters:**
  - `bitrate`: Bitrate in bps (0=auto, typical 32000-128000)

### 10. Packet Buffering
**Method:** `set_packet_buffering(ssrc, min_blocks)`
- **Purpose:** Control RTP packet buffering (0-4 blocks)
- **Use case:** Reduce packet rate at cost of latency
- **Parameters:**
  - `min_blocks`: Minimum blocks (0=none, 4=80ms at 20ms/block)

### 11. Secondary Filter
**Method:** `set_filter2(ssrc, blocksize, kaiser_beta)`
- **Purpose:** Configure additional filtering stage
- **Use case:** Extra selectivity for adjacent channel rejection
- **Parameters:**
  - `blocksize`: Filter size (0=disable, 1-10)
  - `kaiser_beta`: Kaiser window parameter

### 12. Spectrum Analyzer
**Method:** `set_spectrum(ssrc, bin_bw_hz, bin_count, crossover_hz, kaiser_beta)`
- **Purpose:** Configure spectrum analyzer mode parameters
- **Use case:** Spectrum monitoring and analysis
- **Parameters:**
  - `bin_bw_hz`: Frequency bin bandwidth
  - `bin_count`: Number of bins
  - `crossover_hz`: Algorithm crossover frequency
  - `kaiser_beta`: Window parameter

### 13. Status Interval
**Method:** `set_status_interval(ssrc, interval)`
- **Purpose:** Set automatic status reporting rate
- **Use case:** Control metadata update frequency
- **Parameters:**
  - `interval`: Status interval in frames (0=disable)

### 14. Demodulator Type
**Method:** `set_demod_type(ssrc, demod_type)`
- **Purpose:** Change demodulator type dynamically
- **Use case:** Switch between LINEAR/FM/WFM/SPECTRUM modes
- **Parameters:**
  - `demod_type`: 0=LINEAR, 1=FM, 2=WFM, 3=SPECTRUM

### 15. Output Encoding
**Method:** `set_output_encoding(ssrc, encoding)`
- **Purpose:** Set audio output encoding format
- **Use case:** Switch between PCM formats or Opus
- **Parameters:**
  - `encoding`: Encoding type (S16BE, S16LE, F32, F16, OPUS)

### 16. RF Hardware Controls
**Methods:** `set_rf_gain(ssrc, gain_db)`, `set_rf_attenuation(ssrc, atten_db)`
- **Purpose:** Control RF front-end gain/attenuation
- **Use case:** Optimize dynamic range for signal conditions
- **Parameters:**
  - `gain_db` / `atten_db`: Hardware-dependent range
- **Note:** Hardware-dependent (e.g., RX888)

### 17. Output Destination
**Method:** `set_destination(ssrc, address, port)`
- **Purpose:** Change RTP output multicast destination
- **Use case:** Redirect audio stream dynamically
- **Parameters:**
  - `address`: Multicast IP or mDNS name
  - `port`: RTP port (default 5004)

### 18. First LO Control
**Method:** `set_first_lo(ssrc, frequency_hz)`
- **Purpose:** Tune the SDR hardware front-end
- **Use case:** Change hardware tuning frequency
- **Parameters:**
  - `frequency_hz`: First LO frequency
- **Warning:** Affects ALL channels

### 19. Option Bits
**Method:** `set_options(ssrc, set_bits, clear_bits)`
- **Purpose:** Set/clear experimental option flags
- **Use case:** Enable debug features, experimental modes
- **Parameters:**
  - `set_bits`: Bitmask of options to set
  - `clear_bits`: Bitmask of options to clear

## Updated Constants

### types.py Changes
- `SPECTRUM_FFT_N = 76` (was `UNUSED16`)
- `SPECTRUM_KAISER_BETA = 91` (was `UNUSED20`)
- `CROSSOVER = 95` (was `UNUSED21`)

## Compatibility

All new methods:
- Follow existing ka9q-python patterns and conventions
- Include comprehensive docstrings with examples
- Perform input validation with clear error messages
- Use proper logging for debugging
- Are compatible with existing code (no breaking changes)

## Testing

A demonstration script is provided in `examples/advanced_features_demo.py` showing usage of all new features.

## Related RadioD StatusType Codes

The following radiod TLV status types are now fully supported:

- `DOPPLER_FREQUENCY` (30)
- `DOPPLER_FREQUENCY_RATE` (31)
- `PLL_ENABLE` (49)
- `PLL_BW` (50)
- `PLL_SQUARE` (51)
- `SNR_SQUELCH` (52)
- `OUTPUT_CHANNELS` (67)
- `ENVELOPE` (53)
- `INDEPENDENT_SIDEBAND` (54)
- `THRESH_EXTEND` (90)
- `AGC_THRESHOLD` (46)
- `OPUS_BIT_RATE` (71)
- `MINPACKET` (72)
- `FILTER2` (73)
- `FILTER2_KAISER_BETA` (75)
- `NONCOHERENT_BIN_BW` (93)
- `BIN_COUNT` (94)
- `CROSSOVER` (95)
- `SPECTRUM_KAISER_BETA` (91)
- `STATUS_INTERVAL` (68)
- `DEMOD_TYPE` (15)
- `OUTPUT_ENCODING` (16)
- `RF_GAIN` (98)
- `RF_ATTEN` (97)
- `OUTPUT_DATA_DEST_SOCKET` (13)
- `FIRST_LO_FREQUENCY` (27)
- `SETOPTS` (107)
- `CLEAROPTS` (108)

## Previously Exposed Features

The following features were already available in ka9q-python:
- `set_frequency()` - RADIO_FREQUENCY
- `set_preset()` - PRESET
- `set_sample_rate()` - OUTPUT_SAMPRATE
- `set_agc()` - AGC_ENABLE, AGC_HANGTIME, HEADROOM, AGC_RECOVERY_RATE
- `set_gain()` - GAIN
- `set_filter()` - LOW_EDGE, HIGH_EDGE, KAISER_BETA
- `set_shift_frequency()` - SHIFT_FREQUENCY
- `set_output_level()` - OUTPUT_LEVEL
- `create_channel()` - Dynamic channel creation
- `tune()` - Comprehensive channel configuration
- `remove_channel()` - Channel removal

## Implementation Notes

1. All new methods use the existing TLV encoding infrastructure
2. Rate limiting and retry logic from the base `send_command()` method apply
3. Command tags are automatically generated for tracking
4. Thread-safe operation via existing socket handling
5. All methods log their operations for debugging

## Future Enhancements

Possible future additions:
- Batch command sending for multiple parameter changes
- Status polling helpers for the new parameters
- Higher-level convenience wrappers combining multiple settings
- Validation against hardware capabilities
