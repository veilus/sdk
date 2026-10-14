import os
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check
from check import Example, render_table, run_example

PY = sys.executable
OK = 'print("VEILUS_EXAMPLE_VERSION fakepkg 1.2.3"); print("VEILUS_EXAMPLE_OK Example Domain")'


def running(_):
    return True


def test_pass_needs_exit_zero_marker_and_running_profile():
    r = run_example(Example("fake", [PY, "-c", OK]), {}, running)
    assert (r.status, r.version) == ("PASS", "fakepkg 1.2.3")


def test_fail_when_exit_nonzero_even_with_marker():
    r = run_example(
        Example("fake", [PY, "-c", OK + "; raise SystemExit(3)"]), {}, running
    )
    assert r.status == "FAIL" and "exit 3" in r.reason


def test_fail_when_marker_missing():
    r = run_example(Example("fake", [PY, "-c", "print('hello')"]), {}, running)
    assert r.status == "FAIL" and "VEILUS_EXAMPLE_OK" in r.reason


def test_fail_when_example_closed_the_profile():
    r = run_example(Example("fake", [PY, "-c", OK]), {}, lambda _: False)
    assert r.status == "FAIL" and "closed" in r.reason


def test_skip_names_the_missing_env_var(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = run_example(
        Example("llm", [PY, "-c", OK], needs_env=("ANTHROPIC_API_KEY",)), {}, running
    )
    assert r.status == "SKIP" and "ANTHROPIC_API_KEY" in r.reason


def test_skip_names_the_missing_command():
    r = run_example(
        Example("ab", ["x"], needs_cmd=("no-such-cmd-veilus",)), {}, running
    )
    assert r.status == "SKIP" and "no-such-cmd-veilus" in r.reason


def test_table_lists_every_result_with_date():
    rows = [run_example(Example("fake", [PY, "-c", OK]), {}, running)]
    table = render_table(rows, "2026-10-14")
    assert "2026-10-14" in table and "| fake | fakepkg 1.2.3 | PASS |" in table


def test_table_escapes_pipe_in_reason():
    row = check.Result("x", "FAIL", "exit 1: a | b")
    assert "a \\| b" in render_table([row], "2026-10-14")


def test_timeout_kills_the_process_group(tmp_path):
    pidfile = tmp_path / "grandchild.pid"
    code = (
        "import subprocess, sys, time\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(pidfile)!r}, 'w').write(str(p.pid))\n"
        "time.sleep(60)\n"
    )
    r = run_example(Example("slow", [PY, "-c", code]), {}, running, timeout=2)
    assert (r.status, r.reason) == ("FAIL", "timeout after 2s")
    pid = int(pidfile.read_text())
    time.sleep(0.5)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return
    os.kill(pid, signal.SIGKILL)
    raise AssertionError("grandchild survived the timeout")


def _app_dir(monkeypatch, tmp_path, endpoint=None, token="t"):
    monkeypatch.setenv("VEILUS_APP_DIR", str(tmp_path))
    if token is None:
        monkeypatch.delenv("VEILUS_API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("VEILUS_API_TOKEN", token)
    if endpoint is not None:
        (tmp_path / "api-endpoint.json").write_text(endpoint)


def test_main_exits_2_when_endpoint_file_missing(monkeypatch, tmp_path, capsys):
    _app_dir(monkeypatch, tmp_path)
    assert check.main([]) == 2
    err = capsys.readouterr().err
    assert "api-endpoint.json" in err and "Traceback" not in err


def test_main_exits_2_when_token_unset(monkeypatch, tmp_path, capsys):
    _app_dir(monkeypatch, tmp_path, '{"rest_port": 1}', token=None)
    assert check.main([]) == 2
    assert "VEILUS_API_TOKEN" in capsys.readouterr().err


def test_main_exits_2_on_malformed_endpoint(monkeypatch, tmp_path):
    _app_dir(monkeypatch, tmp_path, "{not json")
    assert check.main([]) == 2
    _app_dir(monkeypatch, tmp_path, "{}")
    assert check.main([]) == 2


def test_main_exits_2_when_api_unreachable(monkeypatch, tmp_path):
    _app_dir(monkeypatch, tmp_path, '{"rest_port": 1}')
    assert check.main([]) == 2


def test_main_exits_2_when_no_profiles(monkeypatch, tmp_path):
    _app_dir(monkeypatch, tmp_path, '{"rest_port": 1}')
    monkeypatch.setattr(check.Api, "profiles", lambda self: [])
    assert check.main([]) == 2


def test_main_exits_2_when_launch_fails(monkeypatch, tmp_path, capsys):
    _app_dir(monkeypatch, tmp_path, '{"rest_port": 1}')
    monkeypatch.setenv("VEILUS_PROFILE_ID", "nope")
    monkeypatch.setattr(check.Api, "profiles", lambda self: [{"id": "a"}])
    assert check.main([]) == 2
    assert "Traceback" not in capsys.readouterr().err


def test_only_unknown_name_exits_2_and_lists_valid_names(capsys):
    assert check.main(["--only", "nope"]) == 2
    assert "playwright" in capsys.readouterr().err


def test_write_tested_refuses_with_only(capsys):
    assert check.main(["--only", "playwright", "--write-tested"]) == 2
    assert "--write-tested" in capsys.readouterr().err
