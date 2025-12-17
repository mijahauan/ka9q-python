"""
Addressing utilities for ka9q-radio applications.

This module provides helpers for generating deterministic unique addresses
for applications and streams.
"""

import hashlib
from typing import Optional

def generate_multicast_ip(unique_id: str, prefix: str = "239") -> str:
    """
    Generate a deterministic multicast IP address from a unique identifier.
    
    This function uses a hash of the input ID to select an address within
    the Organization-Local Scope (239.0.0.0/8) or other specified range.
    
    This allows applications to claim a unique "App IP" without needing
    a central registry, with negligible collision probability.
    
    Args:
        unique_id: Any string unique to the application (e.g., "my-sdr-app", "session-1234")
        prefix: The first octet of the multicast range (default: "239")
    
    Returns:
        A valid IPv4 multicast address string (e.g., "239.10.20.30")
        
    Example:
        >>> ip = generate_multicast_ip("my-weather-app")
        >>> print(ip)
        '239.174.23.192'
    """
    if not unique_id:
        raise ValueError("unique_id cannot be empty")
        
    # Use SHA-256 for good distribution
    # We only need 24 bits for the suffix (to fill x.y.z in 239.x.y.z)
    hash_bytes = hashlib.sha256(unique_id.encode('utf-8')).digest()
    
    # Take the first 3 bytes (24 bits)
    # This maps the ID to one of ~16.7 million addresses
    # Collision chance is approx 1 in 16.7 million for a single pair
    b1 = hash_bytes[0]
    b2 = hash_bytes[1]
    b3 = hash_bytes[2]
    
    return f"{prefix}.{b1}.{b2}.{b3}"
