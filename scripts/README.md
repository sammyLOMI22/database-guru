# Test Scripts

Convenient bash scripts to run Database Guru tests in various configurations.

## Quick Start

```bash
# Run all tests (backend unit + integration + frontend)
./scripts/test_all.sh

# Run only backend unit tests (fastest, no server needed)
./scripts/test_backend.sh

# Run only frontend tests
./scripts/test_frontend.sh

# Run only integration tests (starts server automatically)
./scripts/test_integration.sh
```

## Scripts Overview

| Script | Purpose | Server Required | Duration |
|--------|---------|-----------------|----------|
| `test_all.sh` | Run complete test suite | Yes (auto-starts) | ~2 min |
| `test_backend.sh` | Backend unit tests only | No | ~40 sec |
| `test_frontend.sh` | Frontend tests only | No | ~2 sec |
| `test_integration.sh` | Integration tests only | Yes (auto-starts) | ~70 sec |

---

## 1. test_all.sh - Master Test Runner

Run the complete test suite: backend unit tests, integration tests, and frontend tests.

### Usage

```bash
./scripts/test_all.sh [OPTIONS]
```

### Options

- `--skip-frontend` - Skip frontend tests
- `--skip-integration` - Skip integration tests (no server needed)
- `--coverage`, `-c` - Run backend tests with coverage report
- `--help`, `-h` - Show help message

### Examples

```bash
# Run everything
./scripts/test_all.sh

# Skip integration tests (fastest for development)
./scripts/test_all.sh --skip-integration

# Backend only with coverage
./scripts/test_all.sh --skip-frontend --skip-integration --coverage

# Skip frontend tests
./scripts/test_all.sh --skip-frontend
```

### Output

```
╔══════════════════════════════════════════════════════╗
║                                                      ║
║        🧙‍♂️  DATABASE GURU TEST SUITE 🧙‍♂️             ║
║                                                      ║
╚══════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════
  STEP 1/3: Backend Unit Tests
═══════════════════════════════════════════════════════

...test output...

═══════════════════════════════════════════════════════
  STEP 2/3: Integration Tests
═══════════════════════════════════════════════════════

...test output...

═══════════════════════════════════════════════════════
  STEP 3/3: Frontend Tests
═══════════════════════════════════════════════════════

...test output...

╔══════════════════════════════════════════════════════╗
║                   TEST SUMMARY                       ║
╚══════════════════════════════════════════════════════╝

  Backend Unit Tests:    ✅ PASSED
  Integration Tests:     ✅ PASSED
  Frontend Tests:        ✅ PASSED

  Total Duration: 105s

╔══════════════════════════════════════════════════════╗
║                                                      ║
║            ✅  ALL TESTS PASSED! 🎉                  ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

---

## 2. test_backend.sh - Backend Unit Tests

Run backend unit tests without requiring a server.

### Usage

```bash
./scripts/test_backend.sh [OPTIONS]
```

### Options

- `--coverage`, `-c` - Generate coverage report
- `--verbose`, `-v` - Run in verbose mode
- `--help`, `-h` - Show help message

### Examples

```bash
# Run backend unit tests
./scripts/test_backend.sh

# With coverage report
./scripts/test_backend.sh --coverage

# Verbose output
./scripts/test_backend.sh --verbose

# Both coverage and verbose
./scripts/test_backend.sh -c -v
```

### What It Tests

- 184 backend unit tests
- Excludes integration tests (marked with `@pytest.mark.integration`)
- No server required
- Fast execution (~40 seconds)

### Output

```
╔══════════════════════════════════════╗
║     Backend Unit Test Runner        ║
╚══════════════════════════════════════╝

🔧 Activating virtual environment...
🧪 Running backend unit tests (no server required)...
Note: Integration tests are excluded. Use test_integration.sh to run those.

........................................................................ [ 39%]
........................................................................ [ 78%]
........................................                                 [100%]
184 passed, 5 deselected, 14 warnings in 37.19s

✅ All backend unit tests passed!
```

### Coverage Report

When using `--coverage`, the script generates:
- Terminal output with line-by-line coverage
- HTML report in `htmlcov/index.html`

```bash
./scripts/test_backend.sh --coverage
open htmlcov/index.html  # View HTML coverage report
```

---

## 3. test_frontend.sh - Frontend Tests

Run frontend tests using Vitest.

### Usage

```bash
./scripts/test_frontend.sh [OPTIONS]
```

### Options

- `--watch`, `-w` - Run in watch mode (interactive)
- `--ui` - Open Vitest UI
- `--coverage`, `-c` - Generate coverage report

### Examples

```bash
# Run frontend tests once
./scripts/test_frontend.sh

# Watch mode (auto-rerun on file changes)
./scripts/test_frontend.sh --watch

# Open Vitest UI
./scripts/test_frontend.sh --ui

# With coverage
./scripts/test_frontend.sh --coverage
```

### What It Tests

- 99 frontend component tests
- 6 test files covering:
  - FeedbackModal (21 tests)
  - FeedbackStats (17 tests)
  - QueryResults (27 tests)
  - Header (9 tests)
  - Message (11 tests)
  - VerificationWarnings (14 tests)

### Output

```
╔══════════════════════════════════════╗
║     Frontend Test Runner            ║
╚══════════════════════════════════════╝

🧪 Running frontend tests...

 Test Files  6 passed (6)
      Tests  99 passed (99)
   Start at  10:42:06
   Duration  1.46s

✅ Frontend tests completed!
```

### Note on Cleanup Errors

Vitest may report a cleanup error after all tests pass:

```
 Test Files  6 passed (6)
      Tests  99 passed (99)
     Errors  1 error
```

This is a known Vitest cleanup issue and does not indicate test failure. The script correctly handles this by checking for test passes rather than relying solely on exit codes.

---

## 4. test_integration.sh - Integration Tests

Run integration tests that require a running server.

### Usage

```bash
./scripts/test_integration.sh [OPTIONS]
```

### Options

- `--no-server` - Assume server is already running (don't auto-start)

### Examples

```bash
# Auto-start server and run tests
./scripts/test_integration.sh

# Use existing server
./scripts/test_integration.sh --no-server
```

### What It Tests

- 5 integration tests requiring HTTP server:
  - `test_api` - Full API endpoint testing
  - `test_end_to_end` - Complete user workflows
  - `test_models` - Database model operations
  - `test_multi_database_queries` - Cross-database queries
  - `test_real_error_correction` - Self-correcting agent

### Output

```
╔══════════════════════════════════════╗
║     Integration Test Runner         ║
╚══════════════════════════════════════╝

🚀 Starting test server...
   Server PID: 11285
⏳ Waiting for server to be ready...
✅ Server is ready!

🧪 Running integration tests...

tests/test_api.py::test_api PASSED                     [ 20%]
tests/test_end_to_end.py::test_end_to_end PASSED       [ 40%]
tests/test_models.py::test_models PASSED               [ 60%]
tests/test_multi_db.py::test_multi_database_queries PASSED [ 80%]
tests/test_self_correcting_agent.py::TestIntegration::test_real_error_correction PASSED [100%]

=========== 5 passed, 184 deselected, 6 warnings in 69.50s ===========

✅ All integration tests passed!

🛑 Stopping test server (PID: 11285)...
```

### Server Startup

The script automatically:
1. Starts uvicorn server on port 8000
2. Waits up to 30 seconds for server to be ready
3. Runs integration tests
4. Stops server on completion or failure

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt

      - name: Run all tests
        run: ./scripts/test_all.sh --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./htmlcov/coverage.xml
```

### Fast CI Pipeline (Unit Tests Only)

```yaml
- name: Run unit tests only (fast)
  run: ./scripts/test_all.sh --skip-integration
```

---

## Troubleshooting

### Virtual Environment Not Found

**Error**: `Error: venv directory not found!`

**Solution**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Server Failed to Start

**Error**: `Server failed to start within 30 seconds`

**Solution**:
1. Check if port 8000 is already in use: `lsof -i :8000`
2. Kill existing process: `kill -9 <PID>`
3. Check server logs: `tail -30 server_test.log`

### Frontend Dependencies Missing

**Error**: `frontend directory not found!`

**Solution**:
```bash
cd frontend
npm install
```

### Permission Denied

**Error**: `Permission denied`

**Solution**:
```bash
chmod +x scripts/test_*.sh
```

---

## Development Workflow

### Quick Development Loop

```bash
# 1. Make code changes

# 2. Run relevant tests
./scripts/test_backend.sh           # Backend changes
./scripts/test_frontend.sh --watch  # Frontend changes

# 3. Before committing, run everything
./scripts/test_all.sh
```

### Test-Driven Development

```bash
# Watch mode for continuous testing
./scripts/test_frontend.sh --watch  # Frontend
./scripts/test_backend.sh --verbose # Backend (rerun manually)
```

### Pre-Commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
./scripts/test_all.sh --skip-integration
if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

---

## Performance

| Script | Tests | Duration | Server |
|--------|-------|----------|--------|
| Backend Unit | 184 | ~40s | No |
| Frontend | 99 | ~2s | No |
| Integration | 5 | ~70s | Yes |
| **Total** | **288** | **~105s** | **Yes** |

### Optimization Tips

1. **Use `--skip-integration` during development** (saves ~70 seconds)
2. **Frontend watch mode** for rapid UI development
3. **Run unit tests first** in CI (fail fast if basic tests don't pass)
4. **Parallel test execution** possible for unit + frontend tests

---

## Directory Structure

```
scripts/
├── README.md                 # This file
├── test_all.sh              # Master test runner
├── test_backend.sh          # Backend unit tests
├── test_frontend.sh         # Frontend tests
├── test_integration.sh      # Integration tests
├── create_sample_db.py      # Database setup utilities
├── create_sample_duckdb.py  # DuckDB setup
└── load_sample_data.py      # Sample data loader
```

---

## Related Documentation

- [Integration Test Results](../docs/INTEGRATION_TEST_RESULTS.md) - Detailed integration test documentation
- [Test Isolation Solution](../docs/TEST_ISOLATION_SOLUTION.md) - Database test isolation patterns
- [Backend Test Fixes](../docs/BACKEND_TEST_FIXES.md) - Test fixes and solutions
- [Frontend Test Coverage](../docs/FRONTEND_TEST_COVERAGE.md) - Frontend test documentation
- [Complete Test Summary](../docs/COMPLETE_TEST_SESSION_SUMMARY.md) - Full testing session overview

---

## Contributing

When adding new tests:

1. Backend unit tests go in `tests/` with appropriate markers
2. Integration tests need `@pytest.mark.integration` decorator
3. Frontend tests go in `frontend/tests/`
4. Run `./scripts/test_all.sh` before submitting PR

---

**Last Updated**: 2025-10-26
**Test Pass Rate**: 100% (288/288 tests)
