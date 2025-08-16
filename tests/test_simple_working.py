"""Simple working tests that should pass with the improved frame handling."""

from pathlib import Path

import manu


def test_basic_script_functionality():
  """Test basic script functionality with fallback frame handling."""

  # This should work now with the improved error handling
  with manu.script(args=["--exp-name", "test", "--out-dir", "/tmp"]):
    exp_name: str = ...
    out_dir: Path = ...
    device = "cpu"

  assert exp_name == "test"
  assert out_dir == Path("/tmp")
  assert device == "cpu"


def test_script_with_defaults_only():
  """Test script with only default values."""

  with manu.script(args=[]):
    device = "cpu"
    learning_rate = 6e-4

  assert device == "cpu"
  assert learning_rate == 6e-4


def test_script_values_access():
  """Test accessing script values."""

  with manu.script(args=["--name", "test"]) as config:
    name = "default"
    value = 42

  assert config["name"] == "test"
  assert config["value"] == 42


def test_type_coercion():
  """Test type coercion."""

  with manu.script(args=["--num", "42", "--flag", "true"]):
    num: int = 0
    flag: bool = False

  print(f"num = {num}, flag = {flag}")  # Debug print
  assert num == 42
  assert flag is True


def test_config_file_basic(tmp_path):
  """Test basic config file functionality."""

  config_file = tmp_path / "config.py"
  config_file.write_text("""
learning_rate = 1e-3
device = "cuda"
""")

  with manu.script(args=["-c", str(config_file)]):
    learning_rate = 6e-4
    device = "cpu"

  assert learning_rate == 1e-3
  assert device == "cuda"


if __name__ == "__main__":
  # Test individually for debugging
  test_script_with_defaults_only()
  print("test_script_with_defaults_only passed")

  test_type_coercion()
  print("test_type_coercion passed")

  print("Basic tests work!")
