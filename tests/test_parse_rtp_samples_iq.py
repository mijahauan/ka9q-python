"""Tests for parse_rtp_samples IQ-encoding handling.

Regression coverage for the 2026-05-15 fix where the IQ branch of
parse_rtp_samples ignored the encoding parameter and always decoded as
F32LE — so when radiod silently downgraded a channel to S16 the bytes
mis-decoded into ~1e34 garbage and occasional NaN. See discussion in
hf-timestd's TSL3-dark investigation.
"""

from __future__ import annotations

import numpy as np
import pytest

from ka9q.stream import parse_rtp_samples


def _iq_payload(samples_re, samples_im, *, dtype: str, byteorder: str) -> bytes:
    """Interleaved (re, im) sample bytes in the requested dtype/byteorder."""
    interleaved = np.empty(2 * len(samples_re), dtype=dtype)
    interleaved[0::2] = samples_re
    interleaved[1::2] = samples_im
    # numpy dtype string already encodes byteorder in dtype param;
    # the wire format is whatever np.frombuffer reads with the same dtype.
    return interleaved.tobytes()


def test_iq_f32le_default_encoding_0():
    re = np.array([0.5, -0.25, 0.0], dtype='<f4')
    im = np.array([-0.5, 0.25, 1.0], dtype='<f4')
    payload = _iq_payload(re, im, dtype='<f4', byteorder='<')
    samples = parse_rtp_samples(payload, encoding=0, is_iq=True)
    assert samples is not None
    np.testing.assert_allclose(samples.real, re, rtol=0, atol=1e-7)
    np.testing.assert_allclose(samples.imag, im, rtol=0, atol=1e-7)


def test_iq_f32le_encoding_4():
    re = np.array([0.1, 0.2], dtype='<f4')
    im = np.array([-0.1, -0.2], dtype='<f4')
    payload = _iq_payload(re, im, dtype='<f4', byteorder='<')
    samples = parse_rtp_samples(payload, encoding=4, is_iq=True)
    assert samples is not None
    np.testing.assert_allclose(samples.real, re, rtol=0, atol=1e-7)


def test_iq_f32be_encoding_8():
    re = np.array([0.5, -0.5], dtype='>f4')
    im = np.array([0.25, -0.25], dtype='>f4')
    payload = _iq_payload(re, im, dtype='>f4', byteorder='>')
    samples = parse_rtp_samples(payload, encoding=8, is_iq=True)
    assert samples is not None
    np.testing.assert_allclose(samples.real, [0.5, -0.5], rtol=0, atol=1e-7)
    np.testing.assert_allclose(samples.imag, [0.25, -0.25], rtol=0, atol=1e-7)


def test_iq_s16le_encoding_1():
    re = np.array([16384, -16384], dtype='<i2')   # ±0.5
    im = np.array([8192, -8192], dtype='<i2')     # ±0.25
    payload = _iq_payload(re, im, dtype='<i2', byteorder='<')
    samples = parse_rtp_samples(payload, encoding=1, is_iq=True)
    assert samples is not None
    np.testing.assert_allclose(samples.real, [0.5, -0.5], rtol=0, atol=1e-4)
    np.testing.assert_allclose(samples.imag, [0.25, -0.25], rtol=0, atol=1e-4)


def test_iq_s16be_encoding_2_does_not_produce_nan_or_huge():
    """The bug we're fixing: a real-world S16BE IQ payload like radiod's
    T6/TSL3 channel was producing NaN and ~1e34 values when decoded as
    F32LE. Confirm decoding the same bytes as S16BE gives sane samples.
    """
    re = np.array([23876, -10000, 32767], dtype='>i2')
    im = np.array([13433, 25000, -32768], dtype='>i2')
    payload = _iq_payload(re, im, dtype='>i2', byteorder='>')
    samples = parse_rtp_samples(payload, encoding=2, is_iq=True)
    assert samples is not None
    assert not np.any(np.isnan(samples.real))
    assert not np.any(np.isnan(samples.imag))
    assert np.max(np.abs(samples)) <= 2.0  # all should be in [-1.0, +1.0]
    np.testing.assert_allclose(samples.real, [23876 / 32768.0, -10000 / 32768.0, 32767 / 32768.0], rtol=0, atol=1e-4)


def test_iq_odd_sample_count_returns_none():
    """An odd number of int16 values can't form complete IQ pairs."""
    payload = np.array([1, 2, 3], dtype='>i2').tobytes()  # 3 int16 = 6 bytes
    samples = parse_rtp_samples(payload, encoding=2, is_iq=True)
    assert samples is None


def test_iq_unknown_encoding_falls_back_and_warns(caplog):
    re = np.array([0.1], dtype='<f4')
    im = np.array([-0.1], dtype='<f4')
    payload = _iq_payload(re, im, dtype='<f4', byteorder='<')
    import logging
    with caplog.at_level(logging.WARNING):
        samples = parse_rtp_samples(payload, encoding=99, is_iq=True)
    assert samples is not None
    assert any('Unsupported IQ encoding' in rec.message for rec in caplog.records)


def test_iq_smoking_gun_bit_pattern():
    """The empirical fingerprint of the bug on bee1 2026-05-15:
    a 4-byte block 5d 44 34 79 (which is S16BE int16 pair [23876, 13433]
    — sensible loud-signal IQ) was being decoded as F32LE → 5.85e34.
    Verify S16BE decoding gives back the original int16 values normalised.
    """
    payload = bytes.fromhex('5d44 3479'.replace(' ', ''))
    samples = parse_rtp_samples(payload, encoding=2, is_iq=True)
    assert samples is not None
    assert len(samples) == 1
    np.testing.assert_allclose(samples.real, [23876 / 32768.0], rtol=0, atol=1e-4)
    np.testing.assert_allclose(samples.imag, [13433 / 32768.0], rtol=0, atol=1e-4)
    # The "bug behaviour" reference: decoding the same bytes as F32LE
    # gives 5.85e34. Document this in the test so a future regression
    # that re-introduces F32LE-always behaviour will fail with a meaningful
    # signal.
    as_f32le = np.frombuffer(payload, dtype='<f4')[0]
    assert as_f32le > 1e34, "sanity check: bug fingerprint matches"
