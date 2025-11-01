"""
General-purpose radiod control interface via TLV command protocol

This module provides a complete interface to radiod's control protocol using
TLV (Type-Length-Value) encoding, based on ka9q-radio's status.c/status.h.

ARCHITECTURE:
- This module exposes ALL radiod capabilities and parameters
- Application-specific defaults (e.g., GRAPE's 16kHz IQ channels) live in
  higher-level modules (grape_recorder.py, config files)
- Reusable for any application needing radiod channel control

USAGE:
1. Create RadiodControl instance with status address
2. Use granular setters (set_frequency, set_preset, etc.) OR
3. Use create_and_configure_channel() for common channel creation patterns

PARAMETERS:
- All StatusType enum values from ka9q-radio/status.h are supported
- See individual methods for parameter descriptions and valid ranges
"""

import socket
import struct
import random
import logging
from typing import Optional
from .types import StatusType, CMD
from .discovery import discover_channels
from .exceptions import ConnectionError, CommandError

logger = logging.getLogger(__name__)


# Command packet type
CMD = 1


def encode_int64(buf: bytearray, type_val: int, x: int) -> int:
    """
    Encode a 64-bit integer in TLV format
    
    Format: [type:1][length:1][value:variable]
    Value is big-endian, with leading zeros compressed
    """
    buf.append(type_val)
    
    if x == 0:
        # Compress zero to zero length
        buf.append(0)
        return 2
    
    # Convert to bytes and remove leading zeros
    x_bytes = x.to_bytes(8, byteorder='big')
    # Find first non-zero byte
    start = 0
    while start < len(x_bytes) and x_bytes[start] == 0:
        start += 1
    
    value_bytes = x_bytes[start:]
    length = len(value_bytes)
    
    buf.append(length)
    buf.extend(value_bytes)
    
    return 2 + length


def encode_int(buf: bytearray, type_val: int, x: int) -> int:
    """Encode an integer"""
    return encode_int64(buf, type_val, x)


def encode_double(buf: bytearray, type_val: int, x: float) -> int:
    """
    Encode a double (float64) in TLV format
    
    The float is converted to its IEEE 754 representation and encoded as int64
    """
    # Pack as double, unpack as uint64
    packed = struct.pack('>d', x)  # big-endian double
    value = struct.unpack('>Q', packed)[0]  # big-endian uint64
    return encode_int64(buf, type_val, value)


def encode_float(buf: bytearray, type_val: int, x: float) -> int:
    """
    Encode a float (float32) in TLV format
    """
    # Pack as float, unpack as uint32
    packed = struct.pack('>f', x)  # big-endian float
    value = struct.unpack('>I', packed)[0]  # big-endian uint32
    return encode_int64(buf, type_val, value)


def encode_string(buf: bytearray, type_val: int, s: str) -> int:
    """
    Encode a string in TLV format
    """
    buf.append(type_val)
    
    s_bytes = s.encode('utf-8')
    length = len(s_bytes)
    
    if length < 128:
        buf.append(length)
    elif length < 65536:
        # Multi-byte length encoding
        buf.append(0x80 | (length >> 8))
        buf.append(length & 0xff)
    else:
        raise ValueError(f"String too long: {length} bytes")
    
    buf.extend(s_bytes)
    return 2 + length


def encode_eol(buf: bytearray) -> int:
    """Encode end-of-list marker"""
    buf.append(StatusType.EOL)
    return 1


class RadiodControl:
    """
    Control interface for radiod
    
    Sends TLV-encoded commands to radiod's control socket to create
    and configure channels.
    """
    
    def __init__(self, status_address: str):
        """
        Initialize radiod control
        
        Args:
            status_address: mDNS name or IP:port of radiod status stream
        """
        self.status_address = status_address
        self.socket = None
        self._connect()
    
    def _connect(self):
        """Connect to radiod control socket"""
        # Resolve the status address
        import subprocess
        import re
        
        try:
            # Check if it's already an IP address
            if re.match(r'^\d+\.\d+\.\d+\.\d+$', self.status_address):
                mcast_addr = self.status_address
                logger.info(f"Using direct IP address: {mcast_addr}")
            else:
                # Try avahi-resolve first
                try:
                    result = subprocess.run(
                        ['avahi-resolve', '-n', self.status_address],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        # Parse output: "hostname    ip_address"
                        parts = result.stdout.strip().split()
                        if len(parts) >= 2:
                            mcast_addr = parts[1]
                        else:
                            raise ValueError(f"Unexpected avahi-resolve output: {result.stdout}")
                    else:
                        raise ValueError(f"avahi-resolve failed: {result.stderr}")
                except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
                    # Try getaddrinfo as fallback
                    logger.warning(f"avahi-resolve failed ({e}), trying getaddrinfo")
                    import socket as sock
                    addr_info = sock.getaddrinfo(self.status_address, None, sock.AF_INET, sock.SOCK_DGRAM)
                    mcast_addr = addr_info[0][4][0]
            
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Allow multiple sockets to bind to the same port
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set socket options for multicast
            # Use loopback interface with proper ip_mreqn structure
            # This is critical - we need to specify BOTH the IP and interface index
            import struct
            # Get loopback interface index
            lo_index = socket.if_nametoindex('lo')
            # Create ip_mreqn structure matching ka9q-radio's setup_ipv4_loopback:
            # struct ip_mreqn { imr_multiaddr (4 bytes), imr_address (4 bytes), imr_ifindex (4 bytes) }
            # imr_address = 127.0.0.1 (INADDR_LOOPBACK), imr_ifindex = loopback interface
            # Note: imr_multiaddr is not used for IP_MULTICAST_IF, can be 0
            mreqn = struct.pack('=4sIi',  # Use 'I' for network byte order uint32
                               b'\x00\x00\x00\x00',  # imr_multiaddr (not used)
                               socket.htonl(0x7F000001),  # imr_address = 127.0.0.1 in network byte order
                               lo_index)  # imr_ifindex (loopback interface index)
            logger.debug(f"Setting IP_MULTICAST_IF with ip_mreqn: lo_index={lo_index}, mreqn={mreqn.hex()}")
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, mreqn)
            logger.debug(f"IP_MULTICAST_IF set successfully")
            
            # Join the multicast group (required for sending on some systems)
            # This matches what ka9q-radio's control utility does
            mreq = struct.pack('=4s4s', 
                              socket.inet_aton(mcast_addr),  # multicast group address
                              socket.inet_aton('127.0.0.1'))  # interface address (loopback)
            try:
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                logger.debug(f"Joined multicast group {mcast_addr} on 127.0.0.1")
            except OSError as e:
                # EADDRINUSE is not fatal - group already joined
                if e.errno != 98:  # EADDRINUSE
                    logger.warning(f"Failed to join multicast group: {e}")
            
            # Enable multicast loopback so we can send to ourselves
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
            # Set TTL for multicast packets
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            
            self.dest_addr = (mcast_addr, 5006)  # Standard radiod control port
            
            logger.info(f"Connected to radiod at {mcast_addr}:5006 via loopback")
            logger.debug(f"Socket options: REUSEADDR=1, MULTICAST_IF=127.0.0.1, MULTICAST_LOOP=1, MULTICAST_TTL=2")
            
        except Exception as e:
            logger.error(f"Failed to connect to radiod: {e}")
            raise
    
    def send_command(self, cmdbuffer: bytearray):
        """Send a command packet to radiod"""
        if not self.socket:
            raise RuntimeError("Not connected to radiod")
        
        try:
            # Log hex dump of the command
            hex_dump = ' '.join(f'{b:02x}' for b in cmdbuffer)
            logger.debug(f"Sending {len(cmdbuffer)} bytes to {self.dest_addr}: {hex_dump}")
            
            sent = self.socket.sendto(bytes(cmdbuffer), self.dest_addr)
            logger.debug(f"Sent {sent} bytes to radiod")
            return sent
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            raise
    
    def set_frequency(self, ssrc: int, frequency_hz: float):
        """
        Set the frequency of a channel
        
        Args:
            ssrc: SSRC of the channel
            frequency_hz: Frequency in Hz
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)  # Command packet type
        
        encode_double(cmdbuffer, StatusType.RADIO_FREQUENCY, frequency_hz)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting frequency for SSRC {ssrc} to {frequency_hz/1e6:.3f} MHz")
        self.send_command(cmdbuffer)
    
    def set_preset(self, ssrc: int, preset: str):
        """
        Set the preset (mode) of a channel
        
        Args:
            ssrc: SSRC of the channel
            preset: Preset name (e.g., "iq", "usb", "lsb")
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        encode_string(cmdbuffer, StatusType.PRESET, preset)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting preset for SSRC {ssrc} to {preset}")
        self.send_command(cmdbuffer)
    
    def set_sample_rate(self, ssrc: int, sample_rate: int):
        """
        Set the sample rate of a channel
        
        Args:
            ssrc: SSRC of the channel
            sample_rate: Sample rate in Hz
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        encode_int(cmdbuffer, StatusType.OUTPUT_SAMPRATE, sample_rate)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting sample rate for SSRC {ssrc} to {sample_rate} Hz")
        self.send_command(cmdbuffer)
    
    def set_agc(self, ssrc: int, enable: bool, hangtime: Optional[float] = None, 
                headroom: Optional[float] = None, recovery_rate: Optional[float] = None,
                attack_rate: Optional[float] = None):
        """
        Configure AGC (Automatic Gain Control) for a channel
        
        Args:
            ssrc: SSRC of the channel
            enable: Enable/disable AGC (True=enabled, False=manual gain)
            hangtime: AGC hang time in seconds (optional)
            headroom: Target headroom in dB (optional)
            recovery_rate: AGC recovery rate (optional)
            attack_rate: AGC attack rate (optional)
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        encode_int(cmdbuffer, StatusType.AGC_ENABLE, 1 if enable else 0)
        if hangtime is not None:
            encode_float(cmdbuffer, StatusType.AGC_HANGTIME, hangtime)
        if headroom is not None:
            encode_float(cmdbuffer, StatusType.HEADROOM, headroom)
        if recovery_rate is not None:
            encode_float(cmdbuffer, StatusType.AGC_RECOVERY_RATE, recovery_rate)
        if attack_rate is not None:
            encode_float(cmdbuffer, StatusType.AGC_ATTACK_RATE, attack_rate)
        
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting AGC for SSRC {ssrc}: enable={enable}, hangtime={hangtime}, headroom={headroom}")
        self.send_command(cmdbuffer)
    
    def set_gain(self, ssrc: int, gain_db: float):
        """
        Set manual gain for a channel (linear modes only)
        
        Args:
            ssrc: SSRC of the channel
            gain_db: Gain in dB
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        encode_double(cmdbuffer, StatusType.GAIN, gain_db)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting gain for SSRC {ssrc} to {gain_db} dB")
        self.send_command(cmdbuffer)
    
    def set_filter(self, ssrc: int, low_edge: Optional[float] = None, 
                   high_edge: Optional[float] = None, kaiser_beta: Optional[float] = None):
        """
        Configure filter parameters for a channel
        
        Args:
            ssrc: SSRC of the channel
            low_edge: Low frequency edge in Hz (optional)
            high_edge: High frequency edge in Hz (optional)
            kaiser_beta: Kaiser window beta parameter (optional)
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        if low_edge is not None:
            encode_double(cmdbuffer, StatusType.LOW_EDGE, low_edge)
        if high_edge is not None:
            encode_double(cmdbuffer, StatusType.HIGH_EDGE, high_edge)
        if kaiser_beta is not None:
            encode_float(cmdbuffer, StatusType.KAISER_BETA, kaiser_beta)
        
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting filter for SSRC {ssrc}: low={low_edge}, high={high_edge}, beta={kaiser_beta}")
        self.send_command(cmdbuffer)
    
    def set_shift_frequency(self, ssrc: int, shift_hz: float):
        """
        Set post-detection frequency shift (for CW offset, etc.)
        
        Args:
            ssrc: SSRC of the channel
            shift_hz: Frequency shift in Hz
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        encode_double(cmdbuffer, StatusType.SHIFT_FREQUENCY, shift_hz)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting frequency shift for SSRC {ssrc} to {shift_hz} Hz")
        self.send_command(cmdbuffer)
    
    def set_output_level(self, ssrc: int, level: float):
        """
        Set output level for a channel
        
        Args:
            ssrc: SSRC of the channel
            level: Output level (range depends on mode)
        """
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        encode_float(cmdbuffer, StatusType.OUTPUT_LEVEL, level)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        logger.info(f"Setting output level for SSRC {ssrc} to {level}")
        self.send_command(cmdbuffer)
    
    def create_and_configure_channel(self, ssrc: int, frequency_hz: float, 
                                     preset: str = "iq", sample_rate: Optional[int] = 16000,
                                     agc_enable: int = 0, gain: float = 0.0):
        """
        Create a new channel and configure it (GRAPE-compatible)
        
        This sends ALL parameters in a SINGLE packet to radiod.
        This is critical because radiod creates the channel when it receives
        the first command for a new SSRC, using the parameters in that packet.
        
        Args:
            ssrc: SSRC for the new channel
            frequency_hz: Frequency in Hz
            preset: Demod type (default: "iq" = linear mode)
            sample_rate: Sample rate in Hz (default: 16000 for GRAPE)
            agc_enable: AGC enable (0=off, 1=on) (default: 0 for GRAPE)
            gain: Manual gain setting in dB (default: 0.0 for GRAPE)
        """
        logger.info(f"Creating GRAPE channel: SSRC={ssrc}, freq={frequency_hz/1e6:.3f} MHz, "
                   f"demod={preset}, rate={sample_rate}Hz, agc={agc_enable}, gain={gain}dB")
        
        # Build a single command packet with ALL parameters
        # This ensures radiod creates the channel with the correct settings
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        # PRESET: Mode name (e.g., "iq", "usb", "lsb")
        # This MUST come first - radiod uses it to set up the channel
        encode_string(cmdbuffer, StatusType.PRESET, preset)
        logger.info(f"Setting preset for SSRC {ssrc} to {preset}")
        
        # DEMOD_TYPE: 0=linear (IQ/USB/LSB/etc), 1=FM
        # For IQ/GRAPE, we want linear mode
        demod_type = 0 if preset.lower() in ['iq', 'usb', 'lsb', 'cw', 'am'] else 1
        encode_int(cmdbuffer, StatusType.DEMOD_TYPE, demod_type)
        logger.info(f"Setting DEMOD_TYPE for SSRC {ssrc} to {demod_type}")
        
        # Frequency
        encode_double(cmdbuffer, StatusType.RADIO_FREQUENCY, frequency_hz)
        logger.info(f"Setting frequency for SSRC {ssrc} to {frequency_hz/1e6:.3f} MHz")
        
        # Sample rate (16000 Hz for GRAPE)
        if sample_rate:
            encode_int(cmdbuffer, StatusType.OUTPUT_SAMPRATE, sample_rate)
            logger.info(f"Setting sample rate for SSRC {ssrc} to {sample_rate} Hz")
        
        # AGC setting (disable for GRAPE - use fixed gain)
        encode_int(cmdbuffer, StatusType.AGC_ENABLE, agc_enable)
        logger.info(f"Setting AGC_ENABLE for SSRC {ssrc} to {agc_enable}")
        
        # Gain setting (0 dB for GRAPE)
        encode_double(cmdbuffer, StatusType.GAIN, gain)
        logger.info(f"Setting GAIN for SSRC {ssrc} to {gain} dB")
        
        # SSRC and command tag
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        # Send the single packet
        self.send_command(cmdbuffer)
        
        logger.info(f"GRAPE channel {ssrc} created and configured")
    
    def verify_channel(self, ssrc: int, expected_freq: Optional[float] = None) -> bool:
        """
        Verify that a channel exists and is configured correctly
        
        Args:
            ssrc: SSRC to verify
            expected_freq: Expected frequency in Hz (optional)
        
        Returns:
            True if channel exists and matches expectations
        """
        # Discover current channels
        channels = discover_channels(self.status_address)
        
        if ssrc not in channels:
            logger.warning(f"Channel {ssrc} not found")
            return False
        
        channel = channels[ssrc]
        
        if expected_freq and abs(channel.frequency - expected_freq) > 1:  # 1 Hz tolerance
            logger.warning(
                f"Channel {ssrc} frequency mismatch: "
                f"expected {expected_freq/1e6:.3f} MHz, "
                f"got {channel.frequency/1e6:.3f} MHz"
            )
            return False
        
        logger.info(f"Channel {ssrc} verified: {channel.frequency/1e6:.3f} MHz, {channel.preset}")
        return True
    
    def close(self):
        """Close the control socket"""
        if self.socket:
            self.socket.close()
            self.socket = None

