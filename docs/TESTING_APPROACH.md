# Testing Approach for manu:script

## The Challenge

The `manu` library relies on Python frame inspection to capture code within `with` blocks during runtime. This approach works well for standalone scripts but creates challenges in test environments where:

1. **Frame stack differs**: Test frameworks like pytest create different call stacks
2. **Dynamic execution**: Variables in test functions don't persist the same way as in scripts
3. **Globals isolation**: Test environments often isolate global scopes

## Current Status

### What Works ✅
- Basic functionality with fallback frame handling
- CLI argument generation via tyro
- Hook system (custom and built-in)
- Config file loading
- Type validation via Pydantic

### What's Challenging ❌
- Variable capture in test contexts
- Frame inspection reliability across environments
- Globals updating in test functions

## Recommended Testing Strategy

### 1. Unit Testing Core Components

Test individual components separately:

```python
# Test parsing
from manu.parsing import Variable, make_fields_from_vars
variables = [Variable("exp_name", str, ..., "help")]
fields = make_fields_from_vars(variables)

# Test CLI generation
import tyro
from manu.model import ScriptModel
result = tyro.cli(TestModel, args=["--exp-name", "test"])

# Test hooks
from manu.hooks import HookRegistry
from manu import hook
@hook("test")
def test_hook(val, ctx): return f"processed_{val}"
```

### 2. Integration Testing via File Execution

Create actual script files and execute them:

```python
def test_via_file_execution():
    script_content = '''
import sys
sys.path.insert(0, "src")
import manu

with manu.script(args=["--exp-name", "test"]):
    exp_name: str = ...
    device = "cpu"

print(f"exp_name={exp_name}")
print(f"device={device}")
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py') as f:
        f.write(script_content)
        f.flush()

        result = subprocess.run([sys.executable, f.name],
                              capture_output=True, text=True)
        assert "exp_name=test" in result.stdout
```

### 3. Mock-Based Testing

Test by mocking the captured context:

```python
def test_with_mocked_context():
    mock_globals = {
        "__annotations__": {"exp_name": str, "device": str},
        "exp_name": ...,
        "device": "cpu"
    }

    from manu.parsing import get_script_vars
    variables = get_script_vars("test.py", "exp_name: str = ...", mock_globals)
    # Assert variables are parsed correctly
```

### 4. End-to-End Testing

Test the actual CLI interface:

```bash
# Create test script
echo 'import manu; ...' > test_script.py
python test_script.py --exp-name test --device gpu
```

## Library Improvements Made

### 1. Enhanced Frame Inspection Fallback

Modified `src/manu/capture.py` and `src/manu/script.py` to:
- Add graceful fallback when frame inspection fails
- Use warning instead of error for missing frames
- Walk frame stack intelligently to find correct context

### 2. Test-Friendly Error Handling

Added fallback logic in `script.done()` to:
- Handle missing code capture
- Create variables from annotations when needed
- Use current globals as fallback context

### 3. Robust Variable Detection

Enhanced variable detection to work with:
- Empty captured code (test mode)
- Direct annotation scanning
- Graceful degradation

## Testing Recommendations

### For Library Users

1. **Unit tests**: Test individual components separately
2. **Integration tests**: Use file-based execution for complex scenarios
3. **CLI tests**: Test command-line interface directly
4. **Mock tests**: Mock frame context for specific scenarios

### For Library Development

1. **Component tests**: Test parsing, hooks, validation separately
2. **Fallback tests**: Ensure graceful degradation works
3. **Cross-environment tests**: Test in different Python environments
4. **Performance tests**: Ensure fallbacks don't significantly impact performance

## Example Test Structure

```
tests/
├── unit/
│   ├── test_parsing.py      # Variable parsing logic
│   ├── test_hooks.py        # Hook system
│   ├── test_validation.py   # Type validation
│   └── test_cli.py         # CLI generation
├── integration/
│   ├── test_file_execution.py  # File-based tests
│   ├── test_config_files.py    # Config loading
│   └── test_end_to_end.py      # Complete workflows
└── examples/
    ├── test_readme_examples.py # Ensure docs work
    └── test_simple_cases.py    # Basic functionality
```

## Known Limitations

1. **Frame inspection**: May not work in all environments (IPython, Jupyter, some test runners)
2. **Variable persistence**: Test variables may not persist as expected
3. **Globals isolation**: Test frameworks may isolate global scopes

## Workarounds

1. Use subprocess execution for critical integration tests
2. Test components separately when possible
3. Mock frame context for unit tests
4. Use file-based execution for end-to-end validation

## Future Improvements

1. **Test mode flag**: Add explicit test mode to bypass frame inspection
2. **Direct variable injection**: Allow direct variable specification for testing
3. **Alternative capture methods**: Explore AST-based or decorator-based approaches
4. **Better test utilities**: Provide test helpers for common scenarios
