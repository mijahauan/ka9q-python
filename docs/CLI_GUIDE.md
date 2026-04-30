# CLI Guide

ka9q-python installs a single console script, `ka9q`, that mirrors the
operations exposed by the Textual TUI. Source:
[`ka9q/cli.py`](../ka9q/cli.py).

```
ka9q list   HOST                                Discover channels
ka9q query  HOST [--ssrc N] [--field PATH] [--json] [--watch]
ka9q set    HOST --ssrc N PARAM VALUE            Change a parameter
ka9q tui    [HOST] [--ssrc N]                    Launch the Textual TUI
```

---

## Installation

The CLI is registered via `pyproject.toml`:

```toml
[project.scripts]
ka9q = "ka9q.cli:main"
```

Installing the package puts `ka9q` on your `$PATH`:

```
pip install -e .[dev]          # developer install from source
pip install ka9q-python        # from PyPI
pip install ka9q-python[tui]   # pulls textual, enables `ka9q tui`
```

Verify:

```
$ ka9q --help
usage: ka9q [-h] [--interface INTERFACE] {list,query,set,tui} ...
```

---

## Global flags

| Flag | Purpose |
|---|---|
| `--interface ADDR` | IP address of the NIC to use for multicast join. Required on multi-homed hosts. |

---

## `ka9q list HOST`

Discovers channels by listening to `HOST`'s status multicast group
(via [`discover_channels()`](../ka9q/discovery.py)).

```
ka9q list HOST [--timeout SECONDS] [--json]
```

| Flag | Default | Purpose |
|---|---|---|
| `--timeout` | 3.0 | How long to listen for status packets. |
| `--json` | off | Emit JSON array of channels instead of a table. |

### Human-readable output

```
$ ka9q list bee3-status.local
      SSRC       Frequency  Preset    Dest
  14074000   14.074000M    usb       239.100.112.152:5004
  14095600   14.095600M    usb       239.100.112.152:5004
   7074000    7.074000M    usb       239.100.112.152:5004
```

Returns exit code `1` if no channels were heard.

### JSON output

```
$ ka9q list bee3-status.local --json
[
  {
    "ssrc": 14074000,
    "preset": "usb",
    "sample_rate": 12000,
    "frequency": 14074000.0,
    "multicast_address": "239.100.112.152",
    "port": 5004,
    ...
  },
  ...
]
```

Pipe into `jq` for scripted filtering:

```
ka9q list bee3-status.local --json | jq '.[] | select(.preset=="usb") | .ssrc'
```

---

## `ka9q query HOST`

Fetch one channel's full `ChannelStatus` (see
[`ka9q/status.py`](../ka9q/status.py)), or stream status updates
continuously.

```
ka9q query HOST [--ssrc N] [--field PATH] [--json] [--watch] [--timeout S]
```

| Flag | Purpose |
|---|---|
| `--ssrc N` | Required for one-shot polling. Optional with `--watch` (then all SSRCs are shown). |
| `--field PATH` | Dotted path — e.g. `pll.lock`, `frontend.calibrate`, `fm.peak_deviation`. Valid paths come from `ChannelStatus.field_names()`. |
| `--json` | Emit JSON (full status dict, or `{field: value}` when combined with `--field`). |
| `--watch` | Passive listener — stay up and print every status packet radiod emits. Ctrl+C to exit. |
| `--timeout` | One-shot poll timeout, default 2.0 s. |

### One-shot, human-readable

```
$ ka9q query bee3-status.local --ssrc 14074000
SSRC:         14074000
Description:  FT8 20m
Preset / Mode: usb (LINEAR_DEMOD)

[Tuning]
  Carrier:     14.074000 MHz
  First LO:    15.000000 MHz   lock=True
  Second LO:   -926.0 kHz
  Shift:       0.0 Hz
  Filter:      100.0 Hz .. 2800.0 Hz  (β=11.0)
  ...

[Frontend / GPSDO]
  Input rate:  64800000 Hz  (16 bits, real=True)
  Calibrate:   +4.200e-08  (+0.042 ppm)
  ...
```

The renderer lives in `_render_status_text()` in
[`ka9q/cli.py`](../ka9q/cli.py) and adapts to demod type (extra
sections for FM, Linear/PLL, Spectrum).

### Single field

```
$ ka9q query bee3-status.local --ssrc 14074000 --field frontend.calibrate
4.2e-08

$ ka9q query bee3-status.local --ssrc 14074000 --field pll.lock
True

$ ka9q query bee3-status.local --ssrc 14074000 --field snr
18.3
```

Missing or unset fields print an empty line.

### JSON mode

Full status as JSON (via `ChannelStatus.to_dict()`):

```
ka9q query bee3-status.local --ssrc 14074000 --json
```

Single field as JSON:

```
$ ka9q query bee3-status.local --ssrc 14074000 --field snr --json
{"snr": 18.3}
```

### `--watch` live mode

Radiod multicasts a status packet periodically (every 1–2 s). `--watch`
prints each one as it arrives, without re-polling:

```
ka9q query bee3-status.local --ssrc 14074000 --watch
```

Omit `--ssrc` to watch every channel on the host:

```
ka9q query bee3-status.local --watch
```

Combine with `--field` and a shell loop for crude scripting:

```
ka9q query bee3-status.local --ssrc 14074000 --watch --field snr
```

Exit with Ctrl+C.

---

## `ka9q set HOST --ssrc N PARAM VALUE`

Send a setter command. Every verb maps to a `RadiodControl` method —
see the `SET_VERBS` table in [`ka9q/cli.py`](../ka9q/cli.py) for the
authoritative mapping.

```
ka9q set HOST --ssrc N PARAM VALUE
```

### Common verbs

| Verb | Setter | Example |
|---|---|---|
| `frequency` | `set_frequency` | `ka9q set HOST --ssrc N frequency 14.076e6` |
| `preset` / `mode` | `set_preset` | `ka9q set HOST --ssrc N preset usb` |
| `sample-rate` | `set_sample_rate` | `ka9q set HOST --ssrc N sample-rate 24000` |
| `gain` | `set_gain` | `ka9q set HOST --ssrc N gain 12` |
| `agc` | `set_agc` | `ka9q set HOST --ssrc N agc on` |
| `low-edge` / `high-edge` | `set_filter` | `ka9q set HOST --ssrc N low-edge 300` |
| `kaiser-beta` | `set_kaiser_beta` | `ka9q set HOST --ssrc N kaiser-beta 11` |
| `shift` | `set_shift_frequency` | `ka9q set HOST --ssrc N shift -700` |
| `squelch-open` / `squelch-close` | `set_squelch` | `ka9q set HOST --ssrc N squelch-open 8` |
| `pll` / `pll-bw` / `pll-square` | `set_pll` | `ka9q set HOST --ssrc N pll on` |
| `isb` / `envelope` | `set_independent_sideband` / `set_envelope_detection` | |
| `channels` | `set_output_channels` | `ka9q set HOST --ssrc N channels 2` |
| `encoding` | `set_output_encoding` | `ka9q set HOST --ssrc N encoding S16BE` |
| `demod-type` | `set_demod_type` | `ka9q set HOST --ssrc N demod-type LINEAR` |
| `pl-tone` / `threshold-extend` | FM tweaks | |
| `lock` | `set_lock` | `ka9q set HOST --ssrc N lock on` |
| `description` | `set_description` | `ka9q set HOST --ssrc N description 'FT8 20m'` |
| `first-lo` | `set_first_lo` | |
| `status-interval` / `max-delay` | — | |
| `opus-bitrate` / `opus-dtx` / `opus-application` / `opus-bandwidth` / `opus-fec` | Opus stream tuning | |
| `window` | `set_spectrum` (window type) | |
| `destination` | `set_destination` | `ka9q set HOST --ssrc N destination 239.100.112.152:5004` |

Full list: `ka9q set --help` shows the current vocabulary.

### Value coercion

- Booleans accept `1/0`, `true/false`, `yes/no`, `on/off`, `y/n`, `t/f`
  (case-insensitive).
- `encoding`, `demod-type`, `window` accept either the integer protocol
  value or the symbolic name (e.g. `S16BE`, `LINEAR`, `KAISER`).
- `destination` accepts `addr:port`; port defaults to 5004 if omitted.

Unknown verbs produce a sorted list of known verbs on stderr and exit
code 2.

---

## `ka9q tui [HOST]`

Launch the Textual TUI
([`ka9q/tui.py`](../ka9q/tui.py)). Requires `textual` — install via
`pip install ka9q-python[tui]`.

```
ka9q tui                         # omit host → mDNS picker
ka9q tui HOST                    # go straight to SSRC picker
ka9q tui HOST --ssrc N           # go straight to panels for SSRC N
```

If `HOST` or `--ssrc` are omitted, the TUI shows interactive picker
screens (`RadiodPickerScreen`, `SsrcPickerScreen`) populated via the
same `discover_radiod_services()` / `discover_channels()` used by
`ka9q list`. New in v3.9.

Full TUI reference: [TUI_GUIDE.md](TUI_GUIDE.md).

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | No channels discovered (for `list`) |
| 2 | Bad arguments (unknown verb, missing required `--ssrc`, TUI extras missing) |

---

## See also

- [RECIPES.md](RECIPES.md) — task-oriented patterns
- [TUI_GUIDE.md](TUI_GUIDE.md) — interactive panel view
- [API_REFERENCE.md](API_REFERENCE.md) — programmatic equivalents
