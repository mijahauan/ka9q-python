"""
MultiStream - Shared-Socket Multi-SSRC Receiver

Receives RTP packets for multiple channels on a single UDP socket,
demultiplexes by SSRC, and delivers per-channel sample callbacks.

This solves the scalability problem where N ManagedStreams each open
their own socket on the same multicast group, causing the kernel to
copy every packet N times. MultiStream uses ONE socket and ONE
receive thread regardless of channel count.

Each channel gets its own PacketResequencer, StreamQuality, and
sample callback — the per-channel interface is identical to
ManagedStream/RadiodStream.

Usage:
    from ka9q import MultiStream, RadiodControl

    control = RadiodControl("radiod.local")
    multi = MultiStream(control=control)

    multi.add_channel(
        frequency_hz=14.074e6,
        preset="usb",
        sample_rate=12000,
        encoding=2,
        on_samples=my_callback,
    )
    multi.add_channel(
        frequency_hz=7.074e6,
        preset="usb",
        sample_rate=12000,
        encoding=2,
        on_samples=another_callback,
    )

    multi.start()
    # ... all channels receive via one socket ...
    multi.stop()
"""

import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set

import numpy as np

from .discovery import ChannelInfo
from .resequencer import PacketResequencer, RTPPacket
from .rtp_recorder import RTPHeader, parse_rtp_header, rtp_to_wallclock
from .stream import SampleCallback, parse_rtp_samples
from .stream_quality import GapEvent, GapSource, StreamQuality

logger = logging.getLogger(__name__)


@dataclass
class _ChannelSlot:
    """Per-SSRC state within a MultiStream."""

    channel_info: ChannelInfo
    frequency_hz: float
    preset: str
    sample_rate: int
    encoding: int
    is_iq: bool
    resequencer: PacketResequencer
    quality: StreamQuality
    on_samples: Optional[SampleCallback]
    on_stream_dropped: Optional[Callable]
    on_stream_restored: Optional[Callable]
    sample_buffer: List[np.ndarray] = field(default_factory=list)
    gap_buffer: List[GapEvent] = field(default_factory=list)
    packets_since_delivery: int = 0
    deliver_interval: int = 10
    last_packet_time: float = 0.0
    dropped: bool = False
    first_rtp_timestamp: Optional[int] = None
    lifetime: Optional[int] = None


class MultiStream:
    """Shared-socket multi-SSRC receiver with per-channel callbacks.

    All channels MUST resolve to the same multicast group (enforced
    on add_channel). One receive thread drains the socket and
    dispatches by SSRC; one health-monitor thread detects drops and
    restores channels via ensure_channel().
    """

    def __init__(
        self,
        control,
        drop_timeout_sec: float = 15.0,
        restore_interval_sec: float = 5.0,
        deliver_interval_packets: int = 10,
        samples_per_packet: int = 320,
        resequence_buffer_size: int = 64,
    ):
        self._control = control
        self._drop_timeout_sec = drop_timeout_sec
        self._restore_interval_sec = restore_interval_sec
        self._deliver_interval = deliver_interval_packets
        self._samples_per_packet = samples_per_packet
        self._resequence_buffer_size = resequence_buffer_size

        self._slots: Dict[int, _ChannelSlot] = {}
        self._multicast_address: Optional[str] = None
        self._port: Optional[int] = None

        self._socket: Optional[socket.socket] = None
        self._running = False
        self._receive_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._unknown_ssrcs: Set[int] = set()

    def add_channel(
        self,
        frequency_hz: float,
        preset: str = "usb",
        sample_rate: int = 12000,
        encoding: int = 0,
        agc_enable: int = 0,
        gain: float = 0.0,
        on_samples: Optional[SampleCallback] = None,
        on_stream_dropped: Optional[Callable] = None,
        on_stream_restored: Optional[Callable] = None,
        low_edge: Optional[float] = None,
        high_edge: Optional[float] = None,
        kaiser_beta: Optional[float] = None,
        lifetime: Optional[int] = None,
        timeout: float = 5.0,
    ) -> ChannelInfo:
        """Provision a channel and register it for reception.

        Must be called before start(). All channels must resolve to the
        same multicast address (enforced).

        Filter parameters (low_edge, high_edge, kaiser_beta) override the
        preset's default passband. None = use preset defaults. See
        RadiodControl.ensure_channel for the full semantics.

        ``lifetime`` opts the channel into radiod's self-destruct timer
        (radiod commit 0f8b622+, see RadiodControl.set_channel_lifetime).
        The value is stored per-slot so the drop/restore path re-applies
        it: a channel that radiod self-destructs and we then restore
        won't silently lose its lifetime. The caller is still
        responsible for periodic keep-alive via
        ``set_channel_lifetime()`` (or by calling
        RadiodControl.set_channel_lifetime directly on the SSRC).

        ``timeout`` is forwarded to ``ensure_channel`` and bounds the
        wait for radiod's status-message ACK confirming the channel
        was created.  The default 5 s is fine for an idle radiod, but
        when many producers register channels in quick succession
        (e.g. a multi-client deployment restarting) radiod can stall
        long enough that 5 s isn't enough — observed on bee1 2026-05-08
        as the T6 BPSK PPS channel timing out and crashing
        timestd-core-recorder, which in turn left TSL3 SHM stale.
        Callers in latency-sensitive setups should pass a longer
        value (10-30 s) so a brief radiod-busy window doesn't fail
        the whole channel registration.

        Returns the ChannelInfo from ensure_channel().
        """
        channel_info = self._control.ensure_channel(
            frequency_hz=frequency_hz,
            preset=preset,
            sample_rate=sample_rate,
            agc_enable=agc_enable,
            gain=gain,
            encoding=encoding,
            low_edge=low_edge,
            high_edge=high_edge,
            kaiser_beta=kaiser_beta,
            lifetime=lifetime,
            timeout=timeout,
        )

        addr = channel_info.multicast_address
        port = channel_info.port
        if self._multicast_address is None:
            self._multicast_address = addr
            self._port = port
        elif addr != self._multicast_address or port != self._port:
            raise ValueError(
                f"Channel {frequency_hz/1e6:.3f} MHz resolved to "
                f"{addr}:{port}, but MultiStream is bound to "
                f"{self._multicast_address}:{self._port}. "
                f"All channels must share one multicast group."
            )

        ssrc = channel_info.ssrc
        is_iq = preset.lower() in ("iq", "spectrum")

        slot = _ChannelSlot(
            channel_info=channel_info,
            frequency_hz=frequency_hz,
            preset=preset,
            sample_rate=sample_rate,
            encoding=encoding,
            is_iq=is_iq,
            resequencer=PacketResequencer(
                buffer_size=self._resequence_buffer_size,
                samples_per_packet=self._samples_per_packet,
                sample_rate=sample_rate,
            ),
            quality=StreamQuality(),
            on_samples=on_samples,
            on_stream_dropped=on_stream_dropped,
            on_stream_restored=on_stream_restored,
            deliver_interval=self._deliver_interval,
            lifetime=lifetime,
        )
        self._slots[ssrc] = slot

        logger.info(
            f"MultiStream: added {frequency_hz/1e6:.3f} MHz "
            f"SSRC={ssrc} on {addr}:{port}"
        )
        return channel_info

    def start(self) -> None:
        """Open the shared socket and start receive + health threads."""
        if self._running:
            return
        if not self._slots:
            raise RuntimeError("No channels added — call add_channel() first")

        self._running = True
        self._socket = self._create_socket()

        self._receive_thread = threading.Thread(
            target=self._receive_loop, daemon=True, name="MultiStream-Recv",
        )
        self._receive_thread.start()

        self._monitor_thread = threading.Thread(
            target=self._health_monitor_loop, daemon=True,
            name="MultiStream-Health",
        )
        self._monitor_thread.start()

        logger.info(
            f"MultiStream started: {len(self._slots)} channels on "
            f"{self._multicast_address}:{self._port}"
        )

    def set_channel_lifetime(self, ssrc: int, lifetime: int) -> None:
        """Refresh the LIFETIME tag on one channel and update slot state.

        Suitable as a periodic keep-alive: callers should invoke this on
        every active SSRC at a cadence shorter than the lifetime so the
        radiod self-destruct counter never reaches zero. The new value
        is also stored in the slot, so a subsequent drop/restore will
        re-apply this value rather than the original ``add_channel``
        argument.

        No-op if ``ssrc`` is not in this MultiStream.
        """
        slot = self._slots.get(ssrc)
        if slot is None:
            return
        self._control.set_channel_lifetime(ssrc, lifetime)
        slot.lifetime = lifetime

    def stop(self) -> None:
        """Stop threads and close socket."""
        if not self._running:
            return
        self._running = False

        if self._receive_thread:
            self._receive_thread.join(timeout=5.0)
            self._receive_thread = None

        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None

        # Flush all resequencers
        for ssrc, slot in self._slots.items():
            try:
                final_samples, final_gaps = slot.resequencer.flush()
                if final_samples is not None and len(final_samples) > 0:
                    slot.sample_buffer.append(final_samples)
                    slot.gap_buffer.extend(final_gaps)
                    self._deliver(slot)
            except Exception:
                pass

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        logger.info("MultiStream stopped")

    # ── socket ──

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass

        # Large receive buffer for multi-channel throughput
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        except OSError:
            pass

        sock.bind(("0.0.0.0", self._port))

        mreq = struct.pack(
            "=4s4s",
            socket.inet_aton(self._multicast_address),
            socket.inet_aton("0.0.0.0"),
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.settimeout(1.0)
        return sock

    # ── receive loop (hot path) ──

    def _receive_loop(self) -> None:
        while self._running:
            try:
                data, addr = self._socket.recvfrom(8192)
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.error("MultiStream socket error", exc_info=True)
                break

            if len(data) < 12:
                continue

            # Fast SSRC peek before full header parse
            ssrc = struct.unpack_from("!I", data, 8)[0]
            slot = self._slots.get(ssrc)
            if slot is None:
                if ssrc not in self._unknown_ssrcs:
                    self._unknown_ssrcs.add(ssrc)
                    logger.debug(f"MultiStream: unknown SSRC {ssrc}")
                continue

            # Full header parse
            header = parse_rtp_header(data)
            if header is None:
                continue

            slot.last_packet_time = time.time()
            slot.quality.rtp_packets_received += 1

            if slot.first_rtp_timestamp is None:
                slot.first_rtp_timestamp = header.timestamp
                slot.quality.first_rtp_timestamp = header.timestamp
            slot.quality.last_rtp_timestamp = header.timestamp

            # Extract payload
            header_len = 12 + (4 * header.csrc_count)
            payload = data[header_len:]
            if not payload:
                continue

            # Parse samples
            samples = parse_rtp_samples(payload, slot.encoding, slot.is_iq)
            if samples is None:
                continue

            # Wallclock
            wallclock = rtp_to_wallclock(header.timestamp, slot.channel_info)

            # Resequencer
            packet = RTPPacket(
                sequence=header.sequence,
                timestamp=header.timestamp,
                ssrc=header.ssrc,
                samples=samples,
                wallclock=wallclock,
            )
            output, gaps = slot.resequencer.process_packet(packet)

            if output is not None and len(output) > 0:
                slot.sample_buffer.append(output)
                slot.gap_buffer.extend(gaps)
                slot.packets_since_delivery += 1

                if slot.packets_since_delivery >= slot.deliver_interval:
                    self._deliver(slot)

    # ── delivery ──

    def _deliver(self, slot: _ChannelSlot) -> None:
        if not slot.sample_buffer or slot.on_samples is None:
            slot.sample_buffer.clear()
            slot.gap_buffer.clear()
            slot.packets_since_delivery = 0
            return

        combined = np.concatenate(slot.sample_buffer)
        n = len(combined)

        slot.quality.total_samples_delivered += n
        slot.quality.batch_samples_delivered = n
        slot.quality.batch_gaps = list(slot.gap_buffer)
        slot.quality.sample_rate = slot.sample_rate

        try:
            slot.on_samples(combined, slot.quality)
        except Exception:
            logger.exception(
                f"MultiStream: callback error for SSRC {slot.channel_info.ssrc}"
            )

        slot.sample_buffer.clear()
        slot.gap_buffer.clear()
        slot.packets_since_delivery = 0

    # ── health monitor ──

    def _health_monitor_loop(self) -> None:
        time.sleep(10.0)
        check_interval = min(1.0, self._drop_timeout_sec / 4)

        while self._running:
            time.sleep(check_interval)
            if not self._running:
                break

            now = time.time()
            for ssrc, slot in list(self._slots.items()):
                if slot.dropped:
                    self._attempt_restore(ssrc, slot)
                elif slot.last_packet_time > 0:
                    silence = now - slot.last_packet_time
                    if silence > self._drop_timeout_sec:
                        self._handle_drop(
                            ssrc, slot,
                            f"No packets for {silence:.1f}s "
                            f"(timeout: {self._drop_timeout_sec}s)",
                        )

    def _handle_drop(self, ssrc: int, slot: _ChannelSlot, reason: str) -> None:
        logger.warning(
            f"MultiStream: {slot.frequency_hz/1e6:.3f} MHz dropped — {reason}"
        )
        slot.dropped = True
        if slot.on_stream_dropped:
            try:
                slot.on_stream_dropped(reason)
            except Exception:
                logger.exception("Error in on_stream_dropped callback")

    def _attempt_restore(self, ssrc: int, slot: _ChannelSlot) -> None:
        try:
            channel_info = self._control.ensure_channel(
                frequency_hz=slot.frequency_hz,
                preset=slot.preset,
                sample_rate=slot.sample_rate,
                encoding=slot.encoding,
                lifetime=slot.lifetime,
            )
            new_ssrc = channel_info.ssrc
            if new_ssrc != ssrc:
                del self._slots[ssrc]
                self._slots[new_ssrc] = slot

            slot.channel_info = channel_info
            slot.dropped = False
            slot.first_rtp_timestamp = None
            slot.resequencer = PacketResequencer(
                buffer_size=self._resequence_buffer_size,
                samples_per_packet=self._samples_per_packet,
                sample_rate=slot.sample_rate,
            )
            slot.quality = StreamQuality()
            slot.sample_buffer.clear()
            slot.gap_buffer.clear()
            slot.packets_since_delivery = 0

            logger.info(
                f"MultiStream: {slot.frequency_hz/1e6:.3f} MHz restored "
                f"(SSRC={new_ssrc})"
            )
            if slot.on_stream_restored:
                try:
                    slot.on_stream_restored(channel_info)
                except Exception:
                    logger.exception("Error in on_stream_restored callback")

        except Exception as e:
            logger.warning(
                f"MultiStream: restore failed for "
                f"{slot.frequency_hz/1e6:.3f} MHz: {e}"
            )
