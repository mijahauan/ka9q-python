"""
Tests for RTP recorder functionality
"""
from unittest.mock import patch

import pytest

from ka9q.rtp_recorder import rtp_to_wallclock
from ka9q.discovery import ChannelInfo


GPS_UTC_OFFSET = 315964800
BILLION = 1_000_000_000


def _channel(sample_rate, gps_time_ns, rtp_timesnap):
    return ChannelInfo(
        ssrc=1234,
        preset="test",
        sample_rate=sample_rate,
        frequency=100.0,
        snr=0.0,
        multicast_address="239.1.2.3",
        port=5004,
        gps_time=gps_time_ns,
        rtp_timesnap=rtp_timesnap,
    )


def test_rtp_to_wallclock_basic():
    """Same RTP as snapshot → exactly GPS+offset; +N samples → +N/sample_rate s."""
    gps_time_ns = 1234567890000000000   # ~2019
    channel = _channel(48000, gps_time_ns, 1000)
    expected_sec = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION

    # Pin system clock close to the channel's wall-clock so the
    # wrap-disambiguation picks epoch k=0 deterministically.
    with patch("ka9q.rtp_recorder.time.time", return_value=expected_sec):
        assert rtp_to_wallclock(1000, channel) == pytest.approx(expected_sec)
        assert rtp_to_wallclock(1000 + 48000, channel) == pytest.approx(expected_sec + 1.0)
        # One sample later → +1/48000 s
        assert rtp_to_wallclock(1001, channel) == pytest.approx(expected_sec + 1 / 48000.0)


def test_rtp_to_wallclock_signed_32bit_window():
    """RTP within ±2**31 samples of snapshot (the natively-correct window)
    → no wrap adjustment needed regardless of system clock."""
    gps_time_ns = 1234567890000000000
    channel = _channel(96000, gps_time_ns, 1000)
    base_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION

    # 30 minutes ahead at 96 kHz = +30*60*96000 = 172_800_000 samples
    target_rtp = (1000 + 172_800_000) & 0xFFFFFFFF
    expected = base_wall + 30 * 60.0
    with patch("ka9q.rtp_recorder.time.time", return_value=expected):
        assert rtp_to_wallclock(target_rtp, channel) == pytest.approx(expected)


def test_rtp_to_wallclock_wraps_correctly_after_one_period():
    """After one full RTP wrap (2**32 samples), naive subtraction aliases
    to ~snapshot.  System-clock disambiguation must return the right
    wall-clock value one wrap later."""
    sample_rate = 96000
    gps_time_ns = 1234567890000000000
    channel = _channel(sample_rate, gps_time_ns, 1000)
    snapshot_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION

    period_sec = 0x100000000 / sample_rate                              # 12.43 h
    target_rtp = (1000 + 0x100000000) & 0xFFFFFFFF                       # exactly 1 wrap later
    expected = snapshot_wall + period_sec

    # System clock at the *expected* time — wrap counter k must be 1.
    with patch("ka9q.rtp_recorder.time.time", return_value=expected):
        result = rtp_to_wallclock(target_rtp, channel)
        assert result == pytest.approx(expected, abs=1e-3)


def test_rtp_to_wallclock_wraps_correctly_after_two_periods():
    """Same idea, two full wraps (~24.86 h after snapshot at 96 kHz)."""
    sample_rate = 96000
    gps_time_ns = 1234567890000000000
    channel = _channel(sample_rate, gps_time_ns, 1000)
    snapshot_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION

    period_sec = 0x100000000 / sample_rate
    target_rtp = (1000 + 2 * 0x100000000 + 100) & 0xFFFFFFFF             # 2 wraps + 100 samples
    expected = snapshot_wall + 2 * period_sec + 100 / sample_rate

    with patch("ka9q.rtp_recorder.time.time", return_value=expected):
        result = rtp_to_wallclock(target_rtp, channel)
        assert result == pytest.approx(expected, abs=1e-3)


def test_rtp_to_wallclock_disambiguator_tolerates_clock_skew():
    """System clock can be off by hours (NTP not yet locked, holdover,
    operator skew) and the wrap disambiguator should still pick the
    right epoch as long as skew is < period/2 (~6 h at 96 kHz)."""
    sample_rate = 96000
    gps_time_ns = 1234567890000000000
    channel = _channel(sample_rate, gps_time_ns, 1000)
    snapshot_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION

    period_sec = 0x100000000 / sample_rate
    target_rtp = (1000 + 0x100000000 + 50_000_000) & 0xFFFFFFFF
    true_wall = snapshot_wall + period_sec + 50_000_000 / sample_rate    # 12.43 h + ~520 s

    # System clock 4 hours off (within ±6 h tolerance window).
    skewed_now = true_wall - 4 * 3600.0
    with patch("ka9q.rtp_recorder.time.time", return_value=skewed_now):
        result = rtp_to_wallclock(target_rtp, channel)
        assert result == pytest.approx(true_wall, abs=1e-3)


def test_rtp_to_wallclock_returns_none_when_timing_missing():
    channel = _channel(48000, None, None)
    assert rtp_to_wallclock(1000, channel) is None
    channel = _channel(48000, 1234567890000000000, None)
    assert rtp_to_wallclock(1000, channel) is None
    channel = _channel(48000, None, 1000)
    assert rtp_to_wallclock(1000, channel) is None


def test_rtp_to_wallclock_hint_bypasses_system_clock():
    """When `wallclock_hint_sec` is provided, time.time() must NOT be
    consulted.  This is the RTP-reference invariant: authority-aware
    callers can disambiguate the wrap epoch without coupling to the
    host system clock."""
    sample_rate = 96000
    gps_time_ns = 1234567890000000000
    channel = _channel(sample_rate, gps_time_ns, 1000)
    snapshot_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION

    period_sec = 0x100000000 / sample_rate
    target_rtp = (1000 + 0x100000000) & 0xFFFFFFFF
    expected = snapshot_wall + period_sec

    # Pin time.time() to something WAY OFF (1 year earlier) — if the
    # function ignores the hint and consults the system clock anyway,
    # the wrap-epoch math will pick k=0 and the result will be wrong.
    bogus_now = expected - 365 * 86400.0
    with patch("ka9q.rtp_recorder.time.time", return_value=bogus_now) as mock_time:
        result = rtp_to_wallclock(target_rtp, channel, wallclock_hint_sec=expected)
        assert result == pytest.approx(expected, abs=1e-3)
        # Strict: hint path must not call time.time() at all.
        mock_time.assert_not_called()


def test_rtp_to_wallclock_hint_picks_correct_epoch():
    """Hint at a different wrap epoch from the system clock → result
    follows the hint, proving the function uses the hint for k-selection."""
    sample_rate = 12000  # WSPR-band rate; period ≈ 99 hours
    gps_time_ns = 1234567890000000000
    channel = _channel(sample_rate, gps_time_ns, 1000)
    snapshot_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION
    period_sec = 0x100000000 / sample_rate

    # RTP value aliased to ~snapshot, but actually 2 wraps later.
    target_rtp = (1000 + 2 * 0x100000000) & 0xFFFFFFFF
    expected = snapshot_wall + 2 * period_sec

    # System clock at the snapshot wall (would pick k=0); hint says
    # ~2 periods later (correct k=2).
    with patch("ka9q.rtp_recorder.time.time", return_value=snapshot_wall):
        result = rtp_to_wallclock(target_rtp, channel, wallclock_hint_sec=expected)
        assert result == pytest.approx(expected, abs=1e-3)


def test_rtp_to_wallclock_hint_omitted_falls_back_to_system_clock():
    """Default path (no hint) preserves legacy behavior for
    backwards compatibility — the hint parameter is purely additive."""
    sample_rate = 48000
    gps_time_ns = 1234567890000000000
    channel = _channel(sample_rate, gps_time_ns, 1000)
    snapshot_wall = (gps_time_ns + BILLION * (GPS_UTC_OFFSET - 18)) / BILLION
    period_sec = 0x100000000 / sample_rate

    target_rtp = (1000 + 0x100000000) & 0xFFFFFFFF
    expected = snapshot_wall + period_sec

    # No hint → must consult time.time() to land on k=1.
    with patch("ka9q.rtp_recorder.time.time", return_value=expected) as mock_time:
        result = rtp_to_wallclock(target_rtp, channel)
        assert result == pytest.approx(expected, abs=1e-3)
        mock_time.assert_called()
