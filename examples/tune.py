#!/usr/bin/env python3
"""
Interactive program to tune radiod in ka9q-radio
Python implementation of tune.c from ka9q-radio
Copyright 2024 - Based on tune.c by Phil Karn, KA9Q

Usage:
    tune.py -r radiod.local -s 12345678 -f 14.074e6 -m usb
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path for ka9q imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ka9q import RadiodControl
from ka9q.types import Encoding

logger = logging.getLogger(__name__)


def parse_frequency(freq_str):
    """
    Parse frequency string with optional suffixes (k, M, G)
    
    Args:
        freq_str: Frequency string (e.g., "14.074M", "146.52k", "10e6")
        
    Returns:
        Frequency in Hz as float
    """
    freq_str = freq_str.strip().upper()
    
    # Handle suffixes
    multipliers = {
        'K': 1e3,
        'M': 1e6,
        'G': 1e9,
    }
    
    for suffix, mult in multipliers.items():
        if freq_str.endswith(suffix):
            return float(freq_str[:-1]) * mult
    
    # No suffix, just parse as float
    return float(freq_str)


def encoding_from_string(enc_str):
    """
    Parse encoding string to Encoding constant
    
    Args:
        enc_str: Encoding string (e.g., "S16BE", "OPUS", "F32")
        
    Returns:
        Encoding constant
    """
    enc_str = enc_str.upper()
    
    encoding_map = {
        'S16BE': Encoding.S16BE,
        'S16LE': Encoding.S16LE,
        'F32': Encoding.F32,
        'F16': Encoding.F16,
        'OPUS': Encoding.OPUS,
    }
    
    if enc_str in encoding_map:
        return encoding_map[enc_str]
    
    print(f"Unknown encoding: {enc_str}")
    print(f"Available encodings: {', '.join(encoding_map.keys())}")
    return None


def format_frequency(freq_hz):
    """Format frequency for display"""
    if freq_hz >= 1e9:
        return f"{freq_hz/1e9:.6f} GHz"
    elif freq_hz >= 1e6:
        return f"{freq_hz/1e6:.6f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz/1e3:.3f} kHz"
    else:
        return f"{freq_hz:.1f} Hz"


def format_socket(socket_dict):
    """Format socket address for display"""
    if socket_dict and 'address' in socket_dict:
        return f"{socket_dict['address']}:{socket_dict['port']}"
    return "N/A"


def main():
    parser = argparse.ArgumentParser(
        description='Tune radiod channel (Python implementation of ka9q-radio tune utility)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create USB channel on 14.074 MHz
  %(prog)s -r radiod.local -s 12345678 -f 14.074M -m usb
  
  # Create IQ channel with custom sample rate
  %(prog)s -r radiod.local -s 10000000 -f 10M -m iq -R 48000
  
  # Set manual gain (disables AGC)
  %(prog)s -r radiod.local -s 12345678 -f 7.040M -m lsb -g 20
  
  # Enable AGC
  %(prog)s -r radiod.local -s 12345678 -a
""")
    
    parser.add_argument('-r', '--radio', required=True,
                        help='Radiod status address (mDNS name or IP:port)')
    parser.add_argument('-s', '--ssrc', required=True, type=lambda x: int(x, 0),
                        help='SSRC identifier (decimal or hex with 0x prefix)')
    parser.add_argument('-f', '--frequency', type=str,
                        help='Radio frequency (Hz, or with k/M/G suffix)')
    parser.add_argument('-m', '--mode', '--preset', dest='preset',
                        help='Preset/mode name (e.g., iq, usb, lsb, am, fm)')
    parser.add_argument('-R', '--samprate', type=int,
                        help='Sample rate in Hz')
    parser.add_argument('-L', '--low', type=str,
                        help='Low filter edge (Hz, or with k/M suffix)')
    parser.add_argument('-H', '--high', type=str,
                        help='High filter edge (Hz, or with k/M suffix)')
    parser.add_argument('-g', '--gain', type=float,
                        help='Manual gain in dB (disables AGC)')
    parser.add_argument('-a', '--agc', action='store_true',
                        help='Enable AGC')
    parser.add_argument('-G', '--rfgain', '--fegain', dest='rf_gain', type=float,
                        help='RF front-end gain in dB')
    parser.add_argument('-A', '--rfatten', '--featten', dest='rf_atten', type=float,
                        help='RF front-end attenuation in dB')
    parser.add_argument('-e', '--encoding', type=str,
                        help='Output encoding (S16BE, S16LE, F32, F16, OPUS)')
    parser.add_argument('-D', '--destination', type=str,
                        help='Destination multicast address')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Quiet mode - suppress status output')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Verbose mode (repeat for more verbosity)')
    parser.add_argument('-V', '--version', action='version', version='%(prog)s 1.0.0')
    parser.add_argument('-t', '--timeout', type=float, default=5.0,
                        help='Timeout for response in seconds (default: 5.0)')
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose >= 2:
        log_level = logging.DEBUG
    elif args.verbose == 1:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Parse frequency arguments
    frequency_hz = None
    if args.frequency:
        try:
            frequency_hz = parse_frequency(args.frequency)
        except ValueError as e:
            print(f"Error parsing frequency: {e}", file=sys.stderr)
            return 1
    
    low_edge = None
    if args.low:
        try:
            low_edge = parse_frequency(args.low)
        except ValueError as e:
            print(f"Error parsing low edge: {e}", file=sys.stderr)
            return 1
    
    high_edge = None
    if args.high:
        try:
            high_edge = parse_frequency(args.high)
        except ValueError as e:
            print(f"Error parsing high edge: {e}", file=sys.stderr)
            return 1
    
    # Parse encoding
    encoding = None
    if args.encoding:
        encoding = encoding_from_string(args.encoding)
        if encoding is None:
            return 1
    
    # Connect to radiod
    try:
        control = RadiodControl(args.radio)
    except Exception as e:
        print(f"Error connecting to radiod at {args.radio}: {e}", file=sys.stderr)
        return 1
    
    # Send tune command and receive status
    try:
        status = control.tune(
            ssrc=args.ssrc,
            frequency_hz=frequency_hz,
            preset=args.preset,
            sample_rate=args.samprate,
            low_edge=low_edge,
            high_edge=high_edge,
            gain=args.gain,
            agc_enable=args.agc,
            rf_gain=args.rf_gain,
            rf_atten=args.rf_atten,
            encoding=encoding,
            destination=args.destination,
            timeout=args.timeout
        )
    except TimeoutError as e:
        print(f"Timeout: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error tuning channel: {e}", file=sys.stderr)
        return 1
    finally:
        control.close()
    
    # Display status unless quiet mode
    if not args.quiet:
        print(f"SSRC {args.ssrc}")
        
        if 'preset' in status:
            print(f"Preset: {status['preset']}")
        
        if 'sample_rate' in status:
            print(f"Sample rate: {status['sample_rate']:,} Hz")
        
        if 'destination' in status:
            print(f"Destination socket: {format_socket(status['destination'])}")
        
        if 'encoding' in status:
            enc_names = {0: 'None', 1: 'S16BE', 2: 'S16LE', 3: 'F32', 4: 'F16', 5: 'OPUS'}
            enc_name = enc_names.get(status['encoding'], f"Unknown({status['encoding']})")
            print(f"Encoding: {enc_name}")
        
        if 'frequency' in status:
            print(f"Frequency: {format_frequency(status['frequency'])}")
        
        if 'agc_enable' in status:
            print(f"Channel AGC: {'on' if status['agc_enable'] else 'off'}")
        
        if 'gain' in status:
            print(f"Channel Gain: {status['gain']:.1f} dB")
        
        if 'rf_agc' in status:
            print(f"RF AGC: {'on' if status['rf_agc'] else 'off'}")
        
        if 'rf_gain' in status:
            print(f"RF Gain: {status['rf_gain']:.1f} dB")
        
        if 'rf_atten' in status:
            print(f"RF Atten: {status['rf_atten']:.1f} dB")
        
        if 'baseband_power' in status:
            print(f"Baseband power: {status['baseband_power']:.1f} dB")
        
        if 'low_edge' in status and 'high_edge' in status:
            import math
            bandwidth = abs(status['high_edge'] - status['low_edge'])
            print(f"Passband: {status['low_edge']:.1f} Hz to {status['high_edge']:.1f} Hz ({10*math.log10(bandwidth):.1f} dB-Hz)")
        
        if 'noise_density' in status:
            print(f"N0: {status['noise_density']:.1f} dB/Hz")
        
        if 'snr' in status:
            print(f"SNR: {status['snr']:.1f} dB")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
