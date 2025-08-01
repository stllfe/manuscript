import logging

from typing import Any, TypeVar, get_type_hints

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from .context import ValidationContext
from .hooks import HOOK_EXPANSION_REGEX
from .hooks import HOOK_PREFIX
from .hooks import HookRegistry


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ScriptModel(BaseModel):
  """Base model class that automatically builds fields."""

  model_config = ConfigDict(arbitrary_types_allowed=True)

  @classmethod
  def _process_reference(cls, reference: str) -> Any:
    logger.debug(f"Processing reference: {reference}")
    assert reference.startswith(HOOK_PREFIX)

    reference = reference[1:]  # slice out the @-prefix

    if ":" in reference:
      hook, value = reference.split(":")
    # special case, using @{x.y.z} syntax instead of @value:x.y.z syntax
    elif expansion := HOOK_EXPANSION_REGEX.match(value):
      hook = "value"
      value = expansion.group()
    else:
      raise ValueError(f"Incorrect reference format: {reference}")

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
      requires_resolution = (
        isinstance(field_value, str) and field_value.startswith("@")  # @todo: make this more robust
      )

      if requires_resolution:
        v[field_name] = cls._process_reference(field_value)

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
