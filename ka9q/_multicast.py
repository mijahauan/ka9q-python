"""Shared multicast helpers — multi-interface IP_ADD_MEMBERSHIP.

Factored out of ``multi_stream.py`` (Rob Robinett's e3acb6a) so the
same join-on-every-interface logic can also be used by
``stream.RadiodStream`` and ``rtp_recorder.RtpRecorder`` without
duplicating the SIOCGIFADDR enumeration code.

This module is package-private — callers inside ``ka9q`` import the
two public helpers below; nothing outside the package should rely on
the symbol names.
"""

from __future__ import annotations

import fcntl
import logging
import socket
import struct
from typing import Iterator, List, Tuple

logger = logging.getLogger(__name__)


# Linux SIOCGIFADDR — fetch IPv4 of an interface by name.  Used to enumerate
# every UP IPv4 interface so the multicast group join can be made on each
# of them.  Without this, joining with INADDR_ANY lets the kernel pick a
# single interface (typically the default-route one), which misses:
#
#   * Loopback-only multicast emitted by a co-located radiod with TTL=0
#     (packets sit on `lo`; the kernel won't deliver them to a socket
#     joined on `ens0`).
#   * Multi-homed stations where one radiod streams on lo and another
#     on eth: a single receiver should consume both.
#
# Joining on EVERY local IPv4 interface lets one socket receive from any
# radiod source on any path.
_SIOCGIFADDR = 0x8915


def iter_local_ipv4_interfaces() -> Iterator[Tuple[str, str]]:
    """Yield (ifname, ipv4_addr_str) for every local interface with an IPv4.

    Order is ``socket.if_nameindex()`` order — typically ``'lo'`` first,
    then ``ens0``/``eth0``/``wlan0``/etc.  Interfaces without an IPv4
    (IPv6-only, or freshly-created with no addr) are skipped silently.
    Stays stdlib-only on Linux (no ``netifaces``/``psutil`` dependency).
    """
    try:
        names = socket.if_nameindex()
    except OSError:
        return
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for _idx, ifname in names:
            try:
                raw = fcntl.ioctl(
                    probe.fileno(),
                    _SIOCGIFADDR,
                    struct.pack("256s", ifname.encode()[:15]),
                )
                addr = socket.inet_ntoa(raw[20:24])
            except OSError:
                continue
            yield ifname, addr
    finally:
        probe.close()


def join_multicast_all_interfaces(sock: socket.socket,
                                  multicast_address: str) -> List[str]:
    """Join ``multicast_address`` on every local IPv4 interface.

    Returns the list of interface names where the join succeeded.  Empty
    list means no interface was usable (extremely rare — even a freshly-
    booted box has ``lo``).  Per-interface failures are logged at DEBUG
    and skipped (e.g., a virtual interface without an IPv4).
    """
    joined: List[str] = []
    group = socket.inet_aton(multicast_address)
    for ifname, ifaddr in iter_local_ipv4_interfaces():
        mreq = struct.pack("=4s4s", group, socket.inet_aton(ifaddr))
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            joined.append(ifname)
        except OSError as exc:
            logger.debug(
                "multicast join on %s (%s) failed: %s",
                ifname, ifaddr, exc,
            )
    return joined
