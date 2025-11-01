"""
Exceptions for ka9q library
"""

class Ka9qError(Exception):
    """Base exception for all ka9q errors"""
    pass

class ConnectionError(Ka9qError):
    """Failed to connect to radiod"""
    pass

class CommandError(Ka9qError):
    """Failed to send command to radiod"""
    pass

class DiscoveryError(Ka9qError):
    """Failed to discover radiod services or channels"""
    pass

class ValidationError(Ka9qError):
    """Invalid parameter or configuration"""
    pass
