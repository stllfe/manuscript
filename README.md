<div align="center">

# `manu:script` ✍️

_dead simple configuration for simple Python scripts_

@powered by [`tyro`](https://github.com/brentyi/tyro) and [`pydantic`](https://github.com/pydantic/pydantic) 🚀

</div>

`manu` is a small, zero-boilerplate library that turns a section of your Python script into a powerful, type-checked, and configurable CLI application. It's designed for simple scripts, research code, and ML experiments where you want to avoid writing complex `argparse` or `dataclass`-based configuration systems.

It is directly inspired by Andrej Karpathy's "Poor Man's Configurator" from [`nanoGPT`](https://github.com/karpathy/nanoGPT/blob/master/configurator.py) repo and aims to provide a more robust and feature-rich solution to the same problem: how to easily override variables from the command line without cluttering the main script. It's a remedy for simple scripts with rapid changes like the ones typical for ML experiments.

## The Problem

Simple scripts often start with a block of configuration variables at the top. When it's time to run experiments, you might find yourself:

- Manually editing these values.
- Creating brittle `sys.argv` parsers.
- Writing boilerplate `argparse` code.
- Building complex config classes that feel like overkill.

`manu` solves this by automatically creating a CLI for you, based on the variables you've already defined.

## Features

- **Automatic CLI Generation**: Any variable defined between `script.init()` and `script.done()` is automatically exposed as a CLI argument.
- **Type-Safe**: Uses type hints and default values to automatically cast and validate inputs. Powered by `pydantic` under the hood, so you can use fancy types like `EmailStr`, `FilePath`, `PositiveInt`, etc.
- **Variable Interpolation**: Reference other configuration variables in your arguments.
- **Custom Hooks**: Register your own functions to resolve dynamic values at runtime.
- **Config File Overrides**: Load a base configuration from a Python file and override specific values from the CLI.
- **Save Final Configuration**: Save the fully-resolved configuration to a new, runnable Python script for perfect reproducibility.
- **Dynamic Defaults**: Variables can be initialized with runtime values (e.g., `time.time()`), and these can still be overridden from the CLI.

## Usage Example

Here is a simple script that uses `manu`:

```python
# simple.py
from pathlib import Path

from manu import conf
from manu import script

# generate cli with this description
script.init(description="trains a baseline experiment")

# @@ configurable section begins
device: str = "cpu"
learning_rate = 6e-4  # inline comments are used as arg docstrings
max_iters = 6000000
"""this docstring syntax also supported"""

secret: conf.Suppress[str] = "sk-1xzmasda..."  # some values can be excluded or configured with how they appear in the CLI using `conf` module just like with tyro

weight_decay = 1e-1  # for default values the type hint may be ommited
exp_name: str = ...  # name of experiment
beta = 0.9
out_dir: Path = ...  # any variable with '...' marked as required
# @@ configurable section ended
script.done()

print("Using directory:", out_dir)
print("Using exp name:", exp_name)

```

If you are not bothered by a single indent, you may use the context manager like so:

```python

from manu import script

with script.cli(description="trains a baseline experiment"):
    device: str = "cpu"
    learning_rate = 0.1934
    ...
    # no need to call script.done()

# proceed with the actual script here ...
```

### Running the Script

**Get help:**

```shell
python simple.py -h
```

**Run with required arguments and interpolation using `@{another_value}` syntax:**

```shell
$ python simple.py --out-dir /tmp/my-exp --exp-name "test-@{beta}"
> Using directory: /tmp/my-exp
> Using exp name: test-0.9
```

**Override from a config file:**
First, create a config file `configs/base.py`:

```python
learning_rate = 1e-3
beta = 0.99
```

Then run the script, loading the config and overriding one value:

```shell
python simple.py -c configs/base.py --beta 0.95 --out-dir ... --exp-name ...
```

**Use a custom value hook:**

Assuming you've registered a `gpu` hook with:

```python
from manu.hooks import hook, ValidationContext

@hook("gpu")
def gpu_hook(v: str, _: ValidationContext) -> str:
    if v == "free":
        return find_free_cuda_device(...)
    return "cuda:0"
```

You can now reference it in your script invocation:

```shell
python simple.py --device @gpu:free --out-dir ... --exp-name ...
# this will substitute --device with whatever your hooks returns
```

Some built-in hooks include: `@env:ENV_VAR`, `@import:foo.bar.baz` and `@value:another_value` (that's an underlying hook for `@{another_value}`).

**Save the final patched script for reproducibility:**

```shell
python simple.py --beta 0.8 ... -p /tmp/exp/simple_exp_01.py
```

This will create a new `simple_exp_01.py` script with all the final, resolved variable values in place of the previously CLI-configurable ones.

## How It Works

You designate a "configurable section" in your script with `script.init()` and `script.done()`. `manu` parses the source code of this section using Python's `ast` module to extract variable names, types, default values, and even comments as help text. It then uses this information to:

1. Build a configuration schema.
2. Generate a CLI.
3. Parse arguments, handling special syntax for config files (`-c`) and saving a patched script copy (`-p`).
4. Process values for interpolation and custom hooks.
5. Validate the final, resolved values with `pydantic`.
6. Inject the final values back into your script's global scope.

## Installation

This project uses `uv` for package management.

To install dependencies:

```shell
uv venv
uv sync
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

## Core Dependencies

- **`tyro`**: For powerful and elegant CLI generation.
- **`pydantic`**: For robust data validation and type coercion.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
