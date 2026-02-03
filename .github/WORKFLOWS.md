# GitHub Workflows Documentation

This repository uses GitHub Actions for Continuous Integration and Continuous Deployment (CI/CD).

## Workflows

### 1. CI Pipeline (`ci.yml`)
**Triggers:** Push to `main`/`develop` branches, Pull Requests

**Jobs:**
- **Test**: Runs test suite on Python 3.11 and 3.12
  - Installs dependencies
  - Installs Playwright browsers
  - Runs pytest with all test files
  
- **Lint**: Code quality checks
  - Runs Black formatter (check mode)
  - Runs Ruff linter
  - Continues on error to not block PRs

**Purpose:** Main CI pipeline that runs on every push and PR to ensure code quality and functionality.

---

### 2. Tests (`test.yml`)
**Triggers:** Push to `main`/`develop` branches, Pull Requests

**Matrix:** Python 3.11, 3.12

**Features:**
- Runs full test suite with pytest
- Generates code coverage reports
- Uploads coverage to Codecov
- Caches pip packages for faster builds
- Installs Playwright browsers

**Purpose:** Comprehensive testing across Python versions with coverage reporting.

---

### 3. Code Quality (`lint.yml`)
**Triggers:** Push to `main`/`develop` branches, Pull Requests

**Checks:**
- **Black**: Code formatting (PEP 8)
- **Ruff**: Fast Python linter

**Purpose:** Enforces code style and quality standards.

---

### 4. CodeQL Security Analysis (`codeql.yml`)
**Triggers:** 
- Push to `main`/`develop` branches
- Pull Requests
- Scheduled: Every Monday at 00:00 UTC

**Features:**
- Analyzes Python code for security vulnerabilities
- Uses extended security queries
- Reports findings in GitHub Security tab

**Purpose:** Automated security vulnerability scanning.

---

## Running Workflows Locally

### Run Tests
```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Install Playwright browsers
playwright install chromium

# Run tests
python -m pytest test_*.py -v --tb=short
```

### Run Linters
```bash
# Install linting tools
pip install black ruff

# Check formatting
black --check --diff .

# Run linter
ruff check .
```

### Fix Formatting Issues
```bash
# Auto-format with Black
black .

# Auto-fix Ruff issues (where possible)
ruff check --fix .
```

---

## Workflow Status Badges

The README includes badges showing the status of each workflow:

- [![CI](https://github.com/andriyshevchenko/workUA/actions/workflows/ci.yml/badge.svg)](https://github.com/andriyshevchenko/workUA/actions/workflows/ci.yml)
- [![Tests](https://github.com/andriyshevchenko/workUA/actions/workflows/test.yml/badge.svg)](https://github.com/andriyshevchenko/workUA/actions/workflows/test.yml)
- [![Code Quality](https://github.com/andriyshevchenko/workUA/actions/workflows/lint.yml/badge.svg)](https://github.com/andriyshevchenko/workUA/actions/workflows/lint.yml)
- [![CodeQL](https://github.com/andriyshevchenko/workUA/actions/workflows/codeql.yml/badge.svg)](https://github.com/andriyshevchenko/workUA/actions/workflows/codeql.yml)

---

## Troubleshooting

### Tests Failing
1. Check the workflow logs in the Actions tab
2. Run tests locally to reproduce the issue
3. Ensure all dependencies are installed
4. Check Python version compatibility

### Linting Failures
1. Run linters locally: `black --check .` and `ruff check .`
2. Fix issues: `black .` and `ruff check --fix .`
3. Commit and push the fixes

### CodeQL Alerts
1. Check the Security tab for detailed vulnerability reports
2. Review the affected code
3. Apply recommended fixes
4. Re-run the workflow to verify

---

## Workflow Configuration

### Python Versions
Currently testing on:
- Python 3.11
- Python 3.12

### Caching
Workflows use GitHub Actions cache to speed up builds:
- Pip packages are cached based on `requirements.txt` hash
- Linting tools are cached separately

### Permissions
CodeQL workflow requires specific permissions:
- `actions: read`
- `contents: read`
- `security-events: write`

---

## Adding New Workflows

1. Create a new `.yml` file in `.github/workflows/`
2. Define triggers, jobs, and steps
3. Test locally when possible
4. Submit a PR to add the workflow
5. Monitor the first runs in the Actions tab

---

## Best Practices

1. **Keep workflows fast**: Use caching and parallel jobs
2. **Fail fast**: Use `fail-fast: false` for matrix builds
3. **Meaningful names**: Use descriptive job and step names
4. **Continue on error**: For non-critical checks (like linting)
5. **Security**: Never commit secrets, use GitHub Secrets
6. **Documentation**: Keep this file updated with workflow changes
