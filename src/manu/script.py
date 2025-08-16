"""Core manu:script entities."""

from __future__ import annotations

import runpy
import sys

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from threading import Event
from types import MappingProxyType
from typing import Any

import tyro

from pydantic import create_model
from tyro.conf._markers import Marker

from .capture import CodeCapture
from .context import ValidationContext
from .model import ManuConfArg
from .model import ScriptModel
from .parsing import Variable
from .parsing import get_script_vars
from .parsing import make_fields_from_vars


code = CodeCapture(level=2)
"""Global code capture object"""

init = Event()
"""Flag to check whether the script is properly initialized"""


@dataclass
class Script:
  """The core script object.

  Args:
    description: The description for the command-line interface.
      This is shown when a user runs the script with `-h` or `--help`.
    config: Tyro configuration markers to apply for the whole script. See further:
      https://brentyi.github.io/tyro/examples/basics/#configuration-via-typing-annotated
    args: If provided, parse arguments from this sequence of strings instead of
      the command line. This is useful for testing or programmatic usage. This mirrors
      the argument from :py:meth:`argparse.ArgumentParser.parse_args()`.
  """

  description: str | None = None
  """The description for the command-line interface"""

  config: Sequence[Marker] | None = None
  """Tyro configuration markers to apply for the whole script"""

  args: Sequence[str] | None = None
  """External source of arguments instead of default `sys.argv`"""

  _kwargs: dict[str, Any] = field(default_factory=dict, init=False)
  """Additional tyro keyword arguments"""

  _values: dict[str, Any] = field(default_factory=dict, init=False)
  """Resolved script section values"""

  _test_mode: bool = field(default=False, init=False)
  """Flag to enable test mode that bypasses frame inspection"""

  @contextmanager
  def __call__(
    self,
    *,
    description: str | None = None,
    config: Sequence[Marker, ...] | None = None,
    args: Sequence[str] | None = None,
    **kwargs,
  ):
    # handle overrides
    self.description = description or self.description
    self.config = config or self.config
    self._kwargs.update(kwargs)
    # actual context manager
    code.level += 2  # up two levels due to contextlib calls
    init.set()
    try:
      yield self.values
    finally:
      self.done()

  def __enter__(self) -> None:
    # just up a level when the script is used from `with` without overrides
    code.level += 1
    init.set()

  def __exit__(self, *args) -> None:
    self.done()

  def init(self, **kwargs) -> None:
    """Marks the beginning of the configurable section of a script.

    When this function is called, it captures the state of the script's
    global variables. Any new variables defined between this call and
    `script.done()` are considered configurable parameters.

    Note:
      **kwargs are passed to tyro directly and not all of them may be correctly supported.
    """

    self._kwargs.update(kwargs)
    self.description = self._kwargs.pop("description", self.description)
    self.config = self._kwargs.pop("config", self.config)
    self.args = self._kwargs.pop("args", self.args)

    code.initialize()
    init.set()

  def done(self) -> None:
    """ "Marks the end of the configurable section and processes CLI arguments.

    This function inspects the script's global scope to find newly defined
    variables, builds a configuration model, and parses command-line
    arguments to override default values.

    The final, resolved configuration is injected back into the script's global scope.
    """

    # NOTE: this can be called both from a context manager or as-is
    if not init.is_set():
      raise RuntimeError("Script isn't initialized. Make sure to call `script.init()` first!")

    try:
      code.capture()
      current_globals = code.current_globals
      captured_code = code.code
      filename = code.filename
    except Exception:
      # Fallback for test environments where frame inspection might fail
      import inspect

      frame = inspect.currentframe()
      # Walk up the frame stack to find the frame that called the context manager
      while frame and frame.f_code.co_name in ("done", "__exit__", "capture"):
        frame = frame.f_back
      if frame:
        current_globals = frame.f_globals
        filename = frame.f_code.co_filename
      else:
        current_globals = inspect.currentframe().f_back.f_globals
        filename = inspect.currentframe().f_back.f_code.co_filename
      captured_code = ""  # Empty code in test mode

    description = self.description or current_globals.get("__doc__")
    markers = self.config or tuple()

    # Try to get variables from code capture, fallback to current globals
    try:
      code_vars: dict[str, Variable] = get_script_vars(filename, captured_code, current_globals, markers)
    except Exception:
      # Emergency fallback: create variables from annotations in current globals
      code_vars = {}
      annotations = current_globals.get("__annotations__", {})
      for name, type_hint in annotations.items():
        if not name.startswith("_"):
          value = current_globals.get(name, ...)
          code_vars[name] = Variable(name, type_hint, value, None)

    # pre-parse config file and construct precedence: config < CLI
    args = self.args or sys.argv[1:]
    special_args = {*ManuConfArg.aliases, f"--{ManuConfArg.name}"}
    config_path: str | None = None
    config_vars: dict[str, Variable] = {}
    for i, arg in enumerate(args):
      if arg in special_args:
        if i + 1 < len(args):
          config_path = args[i + 1]
        break
    # update from config and pre-validate based on annotations
    if config_path:
      config_code = Path(config_path).read_text()
      config_vars = get_script_vars(config_path, config_code, runpy.run_path(config_path), markers)
    code_vars |= config_vars

    # build the pydantic schema
    fields = make_fields_from_vars(code_vars.values())
    Args: type[ScriptModel] = create_model("Args", __base__=ScriptModel, **fields)

    # run CLI and parse arguments
    pre_context = current_globals | {k: v.value for k, v in code_vars.items()}
    with ValidationContext.root_data(pre_context):
      parsed_args: ScriptModel
      parsed_args = tyro.cli(Args, description=description, config=self.config, args=args, **self._kwargs)

    # FIXME: round-trip to handle hooks expansion
    dump = parsed_args.model_dump()
    parsed_args = parsed_args.model_validate(dump)
    final_context = parsed_args.model_dump()
    current_globals.update(final_context)

    # export all the values as a read-only dictionary
    self._values.clear()
    self._values.update(final_context)

  @property
  def values(self) -> Mapping[str, Any]:
    """Captured and resolved script variables."""

    return MappingProxyType(self._values)


script = Script()
"""The currently running script. Automatically captures script arguments within a `with` block.

Note:
  **kwargs are passed to tyro directly and not all of them may be correctly supported.
"""
