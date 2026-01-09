import json
import os
import pathlib
import subprocess
import sys
import tempfile


def run_cli(args, stdin=None):
    env = os.environ.copy()
    # Try cleanup-text first, fall back to python -m unicodefix.cli if not found
    cmd_list = ["cleanup-text"]
    try:
        # Check if cleanup-text is available
        subprocess.run(
            cmd_list + ["--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=2,
        )
    except (
        FileNotFoundError,
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
    ):
        # Fall back to python module invocation
        cmd_list = [sys.executable, "-m", "unicodefix.cli"]

    p = subprocess.run(
        cmd_list + list(args),
        input=stdin.encode("utf-8") if isinstance(stdin, str) else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    return (
        p.returncode,
        p.stdout.decode("utf-8", errors="replace"),
        p.stderr.decode("utf-8", errors="replace"),
    )


def test_report_json_exitcode_threshold(tmp_path: pathlib.Path):
    s = "“hi”\u200b"  # guaranteed anomalies
    f = tmp_path / "t.txt"
    f.write_text(s, encoding="utf-8")
    code, out, err = run_cli(["--report", "--json", "--threshold", "1", str(f)])
    # Exit code should be 1 when threshold is exceeded
    assert code == 1, f"Expected exit code 1, got {code}. stderr: {err}"
    # JSON should still be output to stdout even when exit code is 1
    assert out.strip(), f"Expected JSON output, got empty. stderr: {err}"
    data = json.loads(out)
    assert str(f) in data
    assert data[str(f)]["total"] >= 1


def test_filter_mode_stdout_roundtrip():
    # When using --report with stdin, if there are anomalies, it may exit with 1
    # unless --exit-zero is used. Let's use --exit-zero to ensure exit code 0
    code, out, err = run_cli(
        ["--report", "--json", "--exit-zero"], stdin="\u201cx\u201d\u2014y"
    )  # "x"—y
    assert (
        code == 0
    ), f"Expected exit code 0, got {code}. stdout: {out[:200]}, stderr: {err[:200]}"
    assert out.strip(), f"Expected JSON output, got empty. stderr: {err[:200]}"
    j = json.loads(out)
    # stdin path key should be "-" per our CLI
    assert "-" in j
