import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

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


def test_custom_marker_passes_without_example_ok_line():
    ex = Example("sol", [PY, "-c", "print('RESULT {}')"], marker="RESULT ")
    assert run_example(ex, {}, running).status == "PASS"


def test_custom_marker_missing_names_it_in_reason():
    ex = Example("sol", [PY, "-c", "print('VEILUS_EXAMPLE_OK x')"], marker="RESULT ")
    r = run_example(ex, {}, running)
    assert r.status == "FAIL" and "no RESULT line" in r.reason


def test_example_env_reaches_the_process():
    code = "import os; print('RESULT ' + os.environ['VEILUS_VAR_X'])"
    ex = Example("sol", [PY, "-c", code], marker="RESULT ", env={"VEILUS_VAR_X": "1"})
    assert run_example(ex, {}, running).status == "PASS"


def test_dataset_rows_turns_csv_into_json_rows(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text(
        "URL,SELECTOR\nhttps://a.test/,.p\nhttps://b.test/,\n", encoding="utf-8"
    )
    assert json.loads(check.dataset_rows(f)) == [
        {"URL": "https://a.test/", "SELECTOR": ".p"},
        {"URL": "https://b.test/", "SELECTOR": ""},
    ]


def _api_with(monkeypatch, profiles):
    monkeypatch.setattr(check.Api, "profiles", lambda self: profiles)
    return object.__new__(check.Api)


def test_debug_port_comes_from_cdp_url(monkeypatch):
    api = _api_with(monkeypatch, [{"id": "a", "cdpUrl": "http://127.0.0.1:9333"}])
    assert api.debug_port("a") == 9333


def test_debug_port_without_cdp_url_is_a_preflight_error(monkeypatch):
    api = _api_with(monkeypatch, [{"id": "a"}])
    with pytest.raises(check.PreflightError, match="CDP"):
        api.debug_port("a")


def test_every_solution_dir_is_run_by_check():
    dirs = {d.name for d in check.SOLUTIONS.iterdir() if (d / "script.ts").exists()}
    listed = {
        e.name.removeprefix("solution:")
        for e in check.EXAMPLES
        if e.name.startswith("solution:")
    }
    assert dirs == listed
