#!/usr/bin/env python3
"""
Spectrum display example — receive real-time FFT data from radiod.

Prints per-frame statistics: bin count, center frequency, resolution
bandwidth, peak power, and noise floor. Demonstrates SpectrumStream,
which receives spectrum data via the status multicast channel (not RTP).

Usage:
    python3 spectrum_example.py HOST [--freq HZ] [--bins N] [--rbw HZ]
                                     [--duration SEC]

Example:
    python3 spectrum_example.py bee1-hf-status.local --freq 14.1e6
    python3 spectrum_example.py bee1-hf-status.local --freq 7.0e6 --bins 2048 --rbw 25
"""

import argparse
import sys
import time

import numpy as np

from ka9q import RadiodControl, SpectrumStream


def bin_frequencies(center_hz: float, bin_count: int, resolution_bw: float):
    """Build a frequency axis (Hz) from spectrum metadata."""
    bins = np.arange(bin_count)
    offsets = np.where(bins <= bin_count // 2, bins, bins - bin_count)
    return center_hz + offsets * resolution_bw


def main():
    parser = argparse.ArgumentParser(
        description="Receive real-time spectrum data from radiod"
    )
    parser.add_argument("host", help="radiod status address (e.g. bee1-hf-status.local)")
    parser.add_argument("--freq", type=float, default=14.1e6,
                        help="Center frequency in Hz (default: 14.1 MHz)")
    parser.add_argument("--bins", type=int, default=1024,
                        help="Number of FFT bins (default: 1024)")
    parser.add_argument("--rbw", type=float, default=100.0,
                        help="Resolution bandwidth in Hz (default: 100)")
    parser.add_argument("--duration", type=float, default=30.0,
                        help="How long to run in seconds (default: 30)")
    parser.add_argument("--averaging", type=int, default=None,
                        help="Number of FFTs to average per frame")
    parser.add_argument("--interface", type=str, default=None,
                        help="Network interface IP for multicast")
    args = parser.parse_args()

    frame_count = 0

    def on_spectrum(status):
        nonlocal frame_count
        frame_count += 1

        db = status.spectrum.bin_power_db
        if db is None:
            print(f"  frame {frame_count}: no bin data")
            return

        freq_mhz = (status.frequency or 0) / 1e6
        rbw = status.spectrum.resolution_bw or args.rbw
        n = len(db)

        # Find peak bin and its frequency
        peak_idx = int(np.argmax(db))
        freqs = bin_frequencies(status.frequency or args.freq, n, rbw)
        peak_freq_mhz = freqs[peak_idx] / 1e6

        print(
            f"  frame {frame_count:4d}: "
            f"{n} bins @ {freq_mhz:.3f} MHz, "
            f"RBW {rbw:.1f} Hz, "
            f"peak {db[peak_idx]:.1f} dB at {peak_freq_mhz:.4f} MHz, "
            f"floor {db.min():.1f} dB"
        )

    print(f"Connecting to {args.host}...")
    with RadiodControl(args.host, interface=args.interface) as ctl:
        print(f"Starting spectrum stream: {args.freq/1e6:.3f} MHz, "
              f"{args.bins} bins, {args.rbw} Hz/bin")

        kwargs = {}
        if args.averaging is not None:
            kwargs["averaging"] = args.averaging

        with SpectrumStream(
            control=ctl,
            frequency_hz=args.freq,
            bin_count=args.bins,
            resolution_bw=args.rbw,
            on_spectrum=on_spectrum,
            **kwargs,
        ) as stream:
            print(f"SSRC: {stream.ssrc}")
            print(f"Receiving for {args.duration} seconds...\n")
            try:
                time.sleep(args.duration)
            except KeyboardInterrupt:
                print("\nInterrupted.")

        print(f"\nDone. {frame_count} frames received.")


if __name__ == "__main__":
    main()
