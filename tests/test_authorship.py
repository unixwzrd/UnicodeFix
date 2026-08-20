from pathlib import Path

from unicodefix import authorship


def _profile(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "profile.toml"
    path.write_text(
        """[authorship]
method = "causal_lm_likelihood"
model_path = "/models/reference"
tokenizer_path = "/models/reference"
metric = "mean_nll"
threshold = 2.5
comparison = "lte"
minimum_tokens = 4
calibration_slope = -2.0
calibration_intercept = 5.0
""" + extra,
        encoding="utf-8",
    )
    return path


def test_paragraphs_preserve_offsets_and_lines():
    text = "first line\ncontinues\n\nsecond paragraph\n"
    paragraphs = authorship._paragraphs(text)

    assert [item["text"] for item in paragraphs] == [
        "first line\ncontinues",
        "second paragraph\n",
    ]
    assert [(item["line"], item["end_line"]) for item in paragraphs] == [
        (1, 2),
        (4, 5),
    ]


def test_profile_flags_only_crossing_paragraph(monkeypatch, tmp_path):
    def fake_score(paragraphs, config):
        assert len(paragraphs) == 2
        return [
            {
                "line": 1,
                "column": 1,
                "end_line": 1,
                "end_column": 13,
                "offset": 0,
                "end_offset": 12,
                "token_count": 8,
                "mean_nll": 2.0,
                "perplexity": 7.4,
                "mean_rank": 3.0,
                "top_10_fraction": 0.9,
            },
            {
                "line": 3,
                "column": 1,
                "end_line": 3,
                "end_column": 17,
                "offset": 14,
                "end_offset": 30,
                "token_count": 10,
                "mean_nll": 4.0,
                "perplexity": 54.6,
                "mean_rank": 20.0,
                "top_10_fraction": 0.2,
            },
        ]

    monkeypatch.setattr(authorship, "_score_causal_lm", fake_score)
    result = authorship.detect_authorship_with_profile(
        "first enough\n\nsecond paragraph", _profile(tmp_path)
    ).to_dict()

    assert result["status"] == "potentially_ai_generated"
    assert [item["flagged"] for item in result["segments"]] == [True, False]
    assert result["segments"][0]["estimated_ai_probability"] is not None
    assert result["configuration_fingerprint"] != "unavailable"


def test_profile_without_calibration_does_not_invent_probability(monkeypatch, tmp_path):
    profile = tmp_path / "uncalibrated.toml"
    profile.write_text(
        """[authorship]
model_path = "/models/reference"
tokenizer_path = "/models/reference"
threshold = 3.0
minimum_tokens = 1
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        authorship,
        "_score_causal_lm",
        lambda paragraphs, config: [
            {
                "line": 1,
                "column": 1,
                "end_line": 1,
                "end_column": 5,
                "offset": 0,
                "end_offset": 4,
                "token_count": 2,
                "mean_nll": 2.0,
                "perplexity": 7.4,
                "mean_rank": 2.0,
                "top_10_fraction": 1.0,
            }
        ],
    )

    result = authorship.detect_authorship_with_profile("text", profile)
    assert result.estimated_ai_probability is None
    assert result.segments[0]["estimated_ai_probability"] is None


def test_unsupported_method_and_bad_profile(tmp_path):
    unsupported = tmp_path / "unsupported.toml"
    unsupported.write_text(
        '[authorship]\nmethod = "vendor_private"\n', encoding="utf-8"
    )
    assert (
        authorship.detect_authorship_with_profile("text", unsupported).status
        == "unsupported"
    )

    bad = tmp_path / "bad.toml"
    bad.write_text("not = [valid", encoding="utf-8")
    assert (
        authorship.detect_authorship_with_profile("text", bad).status
        == "configuration_error"
    )


def test_secret_fields_are_not_present_in_fingerprint_input():
    first = authorship._safe_fingerprint({"key": "one", "model_path": "/model"})
    second = authorship._safe_fingerprint({"key": "two", "model_path": "/model"})
    assert first == second
    assert first != authorship._safe_fingerprint(
        {"key": "two", "model_path": "/other-model"}
    )
    assert first != authorship._safe_fingerprint(
        {"key": "two", "model_path": "/model", "tokenizer_path": "/tokenizer"}
    )
