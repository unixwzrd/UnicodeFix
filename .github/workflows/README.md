# CI/CD Workflows

This directory contains GitHub Actions workflows for continuous integration and testing.

## Workflows

### `ci.yml` - Main CI Pipeline

Runs on every push and pull request to `main`, `master`, or `develop` branches.

**Jobs:**

1. **Test Suite** - Runs on multiple Python versions (3.9-3.12) and operating systems (Ubuntu, macOS)
   - Installs dependencies
   - Runs Python unit tests with pytest and coverage
   - Runs integration test suite (`tests/test_all.sh`)
   - Validates newline preservation (critical regression test)
   - Checks that cleaned files maintain line structure

2. **Lint** - Code quality checks
   - Black code formatting check
   - Ruff linting

3. **ShellCheck** - Shell script linting
   - Validates bash scripts in `tests/` directory

## Test Coverage

The CI pipeline includes comprehensive tests for:

- Unicode normalization (quotes, dashes, spaces)
- Newline preservation (critical - prevents file structure corruption)
- Invisible character handling
- All CLI options and flags
- Report generation modes
- Batch processing
- In-place editing

## Running Tests Locally

Before pushing, you can run the same tests locally:

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov ruff black

# Run Python unit tests
pytest tests/ -v

# Run integration tests
bash tests/test_all.sh

# Check code formatting
black --check src/ tests/

# Lint code
ruff check src/ tests/
```

## Adding New Tests

When adding new features or fixing bugs:

1. Add unit tests to `tests/test_transforms.py` or appropriate test file
2. Add integration test scenarios to `tests/test_all.sh` if needed
3. Ensure tests would have caught the bug you're fixing
4. Run tests locally before pushing
5. CI will automatically validate on push/PR
