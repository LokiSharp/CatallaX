"""Single-line progress display for interactive CLIs."""

from __future__ import annotations

import sys
from typing import TextIO


class ProgressLine:
    """Rewrite one stderr line on a TTY; stay quiet on intermediate updates otherwise.

    Call ``finish`` (optionally with a final message) to end the line cleanly.
    """

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stderr
        self._is_tty: bool = self._stream.isatty()
        self._width: int = 0

    def update(self, message: str) -> None:
        """Show or refresh the current progress text (TTY only)."""
        if not self._is_tty:
            return
        text = message.rstrip("\n")
        pad = max(self._width - len(text), 0)
        self._stream.write(f"\r{text}{' ' * pad}")
        self._stream.flush()
        self._width = max(self._width, len(text))

    def finish(self, message: str | None = None) -> None:
        """End the progress line; print ``message`` as a normal final line if given."""
        if self._is_tty and self._width:
            # Clear the in-place line before printing a final summary.
            self._stream.write(f"\r{' ' * self._width}\r")
            self._stream.flush()
        if message is not None:
            self._stream.write(message.rstrip("\n") + "\n")
            self._stream.flush()
        self._width = 0
