"""Test basic functionality of manu:script."""

from pathlib import Path

import pytest

import manu


class TestBasicScriptFunctionality:
  """Test core script context manager and variable capture."""

  def test_context_manager_with_required_args(self):
    """Test basic context manager usage with required arguments."""
    test_args = ["--exp-name", "test", "--out-dir", "/tmp"]

    with manu.script(args=test_args) as config:
      exp_name: str = ...
      out_dir: Path = ...
      device = "cpu"
      learning_rate = 6e-4

    assert exp_name == "test"
    assert out_dir == Path("/tmp")
    assert device == "cpu"
    assert learning_rate == 6e-4
    assert config["exp_name"] == "test"
    assert config["out_dir"] == Path("/tmp")

  def test_context_manager_with_defaults_only(self):
    """Test context manager with only default values."""
    with manu.script(args=[]) as config:
      device = "cpu"
      learning_rate = 6e-4
      batch_size = 32

    assert device == "cpu"
    assert learning_rate == 6e-4
    assert batch_size == 32
    assert len(config) == 3

  def test_init_done_pattern(self):
    """Test init/done pattern instead of context manager."""
    manu.script.init(args=["--device", "gpu"])

    device = "cpu"
    learning_rate = 1e-3

    manu.script.done()

    assert device == "gpu"
    assert learning_rate == 1e-3

  def test_script_values_property(self):
    """Test script.values property access."""
    with manu.script(args=["--name", "test"]):
      name = "default"
      value = 42

    values = manu.script.values
    assert values["name"] == "test"
    assert values["value"] == 42
    assert isinstance(values, dict)

    # Should be read-only
    with pytest.raises(TypeError):
      values["name"] = "modified"

  def test_type_coercion(self):
    """Test automatic type coercion from CLI strings."""
    args = ["--learning-rate", "0.001", "--batch-size", "64", "--use-dropout", "true", "--model-path", "/tmp/model.pt"]

    with manu.script(args=args):
      learning_rate: float = 1e-4
      batch_size: int = 32
      use_dropout: bool = False
      model_path: Path = Path(".")

    assert learning_rate == 0.001
    assert batch_size == 64
    assert use_dropout is True
    assert model_path == Path("/tmp/model.pt")

  def test_ellipsis_required_args(self):
    """Test that ellipsis (...) marks required arguments."""
    with pytest.raises(SystemExit):  # tyro exits on missing required args
      with manu.script(args=[]):
        required_arg: str = ...
        optional_arg = "default"

  def test_private_variables_ignored(self):
    """Test that private variables (starting with _) are ignored."""
    with manu.script(args=[]):
      public_var = "public"
      _private_var = "private"
      __dunder_var = "dunder"

    assert "public_var" in manu.script.values
    assert "_private_var" not in manu.script.values
    assert "__dunder_var" not in manu.script.values

  def test_script_without_init_raises(self):
    """Test that calling done() without init() raises error."""
    with pytest.raises(RuntimeError, match="Script isn't initialized"):
      manu.script.done()

  def test_multiple_script_sections_error(self):
    """Test that overlapping script sections work correctly."""
    # First section
    with manu.script(args=["--var1", "test1"]):
      var1 = "default1"

    # Second section should work independently
    with manu.script(args=["--var2", "test2"]):
      var2 = "default2"

    assert var1 == "test1"
    assert var2 == "test2"
