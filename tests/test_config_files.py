"""Test config file loading and precedence."""

from pathlib import Path

import pytest

import manu


class TestConfigFiles:
  """Test config file loading and CLI precedence."""

  def test_config_file_loading(self, temp_config_file, sample_config_content):
    """Test basic config file loading."""
    # Write config content
    with open(temp_config_file, "w") as f:
      f.write(sample_config_content)

    args = ["-c", temp_config_file]

    with manu.script(args=args):
      learning_rate = 1e-4
      beta = 0.5
      device = "cpu"
      batch_size = 16

    assert learning_rate == 1e-3  # from config
    assert beta == 0.99  # from config
    assert device == "cuda"  # from config
    assert batch_size == 32  # from config

  def test_config_file_with_cli_override(self, temp_config_file):
    """Test that CLI args override config file values."""
    config_content = """
learning_rate = 1e-3
device = "cuda"
batch_size = 32
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file, "--learning-rate", "2e-3", "--device", "cpu"]

    with manu.script(args=args):
      learning_rate = 1e-4
      device = "gpu"
      batch_size = 16

    assert learning_rate == 2e-3  # CLI override
    assert device == "cpu"  # CLI override
    assert batch_size == 32  # from config file

  def test_with_flag_alias(self, temp_config_file):
    """Test --with flag as alias for -c."""
    config_content = """
model_name = "transformer"
hidden_size = 512
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["--with", temp_config_file]

    with manu.script(args=args):
      model_name = "default"
      hidden_size = 256

    assert model_name == "transformer"
    assert hidden_size == 512

  def test_nonexistent_config_file(self):
    """Test error handling for nonexistent config files."""
    args = ["-c", "/nonexistent/config.py"]

    with pytest.raises(FileNotFoundError):
      with manu.script(args=args):
        learning_rate = 1e-4

  def test_invalid_config_syntax(self, temp_config_file):
    """Test error handling for invalid config syntax."""
    with open(temp_config_file, "w") as f:
      f.write("invalid python syntax !!!!")

    args = ["-c", temp_config_file]

    with pytest.raises(RuntimeError):
      with manu.script(args=args):
        learning_rate = 1e-4

  def test_config_with_required_args(self, temp_config_file):
    """Test config file providing required arguments."""
    config_content = """
exp_name = "config_experiment"
out_dir = "/tmp/outputs"
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file]

    with manu.script(args=args):
      exp_name: str = ...
      out_dir: Path = ...
      device = "cpu"

    assert exp_name == "config_experiment"
    assert out_dir == Path("/tmp/outputs")
    assert device == "cpu"

  def test_config_precedence_order(self, temp_config_file):
    """Test precedence: defaults < config < CLI."""
    config_content = """
learning_rate = 5e-4  # config overrides default
batch_size = 64       # config provides new value
device = "cuda"       # will be overridden by CLI
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file, "--device", "tpu"]

    with manu.script(args=args):
      learning_rate = 1e-3  # default
      batch_size = 32  # default
      device = "cpu"  # default
      epochs = 10  # not in config, keeps default

    assert learning_rate == 5e-4  # config override
    assert batch_size == 64  # config value
    assert device == "tpu"  # CLI override
    assert epochs == 10  # unchanged default

  def test_config_with_complex_types(self, temp_config_file):
    """Test config file with complex Python types."""
    config_content = """
from pathlib import Path

model_paths = ["/model1.pt", "/model2.pt"]
output_dir = Path("/complex/path")
hyperparams = {"lr": 1e-3, "weight_decay": 1e-5}
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file]

    with manu.script(args=args):
      model_paths: list[str] = []
      output_dir: Path = Path(".")
      hyperparams: dict = {}

    assert model_paths == ["/model1.pt", "/model2.pt"]
    assert output_dir == Path("/complex/path")
    assert hyperparams == {"lr": 1e-3, "weight_decay": 1e-5}

  def test_config_with_imports(self, temp_config_file):
    """Test config file that imports modules."""
    config_content = """
import os
from math import pi

data_dir = os.path.expanduser("~/data")
circle_area_factor = pi
num_workers = os.cpu_count()
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file]

    with manu.script(args=args):
      data_dir = "/default"
      circle_area_factor = 3.14
      num_workers = 1

    assert data_dir == str(Path.home() / "data")
    assert abs(circle_area_factor - 3.14159) < 0.001
    assert isinstance(num_workers, int)
    assert num_workers > 0
