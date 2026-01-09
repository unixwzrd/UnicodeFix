import json
import os
import pathlib
import subprocess
import sys
import tempfile


def run_cli(args, stdin=None):
    env = os.environ.copy()
    p = subprocess.run(["cleanup-text", *args],
                       input=stdin.encode() if isinstance(stdin, str) else None,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)
    return p.returncode, p.stdout.decode(), p.stderr.decode()


def test_report_json_exitcode_threshold(tmp_path: pathlib.Path):
    s = '“hi”\u200B'  # guaranteed anomalies
    f = tmp_path / "t.txt"
    f.write_text(s, encoding="utf-8")
    code, out, _ = run_cli(["--report", "--json", "--threshold", "1", str(f)])
    assert code == 1
    data = json.loads(out)
    assert str(f) in data
    assert data[str(f)]["total"] >= 1


def test_filter_mode_stdout_roundtrip():
    code, out, _ = run_cli(["--report","--json"], stdin='“x”—y')
    assert code == 0
    j = json.loads(out)
    # stdin path key should be "-" per our CLI
    assert "-" in j
