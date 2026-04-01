# Release Notes — v3.5.0

**Date:** 2026-03-31

## Summary

This release adds automated protocol compatibility tracking between `ka9q-python` and `ka9q-radio`. A new sync tool code-generates `ka9q/types.py` directly from the ka9q-radio C headers, a compatibility pin records which ka9q-radio commit was validated, and a pytest drift test catches protocol mismatches during development.

The release also absorbs all current ka9q-radio protocol changes, including new encoding types (MULAW, ALAW), new status fields (SPECTRUM_OVERLAP), and several renames.

## New Files

| File | Purpose |
|------|---------|
| `scripts/sync_types.py` | Code-generates `ka9q/types.py` from `status.h` and `rtp.h` |
| `ka9q_radio_compat` | Plain-text pin: the ka9q-radio commit hash types.py was validated against |
| `ka9q/compat.py` | Importable `KA9Q_RADIO_COMMIT` constant for deployment tooling |
| `tests/test_protocol_compat.py` | Drift test (auto-skips without ka9q-radio source) |

## Protocol Sync Workflow

When `ka9q-radio` is updated upstream:

```bash
# 1. Check for drift
python scripts/sync_types.py --check

# 2. Preview changes
python scripts/sync_types.py --diff

# 3. Apply changes (regenerates types.py, updates pins)
python scripts/sync_types.py --apply

# 4. Review, test, commit
git diff ka9q/types.py
python -m pytest tests/
git add -A && git commit -m "Resync with ka9q-radio $(git -C ../ka9q-radio rev-parse --short HEAD)"
```

For deployment tooling (`ka9q-update`):

```python
from ka9q.compat import KA9Q_RADIO_COMMIT
# Ensure radiod is built from this commit
```

## Protocol Changes Absorbed

### StatusType

- **Renamed:** `MINPACKET` → `MAXDELAY`, `GAINSTEP` → `UNUSED4`, `CONVERTER_OFFSET` → `UNUSED3`, `COHERENT_BIN_SPACING` → `UNUSED2`, `BLOCKS_SINCE_POLL` → `UNUSED`
- **Added:** `SPECTRUM_OVERLAP` (116)

### Encoding

- **Added:** `MULAW` (10), `ALAW` (11)
- **Shifted:** `UNUSED_ENCODING` sentinel from 10 to 12

### control.py

- `set_max_delay()` replaces `set_packet_buffering()` (old name kept as deprecated alias)

## Backward Compatibility

All changes are backward compatible:

- `set_packet_buffering()` still works (delegates to `set_max_delay()`)
- `Encoding.F32` and `Encoding.F16` aliases retained
- No breaking API changes

## Upgrade

```bash
pip install --upgrade ka9q-python
```
