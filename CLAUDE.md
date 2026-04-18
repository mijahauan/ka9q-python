# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Overview

**ka9q-python** is a Python library for controlling [ka9q-radio](https://github.com/ka9q/ka9q-radio)'s `radiod` daemon. The package is named `ka9q-python` on PyPI (out of respect for KA9Q / Phil Karn's callsign) but imported as `import ka9q`.

## Commands

### Install for development
```bash
uv sync --extra dev                    # standard; creates .venv/
# or: pip install -e ".[dev]"          # pip fallback
```

### Run tests
```bash
# All tests (unit tests run without a live radiod)
uv run pytest

# Integration tests against a live radiod host
uv run pytest --radiod-host=bee1-hf-status.local
# or via environment variable
RADIOD_HOST=bee1-hf-status.local uv run pytest

# Single test file
uv run pytest tests/test_control.py -v

# With coverage
uv run pytest --cov=ka9q --cov-report=html
```

### Build distribution
```bash
uv build                               # produces sdist + wheel in dist/
```

### Library lockfile policy
`uv.lock` is gitignored for this library; a library's lockfile does not bind
downstream consumers. Clients pin ka9q-python via their own `uv.lock`.

## Architecture

### Abstraction Layers

The library exposes three progressively higher-level abstractions for consuming RTP audio streams:

1. **`RTPRecorder`** (`rtp_recorder.py`) — Low-level raw packet capture with precise GPS/RTP timestamps. Use when timing accuracy is critical (e.g., WSPR, scientific measurement).

2. **`RadiodStream`** (`stream.py`) — Mid-level continuous sample delivery with automatic gap filling. Built on `PacketResequencer` (`resequencer.py`) for out-of-order packet handling.

3. **`ManagedStream`** (`managed_stream.py`) — High-level self-healing wrapper around `RadiodStream` that automatically recovers from radiod restarts and network interruptions.

### Core Components

- **`RadiodControl`** (`control.py`, ~2800 lines) — The central control class. Implements the TLV (Type-Length-Value) binary protocol used by ka9q-radio. All channel operations (create, tune, configure, destroy) go through this class. 110+ protocol constants are defined in `types.py` as `StatusType` enum values, mirroring `status.h` in ka9q-radio.

- **`discovery.py`** — Channel and service discovery via multicast UDP. `discover_channels()` is the primary entry point; it has fallbacks to `discover_channels_native()` and `discover_channels_via_control()`.

- **`monitor.py`** — `ChannelMonitor` detects radiod restarts and triggers channel recreation callbacks.

- **`addressing.py`** — Deterministic multicast IP and SSRC generation from frequency/parameters.

- **`utils.py`** — Cross-platform mDNS resolution and multicast socket configuration.

### Protocol Notes

- All radiod communication uses multicast UDP with TLV-encoded status packets
- SSRC (Synchronization Source) identifies each channel; `allocate_ssrc()` generates deterministic SSRCs to avoid collisions across restarts
- The default integration test radiod is `bee1-hf-status.local`; tests use `--radiod-host` or `RADIOD_HOST` env var to override

### Public API Surface

All public symbols are re-exported from `ka9q/__init__.py`. Key exports:
- Control: `RadiodControl`, `allocate_ssrc`
- Discovery: `discover_channels`, `ChannelInfo`
- Streams: `RadiodStream`, `ManagedStream`, `RTPRecorder`
- Types: `StatusType`, `Encoding`
- Exceptions: `Ka9qError`, `ConnectionError`, `CommandError`, `ValidationError`
- Utilities: `generate_multicast_ip`, `ChannelMonitor`

### Thread Safety

All public `RadiodControl` methods are protected by `RLock`. `ManagedStream` is safe for concurrent use. The library is designed for long-running applications with multiple concurrent channels.
