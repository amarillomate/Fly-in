"""Custom exceptions for the map parser."""


class ParseError(Exception):
    """Raised when a map file is invalid, with line and cause."""


class SchedulingError(Exception):
    """Raised when drones cannot be routed from start to end."""
