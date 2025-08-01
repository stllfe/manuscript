from __future__ import annotations

import inspect
import sys

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Annotated, overload

import tyro
import tyro._docstrings

from pydantic import BaseModel
from tyro.conf import arg as Arg


ManuConfigPath = Annotated[
  Path | None,
  Arg(name="manu-config", aliases=["-c"], help="Path to a Python configuration file to load."),
]
ManuResultPath = Annotated[
  Path | None,
  Arg(name="manu-save", aliases=["-s"], help="Path to save the final configuration as a new script."),
]


@dataclass
class _Script:
  """Internal class to manage script configuration and CLI generation."""

  description: str | None = None
  init_globals: set[str] = field(default_factory=set)
  initialized: bool = False
  file: Path | None = None
  save_path: Path | None = None
  lines: list[str] | None = None
  start: int | None = None
  end: int | None = None

  def init(self, description: str | None = None) -> None:
    """
    Marks the beginning of the configurable section of a script.

    When this function is called, it captures the state of the script's
    global variables. Any new variables defined between this call and
    `script.ready()` are considered configurable parameters.

    Args:
        description: The description for the command-line interface.
            This is shown when a user runs the script with `-h` or `--help`.
    """

    if self.initialized:
      raise RuntimeError("`script.init()` has already been called.")

    frame = inspect.currentframe()
    if not (frame and frame.f_back):
      raise RuntimeError("Could not inspect the caller's frame.")

    frameinfo = inspect.getframeinfo(frame.f_back)
    script_file = frameinfo.filename
    with open(script_file) as f:
      self.lines = f.readlines()
    self.file = Path(script_file)

    context = frame.f_back.f_globals
    self.description = description or context.get("__doc__", "")
    self.init_globals = set(context.keys())
    self.initialized = True
    self.start = frameinfo.lineno

  @overload
  def hook(self, name: str) -> Callable[[Callable], Callable]: ...

  @overload
  def hook(self, name: str, func: Callable) -> None: ...

  def hook(self, name: str, func: Callable | None = None) -> Callable[[Callable], Callable] | None:
    """
    Registers a custom function as a resolver, usable within config values.

    This can be used as a decorator or as a direct registration function.
    The registered function can be invoked in configuration values using `@name:arg` syntax.

    As a decorator:
    ```python
    @script.hook("my_hook")
    def my_function(arg: str) -> str:
        return f"processed_{arg}"
    ```

    As a direct registration:
    ```python
    def my_function(arg: str) -> str:
        return f"processed_{arg}"
    script.hook("my_hook", my_function)
    ```

    Args:
        name: The name to register the hook under.
        func: The function to register. If `None`, returns a decorator.

    Returns:
        A decorator if `func` is not provided, otherwise `None`.
    """
    ...

  def ready(self) -> None:
    """Marks the end of the configurable section and processes CLI arguments.

    This function inspects the script's global scope to find newly defined
    variables, builds a configuration model, and parses command-line
    arguments to override default values.

    The final, resolved configuration is injected back into the script's global scope.
    """

    if not self.initialized:
      raise RuntimeError("`script.init()` must be called before `script.ready()`.")

    frame = inspect.currentframe()
    if not (frame and frame.f_back):
      raise RuntimeError("Could not inspect the caller's frame.")

    caller_globals = frame.f_back.f_globals
    config_globals = {}
    new_vars = {var for var in set(caller_globals.keys()) - self.init_globals if not var.startswith("_")}

    frameinfo = inspect.getframeinfo(frame.f_back)
    code_segment = "".join(self.lines[self.start : frameinfo.lineno - 1])

    if "-c" in sys.argv:
      config = sys.argv[sys.argv.index("-c") + 1]
      config_globals = exec(Path(config).read_text())
    if "-s" in sys.argv:
      # TODO: make sure we use it
      self.save_path = Path(sys.argv[sys.argv.index("-s") + 1])

    # TODO:
    # (1) parse the code block within the section using AST
    # (2) read surrounding comments using docstring utilities
    # (3) construct the final ScriptModel from fields
    # (4) use tyro to parse the CLI arguments

    # FIXME I'm unsure how to properly handle hooks

    # print(code_segment)
    # parsed = ast.parse(code_segment, filename=self.file)
    # var_lines = []
    # for node in parsed.body:
    #   if isinstance(node, (ast.Assign, ast.AnnAssign)):
    #     targets: list[str] = []
    #     if isinstance(node, ast.Assign):
    #       for t in node.targets:
    #         if isinstance(t, ast.Name):
    #           targets.append(t.id)
    #     elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
    #       targets.append(node.target.id)
    #     for var in targets:
    #       # Get the source line(s) for this node
    #       start = node.lineno - 1
    #       end = getattr(node, "end_lineno", node.lineno)  # Python 3.8+
    #       var_lines.extend([self.lines[self.start + i].rstrip() for i in range(start, end)])
    # var_lines now contains only lines assigning to variables in new_vars
    # cls_name = "Main"
    # # body = "  " + "\n  ".join(code_segment)
    # code = f"""@dataclass\nclass {cls_name}:\n{indent(code_segment, prefix="  ")}"""
    # print(code)

    # with tempfile.NamedTemporaryFile("w", suffix=".py") as f:
    #   f.write(code)

    #   c = compile(code, Path(f.name), mode="exec")
    #   l = locals()
    #   g = globals()
    #   exec(c, locals=l, globals=g)

    #   MainArgs: type = l.get(cls_name)
    #   print(MainArgs)
    #   tyro._docstrings.get_field_docstring(MainArgs, "exp_name", ())
    #   print(tyro._docstrings.parse_docstring_from_object(code))
    #   parser = tyro.cli(MainArgs, description=self.description)
    #   print(parser)
    #   return

    # fields = {
    #   "__manu_config__": (ManuConfigPath, None),
    #   "__manu_result__": (ManuResultPath, None),
    # }

    # for name in new_vars:
    #   value = caller_globals[name]
    #   type_hint = caller_globals.get("__annotations__", {}).get(name, Any)
    #   if value is ...:
    #     fields[name] = (type_hint, tyro.MISSING)
    #   elif isinstance(value, FieldInfo):
    #     fields[name] = (type_hint, value)
    #   else:
    #     fields[name] = (type_hint, field(default=value))

    # Args = dataclasses.make_dataclass("Args", [(k, *v) for k, v in fields.items()], bases=(MainArgs,))

    # fields: dict[str, Any] = {}
    # for name in sorted(new_vars):
    #   if name.startswith("_"):
    #     continue
    #   # Get code lines between self.start and current frame lineno and filter for variable assignments in new_vars using ast

    #   value = caller_globals[name]
    #   type_hint = caller_globals.get("__annotations__", {}).get(name, Any)

    #   if value is ...:
    #     fields[name] = (type_hint, ...)
    #   elif isinstance(value, FieldInfo):
    #     fields[name] = (type_hint, value)
    #   else:
    #     fields[name] = (type_hint, Field(default=value))

    # ConfigModel = create_model("Config", **fields)
    # HACK: Puts the dynamically generated model into the module's scope
    # so that it can be pickled by other processes if needed.
    # sys.modules[__name__].Args = Args

    try:
      parser = tyro.cli(MainArgs, description=self.description)
      print(parser)

      # # If a config file is provided, we need to re-parse with its values as defaults.
      # if parser.config:
      #   config_globals: dict[str, Any] = {}
      #   with open(parser.config) as f:
      #     exec(f.read(), config_globals)

      #   # Create a new model with defaults from the file
      #   fields = {
      #     k: (v.annotation, Field(default=config_globals.get(k, v.default)))
      #     for k, v in ConfigModel.model_fields.items()
      #   }
      #   ConfigWithDefaults = create_model("ConfigWithDefaults", **fields)
      #   sys.modules[__name__].ConfigWithDefaults = ConfigWithDefaults

      #   try:

      #     class ArgsWithDefaults(ConfigWithDefaults):
      #       config: Annotated[Path | None, Arg(name="manu-config", aliases=["-c"])] = None
      #       save: Annotated[Path | None, Arg(name="manu-save", aliases=["-s"])] = None

      #     # Re-parse with the new defaults
      #     parser = tyro.cli(ArgsWithDefaults, description=self._description)
      #   finally:
      #     delattr(sys.modules[__name__], "ConfigWithDefaults")

      # raw_config = parser.model_dump(exclude_unset=True)

      # # Convert @{...} and @hook syntax to ${...} for OmegaConf
      # for key, value in raw_config.items():
      #   if isinstance(value, str):
      #     # Replace @{var} with ${var}
      #     value = re.sub(r"@\{(.+?)\}", r"${\1}", value)
      #     # Replace @hook:arg with ${hook:arg}
      #     value = re.sub(r"@([a-zA-Z0-9_]+)(:[^}]*)?", r"${\1:\2}", value)
      #     raw_config[key] = value

      # # Create final config, allowing interpolation to fill in missing values
      # full_config = OmegaConf.create(raw_config)
      # merged_config = OmegaConf.merge(OmegaConf.create(parser.model_dump()), full_config)
      # resolved_config = OmegaConf.to_container(merged_config, resolve=True)

      # final_config = ConfigModel(**resolved_config)

      # if parser.save:
      #   self._save(parser.save, final_config)

      # caller_globals.update(final_config.model_dump())
    finally:
      delattr(sys.modules[__name__], "Args")

  def _save(self, path: Path, config: BaseModel) -> None:
    """
    Saves the final configuration to a Python script for reproducibility.

    Args:
        path: The file path to save the configuration to.
        config: The Pydantic model instance containing the final config values.
    """
    # TODO Implement using patcher.py logic
    # path.parent.mkdir(parents=True, exist_ok=True)
    # with open(path, "w") as f:
    #   f.write("# This file was generated by manu. Do not edit manually.\n")
    #   f.write("from pathlib import Path\n\n")
    #   f.writelines(f"{name} = {value!r}\n" for name, value in config.model_dump().items())
    # print(f"Configuration saved to {path}", file=sys.stderr)


script = _Script()
init = script.init
ready = script.ready
hook = script.hook
