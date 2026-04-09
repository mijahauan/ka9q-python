"""
Protocol compatibility test — catches drift between ka9q/types.py
and the ka9q-radio C headers (status.h, rtp.h, radio.h, window.h).

Skipped automatically when ka9q-radio source is not available on disk.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

# Resolve paths relative to this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNC_SCRIPT = PROJECT_ROOT / "scripts" / "sync_types.py"
KA9Q_RADIO_DEFAULT = PROJECT_ROOT.parent / "ka9q-radio"


def _find_ka9q_radio() -> Optional[Path]:
    """Return the ka9q-radio source path, or None if unavailable."""
    # Check default sibling location
    if (KA9Q_RADIO_DEFAULT / "src" / "status.h").exists():
        return KA9Q_RADIO_DEFAULT
    return None


ka9q_radio_path = _find_ka9q_radio()


@pytest.mark.skipif(
    ka9q_radio_path is None,
    reason="ka9q-radio source tree not found at ../ka9q-radio",
)
def test_types_match_status_h():
    """types.py must match the ka9q-radio C headers exactly."""
    result = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--check",
         "--ka9q-radio", str(ka9q_radio_path)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"types.py is out of sync with ka9q-radio headers:\n"
        f"{result.stdout}\n{result.stderr}"
    )


@pytest.mark.skipif(
    ka9q_radio_path is None,
    reason="ka9q-radio source tree not found at ../ka9q-radio",
)
def test_compat_pin_matches_ka9q_radio_head():
    """ka9q_radio_compat pin should match the ka9q-radio HEAD we validated against."""
    compat_file = PROJECT_ROOT / "ka9q_radio_compat"
    assert compat_file.exists(), "ka9q_radio_compat pin file is missing"

    pinned = None
    for line in compat_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pinned = line
            break

    assert pinned, "ka9q_radio_compat contains no commit hash"

    # Get ka9q-radio HEAD
    result = subprocess.run(
        ["git", "-C", str(ka9q_radio_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    head = result.stdout.strip()

    assert pinned == head, (
        f"ka9q_radio_compat pin ({pinned[:12]}) does not match "
        f"ka9q-radio HEAD ({head[:12]}). "
        f"Run: python scripts/sync_types.py --apply"
    )
