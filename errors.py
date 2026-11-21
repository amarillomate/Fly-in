"""Custom exceptions for the map parser."""


class ParseError(Exception):
    """Raised when a map file is invalid, with line and cause."""

    def __init__(
        self,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        """Store the error message and where it happened."""
        super().__init__(message)
        self.line = line
        self.column = column

    def __str__(self) -> str:
        """Return the message prefixed with its line and column."""
        parts = []
        if self.line is not None:
            parts.append(f"Line {self.line}")
        if self.column is not None:
            parts.append(f"column {self.column}")
        header = ", ".join(parts) if parts else "Error"
        result = f"{header}: {self.args[0]}"
        return result


class SchedulingError(Exception):
    """Raised when drones cannot be routed from start to end."""
