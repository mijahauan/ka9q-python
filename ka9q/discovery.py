"""
Stream discovery using ka9q-radio control utility

This module uses the 'control' utility from ka9q-radio to discover
active channels and their SSRCs, frequencies, and multicast addresses.
"""

import subprocess
import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

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


def discover_channels(status_address: str, timeout: float = 30.0) -> Dict[int, ChannelInfo]:
    """
    Discover channels using the 'control' utility
    
    Args:
        status_address: Status multicast address (e.g., "bee1-hf-status.local")
        timeout: Timeout for control command
        
    Returns:
        Dictionary mapping SSRC to ChannelInfo
    """
    logger.info(f"Discovering channels via control utility from {status_address}")
    
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



def discover_radiod_services():
    """
    Discover all radiod services on the network via mDNS
    
    Returns:
        List of dicts with "name" and "address" keys
    """
    import subprocess
    import re
    
    services = []
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
                    name = parts[3]
                    address = parts[7]
                    services.append({"name": name, "address": address})
    except Exception as e:
        logger.warning(f"Failed to discover radiod services: {e}")
    
    return services

