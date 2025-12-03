"""
Stream discovery for ka9q-radio channels

This module provides functions to discover active channels by listening
to radiod's status multicast stream (native Python) or optionally using
the 'control' utility from ka9q-radio as a fallback.
"""

import subprocess
import re
import logging
import time
import select
import socket
import struct
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from .utils import resolve_multicast_address

logger = logging.getLogger(__name__)


@dataclass
class ChannelInfo:
    """Information about a ka9q-radio channel"""
    ssrc: int
    preset: str
    sample_rate: int
    frequency: float
    snr: float
    multicast_address: str
    port: int
    gps_time: Optional[int] = None  # GPS nanoseconds when RTP_TIMESNAP was captured
    rtp_timesnap: Optional[int] = None  # RTP timestamp at GPS_TIME


def _create_status_listener_socket(multicast_addr: str, interface: Optional[str] = None) -> socket.socket:
    """
    Create a UDP socket configured to listen for radiod status multicast.
    
    This is a standalone function that doesn't require RadiodControl,
    making it lightweight for discovery operations.
    
    Args:
        multicast_addr: IP address of the multicast group
        interface: IP address of the network interface to use (e.g., '192.168.1.100')
                  If None, uses INADDR_ANY (0.0.0.0) which works on single-homed systems
        
    Returns:
        Configured socket ready to receive status packets
    """
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Set SO_REUSEPORT if available (allows multiple processes)
    if hasattr(socket, 'SO_REUSEPORT'):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            logger.debug("SO_REUSEPORT enabled")
        except OSError as e:
            logger.debug(f"Could not set SO_REUSEPORT: {e}")
    
    # Bind to multicast port on all interfaces
    try:
        sock.bind(('0.0.0.0', 5006))  # radiod status port
        logger.debug(f"Bound to port 5006 for multicast reception")
    except OSError as e:
        logger.error(f"Failed to bind socket to port 5006: {e}")
        raise
    
    # Join multicast group on specified interface (or any interface if not specified)
    interface_addr = interface if interface else '0.0.0.0'
    mreq = struct.pack('=4s4s',
                      socket.inet_aton(multicast_addr),  # multicast group
                      socket.inet_aton(interface_addr))  # interface to use
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    logger.debug(f"Joined multicast group {multicast_addr} on interface {interface_addr}")
    
    # Set timeout for non-blocking reception
    sock.settimeout(0.1)
    
    return sock


def discover_channels_native(status_address: str, listen_duration: float = 2.0, 
                            interface: Optional[str] = None) -> Dict[int, ChannelInfo]:
    """
    Discover channels by listening to radiod status multicast (pure Python)
    
    This implementation listens directly to radiod's status multicast stream
    and decodes the status packets without requiring external executables.
    
    Args:
        status_address: Status multicast address (e.g., "radiod.local" or IP)
        listen_duration: How long to listen for status packets in seconds (default: 2.0)
        interface: IP address of the network interface to use for multicast reception
                  (e.g., '192.168.1.100'). Required on multi-homed systems.
                  If None, uses INADDR_ANY which works on single-homed systems.
        
    Returns:
        Dictionary mapping SSRC to ChannelInfo
    """
    # Import decoder function without creating full RadiodControl instance
    from .control import RadiodControl
    
    logger.info(f"Discovering channels via native Python listener from {status_address}")
    logger.info(f"Listening for {listen_duration} seconds...")
    
    channels = {}
    status_sock = None  # Initialize outside try block
    temp_control = None  # Initialize outside try block
    
    try:
        # Resolve address and create lightweight socket (no RadiodControl overhead)
        multicast_addr = resolve_multicast_address(status_address, timeout=2.0)
        status_sock = _create_status_listener_socket(multicast_addr, interface)
        
        # CRITICAL: Send a poll to radiod to trigger STATUS packet broadcasts
        # We need to send this BEFORE creating RadiodControl to avoid socket conflicts
        logger.debug("Sending poll to radiod to trigger STATUS broadcasts")
        try:
            import random
            # Build poll command as control.c does:
            # Type (1) + COMMAND_TAG (1, 4 bytes) + OUTPUT_SSRC (18, 4 bytes) + EOL (0, 0 bytes)
            poll_cmd = bytearray([1])  # CMD packet type (STATUS=0, CMD=1)
            # COMMAND_TAG (tag=1) with random value for tracking
            poll_cmd.extend([1, 4])  # tag=1 (COMMAND_TAG), length=4
            tag = random.randint(0, 0xffffffff)
            poll_cmd.extend(tag.to_bytes(4, 'big'))
            # OUTPUT_SSRC (tag=18) with value 0xffffffff (poll all channels)
            poll_cmd.extend([18, 4])  # tag=18 (OUTPUT_SSRC), length=4
            poll_cmd.extend([0xff, 0xff, 0xff, 0xff])  # SSRC=0xffffffff
            # EOL marker
            poll_cmd.extend([0, 0])  # tag=0 (EOL), length=0
            
            # Send poll using status_sock directly
            dest = (multicast_addr, 5006)
            status_sock.sendto(poll_cmd, dest)
            logger.debug(f"Poll sent successfully to {dest} (tag={tag})")
            # Give radiod a moment to respond
            time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Could not send poll (continuing anyway): {e}")
        
        start_time = time.time()
        packet_count = 0
        
        # We'll create temp_control lazily only when we need to decode a packet
        # This avoids opening an extra socket that would compete for multicast packets
        temp_control = None
        
        while time.time() - start_time < listen_duration:
            # Use remaining time or 0.5s, whichever is smaller (adaptive timeout)
            remaining = listen_duration - (time.time() - start_time)
            select_timeout = min(remaining, 0.5)
            
            ready = select.select([status_sock], [], [], select_timeout)
            if not ready[0]:
                continue
            
            # Receive status packet
            try:
                buffer, addr = status_sock.recvfrom(8192)
                packet_count += 1
                logger.debug(f"Received {len(buffer)} bytes from {addr}")
            except Exception as e:
                logger.debug(f"Error receiving packet: {e}")
                continue
            
            # Skip non-status packets (STATUS = 0, COMMAND = 1)
            if len(buffer) == 0 or buffer[0] != 0:  # STATUS packets have type byte == 0
                logger.debug(f"Skipping non-STATUS packet (type={buffer[0] if buffer else 'empty'})")
                continue
            
            # Decode status packet using temporary control instance
            # Create it lazily on first STATUS packet
            if temp_control is None:
                logger.debug("Creating RadiodControl for decoding")
                temp_control = RadiodControl(status_address)
            
            try:
                status = temp_control._decode_status_response(buffer)
            except Exception as e:
                logger.debug(f"Error decoding status packet: {e}")
                continue
            
            # Extract SSRC - required field
            ssrc = status.get('ssrc')
            if not ssrc:
                logger.debug("Status packet missing SSRC, skipping")
                continue
            
            # Build ChannelInfo from status
            # Extract destination socket info
            dest = status.get('destination', {})
            mcast_addr = dest.get('address', '') if isinstance(dest, dict) else ''
            port = dest.get('port', 0) if isinstance(dest, dict) else 0
            
            channel = ChannelInfo(
                ssrc=ssrc,
                preset=status.get('preset', 'unknown'),
                sample_rate=status.get('sample_rate', 0),
                frequency=status.get('frequency', 0.0),
                snr=status.get('snr', float('-inf')),
                multicast_address=mcast_addr,
                port=port,
                gps_time=status.get('gps_time'),
                rtp_timesnap=status.get('rtp_timesnap')
            )
            
            # Store or update channel info
            if ssrc not in channels:
                channels[ssrc] = channel
                logger.debug(
                    f"Discovered channel: SSRC={ssrc}, freq={channel.frequency/1e6:.3f} MHz, "
                    f"rate={channel.sample_rate} Hz, preset={channel.preset}"
                )
            else:
                # Update with latest info
                channels[ssrc] = channel
        
        logger.info(f"Discovered {len(channels)} channels from {packet_count} packets")
        
    except Exception as e:
        logger.error(f"Error during native channel discovery: {e}")
        logger.debug(f"Exception details:", exc_info=True)
    
    finally:
        # Clean up socket with error handling
        if status_sock:
            try:
                status_sock.close()
                logger.debug("Discovery socket closed successfully")
            except Exception as e:
                logger.warning(f"Error closing discovery socket: {e}")
        
        # Clean up temporary RadiodControl instance
        if temp_control:
            try:
                temp_control.close()
                logger.debug("Temporary control instance closed")
            except Exception as e:
                logger.debug(f"Error closing temporary control: {e}")
    
    return channels


def discover_channels_via_control(status_address: str, timeout: float = 30.0) -> Dict[int, ChannelInfo]:
    """
    Discover channels using the 'control' utility from ka9q-radio
    
    This is a fallback method that requires the 'control' executable
    from ka9q-radio to be installed on the system.
    
    Args:
        status_address: Status multicast address (e.g., "radiod.local")
        timeout: Timeout for control command (default: 30.0 seconds)
        
    Returns:
        Dictionary mapping SSRC to ChannelInfo
    """
    logger.info(f"Discovering channels via 'control' utility from {status_address}")
    
    channels = {}
    
    try:
        # Run control utility with -v flag to get verbose channel listing
        # Send empty input to make it list and exit
        result = subprocess.run(
            ['control', '-v', status_address],
            input='\n',
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        
        # Parse the output
        # Format: SSRC    preset   samprate      freq, Hz   SNR output channel
        #        60000        iq     16,000        60,000   9.5 239.41.204.101:5004
        
        for line in output.split('\n'):
            # Skip header and non-data lines
            if 'SSRC' in line or 'channels' in line or not line.strip():
                continue
            
            # Parse channel line
            # Pattern: whitespace-separated values
            parts = line.split()
            if len(parts) < 6:
                continue
            
            try:
                ssrc = int(parts[0])
                preset = parts[1]
                sample_rate = int(parts[2].replace(',', ''))
                frequency = float(parts[3].replace(',', ''))
                snr_str = parts[4]
                snr = float(snr_str) if snr_str != '-inf' else float('-inf')
                
                # Parse multicast address:port
                addr_port = parts[5]
                if ':' in addr_port:
                    addr, port_str = addr_port.rsplit(':', 1)
                    port = int(port_str)
                else:
                    addr = addr_port
                    port = 5004  # default
                
                channel = ChannelInfo(
                    ssrc=ssrc,
                    preset=preset,
                    sample_rate=sample_rate,
                    frequency=frequency,
                    snr=snr,
                    multicast_address=addr,
                    port=port
                )
                
                channels[ssrc] = channel
                
                logger.debug(
                    f"Found channel: SSRC={ssrc}, freq={frequency/1e6:.3f} MHz, "
                    f"rate={sample_rate} Hz, preset={preset}, addr={addr}:{port}"
                )
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse line: {line} - {e}")
                continue
        
        logger.info(f"Discovered {len(channels)} channels")
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout running control utility")
    except FileNotFoundError:
        logger.error("control utility not found - is ka9q-radio installed?")
    except Exception as e:
        logger.error(f"Error running control utility: {e}")
    
    return channels


def discover_channels(status_address: str, 
                      listen_duration: float = 2.0,
                      use_native: bool = True,
                      interface: Optional[str] = None) -> Dict[int, ChannelInfo]:
    """
    Discover channels using the best available method
    
    By default, uses native Python implementation. If use_native=False or
    if native discovery fails, falls back to the 'control' utility.
    
    Args:
        status_address: Status multicast address (e.g., "radiod.local")
        listen_duration: Duration to listen for native discovery (default: 2.0 seconds)
        use_native: If True, use native Python listener; if False, use control utility
        interface: IP address of network interface for multicast (e.g., '192.168.1.100').
                  Required on multi-homed systems. If None, uses INADDR_ANY (0.0.0.0).
        
    Returns:
        Dictionary mapping SSRC to ChannelInfo
    """
    if use_native:
        try:
            logger.debug("Attempting native channel discovery")
            channels = discover_channels_native(status_address, listen_duration, interface)
            if channels:
                return channels
            else:
                logger.warning("Native discovery found no channels, trying control utility fallback")
        except Exception as e:
            logger.warning(f"Native discovery failed ({e}), trying control utility fallback")
    
    # Fall back to control utility
    logger.debug("Using control utility for channel discovery")
    return discover_channels_via_control(status_address)


def find_channels_by_frequencies(
    status_address: str,
    frequencies: List[float],
    tolerance: float = 1000.0
) -> Dict[float, ChannelInfo]:
    """
    Find channels matching specific frequencies
    
    Args:
        status_address: Status multicast address
        frequencies: List of frequencies to find (in Hz)
        tolerance: Frequency tolerance in Hz (default 1000 Hz = 1 kHz)
        
    Returns:
        Dictionary mapping requested frequency to ChannelInfo
    """
    all_channels = discover_channels(status_address)
    
    matched = {}
    
    for target_freq in frequencies:
        best_match = None
        best_diff = float('inf')
        
        for ssrc, channel in all_channels.items():
            diff = abs(channel.frequency - target_freq)
            if diff < tolerance and diff < best_diff:
                best_match = channel
                best_diff = diff
        
        if best_match:
            matched[target_freq] = best_match
            logger.info(
                f"Matched {target_freq/1e6:.3f} MHz → SSRC {best_match.ssrc} "
                f"({best_match.frequency/1e6:.3f} MHz, diff={best_diff:.0f} Hz)"
            )
        else:
            logger.warning(f"No channel found for {target_freq/1e6:.3f} MHz")
    
    return matched



def _decode_escape_sequences(s: str) -> str:
    """
    Decode decimal escape sequences in a string from avahi-browse output
    
    avahi-browse uses decimal ASCII escape sequences (e.g., \064 = ASCII 64 = '@')
    
    Args:
        s: String potentially containing escape sequences like \032 or \064
        
    Returns:
        Decoded string with escape sequences converted to actual characters
    """
    def replace_decimal(match):
        """Replace decimal escape sequence with actual character"""
        decimal_str = match.group(1)
        char_code = int(decimal_str, 10)  # Decimal, not octal!
        # Replace control characters and non-printable chars with space
        if char_code < 32 or char_code == 127:
            return ' '
        return chr(char_code)
    
    # Replace decimal sequences like \032 (space) or \064 (@) with actual characters
    s = re.sub(r'\\(\d{3})', replace_decimal, s)
    # Replace other common escape sequences
    s = s.replace(r'\n', '\n').replace(r'\t', '\t').replace(r'\\', '\\')
    return s


def discover_radiod_services():
    """
    Discover all radiod services on the network via mDNS
    
    Returns:
        List of dicts with "name" and "address" keys
    """
    import subprocess
    
    # Use dict to automatically deduplicate by address
    services_dict = {}
    try:
        result = subprocess.run(
            ["avahi-browse", "-t", "_ka9q-ctl._udp", "-p", "-r"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        for line in result.stdout.split("\n"):
            if line.startswith("="):
                parts = line.split(";")
                if len(parts) >= 8:
                    name = _decode_escape_sequences(parts[3])
                    address = parts[7]
                    # Use address as key to deduplicate
                    services_dict[address] = {"name": name, "address": address}
    except Exception as e:
        logger.warning(f"Failed to discover radiod services: {e}")
    
    # Convert dict back to list, sorted by name for consistency
    services = sorted(services_dict.values(), key=lambda x: x['name'])
    return services

