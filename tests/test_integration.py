"""Integration tests that test complete workflows."""

import os

from pathlib import Path

import pytest

import manu

from manu import ValidationContext
from manu import hook


class TestIntegrationWorkflows:
  """Test complete end-to-end workflows."""

  def test_complete_ml_training_workflow(self, temp_config_file, env_vars):
    """Test a complete ML training script workflow."""
    # Set up environment
    os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
    os.environ["WANDB_PROJECT"] = "test_project"

    # Create config file
    config_content = """
# Base configuration
model_type = "transformer"
hidden_size = 512
num_layers = 6
learning_rate = 1e-4
batch_size = 32
max_epochs = 100
"""
    with open(temp_config_file, "w") as f:
      f.write(config_content)

    # Define custom hooks
    @hook("gpu_count")
    def gpu_count_hook(value: str, ctx: ValidationContext) -> int:
      devices = os.environ.get("CUDA_VISIBLE_DEVICES", "")
      return len(devices.split(",")) if devices else 0

    @hook("experiment_name")
    def exp_name_hook(value: str, ctx: ValidationContext) -> str:
      model = ctx.get_nested_value("model_type")
      lr = ctx.get_nested_value("learning_rate")
      return f"{model}_lr{lr}_{value}"

    # Run the script
    args = [
      "-c",
      temp_config_file,
      "--model-type",
      "gpt",  # Override config
      "--num-gpus",
      "@gpu_count:",
      "--exp-name",
      "@experiment_name:v1",
      "--wandb-project",
      "@env:WANDB_PROJECT",
    ]

    with manu.script(args=args) as config:
      # Required arguments
      exp_name: str = ...
      output_dir: Path = ...

      # Model configuration
      model_type = "bert"
      hidden_size = 256
      num_layers = 4

      # Training configuration
      learning_rate = 1e-3
      batch_size = 16
      max_epochs = 50

      # Hardware configuration
      num_gpus = 1

      # Experiment tracking
      wandb_project = "default_project"

    # Verify the complete configuration
    assert exp_name.startswith("gpt_lr0.0001_v1")  # Uses hook with config values
    assert model_type == "gpt"  # CLI override
    assert hidden_size == 512  # From config file
    assert learning_rate == 1e-4  # From config file
    assert num_gpus == 2  # From GPU count hook
    assert wandb_project == "test_project"  # From environment

    # Verify config dictionary
    assert len(config) >= 7
    assert config["model_type"] == "gpt"
    assert config["num_gpus"] == 2

  def test_hyperparameter_sweep_setup(self):
    """Test setting up hyperparameter sweeps with variable interpolation."""
    sweep_configs = [
      {
        "args": ["--base-lr", "1e-4", "--sweep-id", "sweep_1", "--run-name", "@{sweep_id}_lr@{base_lr}"],
        "expected_name": "sweep_1_lr0.0001",
      },
      {
        "args": ["--base-lr", "1e-3", "--sweep-id", "sweep_2", "--run-name", "@{sweep_id}_lr@{base_lr}"],
        "expected_name": "sweep_2_lr0.001",
      },
    ]

    for config in sweep_configs:
      with manu.script(args=config["args"]):
        base_lr: float = 1e-5
        sweep_id = "default"
        run_name = "default_name"

      assert run_name == config["expected_name"]

  def test_config_inheritance_chain(self, temp_dir):
    """Test complex config inheritance: base -> specific -> CLI."""
    # Base config
    base_config = temp_dir / "base.py"
    base_config.write_text("""
# Base configuration
model_type = "transformer"
learning_rate = 1e-4
batch_size = 32
use_wandb = True
""")

    # Specific config that imports base
    specific_config = temp_dir / "experiment.py"
    specific_config.write_text(f'''
# Import base config
exec(open(r"{base_config}").read())

# Override specific settings
learning_rate = 5e-4
batch_size = 64
experiment_name = "specific_experiment"
''')

    # CLI overrides
    args = [
      "-c",
      str(specific_config),
      "--learning-rate",
      "1e-3",  # CLI override
      "--model-type",
      "gpt",  # CLI override
    ]

    with manu.script(args=args):
      model_type = "bert"
      learning_rate = 1e-5
      batch_size = 16
      use_wandb = False
      experiment_name = "default"

    # Verify precedence: base < specific < CLI
    assert model_type == "gpt"  # CLI override
    assert learning_rate == 1e-3  # CLI override
    assert batch_size == 64  # Specific config
    assert use_wandb is True  # Base config
    assert experiment_name == "specific_experiment"  # Specific config

  def test_conditional_configuration(self):
    """Test conditional configuration based on other parameters."""

    @hook("conditional_batch_size")
    def batch_size_hook(value: str, ctx: ValidationContext) -> int:
      model_type = ctx.get_nested_value("model_type")
      if model_type == "large":
        return 8  # Large models need smaller batches
      elif model_type == "small":
        return 128
      else:
        return 32

    test_cases = [
      (["--model-type", "large", "--batch-size", "@conditional_batch_size:"], 8),
      (["--model-type", "small", "--batch-size", "@conditional_batch_size:"], 128),
      (["--model-type", "medium", "--batch-size", "@conditional_batch_size:"], 32),
    ]

    for args, expected_batch_size in test_cases:
      with manu.script(args=args):
        model_type = "default"
        batch_size = 16

      assert batch_size == expected_batch_size

  def test_multi_stage_pipeline_config(self):
    """Test configuration for multi-stage ML pipeline."""

    @hook("stage_config")
    def stage_config_hook(stage: str, ctx: ValidationContext) -> dict:
      configs = {
        "preprocess": {"workers": 4, "chunk_size": 1000},
        "train": {"lr": 1e-3, "epochs": 100},
        "evaluate": {"batch_size": 128, "metrics": ["accuracy", "f1"]},
      }
      return configs.get(stage, {})

    # Test preprocessing stage
    args = ["--stage", "preprocess", "--config", "@stage_config:preprocess"]

    with manu.script(args=args):
      stage = "train"
      config: dict = {}

    assert stage == "preprocess"
    assert config["workers"] == 4
    assert config["chunk_size"] == 1000

  def test_configuration_validation_workflow(self):
    """Test end-to-end configuration validation."""
    from pydantic import Field
    from pydantic import PositiveInt

    # Test valid configuration
    args = ["--learning-rate", "0.001", "--batch-size", "32", "--epochs", "100"]

    with manu.script(args=args):
      learning_rate: float = Field(gt=0, le=1)  # Between 0 and 1
      batch_size: PositiveInt = 16
      epochs: PositiveInt = 10

    assert 0 < learning_rate <= 1
    assert batch_size > 0
    assert epochs > 0

  def test_experiment_reproducibility_setup(self, env_vars):
    """Test setting up reproducible experiments."""
    os.environ["RANDOM_SEED"] = "42"

    @hook("derived_seeds")
    def seed_hook(base_seed: str, ctx: ValidationContext) -> dict:
      import random

      base = int(base_seed)
      random.seed(base)
      return {
        "numpy_seed": random.randint(0, 2**32 - 1),
        "torch_seed": random.randint(0, 2**32 - 1),
        "data_seed": random.randint(0, 2**32 - 1),
      }

    args = ["--random-seed", "@env:RANDOM_SEED", "--seeds", "@derived_seeds:@{random_seed}"]

    with manu.script(args=args):
      random_seed: int = 0
      seeds: dict = {}
      experiment_id = "@{random_seed}_reproducible"

    assert random_seed == 42
    assert "numpy_seed" in seeds
    assert "torch_seed" in seeds
    assert "data_seed" in seeds
    assert experiment_id == "42_reproducible"

  def test_complex_type_configuration(self):
    """Test configuration with complex nested types."""

    args = [
      "--model-config",
      '{"layers": [64, 128, 256], "dropout": 0.1}',
      "--optimizer-params",
      '{"lr": 0.001, "weight_decay": 1e-5}',
      "--data-splits",
      "train",
      "val",
      "test",
    ]

    with manu.script(args=args):
      model_config: dict[str, any] = {}
      optimizer_params: dict[str, float] = {}
      data_splits: list[str] = []
      optional_param: str | None = None

    assert model_config["layers"] == [64, 128, 256]
    assert model_config["dropout"] == 0.1
    assert optimizer_params["lr"] == 0.001
    assert data_splits == ["train", "val", "test"]
    assert optional_param is None

  def test_error_recovery_and_validation(self):
    """Test error recovery in complex configurations."""

    # Test that one invalid hook doesn't break the entire config
    @hook("valid_hook")
    def valid_hook(value: str, ctx: ValidationContext) -> str:
      return f"processed_{value}"

    @hook("invalid_hook")
    def invalid_hook(value: str, ctx: ValidationContext) -> str:
      raise ValueError("This hook always fails")

    # Valid configuration should work
    args = ["--good-value", "@valid_hook:test"]
    with manu.script(args=args):
      good_value = "default"
    assert good_value == "processed_test"

    # Invalid configuration should fail gracefully
    args = ["--bad-value", "@invalid_hook:test"]
    with pytest.raises(Exception):
      with manu.script(args=args):
        bad_value = "default"
