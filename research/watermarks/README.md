# Offline watermark research harness

`harness.py` is a small, deterministic boundary for profile-driven research. It never calls a network service, downloads a model, or treats style as provenance. A result applies only to the named profile and its exact local configuration.

```bash
python research/watermarks/harness.py research/watermarks/profiles/example-fixture.toml sample.txt
printf '%s' '[[UNICODEFIX-WATERMARK-FIXTURE]] example' | python research/watermarks/harness.py research/watermarks/profiles/example-fixture.toml
```

The JSON result has one of these statuses: `detected`, `not_detected`, `insufficient_text`, `unsupported`, or `configuration_error`. `not_detected` means only that this profile's detector did not match; it is never a general claim that the text has no watermark.

Profiles require `[profile]` and `[detector]` TOML tables. The harness fingerprints non-secret reproducibility settings and records only the presence of keys, seeds, tokens, and other secrets so low-entropy values cannot be guessed from a published digest. Keep real profiles and local model artifacts out of version control.

The included `fixture_contains` adapter exists solely for deterministic tests. `example-kgw.toml` and `example-synthid.toml` explicitly return `unsupported`. Optional future adapters may wrap locally installed KGW/Transformers, SynthID Text, or Meta TextSeal implementations, but must require their matching tokenizer, model artifacts, algorithm configuration, secret/key material where applicable, and calibrated threshold. They must not download artifacts or use a vendor API at runtime.

This harness intentionally does not transform text. UnicodeFix cleanup can remove observable Unicode/C2PA carriers; any statistical-watermark experiment needs its own matched detector and separate preservation-quality evaluation.

Paragraph-level authorship signals use a separate `[authorship]` profile and the installed UnicodeFix CLI, not this watermark harness. Run `cleanup-text --report --authorship-profile PATH`. These profiles recompute token-distribution measurements with pinned local causal-model artifacts; they do not recover a generator's original probabilities or identify a vendor watermark. The included `profiles/example-authorship.toml` documents the offline configuration boundary.
