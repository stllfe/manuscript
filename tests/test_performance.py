"""Performance and regression tests."""

import time

import pytest

import manu


class TestPerformance:
  """Test performance characteristics of the library."""

  def test_startup_time_reasonable(self):
    """Test that script initialization doesn't take too long."""
    start_time = time.time()

    with manu.script(args=[]):
      simple_var = "test"

    elapsed = time.time() - start_time
    # Should complete in well under a second for simple cases
    assert elapsed < 1.0

  def test_large_config_handling(self):
    """Test handling of large configuration with many variables."""
    # Create arguments for 100 variables
    args = []
    for i in range(100):
      args.extend([f"--var{i}", str(i)])

    start_time = time.time()

    with manu.script(args=args):
      # Create 100 variables dynamically
      for i in range(100):
        locals()[f"var{i}"] = -1

    elapsed = time.time() - start_time

    # Should handle 100 variables reasonably quickly
    assert elapsed < 5.0

    # Verify all variables were set correctly
    for i in range(100):
      assert locals()[f"var{i}"] == i

  def test_deep_hook_resolution_performance(self):
    """Test performance with deep hook resolution chains."""
    from manu import ValidationContext
    from manu import hook

    @hook("add_one")
    def add_one_hook(value: str, ctx: ValidationContext) -> int:
      return int(value) + 1

    # Chain multiple hook resolutions
    args = [
      "--base",
      "0",
      "--level1",
      "@add_one:@{base}",
      "--level2",
      "@add_one:@{level1}",
      "--level3",
      "@add_one:@{level2}",
    ]

    start_time = time.time()

    with manu.script(args=args):
      base = -1
      level1 = -1
      level2 = -1
      level3 = -1

    elapsed = time.time() - start_time

    # Should resolve hooks quickly
    assert elapsed < 1.0
    assert base == 0
    assert level1 == 1
    assert level2 == 2
    assert level3 == 3

  def test_large_config_file_performance(self, temp_dir):
    """Test performance with large config files."""
    # Create a large config file
    config_file = temp_dir / "large_config.py"
    config_lines = []

    for i in range(1000):
      config_lines.append(f"var_{i} = {i}")

    config_file.write_text("\n".join(config_lines))

    start_time = time.time()

    args = ["-c", str(config_file)]
    with manu.script(args=args):
      # Just define a few variables to test loading
      var_0 = -1
      var_500 = -1
      var_999 = -1

    elapsed = time.time() - start_time

    # Should load large config reasonably quickly
    assert elapsed < 3.0
    assert var_0 == 0
    assert var_500 == 500
    assert var_999 == 999

  def test_memory_usage_reasonable(self):
    """Test that memory usage doesn't grow excessively."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Run multiple script contexts
    for i in range(10):
      args = ["--iteration", str(i)]
      with manu.script(args=args):
        iteration = 0
        data = list(range(100))  # Some data

    final_memory = process.memory_info().rss
    memory_growth = final_memory - initial_memory

    # Memory growth should be reasonable (less than 10MB)
    assert memory_growth < 10 * 1024 * 1024

  @pytest.mark.parametrize("num_vars", [1, 10, 50, 100])
  def test_scaling_with_variable_count(self, num_vars):
    """Test that performance scales reasonably with variable count."""
    args = []
    for i in range(num_vars):
      args.extend([f"--var{i}", str(i)])

    start_time = time.time()

    with manu.script(args=args):
      for i in range(num_vars):
        locals()[f"var{i}"] = -1

    elapsed = time.time() - start_time

    # Performance should scale sub-linearly
    expected_max_time = 0.1 + (num_vars * 0.01)  # Base + linear component
    assert elapsed < expected_max_time


class TestRegressionCases:
  """Test specific regression cases and known issues."""

  def test_hook_registry_isolation(self):
    """Test that hook registry properly isolates between tests."""
    from manu import ValidationContext
    from manu import hook

    @hook("test_hook_1")
    def hook1(value: str, ctx: ValidationContext) -> str:
      return "hook1_result"

    args = ["--value", "@test_hook_1:"]
    with manu.script(args=args):
      value = "default"
    assert value == "hook1_result"

    # In a new test, this hook should still be available due to fixtures
    # But the registry should be properly managed

  def test_variable_name_collision_handling(self):
    """Test handling of potential variable name collisions."""
    with manu.script(args=["--config", "test"]):
      # 'config' might collide with internal usage
      config = "default"
      # These are internal-ish names that shouldn't cause issues
      script = "test_script"
      args = "test_args"

    assert config == "test"
    assert script == "test_script"
    assert args == "test_args"

  def test_type_annotation_edge_cases(self):
    """Test edge cases in type annotation handling."""
    from typing import Any

    args = ["--union-val", "42", "--any-val", "anything", "--optional-val", "value"]

    with manu.script(args=args):
      union_val: int | str = "default"
      any_val: Any = None
      optional_val: str | None = None
      no_annotation = "test"  # No type annotation

    assert union_val == 42  # Should convert to int
    assert any_val == "anything"
    assert optional_val == "value"
    assert no_annotation == "test"

  def test_context_manager_exception_handling(self):
    """Test that exceptions in context manager are handled properly."""
    # Test exception during script execution
    with pytest.raises(ValueError):
      with manu.script(args=["--value", "test"]):
        value = "default"
        raise ValueError("Test exception")

    # Script should still be usable afterwards
    with manu.script(args=["--value2", "test2"]):
      value2 = "default2"
    assert value2 == "test2"

  def test_globals_pollution_prevention(self):
    """Test that script execution doesn't pollute global namespace."""
    import manu.script as script_module

    initial_globals = set(script_module.__dict__.keys())

    with manu.script(args=["--test-var", "test"]):
      test_var = "default"

    final_globals = set(script_module.__dict__.keys())

    # No new globals should be added
    assert initial_globals == final_globals

  def test_repeated_script_usage_stability(self):
    """Test that repeated script usage remains stable."""
    # Run the same script configuration multiple times
    for i in range(5):
      args = ["--iteration", str(i), "--constant", "stable"]

      with manu.script(args=args):
        iteration: int = -1
        constant = "default"

      assert iteration == i
      assert constant == "stable"

      # Values should be available in script.values
      values = manu.script.values
      assert values["iteration"] == i
      assert values["constant"] == "stable"

  def test_thread_safety_basic(self):
    """Basic test for thread safety concerns."""
    import queue
    import threading

    results = queue.Queue()

    def run_script(thread_id):
      try:
        args = ["--thread-id", str(thread_id)]
        with manu.script(args=args):
          thread_id_var = -1
        results.put((thread_id, thread_id_var))
      except Exception as e:
        results.put((thread_id, f"ERROR: {e}"))

    # Run multiple threads
    threads = []
    for i in range(3):
      thread = threading.Thread(target=run_script, args=(i,))
      threads.append(thread)
      thread.start()

    # Wait for completion
    for thread in threads:
      thread.join()

    # Check results
    collected_results = []
    while not results.empty():
      collected_results.append(results.get())

    assert len(collected_results) == 3
    for thread_id, result in collected_results:
      if isinstance(result, str) and result.startswith("ERROR"):
        pytest.fail(f"Thread {thread_id} failed: {result}")
      assert result == thread_id
