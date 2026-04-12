"""
Addressing utilities for ka9q-radio applications.

This module provides helpers for generating deterministic unique addresses
for applications and streams.
"""

import hashlib
from typing import Optional

def generate_multicast_ip(unique_id: str, prefix: str = "239", *, radiod_host: Optional[str] = None) -> str:
    """
    Generate a deterministic multicast IP address from a unique identifier
    and, optionally, a radiod host.

    This function uses a hash of the input(s) to select an address within
    the Organization-Local Scope (239.0.0.0/8) or other specified range.

    This allows applications to claim a unique "App IP" without needing
    a central registry, with negligible collision probability.

    When ``radiod_host`` is supplied the generated address is unique to the
    (client, radiod) pair, so a single client application (e.g.
    "hf-timestd") talking to multiple radiod instances will get a distinct
    multicast destination for each one.

    Args:
        unique_id: Any string unique to the application (e.g., "my-sdr-app", "session-1234")
        prefix: The first octet of the multicast range (default: "239")
        radiod_host: Optional radiod hostname or address. When provided the
            hash is computed over both ``unique_id`` and ``radiod_host``,
            producing a different address for each radiod instance.

    Returns:
        A valid IPv4 multicast address string (e.g., "239.10.20.30")

    Example:
        >>> ip = generate_multicast_ip("my-weather-app")
        >>> print(ip)
        '239.174.23.192'
        >>> ip_a = generate_multicast_ip("hf-timestd", radiod_host="sdr1.local")
        >>> ip_b = generate_multicast_ip("hf-timestd", radiod_host="sdr2.local")
        >>> ip_a != ip_b
        True
    """
    if not unique_id:
        raise ValueError("unique_id cannot be empty")

    # Build the hash input.  When radiod_host is provided we include it
    # (separated by a NUL byte that cannot appear in either component) so
    # the same client talking to different radiod instances gets distinct
    # multicast addresses.
    if radiod_host:
        hash_input = f"{unique_id}\x00{radiod_host}"
    else:
        hash_input = unique_id

    # Use SHA-256 for good distribution
    # We only need 24 bits for the suffix (to fill x.y.z in 239.x.y.z)
    hash_bytes = hashlib.sha256(hash_input.encode('utf-8')).digest()
    
    # Take the first 3 bytes (24 bits)
    # This maps the ID to one of ~16.7 million addresses
    # Collision chance is approx 1 in 16.7 million for a single pair
    b1 = hash_bytes[0]
    b2 = hash_bytes[1]
    b3 = hash_bytes[2]
    
    return f"{prefix}.{b1}.{b2}.{b3}"
