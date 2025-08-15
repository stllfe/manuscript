"""
manu: Dead simple configuration for Python scripts.

Turns a section of your Python script into a powerful, type-checked,
and configurable CLI application.
"""

from . import conf
from .script import script


__all__ = ["script", "conf"]
