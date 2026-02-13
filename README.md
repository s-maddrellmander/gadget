# gadget

[![Tests](https://github.com/s-maddrellmander/gadget/actions/workflows/tests.yml/badge.svg)](https://github.com/s-maddrellmander/gadget/actions/workflows/tests.yml)

A tiny helper for quick timing/debug prints with file and line context.

## Install

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

## Install from PyPI

```bash
pip install gadget-timer
```

## Notes

- Package name on PyPI is `gadget-timer`.
- Import path is still `gadget`.
- For Git installs, the repository URL is:

  ```bash
  pip install "git+https://github.com/s-maddrellmander/gadget.git"
  ```
