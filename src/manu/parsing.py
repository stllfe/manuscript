import ast

from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from textwrap import dedent
from typing import Any

from pydantic import Field
from tyro.conf._markers import Marker

from .docstring import get_var_docstring


@dataclass(frozen=True)
class Variable:
  name: str
  hint: type
  value: Any
  docstring: str | None = field(default=None)


def get_script_vars(
  filename: str,
  code: str,
  context: dict[str, Any],
  markers: tuple[Marker, ...] = tuple(),
) -> list[Variable]:
  """Parse the configuration code segment to extract variable definitions."""

  # parse the code segment
  try:
    parsed = ast.parse(dedent(code), filename=filename)
  except SyntaxError as err:
    raise RuntimeError(f"Failed to parse configuration section: {err}")

  # Extract variable assignments
  candidates = []
  for node in parsed.body:
    if isinstance(node, ast.Assign):
      # Handle regular assignments: var = value
      for target in node.targets:
        if isinstance(target, ast.Name):
          candidates.append(target.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
      # Handle annotated assignments: var: type = value
      candidates.append(node.target.id)

  # Process each variable
  variables = []
  annotations = context.get("__annotations__", {})
  for name in candidates:
    if name.startswith("_"):
      continue  # Skip private variables
    value = context.get(name)
    type_hint = annotations.get(name, type(value) if value is not None else Any)
    docstring = get_var_docstring(code, name, markers)
    variables.append(Variable(name, type_hint, value, docstring))

  return variables


def make_fields_from_vars(variables: Sequence[Variable]) -> dict[str, tuple[type, Field]]:
  fields = {}
  for var in variables:
    if var.value is ...:
      field = (var.hint, Field(..., description=var.docstring))
    else:
      field = (var.hint, Field(default=var.value, description=var.docstring))
    fields[var.name] = field
  return fields
