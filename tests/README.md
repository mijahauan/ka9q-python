# Ka9q-Python Test Suite

This directory contains comprehensive tests for the ka9q-python package, with a focus on the tune functionality implementation.

## Test Organization

### Unit Tests

#### `test_decode_functions.py`
Tests for TLV (Type-Length-Value) decode functions that parse status responses from radiod:
- `decode_int()` - Integer decoding with variable-length big-endian encoding
- `decode_int32()` - 32-bit integer decoding
- `decode_float()` - 32-bit float decoding (IEEE 754)
- `decode_double()` - 64-bit double decoding (IEEE 754)
- `decode_bool()` - Boolean value decoding
- `decode_string()` - UTF-8 string decoding
- `decode_socket()` - Socket address decoding (IPv4)

**Coverage:**
- Zero values and empty data
- Single and multi-byte values
- Big-endian encoding verification
- Compressed encoding (leading zeros stripped)
- Edge cases and error handling

#### `test_encode_functions.py`
Tests for TLV encode functions that build command packets:
- `encode_int()` / `encode_int64()` - Integer encoding with compression
- `encode_float()` - 32-bit float encoding
- `encode_double()` - 64-bit double encoding
- `encode_string()` - UTF-8 string encoding with length handling
- `encode_eol()` - End-of-list marker
- Round-trip encode/decode verification

**Coverage:**
- Zero compression (zero-length encoding)
- Leading zero stripping
- Multi-byte length encoding for strings
- Big-endian format verification
- String length limits
- Round-trip symmetry tests

#### `test_tune_method.py`
Tests for the `RadiodControl.tune()` method and related functionality:
- Basic parameter tuning (frequency, preset, sample rate)
- Timeout handling
- SSRC matching in responses
- Command tag matching
- AGC/gain interaction
- All parameters combined
- Status response decoding
- SNR calculation
- Socket setup and multicast joining

**Coverage:**
- Mock socket responses
- Response filtering (wrong SSRC/tag)
- Timeout errors
- Field decoding verification
- Status listener setup

#### `test_tune_cli.py`
Tests for the `tune.py` CLI tool:
- `parse_frequency()` - Parse frequency strings with k/M/G suffixes
- `encoding_from_string()` - Parse encoding type strings
- `format_frequency()` - Format frequencies for display
- `format_socket()` - Format socket addresses
- CLI argument parsing
- Filter edge parsing (including negative values)

**Coverage:**
- Frequency suffixes (k, M, G)
- Scientific notation
- Case insensitivity
- Whitespace handling
- All encoding types
- Edge cases and error handling

## Running Tests

### Install Test Dependencies

```bash
# Install the package with development dependencies
pip install -e .[dev]

# Or install pytest directly
pip install pytest pytest-cov
```

### Run All Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=ka9q --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_decode_functions.py -v

# Run specific test class
pytest tests/test_decode_functions.py::TestDecodeInt -v

# Run specific test
pytest tests/test_decode_functions.py::TestDecodeInt::test_decode_zero -v
```

### Test Output Examples

```bash
# Expected output for passing tests:
$ pytest tests/test_decode_functions.py -v
======================== test session starts =========================
collected 45 items

tests/test_decode_functions.py::TestDecodeInt::test_decode_zero PASSED
tests/test_decode_functions.py::TestDecodeInt::test_decode_single_byte PASSED
...
======================== 45 passed in 0.12s ==========================
```

## Integration Testing

### Manual Integration Tests

For integration testing with a live radiod instance, use the example scripts:

#### 1. Test CLI Tool

```bash
# Basic tune command (requires radiod running)
./examples/tune.py -r radiod.local -s 14074000 -f 14.074M -m usb -v

# Test with all parameters
./examples/tune.py -r radiod.local -s 10000000 \
    -f 10M -m iq -R 48000 \
    -L -24k -H 24k \
    -g 10 -v
```

Expected output:
```
SSRC 10000000
Preset: iq
Sample rate: 48,000 Hz
Frequency: 10.000000 MHz
Channel AGC: off
Channel Gain: 10.0 dB
...
```

#### 2. Test Python API

```bash
# Run the tune example script
python examples/tune_example.py
```

Expected output:
```
Connecting to radiod...

=== Example 1: USB channel for FT8 ===
✓ Channel created successfully
  SSRC: 14074000
  Frequency: 14.074000 MHz
  Preset: usb
  Sample Rate: 12000 Hz
  SNR: 15.3 dB
...
```

#### 3. Test with Different radiod Configurations

```bash
# Test with various presets
for preset in iq usb lsb am fm cw; do
    echo "Testing preset: $preset"
    ./examples/tune.py -r radiod.local -s 10000000 -f 10M -m $preset -q
done

# Test frequency ranges
./examples/tune.py -r radiod.local -s 1 -f 1.8M -m lsb    # 160m
./examples/tune.py -r radiod.local -s 2 -f 3.5M -m lsb    # 80m
./examples/tune.py -r radiod.local -s 3 -f 7.0M -m lsb    # 40m
./examples/tune.py -r radiod.local -s 4 -f 14.0M -m usb   # 20m
./examples/tune.py -r radiod.local -s 5 -f 28.0M -m usb   # 10m
./examples/tune.py -r radiod.local -s 6 -f 144M -m fm     # 2m
```

### Integration Test Checklist

When testing against a live radiod instance, verify:

- [ ] Channel creation succeeds
- [ ] Status response is received within timeout
- [ ] All requested parameters are reflected in status
- [ ] Frequency is set accurately (within 1 Hz)
- [ ] AGC/gain settings work correctly
- [ ] Filter edges are set properly
- [ ] Sample rate matches request
- [ ] Preset/mode is applied
- [ ] SNR is calculated when data available
- [ ] Multiple channels can coexist
- [ ] Re-tuning existing channel works
- [ ] Timeout occurs when radiod unavailable

## Test Coverage Goals

Target coverage by module:
- `ka9q/control.py` decode functions: 100%
- `ka9q/control.py` encode functions: 100%
- `ka9q/control.py` tune() method: 90%+
- `examples/tune.py` utility functions: 100%

Current coverage can be checked with:
```bash
pytest tests/ --cov=ka9q --cov-report=term-missing
```

## Continuous Integration

These tests are designed to run without requiring a live radiod instance (using mocks). They can be integrated into CI/CD pipelines:

```yaml
# Example .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -e .[dev]
      - run: pytest tests/ --cov=ka9q --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

If you see import errors:
```bash
ModuleNotFoundError: No module named 'ka9q'
```

Solution: Install the package in development mode:
```bash
pip install -e .
```

### Socket Permission Errors

If you see permission errors when testing multicast:
```
PermissionError: [Errno 13] Permission denied
```

This typically happens in restricted environments. The unit tests use mocks to avoid this, but integration tests need proper network access.

### Timeout in Tests

If tests timeout, check:
1. Mock setup is correct (for unit tests)
2. radiod is running and accessible (for integration tests)
3. Firewall allows multicast traffic
4. Network interface supports multicast

## Adding New Tests

When adding tune functionality:

1. **Add unit tests** for new encode/decode functions
2. **Add method tests** for new RadiodControl methods
3. **Add CLI tests** if adding command-line options
4. **Update integration checklist** with new features
5. **Document expected behavior** in test docstrings

Example test structure:
```python
class TestNewFeature:
    """Tests for new feature description"""
    
    def test_basic_case(self):
        """Test basic usage"""
        # Arrange
        ...
        # Act
        result = function_under_test()
        # Assert
        assert result == expected
    
    def test_edge_case(self):
        """Test edge case behavior"""
        ...
```

## References

- Main implementation: `TUNE_IMPLEMENTATION.md`
- ka9q-radio source: https://github.com/ka9q/ka9q-radio
- Protocol documentation: ka9q-radio/status.h
