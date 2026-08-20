"""Calibrated, local model-distribution authorship signals.

These profiles do not detect a vendor watermark. They compare observed token
choices with a named local causal language model and an explicitly supplied
threshold. Results are profile-specific evidence, never proof of authorship.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

STATUSES = {
    "potentially_ai_generated",
    "not_flagged",
    "insufficient_text",
    "unsupported",
    "configuration_error",
}
METRICS = {"mean_nll", "perplexity", "mean_rank", "top_10_fraction"}
COMPARISONS = {"lte", "gte"}
_SECRET_FIELD_PARTS = ("key", "secret", "seed", "token", "password")


@dataclass(frozen=True)
class AuthorshipResult:
    profile: str
    method: str
    status: str
    configuration_fingerprint: str
    metric: str
    threshold: float | None = None
    comparison: str | None = None
    estimated_ai_probability: float | None = None
    segments: tuple[dict[str, Any], ...] = ()
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["segments"] = list(self.segments)
        return value


def _safe_fingerprint(config: dict[str, Any]) -> str:
    def is_secret(name: str) -> bool:
        normalized = name.lower()
        if normalized in {"tokenizer", "tokenizer_path", "model_tokenizer"}:
            return False
        return any(part in normalized for part in _SECRET_FIELD_PARTS)

    safe = {
        key: "<configured-secret>" if is_secret(key) else value
        for key, value in config.items()
    }
    encoded = json.dumps(safe, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _paragraphs(text: str) -> list[dict[str, Any]]:
    """Return nonblank paragraph spans with one-based line coordinates."""

    paragraphs = []
    for match in re.finditer(r"(?ms)(?:^|\n)(?![ \t]*\n)(.*?)(?=\n[ \t]*\n|\Z)", text):
        value = match.group(1)
        if not value.strip():
            continue
        start = match.start(1)
        end = match.end(1)
        paragraphs.append(
            {
                "text": value,
                "start": start,
                "end": end,
                "line": text.count("\n", 0, start) + 1,
                "column": start - text.rfind("\n", 0, start),
                "end_line": text.count("\n", 0, end) + 1,
                "end_column": end - text.rfind("\n", 0, end),
            }
        )
    return paragraphs


def _crosses(score: float, threshold: float, comparison: str) -> bool:
    return score <= threshold if comparison == "lte" else score >= threshold


def _probability(score: float, config: dict[str, Any]) -> float | None:
    if "calibration_slope" not in config or "calibration_intercept" not in config:
        return None
    value = float(config["calibration_slope"]) * score + float(
        config["calibration_intercept"]
    )
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _score_causal_lm(
    paragraphs: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, Any]]:
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"install unicodefix[watermark-lab]: {exc}") from exc

    tokenizer = AutoTokenizer.from_pretrained(
        str(config["tokenizer_path"]), local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(config["model_path"]), local_files_only=True, trust_remote_code=False
    )
    model.eval()
    maximum = int(config.get("maximum_tokens", 1024))
    scored = []
    for paragraph in paragraphs:
        inputs = tokenizer(
            paragraph["text"],
            return_tensors="pt",
            add_special_tokens=True,
            truncation=True,
            max_length=maximum,
        )
        input_ids = inputs["input_ids"]
        token_count = max(0, int(input_ids.shape[-1]) - 1)
        if token_count == 0:
            continue
        with torch.inference_mode():
            model_inputs = {
                name: value
                for name, value in inputs.items()
                if name in {"input_ids", "attention_mask"}
            }
            logits = model(**model_inputs).logits[:, :-1, :]
            targets = input_ids[:, 1:]
            target_logits = logits.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
            log_probabilities = torch.log_softmax(logits, dim=-1)
            target_log_probabilities = log_probabilities.gather(
                -1, targets.unsqueeze(-1)
            ).squeeze(-1)
            ranks = (logits > target_logits.unsqueeze(-1)).sum(dim=-1) + 1
        mean_nll = float((-target_log_probabilities.mean()).item())
        metrics = {
            "mean_nll": mean_nll,
            "perplexity": float(math.exp(min(mean_nll, 50.0))),
            "mean_rank": float(ranks.float().mean().item()),
            "top_10_fraction": float((ranks <= 10).float().mean().item()),
        }
        scored.append(
            {
                "line": paragraph["line"],
                "column": paragraph["column"],
                "end_line": paragraph["end_line"],
                "end_column": paragraph["end_column"],
                "offset": paragraph["start"],
                "end_offset": paragraph["end"],
                "token_count": token_count,
                **metrics,
            }
        )
    return scored


def detect_authorship_with_profile(text: str, path: str | Path) -> AuthorshipResult:
    profile_path = Path(path)
    try:
        with profile_path.open("rb") as handle:
            loaded = tomllib.load(handle)
        config = loaded.get("authorship", loaded)
        if not isinstance(config, dict):
            raise ValueError("profile must contain an [authorship] table")
    except Exception as exc:
        return AuthorshipResult(
            str(profile_path),
            "unknown",
            "configuration_error",
            "unavailable",
            "unknown",
            message=str(exc),
        )

    fingerprint = _safe_fingerprint(config)
    method = str(config.get("method", "causal_lm_likelihood"))
    metric = str(config.get("metric", "mean_nll"))
    comparison = str(config.get("comparison", "lte"))
    required = ("model_path", "tokenizer_path", "threshold")
    missing = [name for name in required if name not in config]
    if method != "causal_lm_likelihood":
        return AuthorshipResult(
            str(profile_path),
            method,
            "unsupported",
            fingerprint,
            metric,
            message="no local adapter is available for this authorship method",
        )
    if missing or metric not in METRICS or comparison not in COMPARISONS:
        problem = (
            f"missing: {', '.join(missing)}"
            if missing
            else "invalid metric or comparison"
        )
        return AuthorshipResult(
            str(profile_path),
            method,
            "configuration_error",
            fingerprint,
            metric,
            message=problem,
        )

    try:
        threshold = float(config["threshold"])
        minimum = int(config.get("minimum_tokens", 64))
        maximum = int(config.get("maximum_tokens", 1024))
        if minimum < 1 or maximum < 2:
            raise ValueError("minimum_tokens must be >= 1 and maximum_tokens >= 2")
        calibration_fields = {
            "calibration_slope",
            "calibration_intercept",
        } & config.keys()
        if calibration_fields and len(calibration_fields) != 2:
            raise ValueError(
                "calibration_slope and calibration_intercept must be supplied together"
            )
        if calibration_fields:
            float(config["calibration_slope"])
            float(config["calibration_intercept"])
    except (TypeError, ValueError) as exc:
        return AuthorshipResult(
            str(profile_path),
            method,
            "configuration_error",
            fingerprint,
            metric,
            message=str(exc),
        )

    config = {**config, "maximum_tokens": maximum}
    paragraphs = _paragraphs(text)
    try:
        scored = _score_causal_lm(paragraphs, config)
    except Exception as exc:
        status = (
            "unsupported"
            if str(exc).startswith("install unicodefix[watermark-lab]")
            else "configuration_error"
        )
        return AuthorshipResult(
            str(profile_path),
            method,
            status,
            fingerprint,
            metric,
            message=str(exc),
        )
    eligible = [item for item in scored if item["token_count"] >= minimum]
    if not eligible:
        return AuthorshipResult(
            str(profile_path),
            method,
            "insufficient_text",
            fingerprint,
            metric,
            message=f"no paragraph contained at least {minimum} scored tokens",
        )
    segments = []
    probabilities = []
    for item in eligible:
        score = float(item[metric])
        flagged = _crosses(score, threshold, comparison)
        probability = _probability(score, config)
        if probability is not None:
            probabilities.append(probability)
        segments.append(
            {
                **item,
                "score": score,
                "flagged": flagged,
                "estimated_ai_probability": probability,
            }
        )
    flagged = any(item["flagged"] for item in segments)
    return AuthorshipResult(
        str(profile_path),
        method,
        "potentially_ai_generated" if flagged else "not_flagged",
        fingerprint,
        metric,
        threshold,
        comparison,
        max(probabilities) if probabilities else None,
        tuple(segments),
        "Profile-calibrated model-distribution signal; not a watermark or proof of authorship.",
    )


def detect_authorship_profiles(
    text: str, paths: list[str] | None
) -> list[dict[str, Any]]:
    return [
        detect_authorship_with_profile(text, path).to_dict() for path in paths or []
    ]
