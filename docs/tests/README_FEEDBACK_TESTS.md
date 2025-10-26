# Feedback System Tests

This directory contains comprehensive tests for the User Feedback System.

## Test Files

### 1. `test_feedback_api.py` (100+ tests)
Tests for all feedback API endpoints.

**Test Classes:**
- `TestFeedbackSubmission` - Testing feedback creation with various types and confidence levels
- `TestFeedbackRetrieval` - Testing GET endpoints for feedback retrieval
- `TestFeedbackStats` - Testing statistics calculation
- `TestFeedbackApply` - Testing manual application to learning system
- `TestFeedbackDeletion` - Testing feedback deletion
- `TestFeedbackEdgeCases` - Testing edge cases and boundary conditions
- `TestFeedbackSecurity` - Testing security features (SQL injection, XSS, destructive ops)

**Coverage:**
- ✅ All 6 API endpoints (`/api/feedback/*`)
- ✅ High/medium/low confidence handling
- ✅ All 4 feedback types (sql_correction, column_name, table_name, result_issue)
- ✅ Validation and error responses
- ✅ Pagination and filtering
- ✅ Security validations

### 2. `test_feedback_validator.py` (45+ tests)
Tests for the FeedbackValidator class and validation logic.

**Test Classes:**
- `TestValidationModes` - Testing strict/moderate/lenient validation modes
- `TestSuspiciousPatternDetection` - Testing detection of dangerous SQL patterns
- `TestConfidenceBoost` - Testing confidence boost calculation
- `TestMetadataValidation` - Testing column/table name validation
- `TestEdgeCases` - Testing edge cases
- `TestValidationResult` - Testing ValidationResult object
- `TestIntegrationScenarios` - Testing complete validation workflows

**Coverage:**
- ✅ 3 validation modes with different strictness levels
- ✅ Destructive operation detection (DELETE, UPDATE, DROP, TRUNCATE, ALTER)
- ✅ SQL validation (syntax, execution, error checking)
- ✅ Metadata validation against schema
- ✅ Confidence boost calculation
- ✅ Edge cases (empty SQL, special characters, Unicode)

### 3. `test_feedback_integration.py` (30+ tests)
Integration tests for complete feedback workflows.

**Test Classes:**
- `TestAutoLearningWorkflow` - Testing automatic learning with high confidence
- `TestValidationIntegration` - Testing validation integrated with submission
- `TestLearnedCorrectionApplication` - Testing application to future queries
- `TestFeedbackChaining` - Testing multiple feedback on same query
- `TestBatchProcessing` - Testing deferred feedback batch processing
- `TestErrorScenarios` - Testing error handling
- `TestStatisticsAccuracy` - Testing stats calculation accuracy

**Coverage:**
- ✅ Complete feedback → validation → learning flow
- ✅ High confidence (≥90%) → auto-apply
- ✅ Medium confidence (70-89%) → deferred queue
- ✅ Low confidence (<70%) → manual review
- ✅ Learned corrections applied to similar future queries
- ✅ Success rate tracking
- ✅ Batch processing of deferred feedback
- ✅ Error scenarios and recovery

## Running the Tests

### Run All Feedback Tests
```bash
./run_tests.sh feedback
```

This will run all three test files sequentially with organized output.

### Run Individual Test Files
```bash
# API tests only
pytest tests/test_feedback_api.py -v

# Validation tests only
pytest tests/test_feedback_validator.py -v

# Integration tests only
pytest tests/test_feedback_integration.py -v
```

### Run Specific Test Classes
```bash
# Run only submission tests
pytest tests/test_feedback_api.py::TestFeedbackSubmission -v

# Run only validation mode tests
pytest tests/test_feedback_validator.py::TestValidationModes -v

# Run only auto-learning workflow tests
pytest tests/test_feedback_integration.py::TestAutoLearningWorkflow -v
```

### Run Specific Test Methods
```bash
# Run a single test
pytest tests/test_feedback_api.py::TestFeedbackSubmission::test_submit_sql_correction_high_confidence -v
```

### Run with Coverage
```bash
# Coverage for all feedback modules
pytest tests/test_feedback_*.py \
  --cov=src/api/endpoints/feedback \
  --cov=src/llm/feedback_validator \
  --cov-report=html \
  --cov-report=term-missing

# Open coverage report
open htmlcov/index.html
```

## Test Data Setup

Most tests use pytest fixtures for setup:

**Common Fixtures:**
- `db_session` - Database session for tests
- `sample_query_history` - A failing query for feedback testing
- `failing_query` - Query that failed due to table name error
- `validator` - FeedbackValidator instance

## Expected Test Results

All tests should **PASS** with the following characteristics:

### API Tests
- ✅ 201 Created for successful feedback submission
- ✅ 200 OK for successful retrieval and apply
- ✅ 204 No Content for successful deletion
- ✅ 404 Not Found for non-existent resources
- ✅ 422 Validation Error for invalid inputs
- ✅ High confidence feedback triggers auto-learning
- ✅ Destructive operations are NEVER auto-applied

### Validation Tests
- ✅ Strict mode requires original to fail and corrected to succeed
- ✅ Moderate mode only requires corrected to succeed
- ✅ Lenient mode only requires no errors
- ✅ All destructive operations are flagged as suspicious
- ✅ UPDATE/DELETE without WHERE clause flagged
- ✅ Safe SELECT queries pass validation

### Integration Tests
- ✅ High confidence (≥90%) feedback auto-applies
- ✅ Medium confidence (70-89%) goes to deferred queue
- ✅ Low confidence (<70%) requires manual review
- ✅ Learned corrections apply to future similar queries
- ✅ Success rates are tracked accurately
- ✅ Statistics reflect actual database state

## Test Coverage Goals

Target coverage for feedback system:

| Module | Target | Current |
|--------|--------|---------|
| `src/api/endpoints/feedback.py` | >85% | TBD |
| `src/llm/feedback_validator.py` | >90% | TBD |
| Integration workflows | >80% | TBD |

Run coverage report to see current numbers:
```bash
pytest tests/test_feedback_*.py --cov --cov-report=term
```

## Troubleshooting

### Tests Fail with Database Errors
```bash
# Ensure database is running and migrations are applied
alembic upgrade head

# Check database connection in .env
cat .env | grep DATABASE_URL
```

### Import Errors
```bash
# Install all dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### Fixtures Not Found
```bash
# Ensure conftest.py exists with shared fixtures
ls tests/conftest.py
```

### Mock Errors
Some tests use mocks for external dependencies. If mocks fail:
- Check that mock paths match actual module structure
- Verify mock return values match expected types
- Update mocks if API signatures changed

## Adding New Tests

When adding new feedback features, add tests following this pattern:

```python
class TestNewFeature:
    """Tests for new feedback feature."""

    def test_feature_success_case(self, db_session, sample_query_history):
        """Test feature works correctly."""
        # Arrange
        # ... setup test data

        # Act
        # ... call the feature

        # Assert
        # ... verify results
        assert result.is_valid is True

    def test_feature_failure_case(self, db_session):
        """Test feature handles errors correctly."""
        # ... test error scenarios
```

## Continuous Integration

These tests run automatically:
- On every commit (via pre-commit hook)
- On pull requests (via GitHub Actions)
- On main branch merges

Ensure all tests pass before committing:
```bash
./run_tests.sh feedback
```

## Related Documentation

- [User Feedback System](../docs/USER_FEEDBACK_SYSTEM.md) - Full system documentation
- [Quick Test Guide](../docs/tests/QUICK_TEST.md) - Manual testing procedures
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when server running)

## Support

If tests fail unexpectedly:
1. Check recent code changes in feedback modules
2. Verify database schema is up-to-date
3. Review test output for specific error messages
4. Check that all dependencies are installed
5. Ensure `.env` file has correct configuration

For persistent issues, review the test code to understand what's being tested and why it might fail.
