from types import SimpleNamespace

import gadget as gadget_module


class DummySize:
    columns = 120


def test_gadget_call_updates_group_and_prints(monkeypatch, capsys):
    g = gadget_module.Gadget(verbose=True)

    times = iter([10.0, 10.5, 12.0, 12.2, 13.0, 14.0])
    monkeypatch.setattr(gadget_module.time, "time", lambda: next(times))

    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=2, filename="fake_file.py"),
    )

    class FakeFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def readlines(self):
            return ["line1\n", "line2\n", "line3\n"]

    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: FakeFile())
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "fake_file.py")
    monkeypatch.setattr(gadget_module.shutil, "get_terminal_size", lambda: DummySize())

    g("first", group="phase")
    g("second", group="phase")
    g("third", _caller_frame="explicit_frame")

    out = capsys.readouterr().out
    assert "first" in out
    assert "second" in out
    assert "third" in out
    assert "[phase:" in out
    assert g.group_times["phase"] == 1.5


def test_gadget_call_handles_open_and_relpath_errors(monkeypatch, capsys):
    g = gadget_module.Gadget(verbose=True)

    times = iter([20.0, 20.25])
    monkeypatch.setattr(gadget_module.time, "time", lambda: next(times))

    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=1, filename="/tmp/does-not-exist.py"),
    )
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")))
    monkeypatch.setattr(
        gadget_module.os.path,
        "relpath",
        lambda _p: (_ for _ in ()).throw(ValueError("bad path")),
    )
    monkeypatch.setattr(gadget_module.shutil, "get_terminal_size", lambda: DummySize())

    g("hello")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "does-not-exist.py:1" in out


def test_gadget_early_return_when_not_verbose(capsys):
    g = gadget_module.Gadget(verbose=False)
    g("silent")
    assert capsys.readouterr().out == ""


def test_reset_branches():
    g = gadget_module.Gadget()
    g.group_times = {"a": 1.0, "b": 2.0}

    g.reset("a")
    assert g.group_times == {"b": 2.0}

    g.reset("missing")
    assert g.group_times == {"b": 2.0}

    g.reset()
    assert g.group_times == {}


def test_convenience_functions_and_config(monkeypatch):
    calls = []

    class StubDefault:
        def __call__(self, s, group, _caller_frame=None):
            calls.append(("call", s, group, _caller_frame))

        def reset(self, group=None):
            calls.append(("reset", group))

    stub = StubDefault()
    monkeypatch.setattr(gadget_module, "_default_gadget", stub)
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="callsite_frame"),
    )

    gadget_module.gadget("msg", group="grp")
    gadget_module.gadget_reset("grp")

    assert calls[0] == ("call", "msg", "grp", "callsite_frame")
    assert calls[1] == ("reset", "grp")

    gadget_module.gadget_config(verbose=False)
    assert isinstance(gadget_module._default_gadget, gadget_module.Gadget)
    assert gadget_module._default_gadget.verbose is False


def test_version_export():
    assert gadget_module.__version__ == "0.1.0"


def test_gadget_mem_missing_psutil(monkeypatch, capsys):
    """Test gadget_mem() when psutil is not installed."""
    def mock_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("No module named 'psutil'")
        return __import__(name, *args, **kwargs)
    
    monkeypatch.setattr("builtins.__import__", mock_import)
    
    gadget_module.gadget_mem("test")
    out = capsys.readouterr().out
    assert "requires psutil" in out


def test_gadget_mem_not_verbose(monkeypatch, capsys):
    """Test gadget_mem() respects verbose flag."""
    monkeypatch.setattr(gadget_module._default_gadget, "verbose", False)
    
    # Mock psutil to ensure it returns if not verbose
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)
        def virtual_memory(self):
            return SimpleNamespace(used=10e9, total=32e9)
        def swap_memory(self):
            return SimpleNamespace(used=1e9, total=8e9)
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    gadget_module.gadget_mem("test")
    out = capsys.readouterr().out
    assert out == ""
    
    # Reset verbose
    monkeypatch.setattr(gadget_module._default_gadget, "verbose", True)


def test_gadget_mem_green_color(monkeypatch, capsys):
    """Test gadget_mem() outputs green when all memory < 50%."""
    # Mock psutil with low memory usage
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)  # 1GB
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)  # 31% used
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)  # 12.5% used
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=10, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("low_memory")
    out = capsys.readouterr().out
    
    assert "[mem:low_memory]" in out
    assert "RSS=" in out
    assert "swap=" in out
    assert "sys=" in out
    assert "\033[32m" in out  # Green color code
    assert "test.py:10" in out


def test_gadget_mem_yellow_color(monkeypatch, capsys):
    """Test gadget_mem() outputs yellow when any memory is 50-80%."""
    # Mock psutil with medium memory usage
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=5e9)  # 5GB
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=20e9, total=32e9)  # 62.5% used
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)  # 12.5% used
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=20, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("medium_memory")
    out = capsys.readouterr().out
    
    assert "[mem:medium_memory]" in out
    assert "\033[33m" in out  # Yellow color code


def test_gadget_mem_red_color(monkeypatch, capsys):
    """Test gadget_mem() outputs red when any memory > 80%."""
    # Mock psutil with high memory usage
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=2e9)  # 2GB
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)  # 31% used
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=7e9, total=8e9)  # 87.5% used (triggers red!)
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=30, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("high_memory")
    out = capsys.readouterr().out
    
    assert "[mem:high_memory]" in out
    assert "\033[31m" in out  # Red color code


def test_gadget_mem_with_gpu(monkeypatch, capsys):
    """Test gadget_mem() includes GPU info when torch is available."""
    # Mock psutil
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)
    
    # Mock torch with CUDA
    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available():
                return True
            @staticmethod
            def memory_allocated():
                return 2e9  # 2GB
            @staticmethod
            def get_device_properties(device):
                return SimpleNamespace(total_memory=8e9)  # 8GB total
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    sys.modules['torch'] = FakeTorch()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=40, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("gpu_test")
    out = capsys.readouterr().out
    
    assert "gpu=" in out
    assert "[mem:gpu_test]" in out


def test_gadget_mem_percentages_displayed(monkeypatch, capsys):
    """Test that all memory metrics show percentages."""
    # Mock psutil
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=4e9)  # 4GB
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=16e9, total=32e9)  # 50%
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=2e9, total=8e9)  # 25%
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=50, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("percent_test")
    out = capsys.readouterr().out
    
    # Check that percentages are displayed
    assert "RSS=4.00GB(13%)" in out or "RSS=4.00GB(12%)" in out  # RSS as % of total
    assert "swap=2.00GB(25%)" in out
    assert "sys=16.0/32.0GB(50%)" in out


def test_gadget_mem_handles_relpath_error(monkeypatch, capsys):
    """Test gadget_mem() handles relpath errors gracefully."""
    # Mock psutil
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=60, filename="/some/absolute/path.py"),
    )
    monkeypatch.setattr(
        gadget_module.os.path,
        "relpath",
        lambda _p: (_ for _ in ()).throw(ValueError("bad path")),
    )
    monkeypatch.setattr(gadget_module.os.path, "basename", lambda _p: "path.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem()  # No label
    out = capsys.readouterr().out
    
    assert "[mem]" in out  # No label case
    assert "path.py:60" in out  # Used basename as fallback


def test_gadget_mem_torch_exception(monkeypatch, capsys):
    """Test gadget_mem() handles torch import errors."""
    # Mock psutil
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    # Remove torch from sys.modules to ensure import fails
    if 'torch' in sys.modules:
        del sys.modules['torch']
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=70, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("no_gpu")
    out = capsys.readouterr().out
    
    assert "[mem:no_gpu]" in out
    assert "gpu=" not in out  # No GPU info when import fails


def test_gadget_mem_no_swap_and_no_cuda(monkeypatch, capsys):
    """Test gadget_mem() when swap is zero and CUDA is not available."""
    # Mock psutil with no swap
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=0, total=0)  # No swap
    
    # Mock torch with no CUDA
    class FakeTorch:
        class cuda:
            @staticmethod
            def is_available():
                return False  # CUDA not available
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    sys.modules['torch'] = FakeTorch()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=80, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    gadget_module.gadget_mem("no_swap_cuda")
    out = capsys.readouterr().out
    
    assert "[mem:no_swap_cuda]" in out
    assert "swap=0.00GB(0%)" in out  # Swap exists but is zero
    assert "gpu=" not in out  # No GPU when CUDA not available


def test_gadget_mem_class_method(monkeypatch, capsys):
    """Test using mem() as a class method."""
    # Mock psutil
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=2e9)
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=15e9, total=32e9)
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(
        gadget_module.inspect,
        "currentframe",
        lambda: SimpleNamespace(f_back="fake_frame"),
    )
    monkeypatch.setattr(
        gadget_module.inspect,
        "getframeinfo",
        lambda _frame: SimpleNamespace(lineno=90, filename="test.py"),
    )
    monkeypatch.setattr(gadget_module.os.path, "relpath", lambda _p: "test.py")
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    # Test class-based API
    timer = gadget_module.Gadget(verbose=True)
    timer.mem("class_test")
    out = capsys.readouterr().out
    
    assert "[mem:class_test]" in out
    assert "RSS=" in out
    assert "test.py:90" in out


def test_gadget_mem_class_not_verbose(monkeypatch, capsys):
    """Test class mem() method respects verbose=False."""
    # Mock psutil
    class FakePsutil:
        class Process:
            def __init__(self, pid):
                pass
            def memory_info(self):
                return SimpleNamespace(rss=1e9)
        @staticmethod
        def virtual_memory():
            return SimpleNamespace(used=10e9, total=32e9)
        @staticmethod
        def swap_memory():
            return SimpleNamespace(used=1e9, total=8e9)
    
    import sys
    sys.modules['psutil'] = FakePsutil()
    
    monkeypatch.setattr(gadget_module.os, "getpid", lambda: 12345)
    
    # Test verbose=False
    timer = gadget_module.Gadget(verbose=False)
    timer.mem("silent")
    out = capsys.readouterr().out
    
    assert out == ""
