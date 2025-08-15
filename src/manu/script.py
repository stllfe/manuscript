"""Core manu:script entities."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from threading import Event

import tyro

from pydantic import create_model
from tyro.conf._markers import Marker

from .capture import CodeCapture
from .context import ValidationContext
from .model import ScriptModel
from .parsing import get_script_vars
from .parsing import make_fields_from_vars


code = CodeCapture(level=2)
"""Global code capture object"""

init = Event()
"""Flag to check whether the script is properly initialized"""


@dataclass
class Script:
  """The currently running script.

  Args:
    description: The description for the command-line interface.
      This is shown when a user runs the script with `-h` or `--help`.
    config: Tyro configuration markers to apply for the whole script. See further:
      https://brentyi.github.io/tyro/examples/basics/#configuration-via-typing-annotated
  """

  description: str | None = None
  """The description for the command-line interface"""

  config: tuple[Marker, ...] | None = None
  """Tyro configuration markers to apply for the whole script"""

  @contextmanager
  def __call__(self, description: str | None = None, config: tuple[Marker, ...] | None = None):
    """Automatically capture script arguments within the given `with` block."""

    # handle overrides
    self.description = description or self.description
    self.config = config or self.config

    # actual context manager
    code.level += 2  # up two levels due to contextlib calls
    init.set()
    try:
      yield
    finally:
      self.done()

  def __enter__(self) -> None:
    # just up a level when the script is used from `with` without overrides
    code.level += 1
    init.set()

  def __exit__(self, *args) -> None:
    self.done()

  def init(self) -> None:
    """Marks the beginning of the configurable section of a script.

    When this function is called, it captures the state of the script's
    global variables. Any new variables defined between this call and
    `script.ready()` are considered configurable parameters.
    """

    code.initialize()
    init.set()

  def done(self) -> None:
    """ "Marks the end of the configurable section and processes CLI arguments.

    This function inspects the script's global scope to find newly defined
    variables, builds a configuration model, and parses command-line
    arguments to override default values.

    The final, resolved configuration is injected back into the script's global scope.
    """
    if not init.is_set():
      raise RuntimeError("Script isn't initialized. Make sure to call `script.init()` first!")
    # NOTE: this can be called both in context managet and as-is
    code.capture()
    variables = get_script_vars(code.filename, code.code, code.lframe.context)
    description = self.description or code.current_globals.get("__doc__")
    fields = make_fields_from_vars(variables)

    # build the pydantic schema
    Args: type[ScriptModel] = create_model("Args", __base__=ScriptModel, **fields)

    with ValidationContext.root_data(code.current_globals):
      args: ScriptModel = tyro.cli(Args, description=description, config=self.config)

    # FIXME: round-trip to handle hooks expansion
    dump = args.model_dump()
    args = args.model_validate(dump)
    final_context = args.model_dump()
    code.current_globals.update(final_context)


script = Script()
"""Global script object"""
