# Security

`ka9q-python` is a client library for the `ka9q-radio` `radiod` control protocol. This page describes the security model you should assume when using it.

## Threat Model

The `radiod` control protocol is **unauthenticated and unencrypted** multicast UDP. Any host that can reach the status/command multicast group can:

- Enumerate every active channel on that `radiod` instance
- Tune, retune, reconfigure, or destroy channels
- Subscribe to audio/IQ output streams

`ka9q-python` does not change this. It exposes the same capabilities the `control` utility shipped with ka9q-radio does.

**Use on trusted networks only.** Typical deployments:

- Home lab / shack LAN behind a router NAT
- Dedicated SDR VLAN
- Point-to-point link between an SDR host and a processing host

If you need to expose a radiod to an untrusted network, put an authenticated control layer (SSH, VPN, or application-level API) in front of it. Do not rely on network obscurity.

## What `ka9q-python` itself does

- Uses `secrets.randbits()` (CSPRNG) for RTP command tags — not `random`.
- Rate-limits outbound commands via `RadiodControl(max_commands_per_sec=...)`; default 100/sec. This is a foot-gun guard, not a DoS defense.
- Validates basic parameter ranges (frequency, SSRC, sample rate) before serializing TLV commands. Invalid values raise `ValidationError` rather than being sent to radiod.
- Protects `RadiodControl` state with `RLock` so concurrent callers can't interleave half-written commands.

## What `ka9q-python` does **not** do

- Authenticate radiod — anyone on the multicast path can impersonate it.
- Encrypt commands or status — packets are cleartext TLV.
- Validate that a received status packet actually came from the radiod you asked.
- Sanitize preset/channel names beyond length checks. Don't interpolate untrusted input into a preset name without validating it yourself.

## Multicast scope

Multicast traffic typically does not cross a subnet boundary unless you have configured a router to forward it. If your radiod is on a different subnet from your client, check:

- The router allows IGMP/PIM for the multicast groups in use.
- The sender TTL is high enough to reach the client (see the TTL reporting in `ChannelStatus`).

This is a functional concern, not a security concern, but it also means a typical LAN deployment naturally scopes radiod to link-local hosts.

## CLI and TUI

The `ka9q` CLI and `ka9q tui` bind no network services; they are clients that speak the same multicast control protocol. Security considerations above apply to anyone who can run them and reach the radiod.

The previously-shipped Flask `webui/` has been removed. If you need browser access, consider `textual serve` to render the TUI in a browser over an authenticated channel (e.g., reverse proxy + HTTPS + auth).

## Reporting vulnerabilities

If you find a vulnerability specific to `ka9q-python` (not ka9q-radio itself), please open a non-public issue or email the maintainer. For vulnerabilities in ka9q-radio, report upstream at <https://github.com/ka9q/ka9q-radio>.
