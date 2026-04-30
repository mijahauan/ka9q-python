# Testing Guide

How to run ka9q-python's test suite. Unit tests run without any
hardware; integration tests talk to a live `radiod`.

---

## Quick reference

```bash
# Unit tests only — no radiod needed
pytest

# Integration tests against a live radiod
pytest --radiod-host=bee1-hf-status.local
RADIOD_HOST=bee1-hf-status.local pytest    # equivalent via env var

# Coverage
pytest --cov=ka9q --cov-report=html

# Single file
pytest tests/test_status_decoder.py -v

# Single test
pytest tests/test_tune_method.py::TestTuneBasic::test_frequency -v
```

---

## Setup

Install the package with dev extras:

```bash
pip install -e ".[dev]"
```

This pulls in `pytest` and `pytest-cov` (see `[project.optional-dependencies].dev`
in [`pyproject.toml`](../pyproject.toml)).

---

## Unit tests (default)

`pytest` with no arguments runs everything under `tests/`. Unit tests
mock the network, so they run anywhere — no radiod, no multicast, no
GPS hardware.

```bash
pytest                   # verbose output is on by default via pyproject.toml
pytest -q                # quiet
pytest -x                # stop at first failure
```

Expect a few hundred tests completing in under a minute.

---

## Integration tests

Some tests require a live `radiod`. They are gated on a
`--radiod-host` pytest flag or the `RADIOD_HOST` environment variable
(see [`tests/conftest.py`](../tests/conftest.py)):

```python
parser.addoption("--radiod-host",
                 default=os.environ.get("RADIOD_HOST", "bee1-hf-status.local"),
                 ...)
```

Default host: `bee1-hf-status.local`.

```bash
# Explicit host
pytest --radiod-host=bee3-status.local

# Via env var (convenient in a shell session)
export RADIOD_HOST=bee3-status.local
pytest

# Target just the integration test file
pytest tests/test_integration.py --radiod-host=bee3-status.local -v
```

If you don't have a reachable radiod, integration tests that depend
on one will either skip themselves or fail with clear timeout errors;
the unit test layer is unaffected.

---

## Coverage

```bash
pytest --cov=ka9q --cov-report=term-missing
pytest --cov=ka9q --cov-report=html      # writes htmlcov/index.html
```

---

## Protocol drift test

[`tests/test_protocol_compat.py`](../tests/test_protocol_compat.py)
cross-checks ka9q-python's `StatusType` constants against the
upstream `ka9q-radio/src/status.h`. It looks for a sibling
`../ka9q-radio` checkout; if absent, it skips.

To run it, clone the C project next to ka9q-python:

```bash
cd ..
git clone https://github.com/ka9q/ka9q-radio
cd ka9q-python
pytest tests/test_protocol_compat.py -v
```

Any drift between the Python constants and the C header will fail
loudly — the signal you need to update [`ka9q/types.py`](../ka9q/types.py).

---

## Live smoke tests

Not `pytest` — standalone scripts under `examples/` that exercise
real multicast paths against a host. Useful when diagnosing
network-layer issues.

[`examples/multi_stream_smoke.py`](../examples/multi_stream_smoke.py)
— two-channel MultiStream test. Provisions USB channels for FT8 and
WSPR at 20 m, runs for ~20 s, prints per-SSRC packet/sample counts.

```bash
python examples/multi_stream_smoke.py --host bee3-status.local --duration 20
```

Success criterion: both labels show non-zero callbacks and samples;
RESULT line prints `PASS`.

---

## Current `tests/` contents

Generated from `tests/` at the time of writing. Each file is a
pytest module unless noted.

| File | Scope |
|---|---|
| `conftest.py` | Registers `--radiod-host` flag / `RADIOD_HOST` env var. |
| `test_addressing.py` | Deterministic SSRC and multicast IP generation. |
| `test_channel_verification.py` | `ensure_channel()` verification logic. |
| `test_create_split_encoding.py` | Channel creation with split encoding params. |
| `test_decode_functions.py` | TLV decode (int/float/double/string/socket). Unit. |
| `test_encode_functions.py` | TLV encode + round-trip encode→decode. Unit. |
| `test_encode_socket.py` | Socket address TLV encoding. |
| `test_ensure_channel_encoding.py` | Encoding parameter handling in `ensure_channel()`. |
| `test_integration.py` | Live-radiod integration: create/re-tune/gain/AGC/multiple channels. |
| `test_iq_20khz_f32.py` | IQ 20 kHz F32 stream handling. |
| `test_listen_multicast.py` | Multicast listener plumbing. |
| `test_managed_stream_recovery.py` | `ManagedStream` drop/restore behavior. |
| `test_monitor.py` | `ChannelMonitor` restart detection. |
| `test_multihomed.py` | `interface=` parameter on multi-NIC hosts. |
| `test_native_discovery.py` | `discover_channels_native()` pure-Python listener. |
| `test_performance_fixes.py` | Socket reuse and retry/backoff behavior. |
| `test_protocol_compat.py` | `StatusType` ↔ ka9q-radio `status.h` drift check (auto-skips if `../ka9q-radio` is missing). |
| `test_remove_channel.py` | Channel teardown. |
| `test_rtp_recorder.py` | `RTPRecorder` raw-packet capture path. |
| `test_security_features.py` | Input validation / defensive guards. |
| `test_ssrc_dest_unit.py` | SSRC + destination derivation. Unit. |
| `test_ssrc_encoding_unit.py` | SSRC + encoding derivation. Unit. |
| `test_ssrc_radiod_host_unit.py` | SSRC derivation given a host. Unit. |
| `test_status_decoder.py` | `decode_status_packet()` and typed `ChannelStatus`/`FrontendStatus`/`PllStatus`/etc. Unit. |
| `test_ttl_warning.py` | Multicast TTL configuration warning. |
| `test_tune.py` | `RadiodControl.tune()` surface. |
| `test_tune_cli.py` | `examples/tune.py` CLI parsing. |
| `test_tune_debug.py` | Debug-tool plumbing. |
| `test_tune_live.py` | Live-radiod `tune()` path (integration). |
| `test_tune_method.py` | `tune()` method unit tests: timeouts, SSRC/tag match, decoding. |

Also in `tests/`:

- `README.md` — a longer (partly historical) narrative on the tune
  test suite.
- `INTEGRATION_TESTING.md`, `TROUBLESHOOTING_CHECKLIST.md` — prose
  diagnostics.

---

## CI

Unit tests are safe for CI — no network, no hardware. A minimal
workflow:

```yaml
- run: pip install -e .[dev]
- run: pytest --cov=ka9q --cov-report=xml
```

Integration and live-smoke tests need a reachable radiod and are
typically run by a self-hosted runner on the same LAN, or manually
during release QA.
