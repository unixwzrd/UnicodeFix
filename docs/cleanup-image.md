# `cleanup-image` guide

UnicodeFix 2.0.1 adds a separate local image path so text normalization never accidentally reserializes a binary asset.

`cleanup-text` now routes recognized image signatures to this same backend automatically. `cleanup-text image.png` is equivalent to `cleanup-image --strip-metadata image.png`; it writes `image.clean.png`. Its `--report`, `--dry-run`, `--output`, `--force`, and `--strip-provenance` options apply to the image path, and text/image inputs may be mixed. Unlike `cleanup-text`, calling `cleanup-image` with no cleanup flags remains an audit. Image inputs through either command require separate output files; the text command's in-place, stdout, and text-transform options are not supported for images.

```text
cleanup-image [options] infile [infile ...]
```

## Audit

With no cleanup option, `cleanup-image` is a non-mutating audit. Pillow validates the image and reports format, dimensions, mode, frame count, and metadata visible to the installed local backend. ExifTool metadata is preferred when available; Pillow provides a smaller fallback inventory.

```bash
cleanup-image photo.jpg
cleanup-image --report --json photo.jpg graphic.png
cleanup-image --report --metrics photo.jpg
```

Reports separate location, identity/device, editing, other metadata, and C2PA/JUMBF provenance. Image format, dimensions, color mode, frame count, and animation status are included in every report; `--metrics` is accepted as an explicit report-mode alias. Reports also include backend/version status and explicit `unsupported` results for SynthID and unknown pixel-domain watermarks. An empty finding list does not establish that an image is watermark-free.

## Preview and cleanup

```bash
cleanup-image --dry-run --strip-metadata photo.jpg
cleanup-image --strip-metadata photo.jpg
cleanup-image --strip-provenance image.png
cleanup-image --strip-metadata --strip-provenance -o public.png image.png
```

`--dry-run` inventories the requested actions and validates whether the installed backend can perform them without creating an output file. Cleanup requires ExifTool 12.70 or newer and supports JPEG, PNG, WebP, TIFF, HEIF, and AVIF when both the installed Pillow build and ExifTool recognize the file. The output extension must match the input extension.

`--strip-metadata` removes non-rendering metadata while preserving pixel data, ICC profiles, orientation, and color-space tags. Changing hashed asset metadata can invalidate a signed Content Credential even if its JUMBF bytes remain, so a recognized C2PA image refuses metadata cleanup unless `--strip-provenance` is also supplied. `--strip-provenance` removes C2PA/JUMBF content explicitly. When the audit also finds an XMP C2PA reference, both options are required so the reference is removed with the manifest. The result is audited again before it is atomically placed at the output path.

The default output is `<name>.clean<extension>`. Existing output is rejected unless `--force` is supplied. Input and output must differ; image cleanup deliberately has no in-place mode.

## Limits

- C2PA is provenance, not proof of AI generation. Removing it discards provenance and may invalidate a signed Content Credential.
- UnicodeFix inventories and removes local carrier data but does not validate a C2PA signature or retrieve an external manifest.
- Metadata removal cannot erase a visible logo or a signal embedded in image pixels.
- A pixel transformation may weaken SynthID or another robust watermark, but without the matching detector it cannot prove removal. UnicodeFix therefore does not provide blind crop, noise, recompression, or inpainting modes.
- Proprietary camera raw files and SVG are audit-only because broad mutation can damage raw-maker data or change executable/vector content.

The write backend is the local [ExifTool](https://exiftool.org/) executable. No image, metadata, prompt, identifier, or report is sent to an external service.
