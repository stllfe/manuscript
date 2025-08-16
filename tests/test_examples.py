"""Test examples from the README to ensure documentation accuracy."""

from pathlib import Path

import manu
import manu.conf as conf


class TestReadmeExamples:
  """Test that all examples from README.md work correctly."""

  def test_basic_readme_example(self):
    """Test the main example from README."""
    args = [
      "--exp-name",
      "test_experiment",
      "--out-dir",
      "/tmp/test",
      "--learning-rate",
      "0.001",
      "--max-iters",
      "1000000",
    ]

    with manu.script(args=args) as script_values:
      exp_name: str = ...  # required
      out_dir: Path = ...  # rich types supported
      device = "cpu"  # with default, type hint may be omitted
      learning_rate = 6e-4  # inline comments become help text
      beta = 0.9  #! comments with ! are not rendered as help text
      max_iters = 6000000
      """this is a docstring for max_iters as well"""
      do_something: conf.Fixed[bool] = True  #! configure args via hints

    # Verify values
    assert exp_name == "test_experiment"
    assert out_dir == Path("/tmp/test")
    assert device == "cpu"
    assert learning_rate == 0.001
    assert beta == 0.9
    assert max_iters == 1000000
    assert do_something is True

    # Verify script.values access
    assert script_values["exp_name"] == "test_experiment"
    assert len(script_values) >= 6

  def test_pydantic_types_example(self):
    """Test Pydantic types example from README."""
    from pydantic import FilePath
    from pydantic import PositiveInt

    # Create a test file for FilePath validation
    test_file = Path("/tmp/test_tokenizer.txt")
    test_file.touch()

    try:
      args = ["--num-epochs", "100", "--tokenizer-path", str(test_file)]

      with manu.script(args=args):
        num_epochs: PositiveInt = 50
        tokenizer_path: FilePath = Path("default")

      assert num_epochs == 100
      assert tokenizer_path == test_file

    finally:
      test_file.unlink(missing_ok=True)

  def test_config_file_example(self, temp_config_file):
    """Test config file example from README."""
    # Create base config as shown in README
    config_content = """
learning_rate = 1e-3
beta = 0.99
device = "cuda"
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    args = ["-c", temp_config_file, "--exp-name", "gpu-model", "--out-dir", "./outputs", "--beta", "0.95"]

    with manu.script(args=args):
      exp_name: str = ...
      out_dir: Path = ...
      device = "cpu"
      learning_rate = 6e-4
      beta = 0.9

    assert exp_name == "gpu-model"
    assert out_dir == Path("./outputs")
    assert device == "cuda"  # from config
    assert learning_rate == 1e-3  # from config
    assert beta == 0.95  # CLI override

  def test_interpolation_example(self):
    """Test variable interpolation example from README."""
    args = ["--exp-name", "test-@{beta}", "--beta", "0.85"]

    with manu.script(args=args):
      exp_name = "default"
      beta = 0.9

    assert exp_name == "test-0.85"
    assert beta == 0.85

  def test_hook_examples(self, env_vars):
    """Test built-in hooks examples from README."""
    import os

    # Set up environment
    os.environ["USER"] = "testuser"
    os.environ["CUDA_DEVICE"] = "cuda:1"

    args = ["--exp-name", "@env:USER", "--device", "@env:CUDA_DEVICE"]

    with manu.script(args=args):
      exp_name = "default"
      device = "cpu"

    assert exp_name == "testuser"
    assert device == "cuda:1"

  def test_custom_hook_example(self):
    """Test custom hook example from README."""
    from manu import ValidationContext
    from manu import hook

    @hook("gpu")
    def gpu_hook(val: str, ctx: ValidationContext) -> str:
      if val == "free":
        return "cuda:0"  # Simplified version
      return "cuda:0"

    args = ["--device", "@gpu:free"]

    with manu.script(args=args):
      device = "cpu"

    assert device == "cuda:0"

  def test_capture_final_values_example(self):
    """Test capturing final configuration example."""
    args = ["--exp-name", "test_experiment", "--device", "cuda", "--learning-rate", "0.001"]

    with manu.script(args=args) as config:
      exp_name: str = ...
      device = "cpu"
      learning_rate = 6e-4

    # Test that config contains final values
    assert config["exp_name"] == "test_experiment"
    assert config["device"] == "cuda"
    assert config["learning_rate"] == 0.001

    # This would be used for logging
    # wandb.config.update(config)  # Example usage

  def test_advanced_configuration_example(self):
    """Test advanced configuration with settings."""
    settings = (
      conf.HelptextFromCommentsOff,
      conf.PositionalRequiredArgs,
    )

    args = ["required_arg_value"]

    with manu.script(config=settings, args=args):
      secret: conf.Suppress[str] = "hidden-key"
      model_type: conf.Fixed[str] = "transformer"
      verbose: bool = False
      required_arg: str = ...

    assert secret == "hidden-key"
    assert model_type == "transformer"
    assert verbose is False
    assert required_arg == "required_arg_value"

  def test_alternative_inline_syntax_example(self):
    """Test alternative inline syntax from README."""
    manu.script.description = "Train a transformer model"
    manu.script.config = (conf.HelptextFromCommentsOff, conf.FlagCreatePairsOff)
    manu.script.init(args=["--verbose"])

    secret: conf.Suppress[str] = "hidden-key"
    model_type: conf.Fixed[str] = "transformer"
    verbose: bool = False

    manu.script.done()

    assert secret == "hidden-key"
    assert model_type == "transformer"
    assert verbose is True

  def test_simple_py_example(self):
    """Test that simple.py example works."""
    # This tests the exact content from simple.py
    args = ["--exp-name", "test_simple", "--out-dir", "/tmp/simple_test", "--learning-rate", "0.002", "--beta", "0.95"]

    with manu.script(args=args):
      exp_name: str = ...  # required
      out_dir: Path = ...  # rich types supported
      device = "cpu"  # with default, type hint is optional
      learning_rate = 6e-4  # inline comments become help text
      beta = 0.9  #! comments with ! are ignored
      max_iters = 6000000
      """this docstring also becomes help text"""

    # Verify the results match simple.py expectations
    assert exp_name == "test_simple"
    assert out_dir == Path("/tmp/simple_test")
    assert device == "cpu"
    assert learning_rate == 0.002
    assert beta == 0.95
    assert max_iters == 6000000

    # Test script.values access as shown in simple.py
    values = manu.script.values
    assert "exp_name" in values
    assert "learning_rate" in values
    assert isinstance(values, dict)
