"""
BPSK PPS chain-delay calibrator for ka9q-radio RTP streams

Detects Pulse-Per-Second edges in a BPSK-modulated IQ signal injected into
the RF front-end by a local GPS-disciplined transmitter (e.g., WB6CXC PPS
injector).  The measured edge positions quantify the end-to-end latency
through the RF -> ADC -> DSP -> RTP chain, producing a correction that
rtp_to_wallclock() can apply to all channels on the same radiod instance.

Algorithm ported from Scott Newell's wd-record.c bpsk_state_machine().

Usage:
    from ka9q.pps_calibrator import BpskPpsCalibrator

    cal = BpskPpsCalibrator(sample_rate=24000)

    def on_samples(samples, quality):
        result = cal.process_samples(samples, quality.last_rtp_timestamp)
        if result is not None:
            # result.chain_delay_ns is the measured delay
            for ch in other_channels:
                ch.chain_delay_correction_ns = result.chain_delay_ns

Requires: numpy
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

__all__ = ['BpskPpsCalibrator', 'PpsCalibrationResult', 'NotchFilter500Hz']


@dataclass
class PpsCalibrationResult:
    """Result from a successful PPS calibration measurement."""
    chain_delay_ns: int        # Measured chain delay (nanoseconds)
    chain_delay_samples: float # Measured chain delay (fractional samples)
    pps_ok: int                # Cumulative valid edge count
    pps_noise: int             # Cumulative noise/rejected edge count
    pps_consecutive: int       # Current consecutive valid edge streak
    locked: bool               # True when consecutive >= lock threshold


class NotchFilter500Hz:
    """
    Biquad IIR notch filter at 500 Hz.

    Direct form II transposed, matching wd-record's notch500 implementation.
    Pole radius 0.99 gives a narrow notch (~10 Hz at 24 kHz sample rate).
    """

    def __init__(self, sample_rate: int, pole_radius: float = 0.99):
        w0 = 2.0 * np.pi * 500.0 / sample_rate
        c = np.cos(w0)

        # Numerator (zeros on unit circle at w0)
        self.b0 = 1.0
        self.b1 = -2.0 * c
        self.b2 = 1.0

        # Denominator (poles at radius r, angle w0)
        self.a1 = -2.0 * pole_radius * c
        self.a2 = pole_radius * pole_radius

        # Filter state (I and Q processed independently)
        self._state_i = np.zeros(2, dtype=np.float64)  # [x1, x2] not needed; use y1,y2
        self._xi1 = 0.0
        self._xi2 = 0.0
        self._yi1 = 0.0
        self._yi2 = 0.0
        self._xq1 = 0.0
        self._xq2 = 0.0
        self._yq1 = 0.0
        self._yq2 = 0.0

    def process(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        Apply notch filter to complex IQ samples.

        Filters I and Q channels independently, matching wd-record behavior.
        Processes sample-by-sample to maintain state across calls.
        """
        out = np.empty_like(iq_samples)
        i_in = iq_samples.real.astype(np.float64)
        q_in = iq_samples.imag.astype(np.float64)

        b0, b1, b2 = self.b0, self.b1, self.b2
        a1, a2 = self.a1, self.a2

        # Unpack state for speed in the loop
        xi1, xi2, yi1, yi2 = self._xi1, self._xi2, self._yi1, self._yi2
        xq1, xq2, yq1, yq2 = self._xq1, self._xq2, self._yq1, self._yq2

        i_out = np.empty(len(iq_samples), dtype=np.float64)
        q_out = np.empty(len(iq_samples), dtype=np.float64)

        for n in range(len(iq_samples)):
            x_i = i_in[n]
            y_i = b0 * x_i + b1 * xi1 + b2 * xi2 - a1 * yi1 - a2 * yi2
            xi2, xi1 = xi1, x_i
            yi2, yi1 = yi1, y_i
            i_out[n] = y_i

            x_q = q_in[n]
            y_q = b0 * x_q + b1 * xq1 + b2 * xq2 - a1 * yq1 - a2 * yq2
            xq2, xq1 = xq1, x_q
            yq2, yq1 = yq1, y_q
            q_out[n] = y_q

        # Save state
        self._xi1, self._xi2, self._yi1, self._yi2 = xi1, xi2, yi1, yi2
        self._xq1, self._xq2, self._yq1, self._yq2 = xq1, xq2, yq1, yq2

        out = (i_out + 1j * q_out).astype(np.complex64)
        return out


class BpskPpsCalibrator:
    """
    Detects PPS edges in a BPSK IQ stream and measures RF chain delay.

    The injector produces a BPSK signal whose phase flips 180 degrees on
    each UTC second boundary.  This class detects those phase transitions
    in the IQ sample stream and measures where they fall relative to the
    RTP timestamp grid, yielding the end-to-end chain delay.

    Parameters
    ----------
    sample_rate : int
        Sample rate of the BPSK IQ channel (Hz).
    consecutive_required : int
        Number of consecutive valid PPS edges required before declaring
        lock and reporting a calibration result.  Default 10 matches
        wd-record.
    edge_tolerance_samples : int
        Maximum deviation (samples) of a detected edge from its expected
        position within the second.  Default 10 matches wd-record.
    min_pulse_fraction : float
        Minimum fraction of one second between consecutive edges.
        Edges closer than this are rejected as noise.  Default 0.99.
    enable_notch_500hz : bool
        Apply a 500 Hz notch filter before edge detection.
    """

    def __init__(
        self,
        sample_rate: int,
        consecutive_required: int = 10,
        edge_tolerance_samples: int = 10,
        min_pulse_fraction: float = 0.99,
        enable_notch_500hz: bool = False,
    ):
        self.sample_rate = sample_rate
        self.consecutive_required = consecutive_required
        self.edge_tolerance_samples = edge_tolerance_samples
        self.min_pulse_samples = int(sample_rate * min_pulse_fraction)

        # Edge detection state
        self._last_angle: Optional[float] = None
        self._last_edge_offset: Optional[int] = None  # sample offset within second
        self._last_edge_rtp: Optional[int] = None      # absolute RTP timestamp of last edge
        self._sample_counter: int = 0                   # running count for RTP reconstruction

        # Counters (match wd-record globals)
        self.pps_ok: int = 0
        self.pps_noise: int = 0
        self.pps_consecutive: int = 0

        # Result: measured chain delay as fractional samples from second boundary
        self._chain_delay_samples: Optional[float] = None

        # Optional notch filter
        self._notch: Optional[NotchFilter500Hz] = None
        if enable_notch_500hz:
            self._notch = NotchFilter500Hz(sample_rate)

    @property
    def locked(self) -> bool:
        """True when enough consecutive valid edges have been detected."""
        return self.pps_consecutive >= self.consecutive_required

    def reset(self):
        """Reset all state. Call if the stream is restarted."""
        self._last_angle = None
        self._last_edge_offset = None
        self._last_edge_rtp = None
        self._sample_counter = 0
        self.pps_ok = 0
        self.pps_noise = 0
        self.pps_consecutive = 0
        self._chain_delay_samples = None
        if self._notch is not None:
            self._notch = NotchFilter500Hz(self.sample_rate)

    def process_samples(
        self, iq_samples: np.ndarray, rtp_timestamp: int
    ) -> Optional[PpsCalibrationResult]:
        """
        Process a batch of complex IQ samples and detect PPS edges.

        Parameters
        ----------
        iq_samples : np.ndarray
            Complex64 IQ samples from the BPSK channel.
        rtp_timestamp : int
            RTP timestamp of the first sample in this batch.

        Returns
        -------
        PpsCalibrationResult or None
            Returns a result when locked (consecutive valid edges >=
            threshold).  Returns None while still acquiring.
        """
        if len(iq_samples) == 0:
            return None

        samples = iq_samples.astype(np.complex64)

        # Apply optional notch filter
        if self._notch is not None:
            samples = self._notch.process(samples)

        # Compute per-sample phase angle in degrees
        angles = np.degrees(np.angle(samples))

        sr = self.sample_rate

        for i in range(len(angles)):
            angle = angles[i]
            # RTP timestamp for this specific sample
            ts = (rtp_timestamp + i) & 0xFFFFFFFF

            if self._last_angle is not None:
                # Phase difference between consecutive samples
                angle_diff = angle - self._last_angle
                # Wrap to [-360, 360] -- not strictly necessary but matches
                # the C code's fabs() comparison range
                if angle_diff > 360.0:
                    angle_diff -= 360.0
                elif angle_diff < -360.0:
                    angle_diff += 360.0

                abs_diff = abs(angle_diff)

                # Edge detected: phase transition between 90 and 270 degrees
                if 90.0 < abs_diff < 270.0:
                    noisy = False

                    # Check 1: edge position within the second should be
                    # consistent (within tolerance of last edge's position)
                    if self._last_edge_rtp is not None:
                        current_offset = ts % sr
                        expected_offset = self._last_edge_rtp % sr
                        delta = _signed_mod(
                            current_offset - expected_offset, sr
                        )
                        if abs(delta) > self.edge_tolerance_samples:
                            noisy = True

                        # Check 2: edges must be at least min_pulse_fraction
                        # of one second apart
                        rtp_gap = (ts - self._last_edge_rtp) & 0xFFFFFFFF
                        if rtp_gap > 0x7FFFFFFF:
                            rtp_gap -= 0x100000000
                        if abs(rtp_gap) < self.min_pulse_samples:
                            noisy = True

                    if noisy:
                        self.pps_noise += 1
                        self.pps_consecutive = 0
                    else:
                        self.pps_ok += 1
                        self.pps_consecutive += 1

                        # The chain delay is how far into the second the
                        # edge actually arrives.  At the sample rate, the
                        # PPS edge *should* land exactly on a second
                        # boundary (ts % sr == 0).  The measured offset is
                        # the chain delay.
                        self._chain_delay_samples = float(ts % sr)
                        # Handle wrap: if offset > sr/2 it's negative
                        if self._chain_delay_samples > sr / 2:
                            self._chain_delay_samples -= sr

                    self._last_edge_rtp = ts

            self._last_angle = angle

        self._sample_counter += len(angles)

        # Return result when locked
        if self.locked and self._chain_delay_samples is not None:
            delay_seconds = self._chain_delay_samples / sr
            delay_ns = int(round(delay_seconds * 1_000_000_000))
            return PpsCalibrationResult(
                chain_delay_ns=delay_ns,
                chain_delay_samples=self._chain_delay_samples,
                pps_ok=self.pps_ok,
                pps_noise=self.pps_noise,
                pps_consecutive=self.pps_consecutive,
                locked=True,
            )

        return None


def _signed_mod(value: int, modulus: int) -> int:
    """Signed modular distance -- returns value in [-modulus/2, modulus/2)."""
    result = value % modulus
    if result >= modulus // 2:
        result -= modulus
    return result
