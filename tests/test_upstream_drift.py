"""Classification unit tests for scripts/check_upstream_drift.py.

These exercise the pure-Python diff/classify layer without touching git.
The git-integration path is verified by running the script against the
real ka9q-radio checkout (see CI / smoke tests).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts/ importable
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from check_upstream_drift import (  # noqa: E402
    FieldChange, HeaderDelta,
    STREAM_CRITICAL_STATUS_TYPES,
    _aggregate_severity, _classify_change, _diff_enum,
)


# ---------------------------------------------------------------------------
# _classify_change
# ---------------------------------------------------------------------------

class TestClassifyChange:
    def test_added_field_is_warn(self):
        sev, _ = _classify_change("StatusType", "added", "OUTPUT_SSRC")
        assert sev == "warn"

    def test_added_encoding_is_warn(self):
        sev, _ = _classify_change("Encoding", "added", "FOO")
        assert sev == "warn"

    def test_removed_stream_critical_status_is_fail(self):
        sev, reason = _classify_change("StatusType", "removed", "OUTPUT_SSRC")
        assert sev == "fail"
        assert "RTP" in reason or "channel" in reason.lower()

    def test_value_changed_stream_critical_status_is_fail(self):
        sev, _ = _classify_change("StatusType", "value_changed", "OUTPUT_ENCODING")
        assert sev == "fail"

    def test_removed_non_critical_status_is_warn(self):
        sev, _ = _classify_change("StatusType", "removed", "TP1")
        assert sev == "warn"

    def test_value_changed_non_critical_status_is_warn(self):
        sev, _ = _classify_change("StatusType", "value_changed", "FILTER_DROPS")
        assert sev == "warn"

    def test_encoding_value_shift_is_fail(self):
        sev, _ = _classify_change("Encoding", "value_changed", "F32LE")
        assert sev == "fail"

    def test_demod_value_shift_is_fail(self):
        sev, _ = _classify_change("DemodType", "value_changed", "FM_DEMOD")
        assert sev == "fail"

    def test_window_change_is_only_warn(self):
        # WindowType isn't stream-critical for RTP delivery.
        sev, _ = _classify_change("WindowType", "value_changed", "KAISER_WINDOW")
        assert sev == "warn"
        sev, _ = _classify_change("WindowType", "removed", "HANN_WINDOW")
        assert sev == "warn"


# ---------------------------------------------------------------------------
# _diff_enum
# ---------------------------------------------------------------------------

class TestDiffEnum:
    def test_no_changes(self):
        pin = [("A", 0, ""), ("B", 1, "")]
        assert _diff_enum("StatusType", pin, pin) == []

    def test_added_field(self):
        pin  = [("A", 0, "")]
        head = [("A", 0, ""), ("OUTPUT_SSRC", 1, "")]
        out = _diff_enum("StatusType", pin, head)
        assert len(out) == 1
        assert out[0].kind == "added"
        assert out[0].name == "OUTPUT_SSRC"
        assert out[0].head == 1
        # added is warn even for stream-critical names
        assert out[0].severity == "warn"

    def test_removed_stream_critical(self):
        pin  = [("OUTPUT_SSRC", 18, ""), ("FILTER_DROPS", 77, "")]
        head = [("FILTER_DROPS", 77, "")]
        out = _diff_enum("StatusType", pin, head)
        assert len(out) == 1
        assert out[0].kind == "removed"
        assert out[0].name == "OUTPUT_SSRC"
        assert out[0].pin == 18
        assert out[0].severity == "fail"

    def test_value_changed_stream_critical(self):
        pin  = [("OUTPUT_ENCODING", 107, "")]
        head = [("OUTPUT_ENCODING", 108, "")]
        out = _diff_enum("StatusType", pin, head)
        assert len(out) == 1
        assert out[0].kind == "value_changed"
        assert out[0].pin == 107
        assert out[0].head == 108
        assert out[0].severity == "fail"

    def test_value_changed_non_critical_is_warn(self):
        pin  = [("FILTER_DROPS", 77, "")]
        head = [("FILTER_DROPS", 78, "")]
        out = _diff_enum("StatusType", pin, head)
        assert out[0].severity == "warn"

    def test_encoding_value_shift_is_fail(self):
        pin  = [("F32LE", 4, ""), ("OPUS", 3, "")]
        head = [("F32LE", 5, ""), ("OPUS", 3, "")]
        out = _diff_enum("Encoding", pin, head)
        assert len(out) == 1
        assert out[0].name == "F32LE"
        assert out[0].severity == "fail"

    def test_window_change_is_warn(self):
        pin  = [("KAISER_WINDOW", 0, "")]
        head = [("KAISER_WINDOW", 1, "")]
        out = _diff_enum("WindowType", pin, head)
        assert out[0].severity == "warn"


# ---------------------------------------------------------------------------
# _aggregate_severity
# ---------------------------------------------------------------------------

class TestAggregateSeverity:
    def _delta(self, severities: list[str]) -> HeaderDelta:
        d = HeaderDelta(header="x", enum="y")
        for s in severities:
            d.changes.append(FieldChange("removed", "n", severity=s, reason=""))
        return d

    def test_all_pass(self):
        assert _aggregate_severity([]) == "pass"
        assert _aggregate_severity([self._delta([])]) == "pass"

    def test_warn_only(self):
        assert _aggregate_severity([self._delta(["warn", "warn"])]) == "warn"

    def test_fail_dominates(self):
        deltas = [self._delta(["warn"]), self._delta(["fail"])]
        assert _aggregate_severity(deltas) == "fail"

    def test_single_fail_in_otherwise_clean_set(self):
        deltas = [self._delta([]), self._delta(["fail"])]
        assert _aggregate_severity(deltas) == "fail"


# ---------------------------------------------------------------------------
# Sanity: every name in the stream-critical allowlist actually exists in
# the current types.py — guards against the allowlist drifting away from
# the schema.
# ---------------------------------------------------------------------------

def test_allowlist_names_exist_in_types():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from ka9q.types import StatusType

    missing = [n for n in STREAM_CRITICAL_STATUS_TYPES
               if not hasattr(StatusType, n)]
    assert not missing, (
        f"stream-critical allowlist references unknown StatusType "
        f"name(s): {missing}.  Either the allowlist is stale or "
        f"types.py was regenerated without keeping these fields."
    )
