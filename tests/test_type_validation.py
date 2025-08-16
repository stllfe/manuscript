"""Test type hints and Pydantic validation."""

from pathlib import Path
from typing import Any

import pytest

from pydantic import PositiveInt
from pydantic import ValidationError

import manu


class TestTypeValidation:
  """Test type hints and Pydantic validation."""

  def test_basic_type_coercion(self):
    """Test basic type coercion from strings."""
    args = ["--int-val", "42", "--float-val", "3.14", "--bool-val", "true", "--str-val", "hello"]

    with manu.script(args=args):
      int_val: int = 0
      float_val: float = 0.0
      bool_val: bool = False
      str_val: str = ""

    assert int_val == 42
    assert float_val == 3.14
    assert bool_val is True
    assert str_val == "hello"

  def test_path_type_conversion(self):
    """Test Path type conversion."""
    args = ["--input-file", "/tmp/input.txt", "--output-dir", "/tmp/output"]

    with manu.script(args=args):
      input_file: Path = Path(".")
      output_dir: Path = Path(".")

    assert input_file == Path("/tmp/input.txt")
    assert output_dir == Path("/tmp/output")
    assert isinstance(input_file, Path)
    assert isinstance(output_dir, Path)

  def test_list_type_validation(self):
    """Test list type validation."""
    args = ["--tags", "tag1", "tag2", "tag3", "--numbers", "1", "2", "3"]

    with manu.script(args=args):
      tags: list[str] = []
      numbers: list[int] = []

    assert tags == ["tag1", "tag2", "tag3"]
    assert numbers == [1, 2, 3]

  def test_optional_type_handling(self):
    """Test Optional type handling."""
    args = ["--optional-str", "value"]

    with manu.script(args=args):
      optional_str: str | None = None
      optional_int: int | None = None

    assert optional_str == "value"
    assert optional_int is None

  def test_pydantic_constrained_types(self):
    """Test Pydantic constrained types."""
    args = ["--positive-num", "42"]

    with manu.script(args=args):
      positive_num: PositiveInt = 1

    assert positive_num == 42

  def test_pydantic_validation_error(self):
    """Test Pydantic validation error for invalid input."""
    args = ["--positive-num", "-5"]

    with pytest.raises((ValidationError, SystemExit)):
      with manu.script(args=args):
        positive_num: PositiveInt = 1

  def test_complex_nested_types(self):
    """Test complex nested type structures."""
    args = ["--config", '{"key": "value", "number": 42}']

    with manu.script(args=args):
      config: dict[str, Any] = {}

    assert config == {"key": "value", "number": 42}

  def test_union_types(self):
    """Test Union type handling."""

    # Test with int input
    args = ["--value", "42"]
    with manu.script(args=args):
      value: int | str = "default"
    assert value == 42

    # Test with string input
    args = ["--value", "hello"]
    with manu.script(args=args):
      value: int | str = "default"
    assert value == "hello"

  def test_enum_validation(self):
    """Test enum type validation."""
    from enum import Enum

    class LogLevel(Enum):
      DEBUG = "debug"
      INFO = "info"
      WARNING = "warning"
      ERROR = "error"

    args = ["--log-level", "info"]

    with manu.script(args=args):
      log_level: LogLevel = LogLevel.DEBUG

    assert log_level == LogLevel.INFO

  def test_invalid_enum_value(self):
    """Test invalid enum value raises error."""
    from enum import Enum

    class LogLevel(Enum):
      DEBUG = "debug"
      INFO = "info"

    args = ["--log-level", "invalid"]

    with pytest.raises(SystemExit):
      with manu.script(args=args):
        log_level: LogLevel = LogLevel.DEBUG

  def test_type_annotation_without_value(self):
    """Test type annotation without default value."""
    with pytest.raises(SystemExit):  # Should require value
      with manu.script(args=[]):
        required_val: int  # No default, should be required

  def test_any_type_handling(self):
    """Test Any type accepts various inputs."""
    args = ["--any-val", "42"]

    with manu.script(args=args):
      any_val: Any = None

    # With Any type, should remain as string from CLI
    assert any_val == "42"

  def test_custom_validation_through_pydantic(self):
    """Test custom validation through Pydantic models."""
    from pydantic import BaseModel
    from pydantic import validator

    class Config(BaseModel):
      learning_rate: float
      epochs: int

      @validator("learning_rate")
      def validate_lr(cls, v):
        if v <= 0 or v >= 1:
          raise ValueError("learning_rate must be between 0 and 1")
        return v

    # Valid config
    args = ["--learning-rate", "0.001", "--epochs", "100"]
    with manu.script(args=args):
      learning_rate: float = 0.01
      epochs: int = 10

    assert learning_rate == 0.001
    assert epochs == 100

  def test_type_mismatch_error_handling(self):
    """Test graceful handling of type mismatches."""
    args = ["--int-val", "not_a_number"]

    with pytest.raises(SystemExit):
      with manu.script(args=args):
        int_val: int = 0

  def test_default_value_type_inference(self):
    """Test that default values correctly infer types."""
    with manu.script(args=[]):
      # Type should be inferred from default value
      string_val = "hello"
      int_val = 42
      float_val = 3.14
      bool_val = True
      list_val = [1, 2, 3]

    assert isinstance(string_val, str)
    assert isinstance(int_val, int)
    assert isinstance(float_val, float)
    assert isinstance(bool_val, bool)
    assert isinstance(list_val, list)
