"""
manu: Dead simple configuration for Python scripts.

Turns a section of your Python script into a powerful, type-checked,
and configurable CLI application.
"""

from .script import hook, init, ready

__all__ = ["init", "ready", "hook"]
