"""
pytest configuration for ka9q-python tests
"""
import os

import pytest


def pytest_addoption(parser):
    """Add command line options for tests"""
    parser.addoption(
        "--radiod-host",
        action="store",
        default=os.environ.get("RADIOD_HOST", "bee1-hf-status.local"),
        help="Hostname of radiod instance to test against (for integration tests)"
    )


@pytest.fixture(scope="session")
def radiod_address(request):
    """Address of the radiod instance to test against.

    Resolution order: --radiod-host CLI option > $RADIOD_HOST env > $RADIOD_ADDRESS env > default.
    """
    return (
        request.config.getoption("--radiod-host")
        or os.environ.get("RADIOD_ADDRESS")
        or "bee1-hf-status.local"
    )
