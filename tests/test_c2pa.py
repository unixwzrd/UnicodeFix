import os
import subprocess
import sys
import textwrap
from itertools import pairwise
from pathlib import Path

import pytest

from unicodefix.c2pa import (
    MAGIC,
    build_text_wrapper,
    c2pa_findings,
    encode_variation_selectors,
    find_c2pa_carriers,
    strip_c2pa_carriers,
)


def test_valid_variation_selector_c2pa_carrier_is_found_and_stripped():
    carrier = "\ufeff" + encode_variation_selectors(build_text_wrapper(b"fixture"))
    text = "before" + carrier + "after"
    found = find_c2pa_carriers(text)
    assert len(found) == 1
    assert found[0].valid
    assert strip_c2pa_carriers(text) == "beforeafter"


def test_malformed_variation_selector_data_is_retained():
    text = "before\ufeff" + encode_variation_selectors(b"not-c2pa") + "after"
    assert find_c2pa_carriers(text) == []
    assert strip_c2pa_carriers(text) == text


def test_malformed_c2pa_headers_are_reported_but_retained():
    malformed = (
        MAGIC + b"\x02\x00\x00\x00\x00",
        MAGIC + b"\x01\x00\x00",
        MAGIC + b"\x01\x00\x00\x00\x08short",
    )
    for payload in malformed:
        text = "\ufeff" + encode_variation_selectors(payload)
        found = find_c2pa_carriers(text)
        assert len(found) == 1
        assert not found[0].valid
        assert strip_c2pa_carriers(text) == text


def test_complete_structured_block_is_stripped_but_incomplete_is_not():
    complete = (
        "-----BEGIN C2PA MANIFEST-----\n"
        "https://example.invalid/manifest.c2pa\n"
        "-----END C2PA MANIFEST-----\n"
    )
    assert strip_c2pa_carriers("a\n" + complete + "b\n") == "a\nb\n"
    incomplete = "-----BEGIN C2PA MANIFEST-----\nhttps://example.invalid/manifest\n"
    assert strip_c2pa_carriers(incomplete) == incomplete


def test_structured_single_line_and_embedded_references_are_recognized():
    external = (
        "# -----BEGIN C2PA MANIFEST----- https://example.invalid/a.c2pa "
        "-----END C2PA MANIFEST-----\n"
    )
    embedded = (
        "-----BEGIN C2PA MANIFEST-----\n"
        "data:application/c2pa;base64,Zml4dHVyZQ==\n"
        "-----END C2PA MANIFEST-----\n"
    )
    found = find_c2pa_carriers(external + embedded)
    assert [carrier.kind for carrier in found] == [
        "structured_external_reference",
        "structured_embedded",
    ]
    assert all(carrier.valid for carrier in found)
    assert strip_c2pa_carriers(external + embedded) == ""


def test_structured_lookalikes_and_invalid_references_are_retained():
    old_delimiters = "# -----BEGIN C2PA----- payload -----END C2PA-----\n"
    invalid = (
        "# -----BEGIN C2PA MANIFEST----- not-a-uri " "-----END C2PA MANIFEST-----\n"
    )
    assert find_c2pa_carriers(old_delimiters) == []
    found = find_c2pa_carriers(invalid)
    assert len(found) == 1
    assert not found[0].valid
    assert strip_c2pa_carriers(invalid) == invalid


def test_html_inline_and_external_carriers_are_local_only_and_explicitly_stripped():
    inline = '<script type="application/c2pa">bWFuaWZlc3Q=</script>'
    external = '<link rel="c2pa-manifest" href="https://example.invalid/manifest">'
    text = inline + "\ncontent\n" + external
    found = find_c2pa_carriers(text)
    assert [carrier.kind for carrier in found] == [
        "html_inline",
        "html_external_reference",
    ]
    assert all(carrier.valid for carrier in found)
    assert strip_c2pa_carriers(text) == "\ncontent\n"


def test_malformed_html_c2pa_carriers_are_reported_and_retained():
    inline = '<script type="application/c2pa">not base64!</script>'
    external = '<link rel="c2pa-manifest">'
    text = inline + external
    found = find_c2pa_carriers(text)
    assert len(found) == 2
    assert not any(carrier.valid for carrier in found)
    assert strip_c2pa_carriers(text) == text


@pytest.mark.parametrize(
    "inline",
    [
        '<SCRIPT TYPE = "APPLICATION/C2PA">bWFuaWZlc3Q=</SCRIPT >',
        "<script\nasync\ttype='application/c2pa'\r\n>bWFuaWZlc3Q=</script\n>",
        '<script title="1 > 0 and <script" type="application/c2pa">bWFuaWZlc3Q=</script>',
        '<script type="application/c2pa" title=example>bWFuaWZlc3Q=</script>',
        "<script type=application/c2pa>bWFuaWZlc3Q=</script>",
    ],
)
def test_html_scanner_preserves_exact_spans_and_handles_attributes(inline):
    prefix, suffix = "π\nbefore\n", "\nafter\r\n"
    text = prefix + inline + suffix
    carrier = find_c2pa_carriers(text)[0]
    assert carrier.valid
    assert (carrier.start, carrier.end) == (len(prefix), len(prefix) + len(inline))
    assert text[carrier.start : carrier.end] == carrier.payload == inline
    location = c2pa_findings(text)[0].locations[0]
    assert (location.line, location.column) == (3, 1)
    assert strip_c2pa_carriers(text) == prefix + suffix


@pytest.mark.parametrize(
    "external",
    [
        "<LINK HREF='https://example.invalid/a' REL='alternate C2PA-MANIFEST' />",
        '<link disabled rel="c2pa-manifest" href="https://example.invalid/a?x=1>0">',
        '<link href="https://example.invalid/a"\nrel="c2pa-manifest">',
        "<link rel=c2pa-manifest href=https://example.invalid/a>",
    ],
)
def test_html_external_attributes_are_parsed_without_fetching(external, monkeypatch):
    import urllib.request

    def network_forbidden(*args, **kwargs):
        pytest.fail("C2PA discovery must not retrieve an external manifest")

    monkeypatch.setattr(urllib.request, "urlopen", network_forbidden)
    text = "before\n" + external + "\nafter"
    found = find_c2pa_carriers(text)
    assert len(found) == 1
    assert found[0].valid
    assert text[found[0].start : found[0].end] == external
    assert strip_c2pa_carriers(text) == "before\n\nafter"


@pytest.mark.parametrize(
    "text",
    [
        '<script data-type="application/c2pa">bWFuaWZlc3Q=</script>',
        "<script title=\"type='application/c2pa'\">bWFuaWZlc3Q=</script>",
        '<script-x type="application/c2pa">bWFuaWZlc3Q=</script>',
        '<link data-rel="c2pa-manifest" href="https://example.invalid/a">',
        '<link rel="not-c2pa-manifest" href="https://example.invalid/a">',
        '<script>const value = \'<link rel="c2pa-manifest" href="https://example.invalid/a">\';</script>',
    ],
)
def test_html_attribute_and_script_body_lookalikes_are_not_removed(text):
    assert find_c2pa_carriers(text) == []
    assert strip_c2pa_carriers(text) == text


@pytest.mark.parametrize(
    "text",
    [
        '<script type="application/c2pa">bWFuaWZlc3Q=',
        '<script type="application/c2pa" title="unterminated >',
        '<script type="application/c2pa" <broken>',
        '<script type="application/c2pa"/>bWFuaWZlc3Q=</script>',
        '<script type="application/c2pa" type="text/plain">bWFuaWZlc3Q=</script>',
        '<script type="text/plain" type="application/c2pa">bWFuaWZlc3Q=</script>',
        '<script type="application/c2pa"title="missing separator">bWFuaWZlc3Q=</script>',
        '<link rel="c2pa-manifest" href="https://example.invalid/a"',
        '<link rel="c2pa-manifest" href="https://[broken">',
        '<link rel="c2pa-manifest" href="https://example.invalid/a" href="other">',
    ],
)
def test_incomplete_or_ambiguous_html_carriers_are_reported_but_retained(text):
    found = find_c2pa_carriers(text)
    assert len(found) == 1
    assert not found[0].valid
    assert strip_c2pa_carriers(text) == text


def test_html_scanner_recovers_after_malformed_tag_without_removing_it():
    malformed = "<script broken <link broken "
    inline = '<script type="application/c2pa">bWFuaWZlc3Q=</script>'
    external = '<link rel="c2pa-manifest" href="https://example.invalid/a">'
    text = malformed + inline + "\n" + external + "\nend"
    assert len(find_c2pa_carriers(text)) == 2
    assert strip_c2pa_carriers(text) == malformed + "\n\nend"


def test_html_tag_scanning_never_revisits_consumed_ranges(monkeypatch):
    from unicodefix import c2pa

    original = c2pa._html_start_tag
    ranges = []

    def tracked(text, index):
        tag = original(text, index)
        ranges.append((index, tag.end))
        return tag

    monkeypatch.setattr(c2pa, "_html_start_tag", tracked)
    text = ("<script <link " * 32000) + '<script title="' + ("<link " * 32000)
    assert find_c2pa_carriers(text) == []
    assert all(start <= end for start, end in ranges)
    assert all(left[1] <= right[0] for left, right in pairwise(ranges))
    assert sum(end - start for start, end in ranges) <= len(text)


def test_hostile_html_completes_through_public_apis_with_watchdog():
    # A subprocess watchdog prevents a reintroduced ReDoS from hanging pytest.
    # The large missing-delimiter cases take many seconds with the old patterns;
    # no fragile microsecond timing ratios are asserted on shared CI runners.
    code = textwrap.dedent("""
        from unicodefix import scan_findings
        from unicodefix.c2pa import c2pa_findings, find_c2pa_carriers, strip_c2pa_carriers

        for n in (1000, 2000, 4000, 8000, 16000, 32000):
            for text in (
                '<script ' * n,
                '<link ' * n,
                '<script ' * n + 'application/c2pa',
                '<script type="application/c2pa">' * n,
                '<script type="application/c2pa">' + '</script ' * n,
                '<link rel="c2pa-manifest" href="' + '<link ' * n,
            ):
                assert strip_c2pa_carriers(text) == text
                find_c2pa_carriers(text)
                c2pa_findings(text)
                scan_findings(text)
        print('hostile HTML completed')
        """)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=True,
    )
    assert result.stdout.strip() == "hostile HTML completed"
