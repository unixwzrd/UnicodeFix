from pathlib import Path

from unicodefix.watermarks import _fingerprint, detect_with_profile, load_profile


def _profile(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "profile.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_literal_fixture_profile_is_explicit(tmp_path):
    profile = _profile(
        tmp_path,
        '[watermark]\nscheme = "literal_fixture"\nmarker = "LOCAL-MARK"\n',
    )
    assert detect_with_profile("x LOCAL-MARK y", profile).status == "detected"
    assert detect_with_profile("plain", profile).status == "not_detected"


def test_unknown_profile_is_unsupported(tmp_path):
    profile = _profile(tmp_path, '[watermark]\nscheme = "vendor-secret"\n')
    result = detect_with_profile("enough text", profile)
    assert result.status == "unsupported"
    assert result.configuration_fingerprint


def test_profile_minimum_length(tmp_path):
    profile = _profile(
        tmp_path,
        '[watermark]\nscheme = "literal_fixture"\nmarker = "x"\nminimum_tokens = 3\n',
    )
    assert detect_with_profile("too short", profile).status == "insufficient_text"


def test_keys_are_not_exposed_in_result(tmp_path):
    profile = _profile(
        tmp_path,
        '[watermark]\nscheme = "kgw"\nhashing_key = 987654321\n',
    )
    result = detect_with_profile("a sufficiently long sample", profile)
    assert "987654321" not in str(result.to_dict())


def test_configuration_fingerprint_does_not_hash_low_entropy_keys(tmp_path):
    first = tmp_path / "first.toml"
    second = tmp_path / "second.toml"
    first.write_text('[watermark]\nscheme="kgw"\nhashing_key=1\n')
    second.write_text('[watermark]\nscheme="kgw"\nhashing_key=2\n')
    _, first_fingerprint = load_profile(first)
    _, second_fingerprint = load_profile(second)
    assert first_fingerprint == second_fingerprint


def test_configuration_fingerprint_tracks_local_artifact_paths():
    first = _fingerprint(
        {"hashing_key": 123, "model_path": "/model", "tokenizer_path": "/tokens"}
    )
    assert first == _fingerprint(
        {"hashing_key": 456, "model_path": "/model", "tokenizer_path": "/tokens"}
    )
    assert first != _fingerprint(
        {"hashing_key": 456, "model_path": "/other", "tokenizer_path": "/tokens"}
    )
