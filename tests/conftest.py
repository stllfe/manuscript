"""Pytest configuration and shared fixtures."""

import os
import tempfile

from pathlib import Path

import pytest

from manu.hooks import HookRegistry
from manu.script import init
from manu.script import script


@pytest.fixture(autouse=True)
def reset_script_state():
  """Reset script state before each test."""
  script._values.clear()
  script._kwargs.clear()
  script.description = None
  script.config = None
  script.args = None
  init.clear()
  yield
  # Cleanup after test
  script._values.clear()
  script._kwargs.clear()
  script.description = None
  script.config = None
  script.args = None
  init.clear()


@pytest.fixture(autouse=True)
def reset_hook_registry():
  """Reset hook registry before each test."""
  # Store current handlers
  original_handlers = HookRegistry._handlers.copy()
  yield
  # Restore original handlers
  HookRegistry._handlers.clear()
  HookRegistry._handlers.update(original_handlers)


@pytest.fixture
def temp_config_file():
  """Create a temporary config file."""
  with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
    yield f.name
  os.unlink(f.name)


@pytest.fixture
def temp_dir():
  """Create a temporary directory."""
  with tempfile.TemporaryDirectory() as tmpdir:
    yield Path(tmpdir)


@pytest.fixture
def sample_config_content():
  """Sample config content for testing."""
  return """
learning_rate = 1e-3
beta = 0.99
device = "cuda"
batch_size = 32
"""


@pytest.fixture
def env_vars():
  """Fixture to manage environment variables."""
  original_env = os.environ.copy()
  yield
  # Restore original environment
  os.environ.clear()
  os.environ.update(original_env)


def create_test_script(script_content: str, temp_dir: Path) -> Path:
  """Helper to create test script files."""
  script_file = temp_dir / "test_script.py"
  script_file.write_text(script_content)
  return script_file
