"""Profile-driven, offline statistical watermark detection.

Profiles are intentionally explicit: a negative result only applies to the named
scheme and exact configuration. Model and tokenizer paths are always loaded with
``local_files_only=True`` so report mode cannot contact a vendor or model hub.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib


STATUSES = {
    "detected",
    "not_detected",
    "insufficient_text",
    "unsupported",
    "configuration_error",
}
_SECRET_FIELD_PARTS = ("key", "secret", "seed", "token", "password")


@dataclass(frozen=True)
class WatermarkResult:
    profile: str
    scheme: str
    status: str
    configuration_fingerprint: str
    score: float | None = None
    threshold: float | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fingerprint(config: dict[str, Any]) -> str:
    def is_secret(name: str) -> bool:
        normalized = name.lower()
        if normalized in {"tokenizer", "tokenizer_path", "model_tokenizer"}:
            return False
        return any(part in normalized for part in _SECRET_FIELD_PARTS)

    safe_config = {
        key: "<configured-secret>" if is_secret(key) else value
        for key, value in config.items()
    }
    encoded = json.dumps(safe_config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def load_profile(path: str | Path) -> tuple[dict[str, Any], str]:
    profile_path = Path(path)
    with profile_path.open("rb") as handle:
        config = tomllib.load(handle)
    if "watermark" in config and isinstance(config["watermark"], dict):
        config = config["watermark"]
    return config, _fingerprint(config)


def _error(path: Path, scheme: str, fingerprint: str, message: str) -> WatermarkResult:
    return WatermarkResult(
        profile=str(path),
        scheme=scheme or "unknown",
        status="configuration_error",
        configuration_fingerprint=fingerprint,
        message=message,
    )


def detect_with_profile(text: str, path: str | Path) -> WatermarkResult:
    """Run a configured local detector without downloading artifacts."""
    profile_path = Path(path)
    try:
        config, fingerprint = load_profile(profile_path)
    except Exception as exc:
        return _error(profile_path, "unknown", "unavailable", str(exc))

    scheme = str(config.get("scheme", "")).lower()
    minimum_tokens = int(config.get("minimum_tokens", 1))
    if len(text.split()) < minimum_tokens:
        return WatermarkResult(
            str(profile_path),
            scheme or "unknown",
            "insufficient_text",
            fingerprint,
            message=f"requires at least {minimum_tokens} whitespace-delimited tokens",
        )

    if scheme == "literal_fixture":
        marker = str(config.get("marker", ""))
        if not marker:
            return _error(profile_path, scheme, fingerprint, "marker is required")
        found = marker in text
        return WatermarkResult(
            str(profile_path),
            scheme,
            "detected" if found else "not_detected",
            fingerprint,
            score=1.0 if found else 0.0,
            threshold=1.0,
            message="deterministic research fixture; not a vendor detector",
        )

    if scheme == "kgw":
        return _detect_kgw(text, profile_path, config, fingerprint)
    if scheme == "synthid_text":
        return _detect_synthid(text, profile_path, config, fingerprint)

    return WatermarkResult(
        str(profile_path),
        scheme or "unknown",
        "unsupported",
        fingerprint,
        message="no local adapter is available for this scheme",
    )


def _detect_kgw(
    text: str, path: Path, config: dict[str, Any], fingerprint: str
) -> WatermarkResult:
    required = ("model_path", "tokenizer_path", "hashing_key")
    missing = [name for name in required if name not in config]
    if missing:
        return _error(path, "kgw", fingerprint, f"missing: {', '.join(missing)}")
    try:
        from transformers import (
            AutoConfig,
            AutoTokenizer,
            WatermarkDetector,
            WatermarkingConfig,
        )
    except Exception as exc:
        return WatermarkResult(
            str(path),
            "kgw",
            "unsupported",
            fingerprint,
            message=f"install unicodefix[watermark-lab]: {exc}",
        )

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            str(config["tokenizer_path"]), local_files_only=True
        )
        model_config = AutoConfig.from_pretrained(
            str(config["model_path"]), local_files_only=True
        )
        tokenized = tokenizer(text, return_tensors="pt", add_special_tokens=False)
        if tokenized.input_ids.shape[-1] < int(config.get("minimum_tokens", 20)):
            return WatermarkResult(str(path), "kgw", "insufficient_text", fingerprint)
        wm_config = WatermarkingConfig(
            greenlist_ratio=float(config.get("greenlist_ratio", 0.25)),
            bias=float(config.get("bias", 2.0)),
            hashing_key=int(config["hashing_key"]),
            seeding_scheme=str(config.get("seeding_scheme", "lefthash")),
            context_width=int(config.get("context_width", 1)),
        )
        detector = WatermarkDetector(
            model_config=model_config,
            device="cpu",
            watermarking_config=wm_config,
            ignore_repeated_ngrams=bool(config.get("ignore_repeated_ngrams", False)),
        )
        threshold = float(config.get("threshold", 3.0))
        prediction = detector(tokenized.input_ids, z_threshold=threshold)
        detected = bool(prediction[0])
        return WatermarkResult(
            str(path),
            "kgw",
            "detected" if detected else "not_detected",
            fingerprint,
            threshold=threshold,
        )
    except Exception as exc:
        return _error(path, "kgw", fingerprint, str(exc))


def _detect_synthid(
    text: str, path: Path, config: dict[str, Any], fingerprint: str
) -> WatermarkResult:
    required = ("detector_path", "tokenizer_path")
    missing = [name for name in required if name not in config]
    if missing:
        return _error(
            path, "synthid_text", fingerprint, f"missing: {', '.join(missing)}"
        )
    try:
        from transformers import (
            AutoTokenizer,
            BayesianDetectorModel,
            SynthIDTextWatermarkDetector,
            SynthIDTextWatermarkLogitsProcessor,
        )
    except Exception as exc:
        return WatermarkResult(
            str(path),
            "synthid_text",
            "unsupported",
            fingerprint,
            message=f"install unicodefix[watermark-lab]: {exc}",
        )
    try:
        detector_model = BayesianDetectorModel.from_pretrained(
            str(config["detector_path"]), local_files_only=True
        )
        tokenizer = AutoTokenizer.from_pretrained(
            str(config["tokenizer_path"]), local_files_only=True
        )
        processor = SynthIDTextWatermarkLogitsProcessor(
            **detector_model.config.watermarking_config, device="cpu"
        )
        detector = SynthIDTextWatermarkDetector(detector_model, processor, tokenizer)
        inputs = tokenizer(text, return_tensors="pt", add_special_tokens=False)
        if inputs.input_ids.shape[-1] < int(config.get("minimum_tokens", 20)):
            return WatermarkResult(
                str(path), "synthid_text", "insufficient_text", fingerprint
            )
        output = detector(inputs.input_ids)
        score = float(output.reshape(-1)[0])
        threshold = float(config.get("threshold", 0.5))
        return WatermarkResult(
            str(path),
            "synthid_text",
            "detected" if score >= threshold else "not_detected",
            fingerprint,
            score=score,
            threshold=threshold,
        )
    except Exception as exc:
        return _error(path, "synthid_text", fingerprint, str(exc))


def detect_profiles(text: str, paths: list[str] | None) -> list[dict[str, Any]]:
    return [detect_with_profile(text, path).to_dict() for path in (paths or [])]
