import logging
import re

from pathlib import Path
from typing import Annotated, Any, TypeVar, get_type_hints

import tyro

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from .context import ValidationContext
from .hooks import HOOK_EXPANSION_REGEX
from .hooks import HOOK_PREFIX
from .hooks import PREFIXED_HOOK_EXPANSION_REGEX
from .hooks import HookRegistry


logger = logging.getLogger(__name__)

T = TypeVar("T")

ManuConfArg = tyro.conf.arg(
  metavar="PATH",
  name="@config",
  aliases=["-c"],
  help_behavior_hint="(default: no overrides)",
  help="path to a python config file to load",
)


class ScriptModel(BaseModel):
  """Base model class that automatically resolves hooks."""

  model_config = ConfigDict(arbitrary_types_allowed=True)
  manu_config__: Annotated[str | Path, ManuConfArg] = Field(default="", exclude=True)

  @classmethod
  def _process_reference(cls, ref: str) -> Any:
    logger.debug(f"Processing reference: {ref}")
    assert ref.startswith(HOOK_PREFIX)

    ref = ref.lstrip(HOOK_PREFIX)  # slice out the @-prefix

    # @{var_name} syntax for variable interpolation
    if match := HOOK_EXPANSION_REGEX.match(ref):
      hook = "value"
      value = match.group(1)  # Extract content inside braces
    # @hook:value syntax
    elif ":" in ref:
      hook, value = ref.split(":", 1)
    # simple @hook syntax (no arguments)
    else:
      hook = ref
      value = ""

    handler = HookRegistry.get_handler(hook)
    return handler(value, ValidationContext)

  @classmethod
  def validate_script_fields(cls, v: Any, hints: dict[str, Any]) -> Any:
    """Validate and build script fields in a model."""

    if not isinstance(v, dict):
      return v

    # Reference Loop
    for field_name, field_value in v.items():
      if field_name not in hints:
        continue

      requires_resolution = isinstance(field_value, str) and ("@{" in field_value or field_value.startswith("@"))

      if requires_resolution:
        # Handle string interpolation: replace @{var} with variable values
        processed_value = field_value

        # Find all @{...} patterns and replace them
        for match in re.finditer(PREFIXED_HOOK_EXPANSION_REGEX, field_value):
          var_path = match.group(1)
          logger.debug(f"Attempting to interpolate @{{{var_path}}} in field {field_name}")
          try:
            replacement = ValidationContext.get_nested_value(var_path)
            logger.debug(f"Found replacement value: {replacement}")
            processed_value = processed_value.replace(match.group(0), str(replacement))
          except ValueError as e:
            # If variable not found, leave it as is for now
            logger.debug(f"Failed to interpolate {var_path}: {e}")
            pass

        # If the entire value is a single @reference, process it as a hook
        if processed_value == field_value and field_value.startswith("@") and not field_value.startswith("@{"):
          processed_value = cls._process_reference(field_value)

        v[field_name] = processed_value

    return v

  @classmethod
  def __get_pydantic_core_schema__(
    cls,
    _source_type: Any,
    _handler: GetCoreSchemaHandler,
  ) -> core_schema.CoreSchema:
    schema = super().__get_pydantic_core_schema__(_source_type, _handler)

    hints = get_type_hints(cls)

    return core_schema.chain_schema([
      core_schema.no_info_plain_validator_function(lambda v: cls.validate_script_fields(v, hints)),
      schema,
    ])

  @classmethod
  def model_validate(cls, obj: Any, *args, **kwargs):
    """Validate and build the model."""

    if not isinstance(obj, dict):
      return super().model_validate(obj, *args, **kwargs)

    with ValidationContext.root_data(obj):
      return super().model_validate(obj, *args, **kwargs)
