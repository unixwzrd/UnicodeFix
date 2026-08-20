from unicodefix.c2pa import (
    MAGIC,
    build_text_wrapper,
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
