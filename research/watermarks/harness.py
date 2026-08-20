#!/usr/bin/env python3
"""Offline, deterministic watermark-profile harness.

This is deliberately a research harness, not a generic AI-authorship detector.
It only reports a result for the named local profile.  The built-in
``fixture_contains`` adapter makes tests and integration wiring reproducible;
production KGW, SynthID, and TextSeal adapters must be installed separately
with their exact local artifacts and configurations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # Python 3.10, supplied by the package
    import tomli as tomllib


STATUSES = {
    "detected",
    "not_detected",
    "insufficient_text",
    "unsupported",
    "configuration_error",
}
SECRET_NAMES = {"key", "keys", "secret", "token", "seed", "private_key"}


def _redact_secrets(value: Any, name: str = "") -> Any:
    if any(secret in name.lower() for secret in SECRET_NAMES):
        return "<configured-secret>"
    if isinstance(value, dict):
        return {key: _redact_secrets(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _fingerprint(config: dict[str, Any]) -> str:
    """Hash reproducibility settings without hashing low-entropy secrets."""
    payload = json.dumps(
        _redact_secrets(config), sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _result(
    status: str, profile: dict[str, Any], message: str, **extra: Any
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"unknown result status: {status}")
    metadata = profile.get("profile", {})
    result = {
        "status": status,
        "profile": metadata.get("name", "unnamed"),
        "scheme": metadata.get("scheme", "unknown"),
        "adapter": profile.get("detector", {}).get("adapter", "unknown"),
        "configuration_fingerprint": _fingerprint(profile),
        "message": message,
    }
    result.update(extra)
    return result


def load_profile(path: str | Path) -> dict[str, Any]:
    """Load a TOML profile.  Profile contents never leave this process."""
    try:
        with Path(path).open("rb") as handle:
            profile = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot load profile: {exc}") from exc
    if not isinstance(profile.get("profile"), dict) or not isinstance(
        profile.get("detector"), dict
    ):
        raise TypeError("profile requires [profile] and [detector] tables")
    return profile


def run_profile(text: str, profile_path: str | Path) -> dict[str, Any]:
    """Run one local profile against text, without network or model downloads."""
    try:
        profile = load_profile(profile_path)
    except ValueError as exc:
        return {
            "status": "configuration_error",
            "profile": Path(profile_path).stem,
            "scheme": "unknown",
            "adapter": "unknown",
            "message": str(exc),
        }

    detector = profile["detector"]
    adapter = detector.get("adapter")
    if adapter == "unsupported":
        return _result(
            "unsupported",
            profile,
            detector.get("reason", "no local adapter is installed for this scheme"),
        )

    min_characters = detector.get("min_characters", 1)
    if not isinstance(min_characters, int) or min_characters < 0:
        return _result(
            "configuration_error",
            profile,
            "min_characters must be a non-negative integer",
        )
    if len(text) < min_characters:
        return _result(
            "insufficient_text",
            profile,
            "text is shorter than this profile's minimum length",
            minimum_characters=min_characters,
            observed_characters=len(text),
        )

    if adapter == "fixture_contains":
        marker = detector.get("marker")
        if not isinstance(marker, str) or not marker:
            return _result(
                "configuration_error",
                profile,
                "fixture_contains requires a non-empty marker",
            )
        count = text.count(marker)
        return _result(
            "detected" if count else "not_detected",
            profile,
            (
                "deterministic fixture marker matched"
                if count
                else "fixture marker did not match"
            ),
            score=count,
            threshold=1,
        )

    return _result(
        "configuration_error",
        profile,
        (
            f"unknown adapter {adapter!r}; install an explicit local adapter "
            "or use unsupported"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run an offline watermark research profile."
    )
    parser.add_argument("profile", help="local TOML profile")
    parser.add_argument(
        "input", nargs="?", default="-", help="UTF-8 text file, or - for stdin"
    )
    args = parser.parse_args(argv)
    try:
        text = (
            __import__("sys").stdin.read()
            if args.input == "-"
            else Path(args.input).read_text(encoding="utf-8")
        )
    except OSError as exc:
        parser.error(f"cannot read input: {exc}")
    print(json.dumps(run_profile(text, args.profile), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
