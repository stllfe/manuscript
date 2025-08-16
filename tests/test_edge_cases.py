"""Test error handling and edge cases."""

import sys

from pathlib import Path

import pytest

import manu


class TestErrorHandling:
  """Test error handling and edge cases."""

  def test_script_not_initialized_error(self):
    """Test error when done() called without init()."""
    with pytest.raises(RuntimeError, match="Script isn't initialized"):
      manu.script.done()

  def test_empty_script_section(self):
    """Test script section with no variables."""
    with manu.script(args=[]) as config:
      pass  # No variables defined

    assert len(config) == 0

  def test_syntax_error_in_script_section(self):
    """Test handling of syntax errors in script section."""
    # This is tricky to test directly, but we can test invalid code patterns
    with pytest.raises(RuntimeError):
      # Simulate parsing invalid code
      from manu.parsing import get_script_vars

      get_script_vars("test.py", "invalid syntax !!!", {})

  def test_missing_required_arguments(self):
    """Test error when required arguments are missing."""
    with pytest.raises(SystemExit):
      with manu.script(args=[]):
        required_arg: str = ...

  def test_invalid_type_conversion(self):
    """Test error handling for invalid type conversions."""
    args = ["--number", "not_a_number"]

    with pytest.raises(SystemExit):
      with manu.script(args=args):
        number: int = 0

  def test_nonexistent_config_file_error(self):
    """Test error for nonexistent config file."""
    args = ["-c", "/nonexistent/file.py"]

    with pytest.raises(FileNotFoundError):
      with manu.script(args=args):
        value = "default"

  def test_invalid_config_file_syntax(self, temp_config_file):
    """Test error for config file with invalid syntax."""
    with open(temp_config_file, "w") as f:
      f.write("invalid python syntax !!!")

    args = ["-c", temp_config_file]

    with pytest.raises(Exception):  # Should raise some parsing error
      with manu.script(args=args):
        value = "default"

  def test_circular_hook_reference(self):
    """Test detection/handling of circular hook references."""
    from manu import ValidationContext
    from manu import hook

    @hook("circular")
    def circular_hook(value: str, ctx: ValidationContext) -> str:
      # This creates a circular reference
      return ctx.get_nested_value("result")

    args = ["--result", "@circular:test"]

    # Should handle gracefully or raise appropriate error
    with pytest.raises(Exception):
      with manu.script(args=args):
        result = "default"

  def test_hook_with_invalid_return_type(self):
    """Test hook returning incompatible type."""
    from manu import ValidationContext
    from manu import hook

    @hook("invalid_return")
    def invalid_hook(value: str, ctx: ValidationContext) -> object:
      return object()  # Can't serialize/use this

    args = ["--value", "@invalid_return:test"]

    with pytest.raises(Exception):
      with manu.script(args=args):
        value: str = "default"

  def test_deeply_nested_variable_access(self):
    """Test deeply nested variable access that might fail."""
    args = ["--nested", "@value:very.deep.nested.path.that.does.not.exist"]

    with pytest.raises(Exception):
      with manu.script(args=args):
        nested = "default"

  def test_unicode_and_special_characters(self):
    """Test handling of unicode and special characters."""
    args = ["--unicode", "héllo wörld 🚀", "--special", "!@#$%^&*()"]

    with manu.script(args=args):
      unicode_val = "default"
      special = "default"

    assert unicode_val == "héllo wörld 🚀"
    assert special == "!@#$%^&*()"

  def test_very_long_argument_values(self):
    """Test handling of very long argument values."""
    long_value = "x" * 10000
    args = ["--long-value", long_value]

    with manu.script(args=args):
      long_value_var = "default"

    assert long_value_var == long_value

  def test_empty_string_arguments(self):
    """Test handling of empty string arguments."""
    args = ["--empty", ""]

    with manu.script(args=args):
      empty = "default"

    assert empty == ""

  def test_whitespace_only_arguments(self):
    """Test handling of whitespace-only arguments."""
    args = ["--whitespace", "   \t\n   "]

    with manu.script(args=args):
      whitespace = "default"

    assert whitespace == "   \t\n   "


class TestEdgeCases:
  """Test various edge cases and boundary conditions."""

  def test_variable_name_edge_cases(self):
    """Test variables with edge case names."""
    args = ["--a", "short", "--very-long-variable-name-with-many-hyphens", "long"]

    with manu.script(args=args):
      a = "default"
      very_long_variable_name_with_many_hyphens = "default"

    assert a == "short"
    assert very_long_variable_name_with_many_hyphens == "long"

  def test_mixed_argument_styles(self):
    """Test mixing different argument styles."""
    args = [
      "--kebab-case",
      "kebab",
      "--snake_case",
      "snake",  # This might not work as expected
      "--camelCase",
      "camel",  # This definitely won't work as expected
    ]

    with manu.script(args=args):
      kebab_case = "default"
      # Note: snake_case and camelCase won't work with kebab-case CLI

    assert kebab_case == "kebab"

  def test_number_edge_cases(self):
    """Test various number formats and edge cases."""
    args = ["--int-max", str(sys.maxsize), "--float-scientific", "1.5e-10", "--negative", "-42", "--zero", "0"]

    with manu.script(args=args):
      int_max: int = 0
      float_scientific: float = 0.0
      negative: int = 0
      zero: int = 1

    assert int_max == sys.maxsize
    assert abs(float_scientific - 1.5e-10) < 1e-15
    assert negative == -42
    assert zero == 0

  def test_boolean_edge_cases(self):
    """Test various boolean representations."""
    test_cases = [
      (["--flag", "true"], True),
      (["--flag", "True"], True),
      (["--flag", "1"], True),
      (["--flag", "false"], False),
      (["--flag", "False"], False),
      (["--flag", "0"], False),
    ]

    for args, expected in test_cases:
      with manu.script(args=args):
        flag: bool = None
      assert flag == expected

  def test_list_edge_cases(self):
    """Test edge cases with list arguments."""
    # Empty list
    args = ["--empty-list"]
    with manu.script(args=args):
      empty_list: list[str] = ["default"]
    # Behavior depends on implementation

    # Single item
    args = ["--single", "item"]
    with manu.script(args=args):
      single: list[str] = []
    assert single == ["item"]

  def test_path_edge_cases(self):
    """Test edge cases with Path arguments."""
    args = [
      "--relative",
      "relative/path",
      "--absolute",
      "/absolute/path",
      "--current",
      ".",
      "--parent",
      "..",
      "--home",
      "~/home/path",
    ]

    with manu.script(args=args):
      relative: Path = Path("default")
      absolute: Path = Path("default")
      current: Path = Path("default")
      parent: Path = Path("default")
      home: Path = Path("default")

    assert relative == Path("relative/path")
    assert absolute == Path("/absolute/path")
    assert current == Path(".")
    assert parent == Path("..")
    assert home == Path("~/home/path")  # Note: ~ won't be expanded automatically

  def test_concurrent_script_usage(self):
    """Test that multiple script contexts don't interfere."""

    # This tests thread safety to some degree
    def run_script(args, expected):
      with manu.script(args=args):
        value = "default"
      return value

    result1 = run_script(["--value", "first"], "first")
    result2 = run_script(["--value", "second"], "second")

    assert result1 == "first"
    assert result2 == "second"

  def test_script_reuse_after_error(self):
    """Test that script can be reused after an error."""
    # First attempt with error
    with pytest.raises(SystemExit):
      with manu.script(args=[]):
        required: str = ...

    # Second attempt should work
    with manu.script(args=["--required", "value"]):
      required: str = ...

    assert required == "value"

  def test_config_file_with_complex_imports(self, temp_config_file):
    """Test config file with complex import scenarios."""
    config_content = """
import sys
import os.path
from pathlib import Path
from typing import Dict, List

# Complex calculations
base_path = Path(__file__).parent
data_dir = base_path / "data"
model_configs = {
    "small": {"layers": 6, "heads": 8},
    "large": {"layers": 12, "heads": 16}
}
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
"""

    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file]

    with manu.script(args=args):
      data_dir: Path = Path(".")
      model_configs: dict = {}
      python_version: str = "3.0"

    assert isinstance(data_dir, Path)
    assert "small" in model_configs
    assert "large" in model_configs
    assert python_version.startswith("3.")
