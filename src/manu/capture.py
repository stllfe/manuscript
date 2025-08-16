"""Script section code capturing utility."""

# based on:
# https://stackoverflow.com/questions/36815410/is-there-any-way-to-get-source-code-inside-context-manager-as-string/78485159#78485159

import inspect
import linecache
import logging

from dataclasses import dataclass
from dataclasses import field
from types import FrameType
from typing import Any, Self

import dill


logger = logging.getLogger(__name__)


def get_frame_level(cf: FrameType, level: int = 0) -> FrameType | None:
  f = cf
  for _ in range(level):
    if not (f := f.f_back):
      return None
  return f


@dataclass(frozen=True)
class CallFrame:
  lineno: int
  filename: str
  context: dict[str, Any] = field(default_factory=dict)

  @classmethod
  def from_current(cls, cf: FrameType, level: int = 1, copy=True) -> Self:
    f = get_frame_level(cf, level)
    if not f:
      # Fallback for test environments - use the current frame
      f = cf
      logger.warning("Could not inspect caller's frame, using current frame as fallback")
    context = dill.copy(f.f_globals) if copy else f.f_globals
    return cls(lineno=f.f_lineno, filename=f.f_code.co_filename, context=context)


@dataclass
class CodeCapture:
  level: int = 1
  code: str | None = field(default=None, init=False)
  filename: str | None = field(default=None, init=False)

  def __post_init__(self) -> None:
    self.code: str | None = None
    self.filename: str | None = None
    self.fframe: CallFrame | None = None
    self.lframe: CallFrame | None = None

  @property
  def current_globals(self) -> dict[str, Any]:
    assert self.lframe  # noqa
    return self.lframe.context

  def initialize(self) -> None:
    cf = inspect.currentframe()
    self.fframe = CallFrame.from_current(cf, level=self.level, copy=True)
    logging.debug("Initial code frame added")

  def capture(self) -> None:
    logging.debug("Capturing code...")
    cf = inspect.currentframe()
    lframe = CallFrame.from_current(cf, level=self.level, copy=False)
    fframe = self.fframe
    lines = []
    if fframe:  # was called without a context manager
      assert lframe.filename == fframe.filename  # noqa
      lines = [linecache.getline(fframe.filename, i) for i in range(fframe.lineno + 1, lframe.lineno)]
    else:
      lines = self._parse_with_block(lframe.filename, lframe.lineno)
    self.lframe = lframe
    self.code = "".join(lines)
    self.filename = lframe.filename

  def _parse_with_block(self, filename: str, line: int) -> list[str]:
    lines = []
    indent = 0
    i = 1
    while True:
      next_line = linecache.getline(filename, line + i)
      next_line_indent = len(next_line) - len(next_line.lstrip())
      if indent == 0:
        indent = next_line_indent
      elif (next_line_indent < indent and len(next_line.strip()) > 0) or next_line == "":
        break
      if next_line == "\n":  # preserve newlines
        lines.append(next_line)
      else:
        lines.append(next_line[indent:])
      i += 1
    return lines
