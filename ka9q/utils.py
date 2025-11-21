"""
Shared utility functions for ka9q-python

This module contains common utilities used across the package, primarily
for mDNS address resolution and network operations.
"""

import socket
import subprocess
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def resolve_multicast_address(address: str, timeout: float = 5.0) -> str:
    """
    Resolve hostname or mDNS address to IP for multicast operations
    
    This function tries multiple resolution methods for cross-platform compatibility:
    1. Check if already an IP address (no resolution needed)
    2. Try avahi-resolve (Linux)
    3. Try dns-sd (macOS)
    4. Fallback to getaddrinfo (works everywhere)
    
    Args:
        address: Hostname, .local mDNS name, or IP address
        timeout: Resolution timeout in seconds (default: 5.0)
        
    Returns:
        Resolved IP address as string (e.g., "239.251.200.193")
        
    Raises:
        Exception: If resolution fails after trying all methods
        
    Example:
        >>> resolve_multicast_address("radiod.local")
        '239.251.200.193'
        
        >>> resolve_multicast_address("192.168.1.100")
        '192.168.1.100'
    """
    # Check if already an IP address
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', address):
        logger.debug(f"Address {address} is already an IP")
        return address
    
    # Try avahi-resolve (Linux)
    try:
        result = subprocess.run(
            ['avahi-resolve', '-n', address],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            # Parse output: "hostname    ip_address"
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                resolved = parts[1]
                logger.debug(f"Resolved via avahi-resolve: {address} -> {resolved}")
                return resolved
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f"avahi-resolve not available: {e}")
    
    # Try dns-sd (macOS)
    try:
        result = subprocess.run(
            ['dns-sd', '-G', 'v4', address],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            # Parse dns-sd output for IP address
            for line in result.stdout.split('\n'):
                # Look for lines containing the address and an IP
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match and address in line:
                    resolved = match.group(1)
                    logger.debug(f"Resolved via dns-sd: {address} -> {resolved}")
                    return resolved
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f"dns-sd not available: {e}")
    
    # Fallback to getaddrinfo (works everywhere)
    # Note: getaddrinfo doesn't support timeout, so we set socket default timeout
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            addr_info = socket.getaddrinfo(address, None, socket.AF_INET, socket.SOCK_DGRAM)
            resolved = addr_info[0][4][0]
            logger.debug(f"Resolved via getaddrinfo: {address} -> {resolved}")
            return resolved
        finally:
            socket.setdefaulttimeout(old_timeout)
    except Exception as e:
        raise Exception(f"Failed to resolve {address}: {e}") from e


def create_multicast_socket(multicast_addr: str, port: int = 5006, 
                            bind_addr: str = '0.0.0.0',
                            interface: Optional[str] = None) -> socket.socket:
    """
    Create and configure a UDP socket for multicast operations
    
    This is a convenience function that sets up all the necessary socket options
    for sending to or receiving from a multicast group.
    
    Args:
        multicast_addr: Multicast group IP address
        port: Port number (default: 5006 for radiod)
        bind_addr: Address to bind to (default: '0.0.0.0' for all interfaces)
        interface: IP address of network interface for multicast membership
                  (e.g., '192.168.1.100'). Required on multi-homed systems.
                  If None, uses INADDR_ANY (0.0.0.0).
        
    Returns:
        Configured socket ready for multicast operations
        
    Raises:
        OSError: If socket creation or configuration fails
        
    Example:
        >>> sock = create_multicast_socket('239.251.200.193')
        >>> sock.sendto(data, ('239.251.200.193', 5006))
        
        >>> # Multi-homed system
        >>> sock = create_multicast_socket('239.251.200.193', interface='192.168.1.100')
    """
    import struct
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Allow multiple sockets to bind to the same port
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Set SO_REUSEPORT if available (allows multiple processes)
    if hasattr(socket, 'SO_REUSEPORT'):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            logger.debug("SO_REUSEPORT enabled")
        except OSError as e:
            logger.debug(f"Could not set SO_REUSEPORT: {e}")
    
    # Bind to specified port
    try:
        sock.bind((bind_addr, port))
        logger.debug(f"Bound to {bind_addr}:{port}")
    except OSError as e:
        logger.error(f"Failed to bind socket to {bind_addr}:{port}: {e}")
        sock.close()
        raise
    
    # Join multicast group on specified interface
    interface_addr = interface if interface else '0.0.0.0'
    mreq = struct.pack('=4s4s',
                      socket.inet_aton(multicast_addr),  # multicast group
                      socket.inet_aton(interface_addr))  # interface to use
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        logger.debug(f"Joined multicast group {multicast_addr} on interface {interface_addr}")
    except OSError as e:
        # EADDRINUSE is not fatal - group already joined
        if e.errno != 48:  # EADDRINUSE on macOS
            logger.warning(f"Failed to join multicast group: {e}")
    
    return sock


def validate_multicast_address(address: str) -> bool:
    """
    Validate that an address is a valid multicast address
    
    Multicast addresses are in the range 224.0.0.0 to 239.255.255.255
    
    Args:
        address: IP address string to validate
        
    Returns:
        True if valid multicast address, False otherwise
        
    Example:
        >>> validate_multicast_address('239.251.200.193')
        True
        
        >>> validate_multicast_address('192.168.1.1')
        False
    """
    try:
        parts = address.split('.')
        if len(parts) != 4:
            return False
        
        first_octet = int(parts[0])
        # Multicast range: 224.0.0.0 to 239.255.255.255
        return 224 <= first_octet <= 239
    except (ValueError, AttributeError):
        return False
