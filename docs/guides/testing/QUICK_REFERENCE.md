# Feedback Tests - Quick Reference

## Run All Feedback Tests
```bash
./run_tests.sh feedback
```

## Run Individual Test Files

```bash
# API tests
pytest tests/test_feedback_api.py -v

# Validation tests
pytest tests/test_feedback_validator.py -v

# Integration tests
pytest tests/test_feedback_integration.py -v
```

## Run Specific Test Classes

```bash
# Submission tests
pytest tests/test_feedback_api.py::TestFeedbackSubmission -v

# Validation mode tests
pytest tests/test_feedback_validator.py::TestValidationModes -v

# Auto-learning workflow tests
pytest tests/test_feedback_integration.py::TestAutoLearningWorkflow -v
```

## Run with Coverage

```bash
# All feedback tests with coverage
pytest tests/test_feedback_*.py \
  --cov=src/api/endpoints/feedback \
  --cov=src/llm/feedback_validator \
  --cov-report=html \
  --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

## Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run specific file
npm test FeedbackModal.test.tsx
npm test FeedbackStats.test.tsx

# With coverage
npm test -- --coverage
```

## Common Test Scenarios

### Test High Confidence Auto-Learning
```bash
pytest tests/test_feedback_api.py::TestFeedbackSubmission::test_submit_sql_correction_high_confidence -v
```

### Test Destructive Operation Blocking
```bash
pytest tests/test_feedback_security.py::TestFeedbackSecurity::test_destructive_operations_not_auto_learned -v
```

### Test Validation Modes
```bash
pytest tests/test_feedback_validator.py::TestValidationModes -v
```

### Test Complete Workflow
```bash
pytest tests/test_feedback_integration.py::TestAutoLearningWorkflow -v
```

## Expected Results

✅ All tests should pass
✅ >80% code coverage
✅ No security warnings
✅ All destructive operations blocked
✅ Confidence levels handled correctly

## Troubleshooting

### Tests fail with database error
```bash
# Check database connection
alembic upgrade head
```

### Import errors
```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### Mock errors
Update mocks in test files if API signatures changed

## Quick Stats

- **Total Tests:** 270+
- **Backend Tests:** 180+
- **Frontend Tests:** 90+
- **Test Files:** 5
- **Coverage Target:** >80%

## Files

- `test_feedback_api.py` - API endpoints (100+ tests)
- `test_feedback_validator.py` - Validation logic (45+ tests)
- `test_feedback_integration.py` - Integration workflows (30+ tests)
- `FeedbackModal.test.tsx` - Modal component (50+ tests)
- `FeedbackStats.test.tsx` - Dashboard component (40+ tests)

## More Info

- See `tests/README_FEEDBACK_TESTS.md` for detailed documentation
- See `../../reports/testing/FEEDBACK_TESTS_SUMMARY.md` for test suite overview
- See `QUICK_TEST.md` for manual testing procedures
