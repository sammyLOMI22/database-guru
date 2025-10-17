# GitHub Actions Workflows - Quick Reference

## 🚀 Quick Commands

```bash
# View workflow status
gh workflow list

# Run workflow manually
gh workflow run tests

# View recent runs
gh run list --workflow=test.yml

# View specific run
gh run view <run-id>

# Download artifacts
gh run download <run-id>
```

---

## 📊 Workflows Summary

### 1. Tests (`test.yml`)
**When**: Every push, every PR
```
├─ Test (Python 3.11, 3.12, 3.13)
│  ├─ Run pytest with coverage
│  ├─ Upload to Codecov
│  ├─ Check 45% threshold
│  └─ Comment on PR
├─ Lint (flake8, black, isort, mypy)
├─ Security (bandit, safety)
└─ Summary (aggregate results)
```
**Duration**: ~3-5 minutes
**Artifacts**: Test results, coverage HTML, security reports

### 2. Coverage Badge (`coverage-badge.yml`)
**When**: Push to main, manual
```
├─ Run tests with coverage
├─ Generate badge with genbadge
├─ Extract coverage percentage
├─ Commit badge to repo
└─ Upload artifact
```
**Duration**: ~2-3 minutes
**Output**: `coverage-badge.svg`

### 3. PR Checks (`pr-checks.yml`)
**When**: PRs opened/updated
```
├─ Test Changes (detect changed files)
├─ Coverage Diff (compare PR vs base)
├─ Component Tests (4 components in parallel)
│  ├─ result_verification_agent
│  ├─ correction_learner
│  ├─ schema_aware_fixer
│  └─ self_correcting_agent
└─ PR Comment (post results)
```
**Duration**: ~4-6 minutes
**Output**: PR comment with status

### 4. Scheduled Tests (`scheduled-tests.yml`)
**When**: Daily @ 2 AM UTC, manual
```
├─ Full Test Suite (all tests + slow tests)
├─ Dependency Check (outdated, security audit)
└─ Performance Benchmark (if available)
```
**Duration**: ~5-10 minutes
**Artifacts**: Nightly reports, audit results

---

## 🎯 Workflow Triggers

| Workflow | Push | PR | Schedule | Manual |
|----------|------|-----|----------|--------|
| Tests | ✅ | ✅ | ❌ | ✅ |
| Coverage Badge | ✅ (main) | ❌ | ❌ | ✅ |
| PR Checks | ❌ | ✅ | ❌ | ❌ |
| Scheduled Tests | ❌ | ❌ | ✅ daily | ✅ |

---

## 📈 Success Criteria

### Tests Workflow
- ✅ All tests pass (or ≤3 failures)
- ✅ Coverage ≥45%
- ⚠️ Lint/security issues (non-blocking)

### Coverage Badge Workflow
- ✅ Badge generated
- ✅ Badge committed

### PR Checks Workflow
- ✅ All component tests pass
- ✅ Coverage not decreased >1%
- ✅ Tests added if source changed

### Scheduled Tests Workflow
- ✅ Full test suite passes
- ✅ No critical security issues
- ⚠️ Performance within bounds

---

## 🔧 Manual Workflow Triggers

### Via GitHub UI
1. Go to **Actions** tab
2. Select workflow from left sidebar
3. Click **Run workflow** (dropdown)
4. Select branch
5. Click **Run workflow** (button)

### Via GitHub CLI
```bash
# Run specific workflow
gh workflow run test.yml

# Run on specific branch
gh workflow run test.yml --ref develop

# Run coverage badge generator
gh workflow run coverage-badge.yml
```

### Via API
```bash
curl -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/repos/sammyLOMI22/database-guru/actions/workflows/test.yml/dispatches \
  -d '{"ref":"main"}'
```

---

## 📦 Artifacts Guide

### Test Results Artifacts
**Name**: `test-results-{python-version}`
**Contains**:
- `test-results.xml` - JUnit format
- `htmlcov/` - HTML coverage report
- `coverage.xml` - XML coverage data

**Download**:
```bash
gh run download --name test-results-3.13
```

### Coverage Report
**Name**: `coverage-report`
**Contains**: `htmlcov/` - Full HTML report

**View Locally**:
```bash
gh run download --name coverage-report
open htmlcov/index.html
```

### Security Reports
**Name**: `security-report`, `safety-report`
**Contains**: JSON security scan results

**Download**:
```bash
gh run download --name security-report
cat bandit-report.json | jq
```

### Nightly Reports
**Name**: `nightly-test-reports`
**Contains**:
- Full coverage report
- Test inventory
- Dependency audit

---

## 🚨 Troubleshooting Quick Fixes

### Issue: Tests fail in CI but pass locally

**Quick Fix**:
```bash
# Run tests in clean environment
python -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

### Issue: Coverage badge not updating

**Quick Fix**:
```bash
# Manually trigger badge workflow
gh workflow run coverage-badge.yml

# Or push to main
git commit --allow-empty -m "Trigger badge update"
git push origin main
```

### Issue: Workflow stuck or taking too long

**Quick Fix**:
```bash
# Cancel running workflow
gh run cancel <run-id>

# Re-run failed jobs only
gh run rerun <run-id> --failed
```

### Issue: Permission denied errors

**Quick Fix**:
1. Settings → Actions → General
2. Workflow permissions → "Read and write"
3. ✅ Allow GitHub Actions to create PRs

---

## 📊 Status Check Interpretation

### PR Status Checks

| Check | Meaning | Action |
|-------|---------|--------|
| ✅ Tests / test (3.13) | All tests pass | Safe to merge |
| ❌ Tests / test (3.13) | Tests failing | Fix tests |
| ⚠️ Tests / lint | Linting issues | Optional fix |
| ✅ PR Checks / coverage-diff | Coverage maintained | Good! |
| ❌ PR Checks / coverage-diff | Coverage dropped | Add tests |
| ✅ PR Checks / component-tests | Components pass | Great! |

### Branch Protection (Recommended)

Add these required checks in Settings → Branches:
- `test (3.13)` - Main test suite
- `test-changes` - PR file changes
- `coverage-diff` - Coverage comparison

---

## 🎨 Badge Display

### In README.md
```markdown
<!-- Workflow Status Badges -->
![Tests](https://github.com/sammyLOMI22/database-guru/workflows/Tests/badge.svg)
![PR Checks](https://github.com/sammyLOMI22/database-guru/workflows/PR%20Checks/badge.svg)

<!-- Coverage Badge -->
![Coverage](./coverage-badge.svg)

<!-- Or Codecov -->
[![codecov](https://codecov.io/gh/sammyLOMI22/database-guru/branch/main/graph/badge.svg)](https://codecov.io/gh/sammyLOMI22/database-guru)

<!-- Custom Badges -->
![Tests](https://img.shields.io/badge/tests-69%20passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-46%25-yellow)
```

### In Documentation
```markdown
## CI/CD Status

[![Tests](https://github.com/sammyLOMI22/database-guru/workflows/Tests/badge.svg)](https://github.com/sammyLOMI22/database-guru/actions)
[![Coverage](./coverage-badge.svg)](htmlcov/index.html)
```

---

## ⚡ Performance Tips

### Speed Up Workflows

1. **Cache dependencies**:
   ```yaml
   - uses: actions/setup-python@v5
     with:
       cache: 'pip'
   ```

2. **Run tests in parallel**:
   ```bash
   # Install pytest-xdist
   pip install pytest-xdist

   # Run tests
   pytest -n auto
   ```

3. **Skip slow tests in PRs**:
   ```python
   @pytest.mark.slow
   def test_slow_operation():
       ...
   ```

   ```bash
   pytest -m "not slow"
   ```

---

## 📝 Workflow Customization Checklist

- [ ] Update Python versions in matrix
- [ ] Set coverage threshold
- [ ] Configure Codecov token
- [ ] Enable branch protection
- [ ] Add required status checks
- [ ] Configure PR auto-merge rules
- [ ] Set up Slack notifications (optional)
- [ ] Enable dependabot (optional)

---

## 🔗 Quick Links

- **Actions Tab**: [GitHub Actions](https://github.com/sammyLOMI22/database-guru/actions)
- **Workflows**: `.github/workflows/`
- **Documentation**: [CICD_SETUP.md](CICD_SETUP.md)
- **Test Status**: [TEST_STATUS.md](../TEST_STATUS.md)
- **Coverage**: [COVERAGE_SUMMARY.md](../COVERAGE_SUMMARY.md)

---

## 📞 Need Help?

1. Check [CICD_SETUP.md](CICD_SETUP.md) for detailed docs
2. Review workflow logs in Actions tab
3. Open issue with `ci` label
4. Check GitHub Actions documentation

---

**Pro Tip**: Pin this reference for quick access during development!
