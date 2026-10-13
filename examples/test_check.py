import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
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


def test_skip_names_the_missing_env_var():
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
