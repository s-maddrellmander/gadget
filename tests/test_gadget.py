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
