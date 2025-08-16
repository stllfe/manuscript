import importlib
import logging
import os
import re

from collections.abc import Callable
from typing import Any

from .context import ValidationContext


logger = logging.getLogger(__name__)

HOOK_PREFIX = "@"
HOOK_EXPANSION_REGEX = re.compile(r"\{([^}]+)\}")
PREFIXED_HOOK_EXPANSION_REGEX = re.compile(r"@\{([^}]+)\}")

HandlerType = Callable[[Any, ValidationContext], Any]


class HookRegistry:
  """Global registry mapping reference hooks to their handler functions."""

  _handlers: dict[str, HandlerType] = {}

  @classmethod
  def register(cls, hook: str, handler: HandlerType):
    """Register a handler function for a reference hook."""

    if hook in cls._handlers:
      raise ValueError(f"Handler already registered for hook: {hook}")
    cls._handlers[hook] = handler
    logger.debug(f"Registered handler for hook: {hook}")

  @classmethod
  def get_handler(cls, hook: str) -> HandlerType:
    """Get the handler for a reference hook."""

    if hook not in cls._handlers:
      raise ValueError(f"No handler registered for hook: {hook}")
    return cls._handlers[hook]

  @classmethod
  def clear(cls):
    """Clear all registered handlers."""

    cls._handlers.clear()


def hook(hook: str):
  """Decorator to register a reference hook handler function."""

  def decorator(handler: HandlerType) -> HandlerType:
    HookRegistry.register(hook, handler)
    return handler

  return decorator


#######################
# Built-in hooks below:
#######################


@hook("import")
def import_hook(path: str, _: ValidationContext) -> Any:
  """Handle @import:module.path.to.thing references."""

  module_path, attr = path.rsplit(".", 1)
  try:
    module = importlib.import_module(module_path)
  except ImportError as e:
    raise ValueError(path) from e
  return getattr(module, attr)


@hook("value")
def value_hook(path: str, ctx: ValidationContext) -> Any:
  """Handle @value:path.to.value references."""

  return ctx.get_nested_value(path)


@hook("env")
def env_hook(name: str, _: ValidationContext) -> str:
  """Handle @env:VARIABLE_NAME references."""

  try:
    return os.environ[name]
  except KeyError as e:
    raise ValueError(f"Environment variable {name} not found") from e
