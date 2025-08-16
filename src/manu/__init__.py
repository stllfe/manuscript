"""
manu:script Dead simple configuration for Python scripts.

Turns a section of your Python script into a powerful, type-checked,
and configurable CLI application.
"""

__version__ = "0.1.0"

from . import conf
from .context import ValidationContext
from .hooks import hook
from .script import script


__all__ = (
  "conf",
  "ValidationContext",
  "hook",
  "script",
)
