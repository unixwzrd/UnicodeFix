from unicodefix.findings import FINDINGS_SCHEMA_VERSION, Finding, Findings, Location


def test_findings_are_versioned_and_serializable():
    findings = Findings(
        [Finding("formatting", "soft_break", locations=(Location(2, 3),))]
    )
    data = findings.to_dict()
    assert data["schema_version"] == FINDINGS_SCHEMA_VERSION
    assert data["findings"][0]["locations"][0]["line"] == 2
