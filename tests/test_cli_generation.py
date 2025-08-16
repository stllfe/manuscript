"""Test CLI generation and argument parsing."""

import pytest

import manu


class TestCLIGeneration:
  """Test CLI argument generation and parsing functionality."""

  def test_help_generation(self, capsys):
    """Test that help text is generated correctly."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--help"]):
        exp_name: str = ...  # required arg
        device = "cpu"  # with help comment
        learning_rate = 6e-4  # learning rate for training

    captured = capsys.readouterr()
    assert "exp-name" in captured.out
    assert "device" in captured.out
    assert "learning-rate" in captured.out
    assert "learning rate for training" in captured.out

  def test_comments_as_help_text(self, capsys):
    """Test that inline comments become help text."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--help"]):
        device = "cpu"  # Device to use for training
        batch_size = 32  # Number of samples per batch

    captured = capsys.readouterr()
    assert "Device to use for training" in captured.out
    assert "Number of samples per batch" in captured.out

  def test_exclamation_comments_ignored(self, capsys):
    """Test that comments with ! are not shown in help."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--help"]):
        visible = "cpu"  # This should appear
        hidden = 0.9  #! This should not appear

    captured = capsys.readouterr()
    assert "This should appear" in captured.out
    assert "This should not appear" not in captured.out

  def test_docstring_help_text(self, capsys):
    """Test that docstrings become help text."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--help"]):
        max_iters = 6000000
        """Maximum number of training iterations"""

    captured = capsys.readouterr()
    assert "Maximum number of training iterations" in captured.out

  def test_long_and_short_argument_names(self):
    """Test kebab-case conversion and argument naming."""
    args = ["--learning-rate", "0.001", "--batch-size", "64", "--use-batch-norm", "true"]

    with manu.script(args=args):
      learning_rate: float = 1e-4
      batch_size: int = 32
      use_batch_norm: bool = False

    assert learning_rate == 0.001
    assert batch_size == 64
    assert use_batch_norm is True

  def test_boolean_flags(self):
    """Test boolean flag conversion."""
    # Test --flag and --no-flag patterns
    args_true = ["--verbose"]
    args_false = ["--no-verbose"]

    with manu.script(args=args_true):
      verbose: bool = False

    assert verbose is True

    with manu.script(args=args_false):
      verbose: bool = False

    assert verbose is False

  def test_list_arguments(self):
    """Test list/sequence argument parsing."""
    args = ["--tags", "tag1", "tag2", "tag3"]

    with manu.script(args=args):
      tags: list[str] = []

    assert tags == ["tag1", "tag2", "tag3"]

  def test_enum_arguments(self):
    """Test enum argument parsing."""
    from enum import Enum

    class Device(Enum):
      CPU = "cpu"
      GPU = "gpu"
      TPU = "tpu"

    args = ["--device", "gpu"]

    with manu.script(args=args):
      device: Device = Device.CPU

    assert device == Device.GPU

  def test_description_from_docstring(self, capsys):
    """Test that module docstring becomes CLI description."""
    script_content = '''
"""This is a test script for training models."""

import manu

with manu.script(args=["--help"]):
  learning_rate = 1e-3
'''

    with pytest.raises(SystemExit):
      exec(script_content)

    captured = capsys.readouterr()
    assert "This is a test script for training models" in captured.out

  def test_custom_description(self, capsys):
    """Test custom description override."""
    with pytest.raises(SystemExit):
      with manu.script(description="Custom CLI description", args=["--help"]):
        learning_rate = 1e-3

    captured = capsys.readouterr()
    assert "Custom CLI description" in captured.out

  def test_positional_vs_optional_args(self):
    """Test distinction between positional and optional arguments."""
    args = ["test_exp", "--learning-rate", "0.001"]

    with manu.script(args=args):
      exp_name: str = ...  # required, could be positional
      learning_rate = 1e-4  # optional with default

    assert exp_name == "test_exp"
    assert learning_rate == 0.001

  def test_invalid_arguments_error(self):
    """Test that invalid arguments produce helpful error."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--nonexistent-arg", "value"]):
        valid_arg = "default"
