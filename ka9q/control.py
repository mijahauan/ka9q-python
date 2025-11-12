"""
General-purpose radiod control interface via TLV command protocol

This module provides a complete interface to radiod's control protocol using
TLV (Type-Length-Value) encoding, based on ka9q-radio's status.c/status.h.

ARCHITECTURE:
- This module exposes ALL radiod capabilities and parameters
- Application-specific defaults should be implemented in higher-level modules
  or configuration files
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
import threading
from typing import Optional
from .types import StatusType, CMD
from .discovery import discover_channels
from .exceptions import ConnectionError, CommandError, ValidationError
from .utils import resolve_multicast_address

logger = logging.getLogger(__name__)


# Command packet type
CMD = 1


# Input validation functions
def _validate_ssrc(ssrc: int) -> None:
    """Validate SSRC fits in 32-bit unsigned integer"""
    if not isinstance(ssrc, int):
        raise ValidationError(f"SSRC must be an integer, got {type(ssrc).__name__}")
    if not (0 <= ssrc <= 0xFFFFFFFF):
        raise ValidationError(f"Invalid SSRC: {ssrc} (must be 0-4294967295)")


def _validate_frequency(freq_hz: float) -> None:
    """Validate frequency is within reasonable SDR range"""
    if not isinstance(freq_hz, (int, float)):
        raise ValidationError(f"Frequency must be a number, got {type(freq_hz).__name__}")
    if not (0 < freq_hz < 10e12):  # 10 THz max
        raise ValidationError(f"Invalid frequency: {freq_hz} Hz (must be 0 < freq < 10 THz)")


def _validate_sample_rate(rate: int) -> None:
    """Validate sample rate is positive and reasonable"""
    if not isinstance(rate, int):
        raise ValidationError(f"Sample rate must be an integer, got {type(rate).__name__}")
    if not (1 <= rate <= 100e6):  # 100 MHz max
        raise ValidationError(f"Invalid sample rate: {rate} Hz (must be 1-100000000)")


def _validate_timeout(timeout: float) -> None:
    """Validate timeout is positive"""
    if not isinstance(timeout, (int, float)):
        raise ValidationError(f"Timeout must be a number, got {type(timeout).__name__}")
    if timeout <= 0:
        raise ValidationError(f"Timeout must be positive, got {timeout}")


def _validate_gain(gain_db: float) -> None:
    """Validate gain is within reasonable range"""
    if not isinstance(gain_db, (int, float)):
        raise ValidationError(f"Gain must be a number, got {type(gain_db).__name__}")
    if not (-100 <= gain_db <= 100):  # Reasonable range for most SDRs
        raise ValidationError(f"Invalid gain: {gain_db} dB (must be -100 to +100)")


def _validate_positive(value: float, name: str) -> None:
    """Validate that a value is positive"""
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
    if value <= 0:
        raise ValidationError(f"{name} must be positive, got {value}")


def encode_int64(buf: bytearray, type_val: int, x: int) -> int:
    """
    Encode a 64-bit integer in TLV format
    
    Format: [type:1][length:1][value:variable]
    Value is big-endian, with leading zeros compressed
    
    Args:
        buf: Buffer to write to
        type_val: TLV type identifier
        x: Integer value (must be 0 <= x <= 2^64-1)
        
    Raises:
        ValidationError: If x is negative or too large
    """
    if x < 0:
        raise ValidationError(f"Cannot encode negative integer: {x}")
    if x >= 2**64:
        raise ValidationError(f"Integer too large for 64-bit encoding: {x}")
    
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
    """
    Encode an integer in TLV format (alias for encode_int64)
    
    Args:
        buf: Buffer to write to
        type_val: TLV type identifier
        x: Integer value (must be 0 <= x <= 2^64-1)
        
    Returns:
        Number of bytes written (2 + value length)
        
    Raises:
        ValidationError: If x is negative or too large
    """
    return encode_int64(buf, type_val, x)


def encode_double(buf: bytearray, type_val: int, x: float) -> int:
    """
    Encode a double-precision float (float64) in TLV format
    
    Converts the float to IEEE 754 double-precision format, then encodes
    it as a 64-bit integer in TLV format.
    
    Args:
        buf: Buffer to write to
        type_val: TLV type identifier
        x: Float value to encode
        
    Returns:
        Number of bytes written (2 + value length)
        
    Example:
        >>> buf = bytearray()
        >>> encode_double(buf, StatusType.RADIO_FREQUENCY, 14.074e6)
        10
    """
    # Pack as double, unpack as uint64
    packed = struct.pack('>d', x)  # big-endian double
    value = struct.unpack('>Q', packed)[0]  # big-endian uint64
    return encode_int64(buf, type_val, value)


def encode_float(buf: bytearray, type_val: int, x: float) -> int:
    """
    Encode a single-precision float (float32) in TLV format
    
    Converts the float to IEEE 754 single-precision format, then encodes
    it as a 32-bit integer in TLV format.
    
    Args:
        buf: Buffer to write to
        type_val: TLV type identifier
        x: Float value to encode
        
    Returns:
        Number of bytes written (2 + value length)
        
    Note:
        Single-precision floats have less precision than doubles.
        Use encode_double() for better precision when needed.
    """
    # Pack as float, unpack as uint32
    packed = struct.pack('>f', x)  # big-endian float
    value = struct.unpack('>I', packed)[0]  # big-endian uint32
    return encode_int64(buf, type_val, value)


def encode_string(buf: bytearray, type_val: int, s: str) -> int:
    """
    Encode a UTF-8 string in TLV format
    
    Strings are encoded with variable-length encoding:
    - Length < 128: single-byte length
    - Length >= 128: multi-byte length (0x80 | high_byte, low_byte)
    
    Args:
        buf: Buffer to write to
        type_val: TLV type identifier
        s: String to encode (will be converted to UTF-8)
        
    Returns:
        Number of bytes written (2 + string length)
        
    Raises:
        ValueError: If string is longer than 65535 bytes
        
    Example:
        >>> buf = bytearray()
        >>> encode_string(buf, StatusType.PRESET, "usb")
        5
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
    """
    Encode end-of-list marker
    
    Every TLV command must end with an EOL marker to signal
    the end of the parameter list.
    
    Args:
        buf: Buffer to write to
        
    Returns:
        Number of bytes written (always 1)
    """
    buf.append(StatusType.EOL)
    return 1


# Decode functions for parsing TLV responses

def decode_int(data: bytes, length: int) -> int:
    """
    Decode an integer from TLV response
    
    Args:
        data: Bytes to decode (variable length, big-endian)
        length: Number of bytes
        
    Returns:
        Integer value
    """
    if length == 0:
        return 0
    
    value = 0
    for i in range(length):
        value = (value << 8) | data[i]
    return value


def decode_int32(data: bytes, length: int) -> int:
    """
    Decode a 32-bit integer from TLV response (alias for decode_int)
    
    Args:
        data: Bytes to decode (variable length, big-endian)
        length: Number of bytes
        
    Returns:
        Integer value
    """
    return decode_int(data, length)


def decode_float(data: bytes, length: int) -> float:
    """
    Decode a float (float32) from TLV response
    
    Args:
        data: Bytes to decode (big-endian IEEE 754)
        length: Number of bytes (should be 4 or less with leading zeros stripped)
        
    Returns:
        Float value
    """
    # Reconstruct 4-byte big-endian representation
    value_bytes = b'\x00' * (4 - length) + data[:length]
    return struct.unpack('>f', value_bytes)[0]


def decode_double(data: bytes, length: int) -> float:
    """
    Decode a double (float64) from TLV response
    
    Args:
        data: Bytes to decode (big-endian IEEE 754)
        length: Number of bytes (should be 8 or less with leading zeros stripped)
        
    Returns:
        Float value
    """
    # Reconstruct 8-byte big-endian representation
    value_bytes = b'\x00' * (8 - length) + data[:length]
    return struct.unpack('>d', value_bytes)[0]


def decode_bool(data: bytes, length: int) -> bool:
    """
    Decode a boolean value from TLV response
    
    Args:
        data: Bytes to decode
        length: Number of bytes
        
    Returns:
        True if non-zero, False if zero
    """
    return decode_int(data, length) != 0


def decode_string(data: bytes, length: int) -> str:
    """
    Decode a UTF-8 string from TLV response
    
    Args:
        data: Bytes to decode
        length: String length in bytes
        
    Returns:
        Decoded string
    """
    return data[:length].decode('utf-8', errors='replace')


def decode_socket(data: bytes, length: int) -> dict:
    """
    Decode a socket address from TLV response
    
    Args:
        data: Bytes containing socket address
        length: Length of socket data
        
    Returns:
        Dictionary with 'family', 'address', and 'port' keys
    
    Note:
        ka9q-radio encodes sockets WITHOUT an explicit family field.
        Family is inferred from length:
        - 6 bytes = IPv4 (4 bytes address + 2 bytes port)
        - 10 bytes = IPv6 (8 bytes address + 2 bytes port)
    """
    if length == 6:
        # IPv4: 4 bytes address + 2 bytes port (big-endian)
        address = socket.inet_ntoa(data[0:4])
        port = struct.unpack('>H', data[4:6])[0]
        return {'family': 'IPv4', 'address': address, 'port': port}
    elif length == 10:
        # IPv6: 8 bytes address + 2 bytes port (big-endian)
        # Note: This is a truncated IPv6 address (only 8 bytes instead of 16)
        # This appears to be how ka9q-radio encodes it
        address_bytes = data[0:8]
        port = struct.unpack('>H', data[8:10])[0]
        # Format as hex string since it's truncated
        address = ':'.join(f'{address_bytes[i]:02x}{address_bytes[i+1]:02x}' 
                          for i in range(0, 8, 2))
        return {'family': 'IPv6', 'address': address, 'port': port}
    else:
        return {'family': 'unknown', 'address': '', 'port': 0}


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
        self._status_sock = None  # Cached status listener socket for tune()
        self._status_sock_lock = None  # Will be initialized when needed
        self._socket_lock = threading.RLock()  # Protect control socket operations
        self._connect()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        try:
            self.close()
        except Exception as e:
            logger.warning(f"Error during cleanup in context manager: {e}")
        return False  # Don't suppress exceptions
    
    def _connect(self):
        """Connect to radiod control socket"""
        try:
            # Resolve the status address using shared utility
            mcast_addr = resolve_multicast_address(self.status_address, timeout=5.0)
            
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Allow multiple sockets to bind to the same port
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set socket options for multicast
            import struct
            
            # Use default interface (INADDR_ANY) for multicast
            # This allows the OS to select the appropriate interface
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, 
                                 socket.inet_aton('0.0.0.0'))
            logger.debug(f"Set IP_MULTICAST_IF to INADDR_ANY")
            
            # Join the multicast group on any interface
            mreq = struct.pack('=4s4s', 
                              socket.inet_aton(mcast_addr),  # multicast group address
                              socket.inet_aton('0.0.0.0'))  # any interface (INADDR_ANY)
            try:
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                logger.debug(f"Joined multicast group {mcast_addr} on any interface")
            except OSError as e:
                # EADDRINUSE is not fatal - group already joined
                if e.errno != 48:  # EADDRINUSE on macOS
                    logger.warning(f"Failed to join multicast group: {e}")
            
            # Enable multicast loopback
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
            # Set TTL for multicast packets
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            
            # Store both status and control addresses
            # Status address is where we listen for status multicast
            # Control address is where we send commands (same as status for now)
            self.status_mcast_addr = mcast_addr
            self.dest_addr = (mcast_addr, 5006)  # Standard radiod control port
            
            logger.info(f"Connected to radiod at {mcast_addr}:5006")
            logger.debug(f"Status multicast: {self.status_mcast_addr}, Control: {self.dest_addr}")
            logger.debug(f"Socket options: REUSEADDR=1, MULTICAST_IF=INADDR_ANY, MULTICAST_LOOP=1, MULTICAST_TTL=2")
            
        except socket.error as e:
            logger.error(f"Socket error connecting to radiod: {e}")
            raise ConnectionError(f"Failed to create socket: {e}") from e
        except subprocess.TimeoutExpired as e:
            logger.error(f"Timeout resolving address: {e}")
            raise ConnectionError(f"Address resolution timeout: {e}") from e
        except FileNotFoundError as e:
            # mDNS tools not found, but getaddrinfo should work
            logger.debug(f"mDNS tools not available: {e}")
            raise ConnectionError(f"Cannot resolve address (mDNS tools unavailable): {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error connecting to radiod: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect to radiod: {e}") from e
    
    def send_command(self, cmdbuffer: bytearray, max_retries: int = 3, retry_delay: float = 0.1):
        """
        Send a command packet to radiod with retry logic (thread-safe)
        
        Args:
            cmdbuffer: Command buffer to send
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Initial delay between retries in seconds (default: 0.1)
                        Uses exponential backoff: 0.1s, 0.2s, 0.4s, etc.
        
        Raises:
            RuntimeError: If not connected to radiod
            CommandError: If sending fails after all retries
        """
        import time
        
        with self._socket_lock:
            if not self.socket:
                raise RuntimeError("Not connected to radiod")
            
            last_error = None
            for attempt in range(max_retries):
                try:
                    # Log hex dump of the command
                    hex_dump = ' '.join(f'{b:02x}' for b in cmdbuffer)
                    logger.debug(f"Sending {len(cmdbuffer)} bytes to {self.dest_addr} (attempt {attempt+1}/{max_retries}): {hex_dump}")
                    
                    sent = self.socket.sendto(bytes(cmdbuffer), self.dest_addr)
                    logger.debug(f"Sent {sent} bytes to radiod")
                    return sent
                    
                except socket.error as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        delay = retry_delay * (2 ** attempt)
                        logger.warning(f"Socket error on attempt {attempt+1}/{max_retries}: {e}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Socket error sending command after {max_retries} attempts: {e}")
                        raise CommandError(f"Failed to send command after {max_retries} attempts: {e}") from e
                        
                except Exception as e:
                    logger.error(f"Unexpected error sending command: {e}", exc_info=True)
                    raise CommandError(f"Failed to send command: {e}") from e
            
            # Should not reach here, but just in case
            if last_error:
                raise CommandError(f"Failed to send command after {max_retries} attempts: {last_error}") from last_error
    
    def set_frequency(self, ssrc: int, frequency_hz: float):
        """
        Set the frequency of a channel
        
        Args:
            ssrc: SSRC of the channel
            frequency_hz: Frequency in Hz
        
        Raises:
            ValidationError: If parameters are invalid
        """
        _validate_ssrc(ssrc)
        _validate_frequency(frequency_hz)
        
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
        
        Raises:
            ValidationError: If parameters are invalid
        """
        _validate_ssrc(ssrc)
        _validate_sample_rate(sample_rate)
        
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
        
        Raises:
            ValidationError: If parameters are invalid
        """
        _validate_ssrc(ssrc)
        _validate_gain(gain_db)
        
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
    
    def create_channel(self, ssrc: int, frequency_hz: float, 
                       preset: str = "iq", sample_rate: Optional[int] = None,
                       agc_enable: int = 0, gain: float = 0.0):
        """
        Create and configure a new radiod channel
        
        This sends all parameters in a single packet to radiod, which creates
        the channel when it receives the first command for a new SSRC.
        
        Args:
            ssrc: Channel identifier (0 to 4294967295). Convention is to use
                  frequency in Hz as SSRC (e.g., 14074000 for 14.074 MHz)
            frequency_hz: RF frequency in Hz (typically 0 to 6 GHz for HF/VHF/UHF,
                         depends on your SDR hardware)
            preset: Demodulation mode (default: "iq" for linear/IQ mode)
                    Common values: "iq", "usb", "lsb", "am", "fm", "cw"
            sample_rate: Output sample rate in Hz (optional, radiod uses default if None)
                        Typical values: 12000, 48000, 16000
            agc_enable: Automatic Gain Control (0=disabled/manual gain, 1=enabled)
                       Default: 0 (manual gain mode)
            gain: Manual gain in dB, used when agc_enable=0 (default: 0.0)
                  Typical range: -60 to +60 dB
        
        Raises:
            ValidationError: If parameters are out of valid ranges
            CommandError: If command fails to send
            RuntimeError: If not connected to radiod
        
        Example:
            >>> control = RadiodControl("radiod.local")
            >>> control.create_channel(
            ...     ssrc=14074000,
            ...     frequency_hz=14.074e6,
            ...     preset="usb",
            ...     sample_rate=12000
            ... )
        """
        # Validate inputs
        _validate_ssrc(ssrc)
        _validate_frequency(frequency_hz)
        if sample_rate is not None:
            _validate_sample_rate(sample_rate)
        _validate_gain(gain)
        
        logger.info(f"Creating channel: SSRC={ssrc}, freq={frequency_hz/1e6:.3f} MHz, "
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
        demod_type = 0 if preset.lower() in ['iq', 'usb', 'lsb', 'cw', 'am'] else 1
        encode_int(cmdbuffer, StatusType.DEMOD_TYPE, demod_type)
        logger.info(f"Setting DEMOD_TYPE for SSRC {ssrc} to {demod_type}")
        
        # Frequency
        encode_double(cmdbuffer, StatusType.RADIO_FREQUENCY, frequency_hz)
        logger.info(f"Setting frequency for SSRC {ssrc} to {frequency_hz/1e6:.3f} MHz")
        
        # Sample rate
        if sample_rate:
            encode_int(cmdbuffer, StatusType.OUTPUT_SAMPRATE, sample_rate)
            logger.info(f"Setting sample rate for SSRC {ssrc} to {sample_rate} Hz")
        
        # AGC setting
        encode_int(cmdbuffer, StatusType.AGC_ENABLE, agc_enable)
        logger.info(f"Setting AGC_ENABLE for SSRC {ssrc} to {agc_enable}")
        
        # Gain setting
        encode_double(cmdbuffer, StatusType.GAIN, gain)
        logger.info(f"Setting GAIN for SSRC {ssrc} to {gain} dB")
        
        # SSRC and command tag
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, random.randint(1, 2**31))
        encode_eol(cmdbuffer)
        
        # Send the single packet
        self.send_command(cmdbuffer)
        
        logger.info(f"Channel {ssrc} created and configured")
    
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
    
    def _setup_status_listener(self):
        """Set up socket to listen for status responses"""
        # Create a separate socket for receiving status messages
        status_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        status_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set SO_REUSEPORT to allow multiple processes to bind (if available)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                status_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                logger.debug("SO_REUSEPORT enabled")
            except OSError as e:
                logger.warning(f"Could not set SO_REUSEPORT: {e}")
        
        # CRITICAL: Must bind to the multicast port (5006) to receive multicast packets
        # Multicast packets are addressed to specific port, not just IP
        # Use 0.0.0.0 and SO_REUSEADDR to allow multiple processes
        try:
            status_sock.bind(('0.0.0.0', 5006))  # Bind to radiod status port on all interfaces
            bound_port = status_sock.getsockname()[1]
            logger.debug(f"Bound to port {bound_port} for multicast reception")
        except OSError as e:
            logger.error(f"Failed to bind socket: {e}")
            raise
        
        # Join the multicast group on any interface
        # Use the status multicast address (where status packets are sent)
        mreq = struct.pack('=4s4s', 
                          socket.inet_aton(self.status_mcast_addr),  # status multicast group
                          socket.inet_aton('0.0.0.0'))  # any interface (INADDR_ANY)
        status_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        logger.debug(f"Joined status multicast group {self.status_mcast_addr} for status listening")
        
        # Set timeout for polling
        status_sock.settimeout(0.1)  # 100ms timeout
        
        return status_sock
    
    def _get_or_create_status_listener(self):
        """
        Get cached status listener socket or create new one if needed.
        
        This method implements socket reuse to avoid creating/destroying sockets
        on every tune() call, which saves 20-30ms per operation and prevents
        socket exhaustion.
        
        Returns:
            Cached or newly created status listener socket
        """
        import threading
        
        # Lazy initialization of lock (avoid threading overhead if never used)
        if self._status_sock_lock is None:
            self._status_sock_lock = threading.Lock()
        
        with self._status_sock_lock:
            if self._status_sock is None:
                logger.debug("Creating cached status listener socket")
                self._status_sock = self._setup_status_listener()
            else:
                logger.debug("Reusing cached status listener socket")
            return self._status_sock
    
    def tune(self, ssrc: int, frequency_hz: Optional[float] = None, 
             preset: Optional[str] = None, sample_rate: Optional[int] = None,
             low_edge: Optional[float] = None, high_edge: Optional[float] = None,
             gain: Optional[float] = None, agc_enable: Optional[bool] = None,
             rf_gain: Optional[float] = None, rf_atten: Optional[float] = None,
             encoding: Optional[int] = None, destination: Optional[str] = None,
             timeout: float = 5.0) -> dict:
        """
        Tune a channel and retrieve its status (like tune.c in ka9q-radio)
        
        This method sends tuning commands to radiod and waits for a status response,
        replicating the functionality of the tune utility in ka9q-radio.
        
        Args:
            ssrc: SSRC of the channel to tune
            frequency_hz: Frequency in Hz (optional)
            preset: Preset/mode name (optional, e.g., "iq", "usb", "lsb")
            sample_rate: Sample rate in Hz (optional)
            low_edge: Low filter edge in Hz (optional)
            high_edge: High filter edge in Hz (optional)
            gain: Manual gain in dB (optional, disables AGC)
            agc_enable: Enable AGC (optional)
            rf_gain: RF front-end gain in dB (optional)
            rf_atten: RF front-end attenuation in dB (optional)
            encoding: Output encoding type (optional, use Encoding constants)
            destination: Destination multicast address (optional)
            timeout: Maximum time to wait for response in seconds (default: 5.0)
            
        Returns:
            Dictionary containing channel status with keys:
            - ssrc: Channel SSRC
            - frequency: Radio frequency in Hz
            - preset: Mode/preset name
            - sample_rate: Sample rate in Hz
            - agc_enable: AGC enabled status
            - gain: Current gain in dB
            - rf_gain: RF gain in dB
            - rf_atten: RF attenuation in dB
            - rf_agc: RF AGC status
            - low_edge: Low filter edge in Hz
            - high_edge: High filter edge in Hz
            - noise_density: Noise density in dB/Hz
            - baseband_power: Baseband power in dB
            - encoding: Output encoding type
            - destination: Destination socket address
            - snr: Signal-to-noise ratio in dB (calculated)
        
        Raises:
            TimeoutError: If no matching response received within timeout
        """
        # Validate inputs
        _validate_ssrc(ssrc)
        if frequency_hz is not None:
            _validate_frequency(frequency_hz)
        if sample_rate is not None:
            _validate_sample_rate(sample_rate)
        if gain is not None:
            _validate_gain(gain)
        _validate_timeout(timeout)
        
        import time
        import select
        
        # Build command packet with all specified parameters
        cmdbuffer = bytearray()
        cmdbuffer.append(CMD)
        
        # Generate command tag for matching response
        command_tag = random.randint(1, 2**31)
        encode_int(cmdbuffer, StatusType.COMMAND_TAG, command_tag)
        encode_int(cmdbuffer, StatusType.OUTPUT_SSRC, ssrc)
        
        if preset is not None:
            encode_string(cmdbuffer, StatusType.PRESET, preset)
        
        if sample_rate is not None:
            encode_int(cmdbuffer, StatusType.OUTPUT_SAMPRATE, sample_rate)
        
        if low_edge is not None:
            encode_float(cmdbuffer, StatusType.LOW_EDGE, low_edge)
        
        if high_edge is not None:
            encode_float(cmdbuffer, StatusType.HIGH_EDGE, high_edge)
        
        if frequency_hz is not None:
            encode_double(cmdbuffer, StatusType.RADIO_FREQUENCY, frequency_hz)
        
        if gain is not None:
            encode_float(cmdbuffer, StatusType.GAIN, gain)
            encode_int(cmdbuffer, StatusType.AGC_ENABLE, 0)  # Turn off AGC for manual gain
        elif agc_enable is not None:
            encode_int(cmdbuffer, StatusType.AGC_ENABLE, 1 if agc_enable else 0)
        
        if encoding is not None:
            encode_int(cmdbuffer, StatusType.OUTPUT_ENCODING, encoding)
        
        if rf_gain is not None:
            encode_float(cmdbuffer, StatusType.RF_GAIN, rf_gain)
        
        if rf_atten is not None:
            encode_float(cmdbuffer, StatusType.RF_ATTEN, rf_atten)
        
        if destination is not None:
            # Parse destination address (simplified - would need full socket encoding)
            logger.warning("Destination socket encoding not fully implemented")
        
        encode_eol(cmdbuffer)
        
        # Get cached status listener (or create if first use)
        # Socket is reused across tune() calls to avoid creation/destruction overhead
        status_sock = self._get_or_create_status_listener()
        
        try:
            start_time = time.time()
            last_send_time = 0
            retry_interval = 0.1  # Start at 100ms
            max_retry_interval = 1.0  # Cap at 1 second
            attempts = 0
            
            while time.time() - start_time < timeout:
                # Send command with exponential backoff
                current_time = time.time()
                if current_time - last_send_time >= retry_interval:
                    self.send_command(cmdbuffer)
                    last_send_time = current_time
                    attempts += 1
                    logger.debug(f"Sent tune command with tag {command_tag} (attempt {attempts})")
                    
                    # Exponential backoff: 100ms, 200ms, 400ms, 800ms, 1000ms (capped)
                    # This reduces network spam and CPU usage significantly
                    retry_interval = min(retry_interval * 2, max_retry_interval)
                
                # Check for incoming status messages with adaptive timeout
                try:
                    # Use remaining time or retry interval, whichever is smaller
                    remaining = timeout - (time.time() - start_time)
                    select_timeout = min(retry_interval, remaining, 0.5)
                    
                    ready = select.select([status_sock], [], [], select_timeout)
                    if not ready[0]:
                        logger.debug(f"select() timed out after {select_timeout:.3f}s, no packets received")
                        continue
                    
                    response_buffer, addr = status_sock.recvfrom(8192)
                    logger.debug(f"Received {len(response_buffer)} bytes from {addr}")
                    logger.debug(f"First 16 bytes: {' '.join(f'{b:02x}' for b in response_buffer[:16])}")
                    
                    # Parse response
                    if len(response_buffer) == 0 or response_buffer[0] != 0:
                        continue  # Not a status response
                    
                    # Decode the response
                    status = self._decode_status_response(response_buffer)
                    
                    # Check if this response is for our command
                    if status.get('ssrc') == ssrc and status.get('command_tag') == command_tag:
                        logger.info(f"Received matching status response for SSRC {ssrc}")
                        return status
                    else:
                        logger.debug(f"Response not for us: ssrc={status.get('ssrc')}, tag={status.get('command_tag')}")
                
                except socket.timeout:
                    continue
            
            raise TimeoutError(f"No status response received for SSRC {ssrc} within {timeout}s")
        
        finally:
            # NOTE: Do NOT close status_sock here - it's cached for reuse
            # Socket will be closed in close() method
            pass
    
    def _decode_status_response(self, buffer: bytes) -> dict:
        """
        Decode a status response packet from radiod
        
        Args:
            buffer: Raw response bytes
            
        Returns:
            Dictionary containing decoded status fields
        """
        status = {}
        
        if len(buffer) == 0 or buffer[0] != 0:
            return status  # Not a status response
        
        cp = 1  # Skip packet type byte
        
        while cp < len(buffer):
            if cp >= len(buffer):
                break
            
            type_val = buffer[cp]
            cp += 1
            
            if type_val == StatusType.EOL:
                break
            
            if cp >= len(buffer):
                break
            
            optlen = buffer[cp]
            cp += 1
            
            # Handle extended length encoding
            if optlen & 0x80:
                length_of_length = optlen & 0x7f
                optlen = 0
                for _ in range(length_of_length):
                    if cp >= len(buffer):
                        break
                    optlen = (optlen << 8) | buffer[cp]
                    cp += 1
            
            if cp + optlen > len(buffer):
                break
            
            data = buffer[cp:cp + optlen]
            
            # Decode based on type
            if type_val == StatusType.COMMAND_TAG:
                status['command_tag'] = decode_int32(data, optlen)
            elif type_val == StatusType.RADIO_FREQUENCY:
                status['frequency'] = decode_double(data, optlen)
            elif type_val == StatusType.OUTPUT_SSRC:
                status['ssrc'] = decode_int32(data, optlen)
            elif type_val == StatusType.AGC_ENABLE:
                status['agc_enable'] = decode_bool(data, optlen)
            elif type_val == StatusType.GAIN:
                status['gain'] = decode_float(data, optlen)
            elif type_val == StatusType.RF_GAIN:
                status['rf_gain'] = decode_float(data, optlen)
            elif type_val == StatusType.RF_ATTEN:
                status['rf_atten'] = decode_float(data, optlen)
            elif type_val == StatusType.RF_AGC:
                status['rf_agc'] = decode_int(data, optlen)
            elif type_val == StatusType.PRESET:
                status['preset'] = decode_string(data, optlen)
            elif type_val == StatusType.LOW_EDGE:
                status['low_edge'] = decode_float(data, optlen)
            elif type_val == StatusType.HIGH_EDGE:
                status['high_edge'] = decode_float(data, optlen)
            elif type_val == StatusType.NOISE_DENSITY:
                status['noise_density'] = decode_float(data, optlen)
            elif type_val == StatusType.BASEBAND_POWER:
                status['baseband_power'] = decode_float(data, optlen)
            elif type_val == StatusType.OUTPUT_SAMPRATE:
                status['sample_rate'] = decode_int(data, optlen)
            elif type_val == StatusType.OUTPUT_ENCODING:
                status['encoding'] = decode_int(data, optlen)
            elif type_val == StatusType.OUTPUT_DATA_DEST_SOCKET:
                status['destination'] = decode_socket(data, optlen)
            
            cp += optlen
        
        # Calculate SNR if we have the necessary data
        if all(k in status for k in ['baseband_power', 'low_edge', 'high_edge', 'noise_density']):
            import math
            bandwidth = abs(status['high_edge'] - status['low_edge'])
            
            # Guard against invalid bandwidth
            if bandwidth > 0:
                try:
                    noise_power_db = status['noise_density'] + 10 * math.log10(bandwidth)
                    signal_plus_noise_db = status['baseband_power']
                    # Convert to linear, calculate SNR, convert back to dB
                    noise_power = 10 ** (noise_power_db / 10)
                    signal_plus_noise = 10 ** (signal_plus_noise_db / 10)
                    
                    # Guard against division by zero
                    if noise_power > 0:
                        snr_linear = signal_plus_noise / noise_power - 1
                        if snr_linear > 0:
                            status['snr'] = 10 * math.log10(snr_linear)
                except (ValueError, ZeroDivisionError, OverflowError):
                    # SNR calculation failed, skip it
                    pass
        
        return status
    
    def close(self):
        """
        Close all sockets with proper error handling
        
        This method is safe to call multiple times and handles errors gracefully.
        """
        errors = []
        
        # Close control socket
        if self.socket:
            try:
                self.socket.close()
                logger.debug("Control socket closed")
            except Exception as e:
                errors.append(f"control socket: {e}")
            finally:
                self.socket = None
        
        # Close cached status listener socket
        if self._status_sock:
            try:
                logger.debug("Closing cached status listener socket")
                self._status_sock.close()
            except Exception as e:
                errors.append(f"status socket: {e}")
            finally:
                self._status_sock = None
        
        if errors:
            error_msg = "; ".join(errors)
            logger.warning(f"Errors during socket cleanup: {error_msg}")

