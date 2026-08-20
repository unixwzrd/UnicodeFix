import importlib.util
from pathlib import Path

HARNESS_PATH = Path(__file__).parents[1] / "research" / "watermarks" / "harness.py"
SPEC = importlib.util.spec_from_file_location("watermark_harness", HARNESS_PATH)
harness = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(harness)
PROFILE = HARNESS_PATH.parent / "profiles" / "example-fixture.toml"


def test_fixture_profile_detects_only_its_marker():
    result = harness.run_profile(
        "long enough [[UNICODEFIX-WATERMARK-FIXTURE]] text", PROFILE
    )
    assert result["status"] == "detected"
    assert result["score"] == 1
    assert "marker" not in result


def test_fixture_profile_reports_non_match_and_short_text():
    assert (
        harness.run_profile("ordinary content that is long enough", PROFILE)["status"]
        == "not_detected"
    )
    assert harness.run_profile("short", PROFILE)["status"] == "insufficient_text"


def test_unsupported_profile_and_invalid_profile_are_explicit():
    unsupported = HARNESS_PATH.parent / "profiles" / "example-synthid.toml"
    assert harness.run_profile("x" * 300, unsupported)["status"] == "unsupported"
    assert (
        harness.run_profile("text", "does-not-exist.toml")["status"]
        == "configuration_error"
    )


def test_harness_fingerprint_does_not_hash_low_entropy_secrets():
    first = {"profile": {"name": "x"}, "detector": {"adapter": "x", "seed": 1}}
    second = {"profile": {"name": "x"}, "detector": {"adapter": "x", "seed": 2}}
    assert harness._fingerprint(first) == harness._fingerprint(second)
