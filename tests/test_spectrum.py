"""Unit tests for spectrum bin decoding and SpectrumStream."""
from __future__ import annotations

import struct
import pytest
import numpy as np

from ka9q.control import (
    encode_double, encode_float, encode_int, encode_int64, encode_string,
    encode_eol,
)
from ka9q.status import ChannelStatus, SpectrumStatus, decode_status_packet
from ka9q.types import StatusType, DemodType


# ---------------------------------------------------------------------------
# Helpers — build synthetic TLV status packets
# ---------------------------------------------------------------------------

def _build_packet(*fields) -> bytes:
    """Build a status packet from (kind, tag, value) triples."""
    buf = bytearray()
    buf.append(0)  # status response type
    for kind, tag, value in fields:
        if kind == "int":
            encode_int(buf, tag, value)
        elif kind == "int64":
            encode_int64(buf, tag, value)
        elif kind == "double":
            encode_double(buf, tag, value)
        elif kind == "float":
            encode_float(buf, tag, value)
        elif kind == "string":
            encode_string(buf, tag, value)
        elif kind == "bool":
            encode_int(buf, tag, 1 if value else 0)
        elif kind == "raw":
            # Raw bytes TLV: (tag, bytes_value)
            _encode_raw(buf, tag, value)
        else:
            raise ValueError(kind)
    encode_eol(buf)
    return bytes(buf)


def _encode_raw(buf: bytearray, tag: int, data: bytes):
    """Encode a raw-bytes TLV field (for BIN_DATA / BIN_BYTE_DATA)."""
    buf.append(tag)
    length = len(data)
    if length < 128:
        buf.append(length)
    else:
        # Multi-byte length: 0x80 | number_of_length_bytes, then big-endian length
        if length < 256:
            buf.append(0x81)
            buf.append(length)
        elif length < 65536:
            buf.append(0x82)
            buf.append((length >> 8) & 0xff)
            buf.append(length & 0xff)
        else:
            raise ValueError(f"Data too long: {length}")
    buf.extend(data)


# ---------------------------------------------------------------------------
# BIN_DATA (SPECT_DEMOD) — float32 bin vectors
# ---------------------------------------------------------------------------

class TestBinData:
    """Tests for BIN_DATA (float32 vector) decoding."""

    def test_decode_bin_data_basic(self):
        """Four float32 bins decode correctly."""
        powers = [1.0, 0.5, 0.25, 0.125]
        raw = struct.pack("!" + "f" * len(powers), *powers)
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 100),
            ("int", StatusType.DEMOD_TYPE, DemodType.SPECT_DEMOD),
            ("raw", StatusType.BIN_DATA, raw),
        )
        st = decode_status_packet(pkt)
        assert st is not None
        assert st.spectrum.bin_data is not None
        assert len(st.spectrum.bin_data) == 4
        np.testing.assert_allclose(st.spectrum.bin_data, powers, rtol=1e-6)

    def test_bin_power_db_from_bin_data(self):
        """bin_power_db converts float32 to 10*log10."""
        powers = [1.0, 10.0, 100.0, 0.001]
        raw = struct.pack("!" + "f" * len(powers), *powers)
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 101),
            ("raw", StatusType.BIN_DATA, raw),
        )
        st = decode_status_packet(pkt)
        db = st.spectrum.bin_power_db
        assert db is not None
        expected = 10.0 * np.log10(powers)
        np.testing.assert_allclose(db, expected, rtol=1e-5)

    def test_bin_data_empty_optlen(self):
        """Zero-length BIN_DATA does not create an array."""
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 102),
            ("raw", StatusType.BIN_DATA, b""),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_data is None

    def test_bin_data_large_vector(self):
        """512 bins decode correctly (exercises multi-byte TLV length)."""
        n = 512
        powers = [float(i) / n for i in range(1, n + 1)]
        raw = struct.pack("!" + "f" * n, *powers)
        assert len(raw) == n * 4  # 2048 bytes, needs multi-byte length
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 103),
            ("raw", StatusType.BIN_DATA, raw),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_data is not None
        assert len(st.spectrum.bin_data) == n
        np.testing.assert_allclose(st.spectrum.bin_data, powers, rtol=1e-6)


# ---------------------------------------------------------------------------
# BIN_BYTE_DATA (SPECT2_DEMOD) — uint8 bin vectors
# ---------------------------------------------------------------------------

class TestBinByteData:
    """Tests for BIN_BYTE_DATA (uint8 vector) decoding."""

    def test_decode_bin_byte_data(self):
        """Basic uint8 decoding."""
        raw = bytes([0, 50, 100, 150, 200, 255])
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 200),
            ("int", StatusType.DEMOD_TYPE, DemodType.SPECT2_DEMOD),
            ("raw", StatusType.BIN_BYTE_DATA, raw),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_byte_data is not None
        assert len(st.spectrum.bin_byte_data) == 6
        np.testing.assert_array_equal(
            st.spectrum.bin_byte_data, [0, 50, 100, 150, 200, 255]
        )

    def test_bin_power_db_from_byte_data(self):
        """bin_power_db applies base + byte * step formula."""
        raw = bytes([0, 100, 200])
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 201),
            ("float", StatusType.SPECTRUM_BASE, -120.0),
            ("float", StatusType.SPECTRUM_STEP, 0.5),
            ("raw", StatusType.BIN_BYTE_DATA, raw),
        )
        st = decode_status_packet(pkt)
        db = st.spectrum.bin_power_db
        assert db is not None
        expected = np.array([-120.0, -120.0 + 100 * 0.5, -120.0 + 200 * 0.5])
        np.testing.assert_allclose(db, expected, rtol=1e-5)

    def test_bin_byte_data_empty(self):
        """Zero-length BIN_BYTE_DATA does not create an array."""
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 202),
            ("raw", StatusType.BIN_BYTE_DATA, b""),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_byte_data is None

    def test_bin_byte_data_large(self):
        """1024 uint8 bins (exercises multi-byte TLV length)."""
        n = 1024
        raw = bytes(i % 256 for i in range(n))
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 203),
            ("raw", StatusType.BIN_BYTE_DATA, raw),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_byte_data is not None
        assert len(st.spectrum.bin_byte_data) == n


# ---------------------------------------------------------------------------
# Combined metadata + bin data
# ---------------------------------------------------------------------------

class TestSpectrumFull:
    """Full spectrum packet with metadata and bin vectors."""

    def test_complete_spectrum_packet(self):
        """Decode a packet with all spectrum metadata plus bin data."""
        n_bins = 8
        powers = [float(i + 1) for i in range(n_bins)]
        raw = struct.pack("!" + "f" * n_bins, *powers)

        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 300),
            ("int", StatusType.DEMOD_TYPE, DemodType.SPECT_DEMOD),
            ("double", StatusType.RADIO_FREQUENCY, 14.1e6),
            ("int", StatusType.SPECTRUM_FFT_N, 2048),
            ("int", StatusType.BIN_COUNT, n_bins),
            ("float", StatusType.RESOLUTION_BW, 100.0),
            ("int", StatusType.SPECTRUM_AVG, 10),
            ("float", StatusType.SPECTRUM_OVERLAP, 0.5),
            ("int", StatusType.WINDOW_TYPE, 0),
            ("raw", StatusType.BIN_DATA, raw),
        )
        st = decode_status_packet(pkt)
        assert st.ssrc == 300
        assert st.frequency == pytest.approx(14.1e6)
        assert st.spectrum.fft_n == 2048
        assert st.spectrum.bin_count == n_bins
        assert st.spectrum.resolution_bw == pytest.approx(100.0)
        assert st.spectrum.avg == 10
        assert st.spectrum.overlap == pytest.approx(0.5)
        assert st.spectrum.window_type == 0
        assert st.spectrum.bin_data is not None
        assert len(st.spectrum.bin_data) == n_bins
        np.testing.assert_allclose(st.spectrum.bin_data, powers, rtol=1e-6)
        # bin_power_db should work
        db = st.spectrum.bin_power_db
        assert db is not None
        assert len(db) == n_bins

    def test_bin_power_db_none_without_data(self):
        """bin_power_db returns None when no bin vectors present."""
        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 301),
            ("int", StatusType.SPECTRUM_FFT_N, 1024),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_power_db is None

    def test_bin_data_takes_priority_over_byte_data(self):
        """When both are present, bin_data (float) takes priority in bin_power_db."""
        float_powers = [1.0, 2.0]
        float_raw = struct.pack("!ff", *float_powers)
        byte_raw = bytes([100, 200])

        pkt = _build_packet(
            ("int", StatusType.OUTPUT_SSRC, 302),
            ("raw", StatusType.BIN_DATA, float_raw),
            ("raw", StatusType.BIN_BYTE_DATA, byte_raw),
        )
        st = decode_status_packet(pkt)
        assert st.spectrum.bin_data is not None
        assert st.spectrum.bin_byte_data is not None
        # bin_power_db should use bin_data (float), not byte
        db = st.spectrum.bin_power_db
        expected = 10.0 * np.log10(float_powers)
        np.testing.assert_allclose(db, expected, rtol=1e-5)


# ---------------------------------------------------------------------------
# SpectrumStream import / construction (no live radiod needed)
# ---------------------------------------------------------------------------

class TestSpectrumStreamImport:
    """Verify SpectrumStream is importable and constructible."""

    def test_import_from_package(self):
        from ka9q import SpectrumStream
        assert SpectrumStream is not None

    def test_import_from_module(self):
        from ka9q.spectrum_stream import SpectrumStream, SpectrumCallback
        assert SpectrumStream is not None
        assert SpectrumCallback is not None
