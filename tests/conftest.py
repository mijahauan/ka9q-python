"""
pytest configuration for ka9q-python tests
"""
import os


def pytest_addoption(parser):
    """Add command line options for tests"""
    parser.addoption(
        "--radiod-host",
        action="store",
        default=os.environ.get("RADIOD_HOST", "radiod.local"),
        help="Hostname of radiod instance to test against (for integration tests)"
    )
