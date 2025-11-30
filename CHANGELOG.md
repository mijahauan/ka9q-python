# Changelog

## [Unreleased] - 2025-11-29

### Added - RTP Destination Control
- **`encode_socket()` function** in `ka9q/control.py`
  - Encodes IPv4 socket addresses in radiod's TLV format (6-byte format)
  - Validates IP addresses and port numbers
  - Matches radiod's `decode_socket()` expectations exactly

- **`_validate_multicast_address()` function** in `ka9q/control.py`
  - Validates multicast address format (IP or hostname)
  - Allows both IP addresses and DNS names

- **`destination` parameter** to `create_channel()` method
  - Accepts format: "address" or "address:port"
  - Examples: "239.1.2.3", "wspr.local", "239.1.2.3:5004"
  - Enables per-channel RTP destination control

- **Full `destination` support** in `tune()` method
  - Removed "not implemented" warning
  - Properly encodes destination socket addresses
  - Supports port specification (defaults to 5004)

- **Comprehensive documentation**:
  - `RTP_DESTINATION_FEATURE.md` - Feature documentation with examples
  - `CONTROL_COMPARISON.md` - Command-by-command comparison with control.c
  - `IMPLEMENTATION_STATUS.md` - Complete status of ka9q-python vs control/tune
  - `WEBUI_SUMMARY.md` - Web UI implementation details

- **Test suite** for socket encoding
  - `tests/test_encode_socket.py` - Comprehensive tests for encode_socket()
  - Tests roundtrip encoding/decoding
  - Tests error handling and validation

### Added - Web UI
- **Complete web-based control interface** (`webui/` directory)
  - `webui/app.py` - Flask backend with REST API
  - `webui/templates/index.html` - Modern responsive UI
  - `webui/static/style.css` - Dark theme styling
  - `webui/static/app.js` - Frontend logic with auto-refresh
  - `webui/start.sh` - Quick start script
  - `webui/requirements.txt` - Python dependencies
  - `webui/README.md` - Complete usage documentation

- **Web UI Features**:
  - Auto-discovery of radiod instances on LAN
  - Pull-down selector for radiod instances
  - Channel list with frequency, mode, sample rate, destination
  - Real-time channel monitoring (1-second auto-refresh)
  - 4-column layout: Tuning, Filter, Output, Signal
  - Full-width Gain & AGC section
  - Live SNR, baseband power, noise density
  - Error handling with auto-stop after 3 consecutive failures
  - Responsive design (desktop, tablet, mobile)
  - No framework dependencies (vanilla JavaScript)

- **Web UI API Endpoints**:
  - `GET /api/discover` - Discover radiod instances
  - `GET /api/channels/<address>` - List channels
  - `GET /api/channel/<address>/<ssrc>` - Get channel status
  - `POST /api/tune/<address>/<ssrc>` - Tune channel

### Fixed
- **Deduplication** in `discover_radiod_services()`
  - Uses dict with address as key to remove duplicates
  - Sorts results by name for consistency
  - Fixes multiple entries from avahi-browse (IPv4/IPv6, multiple interfaces)

- **Timeout handling** in web UI
  - Increased backend timeout from 2s to 10s
  - Added consecutive error tracking (stops after 3 failures)
  - Better error messages for inactive channels
  - Prevents refresh interval overlap

- **Channel selection** in web UI
  - Fixed bouncing between multiple channels
  - Only one channel refreshes at a time
  - Proper cleanup when switching channels
  - Added `isRefreshing` flag to prevent race conditions

### Changed
- **Control comparison** - Documented 52.5% coverage of control.c commands
  - 21 commands fully implemented (all core functionality)
  - 19 advanced commands not yet implemented (PLL, squelch, etc.)
  - 100% coverage of tune.c commands

- **Implementation status** - Confirmed ka9q-python is production-ready
  - Complete frequency control
  - Complete mode/preset control
  - Complete filter control (including Kaiser beta)
  - Complete AGC control (all 5 parameters)
  - Complete gain control (manual, RF gain, RF atten)
  - Complete output control (sample rate, encoding, destination)
  - Complete status interrogation

## Summary of Changes

This release adds:
1. **Per-channel RTP destination control** - Clients can now specify unique RTP destinations for each channel
2. **Web UI** - Modern browser-based interface for monitoring and controlling radiod
3. **Better discovery** - Deduplicated radiod instance discovery
4. **Comprehensive documentation** - Full comparison with control.c and implementation status

### Files Modified
- `ka9q/control.py` - Added encode_socket(), updated tune() and create_channel()
- `ka9q/discovery.py` - Fixed deduplication in discover_radiod_services()
- `tests/test_encode_socket.py` - New test suite

### Files Added
- `webui/` - Complete web UI implementation (7 files)
- `RTP_DESTINATION_FEATURE.md` - Feature documentation
- `CONTROL_COMPARISON.md` - Command comparison
- `IMPLEMENTATION_STATUS.md` - Implementation status
- `WEBUI_SUMMARY.md` - Web UI documentation
- `CHANGELOG.md` - This file

### Backward Compatibility
All changes are backward compatible. Existing code continues to work without modification.
The `destination` parameter is optional in both `create_channel()` and `tune()`.
