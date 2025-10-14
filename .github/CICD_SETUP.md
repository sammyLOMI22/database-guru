# CI/CD Setup Guide

This document explains the GitHub Actions workflows configured for Database Guru.

## 📋 Table of Contents

- [Workflows Overview](#workflows-overview)
- [Setup Instructions](#setup-instructions)
- [Workflow Details](#workflow-details)
- [Secrets Configuration](#secrets-configuration)
- [Status Badges](#status-badges)
- [Troubleshooting](#troubleshooting)

---

## Workflows Overview

Database Guru has 4 GitHub Actions workflows:

| Workflow | Trigger | Purpose | Status Badge |
|----------|---------|---------|--------------|
| **Tests** | Push, PR | Run test suite, coverage | ![Tests](https://github.com/sammyLOMI22/database-guru/workflows/Tests/badge.svg) |
| **Coverage Badge** | Push to main | Generate coverage badge | ![Coverage](https://github.com/sammyLOMI22/database-guru/workflows/Coverage%20Badge/badge.svg) |
| **PR Checks** | Pull requests | Validate PRs, post comments | ![PR Checks](https://github.com/sammyLOMI22/database-guru/workflows/PR%20Checks/badge.svg) |
| **Scheduled Tests** | Daily @ 2 AM UTC | Nightly tests, dependency checks | ![Scheduled](https://github.com/sammyLOMI22/database-guru/workflows/Scheduled%20Tests/badge.svg) |

---

## Setup Instructions

### 1. Enable GitHub Actions

GitHub Actions should be enabled by default. Verify in your repository:

1. Go to **Settings** → **Actions** → **General**
2. Ensure "Allow all actions and reusable workflows" is selected
3. Set workflow permissions to "Read and write permissions"

### 2. Configure Secrets (Optional)

For enhanced features, add these secrets in **Settings** → **Secrets and variables** → **Actions**:

#### Required Secrets

None! The workflows run with default `GITHUB_TOKEN`.

#### Optional Secrets

- `CODECOV_TOKEN`: For Codecov integration (get from [codecov.io](https://codecov.io))
  - Sign up at codecov.io
  - Add your repository
  - Copy the token
  - Add as repository secret

### 3. First Run

The workflows will automatically run on your next push. To trigger manually:

1. Go to **Actions** tab
2. Select a workflow
3. Click **Run workflow**

---

## Workflow Details

### 1. Tests Workflow (`.github/workflows/test.yml`)

**Triggers**: Push to main/develop/Result-Verification-Agent, Pull requests

**Jobs**:

#### Test Job
- **Matrix Testing**: Runs on Python 3.11, 3.12, 3.13
- **Steps**:
  1. Checkout code
  2. Set up Python with pip caching
  3. Install dependencies
  4. Run pytest with coverage
  5. Upload to Codecov (if token configured)
  6. Upload test results as artifacts
  7. Check 45% coverage threshold
  8. Comment coverage on PRs

#### Lint Job
- **Tools**: flake8, black, isort, mypy
- **Mode**: Check only (non-blocking)
- **Purpose**: Code quality checks

#### Security Job
- **Tools**: bandit, safety
- **Purpose**: Vulnerability scanning
- **Output**: JSON reports uploaded as artifacts

#### Test Summary Job
- **Purpose**: Aggregate results
- **Action**: Fails if tests fail

**Usage**:
```bash
# Workflow runs automatically on push/PR
# View results in Actions tab
```

**Artifacts Generated**:
- `test-results-{python-version}` - JUnit XML and HTML coverage
- `coverage-report` - Detailed HTML coverage (Python 3.13 only)
- `security-report` - Bandit JSON results
- `safety-report` - Safety check results

---

### 2. Coverage Badge Workflow (`.github/workflows/coverage-badge.yml`)

**Triggers**: Push to main, Manual dispatch

**Purpose**: Generate and commit coverage badge

**Steps**:
1. Run tests with coverage
2. Generate badge using `genbadge`
3. Extract coverage percentage
4. Commit badge to repository
5. Upload as artifact

**Generated Files**:
- `coverage-badge.svg` - Coverage badge image
- `.github/badges/` - Badge storage directory

**Usage**:
```bash
# Runs automatically on push to main
# Manual trigger:
# Actions → Coverage Badge → Run workflow
```

**Display Badge**:
```markdown
![Coverage](./coverage-badge.svg)
```

---

### 3. PR Checks Workflow (`.github/workflows/pr-checks.yml`)

**Triggers**: Pull request opened, synchronized, reopened

**Jobs**:

#### Test Changes Job
- Identifies changed Python files
- Runs tests for changed files
- Warns if source changed without tests

#### Coverage Diff Job
- Compares coverage: PR vs base branch
- **Pass**: Coverage maintained or increased
- **Fail**: Coverage decreased by >1%

#### Component Tests Job
- **Matrix**: Tests each major component separately
  - result_verification_agent
  - correction_learner
  - schema_aware_fixer
  - self_correcting_agent
- Runs component-specific tests with coverage

#### PR Comment Job
- Posts summary comment on PR
- Shows test status, coverage status
- Provides actionable next steps

**Example PR Comment**:
```
## ✅ PR Check Results

| Check | Status |
|-------|--------|
| Tests | ✅ success |
| Coverage | ✅ success |
| Component Tests | ✅ success |

### Next Steps
✅ All checks passed! Ready for review.
```

**Usage**:
```bash
# Runs automatically on PRs
# Results appear as PR comment
```

---

### 4. Scheduled Tests Workflow (`.github/workflows/scheduled-tests.yml`)

**Triggers**:
- Daily at 2 AM UTC (cron: `0 2 * * *`)
- Manual dispatch

**Jobs**:

#### Full Test Suite Job
- Runs complete test suite
- Includes slow/integration tests
- Generates detailed reports
- Shows test durations
- Creates GitHub issue if >3 tests fail

#### Dependency Check Job
- Lists outdated packages
- Runs security audit with `pip-audit`
- Uploads audit reports

#### Performance Benchmark Job
- Runs benchmark tests (if available)
- Tracks performance regressions

**Generated Artifacts**:
- `nightly-test-reports` - Full coverage and test inventory
- `dependency-audit` - Outdated packages and security audit
- `benchmark-results` - Performance benchmarks

**Usage**:
```bash
# Runs automatically daily at 2 AM UTC
# Manual trigger:
# Actions → Scheduled Tests → Run workflow
```

**Issue Creation**:
If nightly tests fail, an issue is automatically created:
- Title: "🚨 Nightly Test Failure"
- Labels: bug, tests, automated
- Contains: Link to workflow run, timestamp

---

## Secrets Configuration

### Current Setup
Workflows use default `GITHUB_TOKEN` - no configuration needed!

### Optional Integrations

#### Codecov (Coverage Reporting)

1. **Sign Up**:
   - Go to [codecov.io](https://codecov.io)
   - Sign in with GitHub
   - Add repository

2. **Get Token**:
   - Navigate to repository settings on Codecov
   - Copy upload token

3. **Add Secret**:
   ```
   Repository → Settings → Secrets → New repository secret
   Name: CODECOV_TOKEN
   Value: <your-token>
   ```

4. **Verify**:
   - Next push will upload to Codecov
   - View coverage trends at codecov.io

#### Slack Notifications (Optional)

To add Slack notifications on test failures:

1. Create Slack webhook
2. Add as secret: `SLACK_WEBHOOK_URL`
3. Add to workflow:
   ```yaml
   - name: Slack Notification
     if: failure()
     uses: 8398a7/action-slack@v3
     with:
       status: ${{ job.status }}
       webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
   ```

---

## Status Badges

### Available Badges

Add these to your README.md:

```markdown
<!-- Test Status -->
![Tests](https://github.com/sammyLOMI22/database-guru/workflows/Tests/badge.svg)

<!-- Coverage Badge (generated) -->
![Coverage](./coverage-badge.svg)

<!-- Or use Codecov badge -->
[![codecov](https://codecov.io/gh/sammyLOMI22/database-guru/branch/main/graph/badge.svg)](https://codecov.io/gh/sammyLOMI22/database-guru)

<!-- Python Version -->
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)

<!-- License -->
![License](https://img.shields.io/badge/license-MIT-green)

<!-- Last Commit -->
![Last Commit](https://img.shields.io/github/last-commit/sammyLOMI22/database-guru)

<!-- Issues -->
![Issues](https://img.shields.io/github/issues/sammyLOMI22/database-guru)

<!-- PR Checks -->
![PR Checks](https://github.com/sammyLOMI22/database-guru/workflows/PR%20Checks/badge.svg)
```

### Custom Shields.io Badges

Create custom badges at [shields.io](https://shields.io):

```markdown
![Tests](https://img.shields.io/badge/tests-69%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-46%25-yellow)
![Test%20Files](https://img.shields.io/badge/test%20files-12-blue)
```

---

## Troubleshooting

### Workflow Not Running

**Issue**: Workflow doesn't trigger on push/PR

**Solutions**:
1. Check Actions are enabled: Settings → Actions → General
2. Check workflow file syntax: Use YAML validator
3. Check branch protection rules don't block Actions
4. Verify file is in `.github/workflows/` directory

### Coverage Upload Fails

**Issue**: Codecov upload step fails

**Solutions**:
1. Check `CODECOV_TOKEN` secret is set
2. Verify token is valid on codecov.io
3. Check Codecov service status
4. Review workflow logs for error message

### Tests Fail in CI But Pass Locally

**Issue**: Tests pass on your machine but fail in GitHub Actions

**Common Causes**:
1. **Missing dependencies**: Check `requirements.txt` is complete
2. **Environment differences**: Python version mismatch
3. **File paths**: Use `os.path.join()`, not hardcoded paths
4. **Database setup**: Mock database connections in tests
5. **Async tests**: Ensure pytest-asyncio is installed

**Debug Steps**:
```yaml
# Add to workflow for debugging
- name: Debug Environment
  run: |
    python --version
    pip list
    pwd
    ls -la
    env
```

### Permission Denied Errors

**Issue**: Workflow can't commit badge or create issues

**Solution**:
1. Go to Settings → Actions → General
2. Under "Workflow permissions"
3. Select "Read and write permissions"
4. Check "Allow GitHub Actions to create and approve pull requests"

### Slow Test Runs

**Issue**: Workflows take too long

**Optimizations**:
1. **Use caching**:
   ```yaml
   - uses: actions/setup-python@v5
     with:
       cache: 'pip'  # Already enabled
   ```

2. **Parallel test execution**:
   ```yaml
   - name: Run tests in parallel
     run: pytest -n auto  # Requires pytest-xdist
   ```

3. **Skip slow tests in PRs**:
   ```yaml
   - name: Run fast tests only
     run: pytest -m "not slow"
   ```

### Badge Not Updating

**Issue**: Coverage badge shows old percentage

**Solutions**:
1. Manually trigger "Coverage Badge" workflow
2. Clear browser cache
3. Check badge was committed: `git log coverage-badge.svg`
4. Verify workflow completed successfully

---

## Workflow Customization

### Change Test Matrix

Edit `.github/workflows/test.yml`:

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12', '3.13']  # Add/remove versions
    os: [ubuntu-latest, macos-latest]        # Add Mac/Windows
```

### Add Test Markers

Skip certain tests in CI:

```python
# In test file
@pytest.mark.slow
def test_slow_operation():
    ...

@pytest.mark.integration
def test_database_integration():
    ...
```

```yaml
# In workflow
- name: Run fast tests only
  run: pytest -m "not slow and not integration"
```

### Custom Coverage Threshold

Edit `.github/workflows/test.yml`:

```yaml
- name: Check coverage threshold
  run: |
    coverage report --fail-under=50  # Change from 45
```

### Add Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

Run locally:
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## Best Practices

### For Developers

1. **Run tests locally before pushing**:
   ```bash
   ./run_tests.sh
   ```

2. **Check coverage locally**:
   ```bash
   pytest --cov=src --cov-report=term-missing
   ```

3. **Fix failing tests immediately**:
   - Don't let broken tests accumulate
   - CI should always be green on main

4. **Add tests for new features**:
   - Coverage should not decrease
   - Aim for >80% on new code

### For Reviewers

1. **Check CI status before reviewing**:
   - All checks must pass
   - Review coverage diff

2. **Review test changes**:
   - Ensure tests are meaningful
   - Check edge cases are covered

3. **Look for coverage decrease**:
   - PR should maintain or increase coverage
   - New code should be tested

### For Maintainers

1. **Monitor nightly tests**:
   - Check daily test runs
   - Fix issues promptly
   - Review dependency audit

2. **Update dependencies regularly**:
   - Review outdated packages report
   - Update requirements.txt
   - Run tests after updates

3. **Review workflow artifacts**:
   - Download and review reports
   - Track coverage trends
   - Monitor test durations

---

## CI/CD Metrics

Track these metrics for project health:

### Test Metrics
- ✅ Pass rate: 83.1% (target: 100%)
- 📊 Total tests: 83 (growing)
- ⚡ Test duration: ~1.26s (fast!)
- 🔄 Flaky tests: 0 (excellent)

### Coverage Metrics
- 📈 Overall coverage: 46% (target: 75%)
- 🎯 High-coverage modules: 9
- ⚠️ Low-coverage modules: 10
- 📊 Coverage trend: Increasing

### CI Metrics
- ⏱️ Average build time: ~3-5 minutes
- 💚 Build success rate: Target 95%+
- 🔄 Daily test runs: Automated
- 📊 Dependency audits: Daily

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.com/)

---

## Support

For issues with CI/CD:
1. Check workflow logs in Actions tab
2. Review this documentation
3. Check [TEST_STATUS.md](../TEST_STATUS.md) for test details
4. Open issue with `ci` label

---

**Last Updated**: 2025-10-14
**Maintained By**: Database Guru Team
