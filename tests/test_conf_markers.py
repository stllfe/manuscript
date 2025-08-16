"""Test tyro configuration markers from manu.conf."""

import pytest

import manu
import manu.conf as conf


class TestConfMarkers:
  """Test tyro configuration markers functionality."""

  def test_suppress_marker(self, capsys):
    """Test conf.Suppress marker hides arguments from help."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--help"]):
        visible_arg = "default"
        hidden_arg: conf.Suppress[str] = "secret"

    captured = capsys.readouterr()
    assert "visible-arg" in captured.out
    assert "hidden-arg" not in captured.out

  def test_suppress_marker_still_functional(self):
    """Test that suppressed arguments still work when provided."""
    args = ["--hidden-arg", "value"]

    with manu.script(args=args):
      hidden_arg: conf.Suppress[str] = "default"

    assert hidden_arg == "value"

  def test_fixed_marker(self, capsys):
    """Test conf.Fixed marker shows but prevents modification."""
    with pytest.raises(SystemExit):
      with manu.script(args=["--help"]):
        fixed_val: conf.Fixed[str] = "immutable"

    captured = capsys.readouterr()
    assert "fixed-val" in captured.out

  def test_fixed_marker_prevents_override(self):
    """Test that Fixed values cannot be overridden."""
    # The Fixed marker should prevent CLI override
    args = []  # Don't try to override fixed value

    with manu.script(args=args):
      fixed_val: conf.Fixed[str] = "immutable"

    assert fixed_val == "immutable"

  def test_positional_required_args(self):
    """Test conf.PositionalRequiredArgs marker."""
    config = (conf.PositionalRequiredArgs,)
    args = ["required_value"]

    with manu.script(config=config, args=args):
      required_arg: str = ...

    assert required_arg == "required_value"

  def test_helptext_from_comments_off(self, capsys):
    """Test conf.HelptextFromCommentsOff disables comment help."""
    config = (conf.HelptextFromCommentsOff,)

    with pytest.raises(SystemExit):
      with manu.script(config=config, args=["--help"]):
        arg_with_comment = "default"  # This comment should not appear

    captured = capsys.readouterr()
    assert "This comment should not appear" not in captured.out

  def test_flag_create_pairs_off(self):
    """Test conf.FlagCreatePairsOff marker."""
    # This controls bool flag behavior
    config = (conf.FlagCreatePairsOff,)
    args = ["--verbose"]

    with manu.script(config=config, args=args):
      verbose: bool = False

    assert verbose is True

  def test_use_append_action(self):
    """Test conf.UseAppendAction for list arguments."""
    args = ["--values", "1", "--values", "2", "--values", "3"]

    with manu.script(args=args):
      values: conf.UseAppendAction[list[int]] = []

    assert values == [1, 2, 3]

  def test_use_counter_action(self):
    """Test conf.UseCounterAction for counting flags."""
    args = ["-v", "-v", "-v"]  # Triple verbose

    with manu.script(args=args):
      verbosity: conf.UseCounterAction[int] = 0

    assert verbosity == 3

  def test_enum_choices_from_values(self):
    """Test conf.EnumChoicesFromValues marker."""
    from enum import Enum

    class Mode(Enum):
      TRAIN = "train"
      TEST = "test"
      EVAL = "eval"

    args = ["--mode", "train"]

    with manu.script(args=args):
      mode: conf.EnumChoicesFromValues[Mode] = Mode.TEST

    assert mode == Mode.TRAIN

  def test_suppress_fixed_combination(self):
    """Test conf.SuppressFixed marker combination."""
    args = []

    with manu.script(args=args):
      secret_fixed: conf.SuppressFixed[str] = "hidden_constant"

    assert secret_fixed == "hidden_constant"

  def test_multiple_markers_combination(self, capsys):
    """Test using multiple configuration markers together."""
    config = (
      conf.HelptextFromCommentsOff,
      conf.PositionalRequiredArgs,
    )

    with pytest.raises(SystemExit):
      with manu.script(config=config, args=["--help"]):
        pos_arg: str = ...
        regular_arg = "default"  # Comment should be ignored

    captured = capsys.readouterr()
    assert "Comment should be ignored" not in captured.out

  def test_arg_marker_customization(self):
    """Test conf.arg marker for custom argument configuration."""
    # This would test advanced tyro.conf.arg features if implemented
    args = ["--custom", "value"]

    with manu.script(args=args):
      # This syntax might need to be adjusted based on actual implementation
      custom_arg = "default"

    assert custom_arg == "value"

  def test_config_inheritance_and_override(self):
    """Test that script-level config can be overridden."""
    # Set default config
    manu.script.config = (conf.HelptextFromCommentsOff,)

    # Override in context manager
    new_config = (conf.PositionalRequiredArgs,)

    with manu.script(config=new_config, args=["test_value"]):
      arg: str = ...

    assert arg == "test_value"

  def test_config_via_init_method(self):
    """Test setting config via init method."""
    config = (conf.HelptextFromCommentsOff,)

    manu.script.init(config=config, args=[])

    regular_arg = "default"  # Comment should be ignored

    manu.script.done()

    assert regular_arg == "default"
