# ka9q TUI Guide

A Textual-based terminal UI for monitoring and controlling a live
`radiod` channel. Modeled on ka9q-radio's ncurses `control` program:
eight panels of channel state and one-letter keybindings that drive the
same setters as `ka9q set`.

## Install

The TUI dependency (`textual`) ships as an optional extra:

```bash
pip install -e ".[tui]"
# or, for development:
pip install -e ".[dev,tui]"
```

## Launch

```bash
# Watch a specific SSRC (recommended)
ka9q tui bee1-hf-status.local --ssrc 14095000

# Or discover interactively — the TUI latches onto the first SSRC
# seen on the status multicast
ka9q tui bee1-hf-status.local

# Pin a network interface when the host is multi-homed
ka9q tui bee1-hf-status.local --ssrc 14095000 --interface eth0
```

Find SSRCs first with `ka9q list HOST`.

## Update cadence

radiod emits per-channel status packets in two situations:

1. **On change** — when any setter modifies the channel.
2. **On poll** — in response to a status-request command.

The TUI uses both:

- A background thread runs `RadiodControl.listen_status()` and pushes
  any status packet for the focused SSRC onto an internal queue
  ([tui.py:38-62](../ka9q/tui.py#L38-L62)). This captures change-driven
  updates and anything triggered by other clients (e.g. a running
  `control` instance).
- A 1 Hz timer calls `poll_status(ssrc, timeout=0.8)` in a worker
  thread ([tui.py:412-421](../ka9q/tui.py#L412-L421)), so values
  refresh every second even when the channel is idle.
- The UI drains the queue and repaints every 200 ms
  ([tui.py:399](../ka9q/tui.py#L399)).

A one-shot `poll_status(timeout=2.0)` fires at mount to populate the
panels immediately.

## Panels

Grid layout (3×3, last cell blank):

| Panel | Source fields |
|---|---|
| **Tuning** | Carrier, first/second LO, shift, channel filter edges, frontend filter edges, Doppler |
| **Frontend / GPSDO** | Description, input sample rate, AD bits, real/complex, **`calibrate_ppm`**, **`gpsdo_reference_hz`** (10 MHz reference), `ad_over`, `samples_since_over`, LNA/MIX/IF gains, RF gain/atten/AGC |
| **Signal / Levels** | IF power (dBFS), RF level cal, input dBm, baseband power, noise density, S/N₀, S/N + bandwidth, output level |
| **Filter / FFT** | Kaiser β, blocksize, FIR length, drops, noise BW, optional Filter2 block |
| **Demod** | Mode + demod name, plus mode-specific block (FM SNR / peak dev / PL tone / de-emphasis; linear AGC / ISB / envelope / PLL; spectrum RBW / bins / window / FFT N) |
| **Options / Squelch** | Lock, SNR squelch enable, open/close thresholds, ISB, envelope, AGC, FM threshold-extend |
| **Input / Status** | GPS time, cmd count, input sample rate, samples in, ADC overrange counters, status destination + interval |
| **Output / RTP** | SSRC, output rate, channels, encoding, TTL, destination, sample count, packet counters, errors, max delay, Opus parameters when present |

A "—" means the field is absent from the latest status packet — many
fields depend on frontend/demod type (RX888 vs Airspy; linear vs FM vs
spectrum), so not every cell is populated for every channel.

### Where GPSDO and ADC governance show up

- **GPSDO discipline**: `Frontend / GPSDO` panel — `Calibrate: ±x.xxx
  ppm` is the frontend's fractional-frequency error vs. its 10 MHz
  reference, and `Ref (10M): …` is the measured reference frequency.
- **ADC overranges**: both `Frontend / GPSDO` and `Input / Status` show
  `AD over` (total clip count) and `samples_since_over` (how long ago
  the last clip occurred, in samples at the input sample rate).

## Keybindings

Modeled after `control`. Parameter keys open a single-line modal
prompt; toggle keys act immediately.

| Key | Action | Setter |
|---|---|---|
| `f` | Carrier frequency (Hz) | `set_frequency` |
| `p` | Preset / mode | `set_preset` |
| `S` | Sample rate (Hz) | `set_sample_rate` |
| `s` | Squelch open (dB) | `set_squelch` |
| `G` | RF gain (dB) | `set_rf_gain` |
| `A` | RF attenuation (dB) | `set_rf_attenuation` |
| `g` | Linear gain (dB) | `set_gain` |
| `H` | Headroom (dB) | `set_headroom` |
| `L` | AGC threshold (dB) | `set_agc_threshold` |
| `R` | AGC recovery (dB/s) | `set_agc_recovery_rate` |
| `T` | AGC hang time (s) | `set_agc_hangtime` |
| `P` | PLL bandwidth (Hz) | `set_pll` |
| `K` | Kaiser β | `set_kaiser_beta` |
| `e` | Output encoding (S16LE, F32LE, OPUS…) | `set_output_encoding` |
| `b` | Opus bitrate (bps) | `set_opus_bitrate` |
| `t` | PL tone (Hz, 0 off) | `set_pl_tone` |
| `D` | Demod type (linear/fm/wfm/spect) | `set_demod_type` |
| `l` | Toggle channel lock | `set_lock` |
| `i` | Toggle independent sideband | `set_independent_sideband` |
| `v` | Toggle envelope detection | `set_envelope_detection` |
| `x` | Toggle FM threshold-extend | `set_fm_threshold_extension` |
| `?` / `h` | Show help overlay | — |
| `q` | Quit | — |

Prompt keys dispatch through `SET_VERBS` in
[cli.py:163](../ka9q/cli.py#L163), so any value accepted by `ka9q set`
is also accepted in the modal — the TUI and CLI share one vocabulary.

If a setter raises, the header line shows `ERR: …` instead of dimming
the panels, so you can see the failure without losing context.

## Under the hood

- [tui.py](../ka9q/tui.py) — app, panels, keybindings, status worker.
- [control.py `listen_status`](../ka9q/control.py) — passive receive on
  the status multicast.
- [control.py `poll_status`](../ka9q/control.py) — active poll (sends a
  command tagged with the target SSRC and waits for the matching
  status reply).
- [status.py `ChannelStatus`](../ka9q/status.py) — the typed dataclass
  every panel reads from.

## Troubleshooting

**Nothing updates / panels stay blank.** Confirm the SSRC exists:
`ka9q query HOST --ssrc N` should print a status. If `query` works but
the TUI doesn't, the status multicast may be reaching the control
socket but not the passive listener — check `--interface` on multi-homed
hosts.

**All values are "—".** The SSRC is receiving packets but they lack
populated TLVs. Usually this means the channel is in an unusual demod
state; pressing `p` and re-setting the preset forces radiod to emit a
full status.

**Key does nothing.** Parameter keys require a focused SSRC. Pass
`--ssrc` explicitly or wait for the listener to latch onto one.
