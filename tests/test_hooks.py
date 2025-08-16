"""Test hooks system including built-in and custom hooks."""

import os

from pathlib import Path

import pytest

import manu

from manu import ValidationContext
from manu import hook
from manu.hooks import HookRegistry


class TestBuiltInHooks:
  """Test built-in hook functionality."""

  def test_env_hook(self, env_vars):
    """Test @env:VAR environment variable hook."""
    os.environ["TEST_VAR"] = "test_value"
    os.environ["CUDA_DEVICE"] = "cuda:1"

    args = ["--device", "@env:CUDA_DEVICE", "--name", "@env:TEST_VAR"]

    with manu.script(args=args):
      device = "cpu"
      name = "default"

    assert device == "cuda:1"
    assert name == "test_value"

  def test_env_hook_missing_var(self):
    """Test @env hook with missing environment variable."""
    args = ["--device", "@env:NONEXISTENT_VAR"]

    with pytest.raises(Exception):  # Should raise error for missing env var
      with manu.script(args=args):
        device = "cpu"

  def test_import_hook(self):
    """Test @import:module.attr hook."""
    args = ["--pi-value", "@import:math.pi", "--path-sep", "@import:os.sep"]

    with manu.script(args=args):
      pi_value: float = 3.0
      path_sep: str = "/"

    assert abs(pi_value - 3.14159) < 0.001
    assert path_sep in ["/", "\\"]  # Unix or Windows

  def test_import_hook_invalid_module(self):
    """Test @import hook with invalid module."""
    args = ["--value", "@import:nonexistent.module.attr"]

    with pytest.raises(Exception):
      with manu.script(args=args):
        value = "default"

  def test_value_hook_simple(self):
    """Test @value:var and @{var} variable interpolation."""
    args = ["--name", "test", "--message", "Hello @{name}!", "--copy", "@value:name"]

    with manu.script(args=args):
      name = "default"
      message = "default message"
      copy = "default"

    assert name == "test"
    assert message == "Hello test!"
    assert copy == "test"

  def test_value_hook_nested(self):
    """Test @value hook with nested path access."""
    # This would need to be implemented if the library supports nested config
    args = ["--simple", "42"]

    with manu.script(args=args):
      simple = 0

    assert simple == 42
    # Note: This test might need adjustment based on actual implementation

  def test_interpolation_multiple_variables(self):
    """Test string interpolation with multiple variables."""
    args = ["--exp-name", "experiment", "--version", "v1.0", "--full-name", "@{exp_name}_@{version}_final"]

    with manu.script(args=args):
      exp_name = "default"
      version = "v0"
      full_name = "default_name"

    assert exp_name == "experiment"
    assert version == "v1.0"
    assert full_name == "experiment_v1.0_final"


class TestCustomHooks:
  """Test custom hook registration and usage."""

  def test_custom_hook_registration(self):
    """Test registering and using custom hooks."""

    @hook("multiply")
    def multiply_hook(value: str, ctx: ValidationContext) -> int:
      return int(value) * 2

    args = ["--doubled", "@multiply:21"]

    with manu.script(args=args):
      doubled = 0

    assert doubled == 42

  def test_custom_hook_with_context(self):
    """Test custom hook that uses validation context."""

    @hook("add_to_base")
    def add_hook(value: str, ctx: ValidationContext) -> int:
      base = ctx.get_nested_value("base_value")
      return base + int(value)

    args = ["--base-value", "10", "--result", "@add_to_base:5"]

    with manu.script(args=args):
      base_value = 0
      result = 0

    assert base_value == 10
    assert result == 15

  def test_custom_hook_complex_logic(self, env_vars):
    """Test custom hook with complex logic."""

    @hook("gpu")
    def gpu_hook(value: str, ctx: ValidationContext) -> str:
      if value == "auto":
        # Mock auto-detection logic
        return "cuda:0" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
      elif value == "free":
        # Mock finding free GPU
        return "cuda:1"
      return value

    # Test auto mode without CUDA
    args = ["--device", "@gpu:auto"]
    with manu.script(args=args):
      device = "cpu"
    assert device == "cpu"

    # Test auto mode with CUDA
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    with manu.script(args=args):
      device = "cpu"
    assert device == "cuda:0"

    # Test free mode
    args = ["--device", "@gpu:free"]
    with manu.script(args=args):
      device = "cpu"
    assert device == "cuda:1"

  def test_hook_duplicate_registration_error(self):
    """Test that registering duplicate hooks raises error."""

    @hook("test_hook")
    def first_hook(value: str, ctx: ValidationContext) -> str:
      return value

    with pytest.raises(ValueError, match="Handler already registered"):

      @hook("test_hook")
      def second_hook(value: str, ctx: ValidationContext) -> str:
        return value

  def test_hook_unregistered_error(self):
    """Test error when using unregistered hook."""
    args = ["--value", "@nonexistent:arg"]

    with pytest.raises(Exception):
      with manu.script(args=args):
        value = "default"

  def test_hook_error_handling(self):
    """Test error handling within custom hooks."""

    @hook("error_hook")
    def error_hook(value: str, ctx: ValidationContext) -> str:
      raise ValueError("Custom hook error")

    args = ["--value", "@error_hook:arg"]

    with pytest.raises(Exception):
      with manu.script(args=args):
        value = "default"

  def test_hook_registry_clear(self):
    """Test clearing hook registry."""

    @hook("temp_hook")
    def temp_hook(value: str, ctx: ValidationContext) -> str:
      return "processed"

    # Hook should work
    args = ["--value", "@temp_hook:test"]
    with manu.script(args=args):
      temp_value = "default"
    assert temp_value == "processed"

    # Clear registry
    HookRegistry.clear()

    # Hook should no longer work
    with pytest.raises(Exception):
      with manu.script(args=args):
        temp_value = "default"


class TestHookEdgeCases:
  """Test edge cases and complex hook scenarios."""

  def test_hook_with_special_characters(self):
    """Test hooks with special characters in values."""

    @hook("special")
    def special_hook(value: str, ctx: ValidationContext) -> str:
      return f"processed_{value}"

    args = ["--value", "@special:test-with-dashes_and_underscores.and.dots"]

    with manu.script(args=args):
      special_value = "default"

    assert special_value == "processed_test-with-dashes_and_underscores.and.dots"

  def test_nested_interpolation(self):
    """Test nested variable interpolation."""
    args = [
      "--base",
      "hello",
      "--suffix",
      "world",
      "--message",
      "@{base}_@{suffix}",
      "--meta",
      "prefix_@{message}_suffix",
    ]

    with manu.script(args=args):
      base = "default"
      suffix = "default"
      message = "default"
      meta = "default"

    assert base == "hello"
    assert suffix == "world"
    assert message == "hello_world"
    assert meta == "prefix_hello_world_suffix"

  def test_hook_return_type_conversion(self):
    """Test that hook return values are properly converted."""

    @hook("return_int")
    def int_hook(value: str, ctx: ValidationContext) -> int:
      return 42

    @hook("return_path")
    def path_hook(value: str, ctx: ValidationContext) -> Path:
      return Path("/test/path")

    args = ["--num", "@return_int:", "--path", "@return_path:"]

    with manu.script(args=args):
      num: int = 0
      path: Path = Path(".")

    assert num == 42
    assert path == Path("/test/path")
