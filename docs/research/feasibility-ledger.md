# Watermark feasibility ledger

Last reviewed: 2026-08-18. This ledger distinguishes public research implementations from production deployment claims. It is deliberately conservative: unknown configurations are not generically detectable or removable.

| Scheme/carrier | Offline detection | Direct cleanup | Status | Conditions and limits |
| --- | --- | --- | --- | --- |
| Unicode invisible/control payload | Yes | Yes | detectable, removable | Exact code points and carrier grammar are locally observable. Preserve legitimate language shaping when requested. |
| C2PA text credential/carrier | Yes | Yes, explicit | detectable, removable | Recognize and remove only complete, recognized carriers. C2PA is provenance, not proof of AI generation. |
| Fixed-column Markdown wrapping | Yes | Yes, opt-in | detectable, removable | Formatting only; never attribute it to AI. Maintain Markdown block structure. |
| KGW green-list | Conditional | Experimental | conditionally_detectable | Requires exact tokenizer, vocabulary, key/seeding rule, generation settings, length, and calibrated threshold. No generic removal claim. |
| SynthID Text | Conditional | Experimental | conditionally_detectable | Requires matching local tokenizer/model and watermark configuration/keys; Google’s public repository is a research reference, not a Gemini production detector. |
| Meta TextSeal | Conditional | Experimental | conditionally_detectable | Requires the matched model/checkpoint and TextSeal configuration. Research toolkit availability does not establish deployment in Meta products. |
| Unknown/proprietary vendor text scheme | No | No | not_publicly_detectable | Do not infer one from prose, Unicode cleanup, or a negative profile result. |
| Source-code semantic/AST watermark | No generic method | No generic method | unsupported | Rewriting identifiers or syntax can change behavior and cannot establish removal across languages without a matched scheme and test suite. |
| Local causal-model likelihood | Yes, with artifacts | No | authorship_signal | Scores token surprise, rank, or top-k frequency under one named reference model. It is not a watermark detector and requires corpus-matched calibration for a probability. |
| DetectGPT / Fast-DetectGPT | Conditional | No | research_only | Compare the candidate's likelihood geometry with perturbed or sampled alternatives. They require local models, substantial compute, length calibration, and validation against current domains and generators. |
| Binoculars | Conditional | No | research_only | Contrasts perplexity measurements from a matched pair of local models. It is an authorship classifier, not a watermark detector, and published aggregate accuracy is not a universal operating guarantee. |

## How generation-time statistical marks work

The original [KGW watermark](https://arxiv.org/abs/2301.10226) derives a pseudorandom green-token set from preceding tokens and a secret key, then adds a small positive bias to those tokens' logits before sampling. Detection retokenizes the finished text with the exact tokenizer and configuration, reconstructs the green lists, and tests whether green tokens occur more often than chance. A p-value or z-score is meaningful only for that named configuration and its calibrated text-length regime.

[SynthID Text](https://www.nature.com/articles/s41586-024-08025-4) also modifies generation-time sampling, but uses keyed tournament sampling and multiple scoring functions rather than a simple universal list of telltale words. The random choice at token position *t* is conditioned on earlier text and the watermark key. Its public implementation therefore cannot detect a private production configuration unless the required keys and parameters match.

This does have the trajectory effect the project owner identified: changing one sampled token changes the context used to calculate every later conditional distribution. Papers generally measure aggregate quality or utility and report small average effects; that does not mean the watermarked sequence is identical to the sequence the unmodified sampler would have produced. UnicodeFix should expose that tradeoff in experiments instead of promising zero quality impact.

Lexical, semantic, post-hoc rewriting, and representation-based schemes form other families. They may choose synonyms, sentence structures, semantic regions, or learned encodings. Their detectors still require the matching scheme, model, key, or checkpoint. Surface punctuation, smart quotes, and line wrapping can be audited and normalized, but they are not reliable evidence that one of these statistical schemes is present.

## Watermark evidence versus authorship evidence

| Evidence | What UnicodeFix can say | What it cannot say |
| --- | --- | --- |
| Exact Unicode or C2PA carrier | The named carrier is present at these locations. | C2PA alone proves neither AI generation nor authorship. |
| Matched KGW, SynthID, or other keyed profile | The text crossed this detector's threshold with this configuration fingerprint. | A negative result excludes no other key, configuration, edit, or scheme. |
| Local model likelihood profile | These paragraphs have low/high surprise, rank, or top-k measurements under this reference model. | The paragraph was written by a named vendor, or even necessarily by AI. |
| Typography or Markdown wrapping | These observable formatting patterns occur and can be normalized safely. | Smart quotes, em dashes, or column 80 are AI watermarks or authorship proof. |

The finished text does not contain the generator's original full probability distribution. An unkeyed audit can only recompute a surrogate distribution with a local reference model. Model mismatch, topic, language, editing, quotation, code, formulae, and short samples all change the score. UnicodeFix therefore labels these results `authorship_signal`, keeps them separate from `known_watermark`, and never cleans text merely because a paragraph crossed a likelihood threshold.

The initial local adapter reports mean negative log likelihood, perplexity, mean selected-token rank, and top-10-token fraction per paragraph. A profile supplies its own threshold. UnicodeFix reports `estimated_ai_probability` only when the operator supplies calibration coefficients fitted on a held-out, source-matched human/AI corpus; otherwise it reports only the measured score and threshold result. The [DetectGPT paper](https://proceedings.mlr.press/v202/mitchell23a.html), [Fast-DetectGPT](https://arxiv.org/abs/2310.05130), and [Binoculars](https://arxiv.org/abs/2401.12070) are recorded as next research adapters rather than silently approximated by the simpler likelihood score.

## Research protocol

For a scheme to move from conditional to supported, keep a local, versioned profile; matched watermarked and control fixtures; detector calibration by text length; false-positive and false-negative measurements; and edits that verify content preservation. Test Unicode cleanup, Markdown reformatting, copy/editing, token substitutions, mixed documents, URLs, numbers, citations, and source compilation/parsing. A transformation is only experimentally removable when the matched detector crosses its documented threshold and the preservation checks pass.

All core behavior remains local after installation. The research harness neither sends user text to a vendor nor offers a generic authorship decision. Any evaluation must report sample source, language, domain, generator and decoding settings, reference model, paragraph length, threshold selection, calibration split, false-positive rate, false-negative rate, and edit robustness.
