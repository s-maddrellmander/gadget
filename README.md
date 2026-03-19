# gadget

[![Tests](https://github.com/s-maddrellmander/gadget/actions/workflows/tests.yml/badge.svg)](https://github.com/s-maddrellmander/gadget/actions/workflows/tests.yml)

A tiny helper for quick timing/debug prints with file and line context.

## Install

### From PyPI

```bash
pip install gadget-timer
```

To enable memory profiling features:

```bash
pip install 'gadget-timer[mem]'
```

### From a local checkout

```bash
pip install .
```

### Directly from GitHub

```bash
pip install "git+https://github.com/s-maddrellmander/gadget.git"
```

### Editable install (for development)

```bash
pip install -e .
```

## Usage

### Functional API

```python
from gadget import gadget, gadget_reset, gadget_config

gadget("start")
# ... some code ...
gadget("after step")

gadget("phase 1", group="build")
gadget("phase 2", group="build")
gadget_reset("build")

gadget_config(verbose=False)  # disable output globally
```

### Class-based API

```python
from gadget import Gadget

timer = Gadget(verbose=True)
timer("start")
# ... some code ...
timer("step", group="build")
timer.reset("build")
timer.reset()  # reset all groups
```

## Memory Profiling

Track memory usage at key checkpoints with color-coded output.

### Installation

Memory profiling requires `psutil`:

```bash
pip install 'gadget-timer[mem]'
```

### Functional API

```python
from gadget import gadget_mem

gadget_mem("after_data_load")
# Output: [mem:after_data_load] RSS=2.34GB(7%) swap=0.50GB(6%) sys=10.2/32.0GB(32%) → script.py:42
```

### Class-based API

```python
from gadget import Gadget

timer = Gadget()
timer.mem("model_initialized")
timer.mem("training_started")
```

### Color Coding

Memory output is color-coded based on the highest usage across all metrics:

- 🟢 **Green**: All memory usage < 50%
- 🟡 **Yellow**: Any memory usage between 50-80%
- 🔴 **Red**: Any memory usage > 80%

### Metrics Displayed

- **RSS**: Resident Set Size (process memory usage)
- **swap**: Swap memory used
- **sys**: System memory (used/total)
- **gpu**: GPU memory (if PyTorch with CUDA is available)

All metrics show percentages for at-a-glance assessment.

## Notes

- Package name on PyPI is `gadget-timer`.
- Import path is still `gadget`.
- For Git installs, the repository URL is:

  ```bash
  pip install "git+https://github.com/s-maddrellmander/gadget.git"
  ```
