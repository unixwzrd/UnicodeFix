# `cleanup-image` guide

UnicodeFix 2.1 includes its image cleanup backend in the Python package. No ExifTool, Perl interpreter, separate executable, or network service is required.

```text
cleanup-image [options] infile [infile ...]
```

`cleanup-text` automatically routes image signatures to this same backend. `cleanup-text image.png` selects metadata cleanup into `image.clean.png`; the direct `cleanup-image` command defaults to audit unless a cleanup flag is given. Both commands support separate file output, reports, dry runs, explicit provenance removal, and overwrite protection.

## Format support

| Format | Audit | Cleanup |
| --- | --- | --- |
| PNG / APNG | Container and metadata inventory | Built-in, without re-encoding |
| JPEG, including progressive JPEG | Container and metadata inventory | Built-in, without re-encoding |
| WebP, including animated WebP | Container and metadata inventory | Built-in, without re-encoding |
| TIFF / GIF / BMP | Pillow inventory | Audit-only |
| HEIF / AVIF | Pillow inventory when a decoder is available; otherwise explicitly incomplete header-only inventory | Audit-only |

Inputs are limited to 256 MiB per file. Individual EXIF/XMP and decompressed PNG text fields are bounded to 4 MiB. Unsupported metadata variants and malformed framing are refused; no fallback calls an external program.

## Audit

```bash
cleanup-image photo.jpg
cleanup-image --report --json graphic.png photo.tiff
cleanup-text --report --metrics photo.jpg graphic.png
```

Reports distinguish metadata, C2PA/JUMBF provenance, and unsupported pixel-watermark detectors. Image schema `2.1` uses `backend.name`, `backend.write_supported`, `backend.metadata_source`, and `backend.message`; it no longer contains an ExifTool installation/version object. Audit-only formats explicitly report that writing is unavailable. A missing decoder does not become a successful or complete metadata scan.

## Preview and cleanup

```bash
cleanup-image --dry-run --strip-metadata photo.jpg
cleanup-image --strip-metadata photo.jpg
cleanup-image --strip-provenance image.png
cleanup-image --strip-metadata --strip-provenance -o public.png image.png
cleanup-text --dry-run image.webp
```

`--strip-metadata` removes known non-rendering carriers: PNG text/time metadata, private EXIF fields, supported XMP properties, JPEG comments, and recognized descriptive Photoshop/IPTC resources. Unknown blocks and unknown Photoshop resources are retained. This is selected-carrier cleanup, not a promise that every possible private encoding has been removed.

The writer preserves original image coding data, ICC profiles, EXIF/XMP orientation and supported color-space fields, JPEG JFIF/Adobe blocks, and animation frames and timing. Pillow parses/serializes EXIF metadata; it never re-saves image pixels during cleanup. PNG chunks are CRC-checked, JPEG scans and metadata segments are walked separately, and WebP RIFF sizes, padding, and metadata feature flags are handled explicitly. Output is re-audited and protected block digests plus EXIF/ICC rendering snapshots must match before atomic publication.

Known HDR gain-map XMP, extended JPEG XMP, nested EXIF JUMBF, unsupported nested Photoshop EXIF/XMP, and unsupported/malformed EXIF variants are audit-only until their preservation rules are implemented. Corrupt CRCs, invalid sizes, and trailing bytes prevent writing.

The default output is `<name>.clean<extension>`. Existing output is rejected unless `--force` is supplied. Input and output must differ, and the extension must be preserved. A same-directory temporary file is synced and published without clobbering an output that appeared concurrently.

## Provenance

PNG `caBX`, WebP `C2PA`, and complete JPEG APP11 fragment sequences are checked for a structurally recognized C2PA JUMBF manifest-store envelope, including its UUID and label. This does not validate a signature, claim, certificate, or trust chain.

Metadata cleanup on recognized provenance requires explicit `--strip-provenance`, because changing metadata can invalidate a retained credential. XMP manifest references additionally require `--strip-metadata` so the reference is not left behind. Malformed or unrecognized provenance carriers remain in place and block cleanup. External manifests are never fetched.

## Limits

- C2PA is provenance, not proof of AI generation. Removing it discards that provenance.
- Unknown blocks are retained and reported limitations remain visible; absence of findings does not establish that a file is metadata-free.
- Metadata cleanup cannot erase a visible logo or a signal embedded in image pixels.
- SynthID and unknown pixel-domain watermark detection/removal remain unsupported without a matching local detector. There are no blind crop, noise, recompression, or inpainting modes.
- No legacy `--exiftool` option, `exiftool=` API parameter, executable discovery, or subprocess fallback is retained.

Container rules follow the [W3C PNG specification](https://www.w3.org/TR/png-3/), [WebP RIFF specification](https://developers.google.com/speed/webp/docs/riff_container), and [C2PA 2.4 embedding specification](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html). EXIF metadata parsing and serialization use the installed, patched Pillow library.
