import csv
import io
import json
import os
import pathlib
import stat
import subprocess
import sys

from unicodefix.c2pa import build_text_wrapper, encode_variation_selectors
from unicodefix.metrics import compute_metrics


def run_cli(args, stdin=None):
    environment = os.environ.copy()
    source = str(pathlib.Path(__file__).resolve().parents[1] / "src")
    environment["PYTHONPATH"] = source
    process = subprocess.run(
        [sys.executable, "-m", "unicodefix.cli", *args],
        input=stdin,
        text=True,
        capture_output=True,
        env=environment,
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def test_dry_run_json_is_non_mutating_and_reports_before_after(tmp_path):
    source = tmp_path / "sample.txt"
    original = "“hello”\u200b\n"
    source.write_text(original, encoding="utf-8")
    code, stdout, stderr = run_cli(["--dry-run", "--json", str(source)])
    assert code == 0, stderr
    assert source.read_text(encoding="utf-8") == original
    assert not (tmp_path / "sample.clean.txt").exists()
    report = json.loads(stdout)[str(source)]
    assert report["planned"]["changed"] is True
    assert report["planned"]["before"] != report["planned"]["after"]

    output = tmp_path / "cleaned.txt"
    code, _, stderr = run_cli(["-o", str(output), str(source)])
    assert code == 0, stderr
    assert report["planned"]["after"] == compute_metrics(
        output.read_text(encoding="utf-8")
    )


def test_dry_run_diff_shows_exact_cleanup_without_writing(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("a\u200bb\n", encoding="utf-8")
    code, stdout, stderr = run_cli(["--dry-run", "--diff", str(source)])
    assert code == 0, stderr
    assert "-a\u200bb" in stdout
    assert "+ab" in stdout
    assert source.read_text(encoding="utf-8") == "a\u200bb\n"


def test_dry_run_csv_contains_structured_before_after_counts(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("a\u200bb\n", encoding="utf-8")
    code, stdout, stderr = run_cli(["--dry-run", "--csv", str(source)])
    assert code == 0, stderr
    row = next(csv.DictReader(io.StringIO(stdout)))
    assert row["planned_changed"] == "True"
    assert int(row["before_characters"]) > int(row["after_characters"])


def test_in_place_cleanup_is_atomic_and_preserves_mode(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("“hello”\u200b\n", encoding="utf-8")
    source.chmod(0o640)
    os.utime(source, (1, 1))

    code, _, stderr = run_cli(["--temp", str(source)])

    assert code == 0, stderr
    assert source.read_text(encoding="utf-8") == '"hello"\n'
    assert stat.S_IMODE(source.stat().st_mode) == 0o640
    assert source.stat().st_mtime > 1
    assert list(tmp_path.glob(".sample.txt.*.tmp")) == []
    assert not (tmp_path / "sample.txt.tmp").exists()


def test_preserved_backup_never_overwrites_an_existing_backup(tmp_path):
    source = tmp_path / "sample.txt"
    existing = tmp_path / "sample.txt.tmp"
    source.write_text("“original”\n", encoding="utf-8")
    existing.write_text("existing backup\n", encoding="utf-8")

    code, _, stderr = run_cli(["--temp", "--preserve-tmp", str(source)])

    assert code == 0, stderr
    assert source.read_text(encoding="utf-8") == '"original"\n'
    assert existing.read_text(encoding="utf-8") == "existing backup\n"
    assert (tmp_path / "sample.txt.tmp.1").read_text(encoding="utf-8") == (
        "“original”\n"
    )


def test_markdown_unwrap_preserves_distinct_list_items(tmp_path):
    source = tmp_path / "sample.md"
    output = tmp_path / "out.md"
    source.write_text(
        "- first item that\n  continues here\n- second item\n", encoding="utf-8"
    )
    code, _, stderr = run_cli(["--unwrap-markdown", "-o", str(output), str(source)])
    assert code == 0, stderr
    assert output.read_text(encoding="utf-8") == (
        "- first item that continues here\n- second item\n"
    )


def test_markdown_refuses_c2pa_without_explicit_strip(tmp_path):
    carrier = "\ufeff" + encode_variation_selectors(build_text_wrapper(b"fixture"))
    source = tmp_path / "signed.md"
    output = tmp_path / "out.md"
    source.write_text(f"paragraph{carrier}\nwraps\n", encoding="utf-8")
    code, _, stderr = run_cli(["--unwrap-markdown", "-o", str(output), str(source)])
    assert code == 1
    assert "C2PA provenance" in stderr
    assert not output.exists()

    code, _, stderr = run_cli(
        [
            "--unwrap-markdown",
            "--strip-provenance",
            "-o",
            str(output),
            str(source),
        ]
    )
    assert code == 0, stderr
    assert carrier not in output.read_text(encoding="utf-8")


def test_category_threshold_only_counts_selected_findings(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("“typography only”\n", encoding="utf-8")
    code, _, _ = run_cli(
        [
            "--report",
            "--threshold",
            "1",
            "--threshold-category",
            "unicode_security",
            str(source),
        ]
    )
    assert code == 0
    code, _, _ = run_cli(
        [
            "--report",
            "--threshold",
            "1",
            "--threshold-category",
            "typography",
            str(source),
        ]
    )
    assert code == 1


def test_source_mode_cleans_comments_only(tmp_path):
    source = tmp_path / "sample.py"
    output = tmp_path / "out.py"
    source.write_text("# remove\u200b\nvalue = 'keep\u200b'\n", encoding="utf-8")
    code, _, stderr = run_cli(["--source", "-o", str(output), str(source)])
    assert code == 0, stderr
    assert output.read_text(encoding="utf-8") == "# remove\nvalue = 'keep\u200b'\n"


def test_local_profile_status_is_reported_without_secret(tmp_path):
    profile = tmp_path / "profile.toml"
    profile.write_text(
        '[watermark]\nscheme="literal_fixture"\nmarker="MARK"\n', encoding="utf-8"
    )
    code, stdout, stderr = run_cli(
        ["--report", "--json", "--watermark-profile", str(profile)], stdin="MARK\n"
    )
    assert code == 0, stderr
    result = json.loads(stdout)["-"]["known_watermarks"][0]
    assert result["status"] == "detected"
    assert result["scheme"] == "literal_fixture"


def test_known_watermark_threshold_counts_profile_detection(tmp_path):
    profile = tmp_path / "profile.toml"
    profile.write_text(
        '[watermark]\nscheme="literal_fixture"\nmarker="MARK"\n', encoding="utf-8"
    )
    code, _, stderr = run_cli(
        [
            "--report",
            "--threshold",
            "1",
            "--threshold-category",
            "known_watermark",
            "--watermark-profile",
            str(profile),
        ],
        stdin="MARK\n",
    )
    assert code == 1, stderr


def test_authorship_profile_reports_unsupported_without_claiming_detection(tmp_path):
    profile = tmp_path / "authorship.toml"
    profile.write_text('[authorship]\nmethod="anthropic_private"\n', encoding="utf-8")
    code, stdout, stderr = run_cli(
        ["--report", "--json", "--authorship-profile", str(profile)],
        stdin="A paragraph for an explicitly unsupported detector.\n",
    )
    assert code == 0, stderr
    report = json.loads(stdout)["-"]
    assert report["authorship_signals"][0]["status"] == "unsupported"
    assert not any(
        item["category"] == "authorship_signal" for item in report["findings"]
    )
