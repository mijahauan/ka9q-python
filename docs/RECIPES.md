# Recipes

Task-oriented cookbook for ka9q-python. Each recipe answers one concrete
question: "I want to do X — how?" Code snippets are runnable against a
live `radiod` instance; replace hostnames with your own.

For API details see [API_REFERENCE.md](API_REFERENCE.md). For the CLI
surface see [CLI_GUIDE.md](CLI_GUIDE.md). For background on multi-homed
hosts and mDNS resolution see [GETTING_STARTED.md](GETTING_STARTED.md).

---

## Recipe 1 — Probing radiod instances on a LAN

Discovering what's out there has two layers:

1. **Which hosts are running `radiod`?** — mDNS service browse.
2. **What channels does each host have configured?** — listen to its
   status multicast group.

### 1.1 Enumerating radiod hosts via mDNS

[`discover_radiod_services()`](../ka9q/discovery.py) wraps
`avahi-browse -t _ka9q-ctl._udp`. It returns a list of
`{"name": ..., "address": ...}` dicts, deduplicated by address and
sorted by name.

```python
from ka9q import discover_radiod_services

for svc in discover_radiod_services(timeout=5.0):
    print(f"{svc['name']:40s}  {svc['address']}")
```

Typical output on a lab LAN:

```
bee1-hf-status.local                      239.100.101.1
bee3-status.local                         239.100.112.151
rx888-wspr-status.local                   239.100.104.1
```

Requires `avahi-browse` on the local host. If the tool is missing or
your LAN uses a different mDNS responder, fall back to a static host
list or point at IPs directly.

### 1.2 Listing channels on a host

Once you know a host, [`discover_channels()`](../ka9q/discovery.py)
polls it and listens to the status multicast group for a couple of
seconds, decoding every `ChannelInfo` it hears.

```python
from ka9q import discover_channels

channels = discover_channels("bee3-status.local", listen_duration=2.0)

for ssrc, ch in sorted(channels.items()):
    print(f"SSRC={ssrc:>10}  {ch.frequency/1e6:10.4f} MHz  "
          f"preset={ch.preset:6s}  rate={ch.sample_rate:>6d}  "
          f"dest={ch.multicast_address}:{ch.port}")
```

`discover_channels()` tries the native pure-Python listener first and
falls back to the `control` utility (from ka9q-radio) if the native
path returns empty. See also `discover_channels_native()` and
`discover_channels_via_control()` if you want to pin one method.

### 1.3 Multi-host sweep

Combining the two calls gives a LAN-wide inventory.

```python
from ka9q import discover_radiod_services, discover_channels

for svc in discover_radiod_services(timeout=5.0):
    host = svc["name"]
    print(f"\n=== {host} ({svc['address']}) ===")
    try:
        channels = discover_channels(host, listen_duration=2.0)
    except Exception as e:
        print(f"  (probe failed: {e})")
        continue
    if not channels:
        print("  (no channels heard)")
        continue
    for ssrc, ch in sorted(channels.items()):
        print(f"  SSRC={ssrc:>10}  {ch.frequency/1e6:10.4f} MHz  "
              f"preset={ch.preset}")
```

Run this before standing up a new recorder: you can see at a glance
what the radiod fleet is producing.

### 1.4 One-off CLI

For interactive use, `ka9q list HOST` does exactly this:

```
$ ka9q list bee3-status.local
      SSRC       Frequency  Preset    Dest
  14074000   14.074000M    usb       239.100.112.152:5004
  14095600   14.095600M    usb       239.100.112.152:5004
  ...
```

`--json` emits machine-readable output. See [CLI_GUIDE.md](CLI_GUIDE.md).

### 1.5 Multi-homed hosts

On a host with more than one network interface, multicast join goes to
whichever interface the kernel picks — often the wrong one. Pass
`interface=` to point at the right NIC:

```python
channels = discover_channels(
    "bee3-status.local",
    interface="192.168.10.23",   # local IP of the correct NIC
)
```

The same flag is accepted by `discover_channels_native()`,
`RadiodControl(...)`, and `MultiStream` (indirectly, via the
`RadiodControl` it wraps). See
[GETTING_STARTED.md](GETTING_STARTED.md) for background on why this
matters.

---

## Recipe 2 — Fixed sets of same-type channels (WSPR, PSK, FT8, timing)

This is the pattern used by
[wspr-recorder](https://github.com/mijahauan/wspr-recorder),
[psk-recorder](https://github.com/mijahauan/psk-recorder), and
[hf-timestd](https://github.com/mijahauan/hf-timestd):

1. Read a band plan (list of frequencies + preset + sample rate).
2. For each entry, call `ensure_channel()` — deterministic SSRC
   means re-running the app doesn't create duplicates, and a radiod
   restart doesn't orphan anything.
3. Wrap the lot in a single [`MultiStream`](../ka9q/multi_stream.py)
   so that N channels share one socket and one receive thread.

### 2.1 The recorder pattern

```python
from ka9q import RadiodControl, MultiStream

BAND_PLAN = [
    # label,     freq Hz,       preset, sample_rate
    ("FT8-20m",  14.074e6,      "usb",  12000),
    ("FT8-40m",   7.074e6,      "usb",  12000),
    ("FT8-80m",   3.573e6,      "usb",  12000),
    ("FT4-20m",  14.080e6,      "usb",  12000),
    ("FT4-40m",   7.0475e6,     "usb",  12000),
]

def make_callback(label):
    def on_samples(samples, quality):
        # Label-aware sink: write to a per-channel WAV, feed a decoder, etc.
        handle(label, samples, quality)
    return on_samples

with RadiodControl("bee3-status.local") as control:
    multi = MultiStream(control=control)
    for label, fhz, preset, rate in BAND_PLAN:
        multi.add_channel(
            frequency_hz=fhz,
            preset=preset,
            sample_rate=rate,
            encoding=2,                     # S16BE
            on_samples=make_callback(label),
            on_stream_dropped=lambda r, l=label: log.warning(f"{l} dropped: {r}"),
            on_stream_restored=lambda ch, l=label: log.info(f"{l} restored"),
        )
    multi.start()
    try:
        run_forever()
    finally:
        multi.stop()
```

### 2.2 Deterministic SSRC + self-healing

`MultiStream.add_channel()` calls
[`RadiodControl.ensure_channel()`](../ka9q/control.py) under the hood.
`ensure_channel()`:

- Computes an SSRC deterministically from `(frequency, preset,
  sample_rate, destination)` so repeated invocations resolve to the
  same channel.
- Returns the existing channel if one already matches; creates it
  otherwise.
- Waits up to `timeout` for radiod to confirm the channel exists.

Combined with `MultiStream`'s health monitor, this means:

- **App restart**: `ensure_channel()` reuses the existing radiod
  channel; no duplicates, no gap.
- **radiod restart**: after `drop_timeout_sec` of silence on a slot,
  the health thread calls `ensure_channel()` again and swaps in a
  fresh resequencer. `on_stream_restored` fires when samples resume.

You do not need to write restart-handling code yourself.

### 2.3 When to pick MultiStream vs. N × ManagedStream

Both solve the self-healing problem. The difference is the socket
layer.

| | `ManagedStream` | `MultiStream` |
|---|---|---|
| Sockets per channel | 1 | — |
| Receive threads | 1 per channel | 1 total |
| Per-channel callbacks | yes | yes (same signature) |
| Self-healing | yes | yes |
| Best for | 1–3 channels, or channels on different groups | 5+ channels sharing a multicast group |

`N × ManagedStream` on one multicast group means the kernel copies
every packet into N socket buffers. `MultiStream` receives once and
demultiplexes by SSRC in user space — one kernel copy regardless of
channel count.

**Important constraint:** every channel added to a `MultiStream` must
resolve to the same multicast address and port. `add_channel()`
enforces this and raises `ValueError` if it doesn't. If your band
plan spans multiple output groups, use one `MultiStream` per group.

See also [MULTI_STREAM.md](MULTI_STREAM.md).

---

## Recipe 3 — Nimble channel switching (SWL-style interactive tuning)

For interactive receivers — bandscanners, SWL tuners, a TUI — you do
not want to tear down a channel on every tune. Open one channel,
retune it in place.

### 3.1 One stream, many frequencies

```python
from ka9q import RadiodControl, ManagedStream

with RadiodControl("bee1-hf-status.local") as control:
    stream = ManagedStream(
        control=control,
        frequency_hz=14.074e6,
        preset="usb",
        sample_rate=12000,
        on_samples=play_audio,
    )
    channel = stream.start()          # returns the ChannelInfo
    ssrc = channel.ssrc

    # User tunes the dial:
    for new_freq in (14.200e6, 14.230e6, 7.200e6):
        control.set_frequency(ssrc=ssrc, frequency_hz=new_freq)
        time.sleep(5.0)  # listen for a bit

    stream.stop()
```

[`RadiodControl.set_frequency()`](../ka9q/control.py) is a single UDP
command — retuning is fast (1–2 ms on the wire) and does not drop
audio. The underlying SSRC and multicast stream stay put.

### 3.2 Preset, gain, filter while tuning

Other interactive verbs on `RadiodControl`:

- `set_preset(ssrc, "usb" | "lsb" | "am" | ...)` — change demod mode.
- `set_gain(ssrc, gain_db)` — manual gain (AGC off).
- `set_agc(ssrc, True | False)` — toggle AGC.
- `set_filter(ssrc, low_edge=..., high_edge=...)` — passband.
- `set_sample_rate(ssrc, rate)`.
- `set_shift_frequency(ssrc, offset_hz)` — fine BFO-style shift.

Full list: see the `SET_VERBS` table in
[`ka9q/cli.py`](../ka9q/cli.py), which maps every `ka9q set` verb to
its `RadiodControl` setter.

### 3.3 Driving from the CLI or TUI

You do not need to write Python to retune. The same setters are
reachable from the shell:

```
# Retune an existing channel:
ka9q set bee1-hf-status.local --ssrc 14074000 frequency 14.076e6

# Change gain:
ka9q set bee1-hf-status.local --ssrc 14074000 gain 12

# Swap preset:
ka9q set bee1-hf-status.local --ssrc 14074000 preset lsb
```

See [CLI_GUIDE.md](CLI_GUIDE.md) for the full `set` vocabulary.

For a live view while you tune:

```
ka9q query bee1-hf-status.local --ssrc 14074000 --watch
```

This prints a decoded `ChannelStatus` every time radiod multicasts a
fresh status packet — typically every 1–2 seconds. Scalar fields
(SNR, frequency offset, PLL lock, IF power) update in place.

Or launch the Textual TUI, which wraps all of the above in a
keyboard-driven panel view:

```
ka9q tui bee1-hf-status.local --ssrc 14074000
```

See [TUI_GUIDE.md](TUI_GUIDE.md).

### 3.4 Pattern for GUI / app code

For a desktop-style tuner, the usual shape is:

```python
class Receiver:
    def __init__(self, host):
        self._control = RadiodControl(host)
        self._stream = ManagedStream(
            control=self._control,
            frequency_hz=14.200e6,
            preset="usb",
            sample_rate=12000,
            on_samples=self._on_audio,
        )
        self._ssrc = self._stream.start().ssrc

    def tune(self, frequency_hz):
        self._control.set_frequency(self._ssrc, frequency_hz)

    def set_mode(self, preset):
        self._control.set_preset(self._ssrc, preset)

    def close(self):
        self._stream.stop()
        self._control.close()
```

Keep one `ManagedStream` alive for the session; retune via
`RadiodControl` setters; let `ManagedStream` handle radiod restarts
transparently.

---

## Recipe 4 — Using ka9q-python with a variety of SDRs

### 4.1 Architecture: ka9q-python does not touch the SDR

ka9q-python talks to `radiod`. `radiod` talks to the SDR. The Python
library never opens a USB device, never picks a sample rate on the
hardware, never configures an antenna input. What you see through
ka9q-python is whatever `radiod` exposes in its `FrontendStatus`.

This means:

- Adding support for a new SDR is a `radiod` job, not a ka9q-python
  job. If `radiod` was built with the right backend, it just works
  through the same TLV protocol.
- The capabilities you observe (maximum sample rate, A/D bit depth,
  real vs complex IF, available gains, tuning range) are reported by
  `radiod` based on the backend it loaded.

### 4.2 Tested and in-development SDRs

| SDR | Status | Notes |
|---|---|---|
| RX888 (MkII) | Primary, production | AC0G's WSPR, PSK, and hf-timestd deployments all run on RX888. 16-bit, 64.8 MSPS direct-sampling, HF+VHF. |
| Airspy R2 | In development | Being characterized; behavior not yet documented here. |
| Airspy HF+ Discovery | In development | Ditto. |

Other SDRs supported by the upstream ka9q-radio project (SDRplay,
FunCube, etc.) should work through ka9q-python without code changes,
but they are not exercised by AC0G's deployments.

### 4.3 Reporting SDR capabilities via `FrontendStatus`

Every `ChannelStatus` carries a `frontend: FrontendStatus` nested
object. The fields are populated from whatever `radiod` tells us
about its input. From [`ka9q/status.py`](../ka9q/status.py):

```python
@dataclass
class FrontendStatus:
    input_samprate: Optional[int]         # Hz at the A/D
    ad_bits_per_sample: Optional[int]     # e.g. 16 for RX888
    isreal: Optional[bool]                # True for real IF, False for IQ
    calibrate: Optional[float]            # GPSDO ratio; .calibrate_ppm is derived
    lna_gain: Optional[int]               # dB
    mixer_gain: Optional[int]             # dB
    if_gain: Optional[int]                # dB
    rf_gain: Optional[int]                # dB
    rf_atten: Optional[int]               # dB
    rf_agc: Optional[bool]
    if_power: Optional[float]             # dBFS
    rf_level_cal: Optional[float]         # dB, front-end calibration offset
    ad_over: Optional[int]                # overrange counter
    samples_since_over: Optional[int]
    fe_low_edge: Optional[float]          # Hz, front-end passband
    fe_high_edge: Optional[float]
    lock: Optional[bool]
    # ... (see status.py for the full list)

    @property
    def calibrate_ppm(self): ...
    @property
    def gpsdo_reference_hz(self): ...
    @property
    def input_power_dbm(self): ...
```

Grab one channel's frontend and report what the SDR is telling you:

```python
from ka9q import RadiodControl

with RadiodControl("bee3-status.local") as control:
    st = control.poll_status(ssrc=14074000, timeout=2.0)
    fe = st.frontend

    print(f"A/D rate:   {fe.input_samprate/1e6:.3f} MSPS")
    print(f"Bit depth:  {fe.ad_bits_per_sample} bits")
    print(f"IF type:    {'real' if fe.isreal else 'complex (IQ)'}")
    print(f"Passband:   {fe.fe_low_edge/1e6:.3f} – {fe.fe_high_edge/1e6:.3f} MHz")
    print(f"Gains:      LNA={fe.lna_gain} MIX={fe.mixer_gain} IF={fe.if_gain} dB")
    print(f"RF AGC:     {fe.rf_agc}")
    if fe.calibrate is not None:
        print(f"GPSDO:      {fe.calibrate_ppm:+.3f} ppm "
              f"(10 MHz → {fe.gpsdo_reference_hz:.3f} Hz)")
    if fe.if_power is not None:
        print(f"IF power:   {fe.if_power:.1f} dBFS "
              f"→ input {fe.input_power_dbm:.1f} dBm")
    print(f"Overranges: {fe.ad_over} "
          f"(samples since last: {fe.samples_since_over})")
```

For a production RX888 channel on bee3 this prints something like:

```
A/D rate:   64.800 MSPS
Bit depth:  16 bits
IF type:    real
Passband:   0.000 – 32.400 MHz
Gains:      LNA=0 MIX=0 IF=0 dB
RF AGC:     False
GPSDO:      +0.042 ppm (10 MHz → 10000000.420 Hz)
IF power:   -41.3 dBFS → input -54.8 dBm
Overranges: 0 (samples since last: 2147483647)
```

You now know, without leaving Python, exactly what the SDR is doing.

### 4.4 From the CLI

`ka9q query` also renders these fields:

```
ka9q query bee3-status.local --ssrc 14074000
```

Or just the one you want:

```
ka9q query bee3-status.local --ssrc 14074000 --field frontend.calibrate
ka9q query bee3-status.local --ssrc 14074000 --field frontend.input_samprate
```

Dotted paths are whatever
[`ChannelStatus.field_names()`](../ka9q/status.py) returns.

### 4.5 Roadmap note — `probe_frontend()` helper

There is no `probe_frontend()` helper in the library today. The
pattern in 4.3 — poll any active channel, read `.frontend` — works
and is ~8 lines, so it has not been worth abstracting.

A future direction would be a library function:

```python
# Not implemented. Sketch only.
caps = ka9q.probe_frontend("radiod-host.local", interface="eth0")
# caps: Dict with SDR identity, sample rate, bit depth, tuning range,
# gain stages, GPSDO status, overrange history, ...
```

It would need to (a) call `discover_channels()` to pick any SSRC,
(b) poll its status, (c) summarize the `FrontendStatus` into a
backend-neutral report. Once Airspy R2/HF+ characterization is done,
this helper would be a natural place to expose per-backend quirks
(e.g. "this SDR reports `isreal=False` but `input_samprate` is the
complex rate").

Until then, use the recipe above.

---

## Further reading

- [GETTING_STARTED.md](GETTING_STARTED.md) — install, mDNS, multi-homed hosts
- [MULTI_STREAM.md](MULTI_STREAM.md) — MultiStream in depth
- [CLI_GUIDE.md](CLI_GUIDE.md) — `ka9q list/query/set/tui`
- [TUI_GUIDE.md](TUI_GUIDE.md) — Textual TUI
- [API_REFERENCE.md](API_REFERENCE.md) — every public symbol
- [ARCHITECTURE.md](ARCHITECTURE.md) — internals
