import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--with-nltk", action="store_true", default=False,
        help="Run tests requiring NLTK data downloads"
    )


@pytest.fixture(scope="session")
def nltk_available(request):
    try:
        import nltk
        missing = []
        for pkg in ("punkt","stopwords","wordnet","averaged_perceptron_tagger"):
            try:
                nltk.data.find(f"tokenizers/{pkg}") if pkg=="punkt" else nltk.data.find(f"corpora/{pkg}")
            except LookupError:
                missing.append(pkg)
        if missing and not request.config.getoption("--with-nltk"):
            pytest.skip(f"Skipping NLTK tests (missing: {missing}). Run with --with-nltk to force downloads.")
        return nltk
    except ImportError:
        pytest.skip("Skipping NLTK tests (nltk not installed).")
