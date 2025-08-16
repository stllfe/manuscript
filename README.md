<div align="center">

# `manu:script` ✍️

_Dead simple configuration for Python scripts_

Powered by [`tyro`](https://github.com/brentyi/tyro) and [`pydantic`](https://github.com/pydantic/pydantic) 🚀

</div>

`manu` is a small, zero-boilerplate library that turns a section of your Python script into a powerful, type-checked, configurable CLI application:

```python
import manu
import manu.conf as conf

with manu.script:
  exp_name: str = ...  # means required
  out_dir: Path = ...  # rich types supported
  device = "cpu" # with a default value, type hint may be omitted
  learning_rate = 6e-4  # inline comments are used as arg help text
  beta = 0.9  #! comments with ! are not rendered as help text
  max_iters = 6000000
  """this is a docstring for max_iters as well"""
  do_something: conf.Fixed[bool] = True  #! configure args via hints

# at this point `exp_name` is an actual runtime string
# so you can use it as usual
print("Using exp name:", exp_name)

# you can also do something with all the captured values
print("All CLI variables:")
print(script.values)  # Mapping[str, Any]

# like log them or store them to a file:
wandb.config.update(script.values)
```

It's designed for simple scripts, research code, and ML experiments where you want to avoid writing complex `argparse` or `dataclass`-based configuration systems.

It's inspired by Andrej Karpathy's Poor Man's Configurator from the [`nanoGPT`](https://github.com/karpathy/nanoGPT/blob/master/configurator.py) repo and aims to provide a more robust and feature-rich solution to the same problem: easily overriding variables from the CLI without cluttering the main script.

## Why? 🤔

Simple scripts often start with a block of configuration variables at the top. When it's time to run experiments, you might find yourself:

- Manually editing these values.
- Creating brittle `sys.argv` parsers.
- Writing boilerplate `argparse` code.
- Building complex config classes that feel like overkill.

`manu` solves this by automatically creating a CLI for you, based on the variables you've already defined ✨

## Get started

Install from the repo:

```shell
uv pip install git+https://github.com/stllfe/manuscript
```

Let's build a simple ML training script step by step to show how `manu` works.

### Step 1: Create your script

Start with a basic `train.py`:

```python
from pathlib import Path
import manu

with manu.script:
  exp_name: str = ...  # required
  out_dir: Path = ...  # rich types supported
  device = "cpu"  # with default, type hint is optional
  learning_rate = 6e-4  # inline comments become help text
  beta = 0.9  #! comments with ! are ignored
  max_iters = 6000000
  """this docstring also becomes help text"""

# variables are now populated with CLI values
print(f"Training {exp_name} on {device}")
print(f"Output: {out_dir}")
print(f"Params: {beta=} and {learning_rate=}")
```

### Step 2: Run and see the magic

**✨ Automagical CLI**: Get help automatically:

```shell
$ python train.py -h
```
**ℹ️ Self-documenting**: Comments and docstrings become help text without any extra work.

**🧩 Type-driven**: Supports rich Python built-in types like `pathlib.Path` or [Pydantic types](https://docs.pydantic.dev/2.0/usage/types/types/):

```python
from pydantic import PositiveInt, FilePath

with manu.script:
  num_epochs: PositiveInt = ...  # validates > 0
  tokenizer_path: FilePath = ...  # ensures file exists
  ...
```

### Step 3: Override from config files

**📄 Config file override**: Create `configs/base.py`:

```python
learning_rate = 1e-3
beta = 0.99
device = "cuda"
```

Load the config, then override specific values (config < CLI precedence):

```shell
$ python train.py -c configs/base.py --exp-name "gpu-model" --out-dir "./outputs" --beta 0.95

> Training gpu-model on cuda
> Output: ./outputs
> Params: beta=0.95 and learning_rate=0.001
```

### Step 4: Use interpolation and hooks

**🪝 Variable interpolation**: Reference other variables with `@{var}`:

```shell
$ python train.py --exp-name "test-@{beta}" --beta 0.85

> Training test-0.85 on cpu
...
```

**Built-in hooks**: Use `@env:ENV_VAR`, `@import:pkg.mod.attr`, or `@value:foo` (same as `@{foo}`).

```shell
python train.py --exp-name @env:USER --device @env:CUDA_DEVICE
```

**Custom hooks**: Hooks are callables that take exactly two positional arguments:

```python
from manu import hook, ValidationContext

@hook("gpu")
def gpu_hook(val: str, ctx: ValidationContext) -> str:
    if val == "free":
        return find_free_cuda_device(...)
    # ... some fancy logic
    # get any other context value:
    # ctx.get_nested_value("bar")
    return "cuda:0"
```

You can now reference it in your script invocation:

```shell
python simple.py --device @gpu:free
# this will substitute --device with whatever your hook returns
```

### Step 5: Capture final values

**💾 Access resolved config**: Get the final configuration for logging:

```python
with manu.script as config:
  exp_name: str = ...
  device = "cpu"
  learning_rate = 6e-4

# log final config to wandb, mlflow, etc.
wandb.config.update(config)
print("Final config:", config)
```

### Advanced: Custom Configuration

**⚙️ Fine-tune behavior** with `manu.conf`:

```python
from manu import conf, script

settings = (
  conf.HelptextFromCommentsOff,
  conf.PositionalRequiredArgs,
)
with script(config=settings):
  secret: conf.Suppress[str] = "hidden-key"  # won't show in help
  model_type: conf.Fixed[str] = "transformer"  # shows but can't be changed
  verbose: bool = False  # becomes --verbose/--no-verbose flags
```

**Alternative inline syntax**:

```python
from manu import conf, script

script.description = "Train a transformer model"
script.config = (conf.HelptextFromCommentsOff, conf.FlagConvertPairsOff)
script.init()

secret: conf.Suppress[str] = "hidden-key"
model_type: conf.Fixed[str] = "transformer"
verbose: bool = False

script.done()
```

## How It Works

You designate a "configurable section" in your script with `script.init()` and `script.done()`. `manu` parses the source code of this section using Python's `ast` module to extract variable names, types, default values, and even comments as help text. It then uses this information to:

1. Build a configuration schema.
2. Generate a CLI.
3. Parse arguments, handling special syntax for config files (`-c` / `--with`).
4. Process values for interpolation and custom hooks.
5. Validate the final resolved values with `pydantic`.
6. Inject the final values back into your script's global scope and expose them via a read-only dictionary.

## Installation

This project uses [`uv`](https://docs.astral.sh/uv/) for package management.

- **Create a virtual environment and install dependencies:**

```shell
uv venv
uv sync
```

- **Run inside the env:**

```shell
uv run simple.py -h
```

## Development

- **Testing**: `pytest`
- **Linting/Formatting**: `ruff`

Run tests with:

```shell
pytest
```

Format code with:

```shell
ruff format .
ruff check . --fix
```

## Limitations (Beta)

- **Thread safety**: Global state is used; thread safety is not designed or tested yet.
- **Multiprocessing**: Not yet addressed; global state may not behave as expected across processes.
- **Scope**: Optimized for flat/simple script configs, not nested config trees.

## Core Dependencies

- **`tyro`**: For powerful and elegant CLI generation.
- **`pydantic`**: For robust data validation and type coercion.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
