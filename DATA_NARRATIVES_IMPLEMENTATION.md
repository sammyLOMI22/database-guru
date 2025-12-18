# 📊 Intelligent Data Narratives & Human Insights - Implementation Tracking

**Status**: 🟢 IN PROGRESS - Phase 1: Backend Foundation
**Branch**: `Intelligent-Data-Narratives-and-Human-Insights`
**Start Date**: 2025-12-13
**Estimated Completion**: 2025-12-22 (7-9 days)
**Complexity**: Medium-High | **User Value**: Very High

---

## 📋 Overview

Transform Database Guru query results from raw tables into intelligent narratives with:
- Natural language summaries
- Statistical anomaly detection
- Comparative historical analysis
- Time-series trend detection
- Cross-metric correlation insights

**Example**: "Found 42 customers from California with an average order value of $1,245 (27% higher than NY). **Note: This is the highest average in 6 months.** Sales have been trending upward by 15% monthly."

---

## 🎯 Implementation Phases

### Phase 1: Backend Foundation - MVP (Days 1-2) ✅ COMPLETE
**Goal**: Build core narrative generation engine
**Status**: ✅ COMPLETE

- [x] Create `src/llm/result_narrator.py` with:
  - [x] `NarrativeResult` dataclass with fields: summary, key_insights, direct_answer, confidence, statistics, generated_at
  - [x] `ResultNarrator` class initialization with OllamaClient, enable_statistics flag, max_sample_rows=20
  - [x] `generate_narrative()` main entry point async method
  - [x] `_extract_statistics()` for numeric (min/max/avg/sum/median) and string (unique count, most common) analysis
  - [x] `_build_prompt()` to construct LLM prompt with question, SQL, sample data, and statistics
  - [x] `_parse_response()` to validate and parse JSON from LLM
  - [x] Error handling and graceful fallback
  - [x] Timeout protection (5 seconds max)

- [x] Add to `src/llm/prompts.py`:
  - [x] `NARRATIVE_GENERATION_PROMPT` template with enhanced guidance
  - [x] Few-shot examples for consistent output
  - [x] JSON schema expectations

- [x] Write unit tests in `tests/test_result_narrator.py`:
  - [x] Test basic count queries
  - [x] Test aggregation queries
  - [x] Test filter queries
  - [x] Test multi-column results
  - [x] Test empty results handling
  - [x] Test statistics extraction (numeric columns)
  - [x] Test statistics extraction (string columns)
  - [x] Test statistics extraction (temporal columns)
  - [x] Test LLM timeout handling
  - [x] Test invalid JSON response handling
  - [x] Test missing fields in response
  - [x] Test large result sampling (verify only first 20 rows analyzed)
  - [x] Test graceful degradation on LLM failure
  - [x] Test with mocked Ollama responses
  - [x] Test confidence score calculation
  - **Target**: 35+ tests, 100% passing ✅

**Completion Checklist**:
- [x] ResultNarrator class complete and tested
- [x] All 35+ unit tests written
- [x] Code follows existing agent patterns
- [x] Async/await properly implemented
- [x] Error logging in place
- [x] Comprehensive test coverage

**Status**: ✅ COMPLETE - Ready for Phase 2 API Integration
**Actual Time**: ~2 hours

---

### Phase 2: API Integration - MVP (Day 3) ✅ COMPLETE
**Goal**: Wire narrator into query pipeline
**Status**: ✅ COMPLETE

- [x] Extend `src/models/schemas.py`:
  - [x] Create `ResultAnalysis` Pydantic model with fields:
    - [x] summary: str
    - [x] key_insights: List[str]
    - [x] direct_answer: Optional[str]
    - [x] confidence: float (0.0-1.0)
    - [x] statistics: Dict[str, Any]
    - [x] generated_at: str
  - [x] Add `enable_narratives: bool = True` to `QueryRequest`
  - [x] Add `result_analysis: Optional[ResultAnalysis] = None` to `QueryResponse`

- [x] Modify `src/api/endpoints/query.py`:
  - [x] Import ResultNarrator
  - [x] After execution_result is built (line ~365), add conditional narrative generation:
    - [x] Check: enable_narratives=true AND success AND 1 <= row_count <= 1000
    - [x] Initialize narrator with ollama client
    - [x] Call generate_narrative() with question, sql, results, row_count, execution_time, database_type
    - [x] Convert to response format
    - [x] Add to agent_trace for observability
  - [x] Add result_analysis to response_data
  - [x] Wrapped in try/except - never blocks query response on narrative failure

- [x] Add to `src/config/settings.py`:
  - [x] `ENABLE_NARRATIVES: bool = True`
  - [x] `NARRATIVE_TIMEOUT_SECONDS: int = 5`
  - [x] `NARRATIVE_MAX_SAMPLE_ROWS: int = 20`

- [ ] Write API integration tests in `tests/test_query_endpoints.py`:
  - [ ] Test query with narratives enabled
  - [ ] Test query with narratives disabled
  - [ ] Test narrative generation on various query types (5-10 types)
  - [ ] Test query still succeeds if narrative fails
  - [ ] Test semantic cache integration
  - **Target**: 4-6 tests, 100% passing

**Completion Checklist**:
- [x] Schemas extended and validated
- [x] API integration complete
- [x] Settings configured
- [ ] All integration tests passing
- [ ] Real database query testing done
- [x] Agent trace includes narrative generation step
- [x] Fallback behavior tested

**Status**: ✅ COMPLETE (except integration tests - next task)
**Actual Time**: ~1.5 hours

---

### Phase 3: Frontend Components - MVP (Days 4-5)
**Goal**: Display narratives beautifully to users

- [ ] Create `frontend/src/components/ResultSummary.tsx`:
  - [ ] Accept `ResultAnalysis` object, rowCount, executionTime as props
  - [ ] Header with sparkles icon + confidence badge (green/amber/red based on confidence)
  - [ ] Direct answer section (if available) with blue accent border
  - [ ] Summary paragraph
  - [ ] Key insights list with trend icons (TrendingUp from lucide-react)
  - [ ] Expandable statistics section using `<details>` element
  - [ ] Gradient background (blue-to-indigo) for visual distinction
  - [ ] Responsive Tailwind CSS styling
  - [ ] Accessibility: semantic HTML, ARIA labels, keyboard navigation

- [ ] Add types to `frontend/src/types/api.ts`:
  - [ ] `ResultAnalysis` interface matching backend schema
  - [ ] Update `QueryResponse` interface to include optional result_analysis

- [ ] Modify `frontend/src/components/QueryResults.tsx`:
  - [ ] Import ResultSummary component
  - [ ] Add resultAnalysis prop to component interface
  - [ ] Add conditional render after cache badge, before SQL display:
    ```typescript
    {resultAnalysis && (
      <ResultSummary analysis={resultAnalysis} rowCount={rowCount || 0} executionTime={executionTime || 0} />
    )}
    ```

- [ ] Add settings toggle (location: existing settings panel or new setting):
  - [ ] Checkbox for "Generate Insights" / "Show AI Narratives"
  - [ ] Store in localStorage: `enableNarratives: boolean`
  - [ ] Pass to QueryRequest as `enable_narratives` flag
  - [ ] Default: true (enabled)

- [ ] Write frontend tests in `frontend/tests/ResultSummary.test.tsx`:
  - [ ] Test summary text renders
  - [ ] Test direct answer displays prominently
  - [ ] Test all key insights render
  - [ ] Test confidence badge shows correct percentage
  - [ ] Test confidence badge color changes (high=green, medium=amber, low=red)
  - [ ] Test statistics hidden by default (expandable)
  - [ ] Test statistics visible when expanded
  - [ ] Test accessibility (semantic HTML, ARIA labels)
  - [ ] Test responsive layout
  - [ ] Test with edge cases (empty insights, no direct answer)
  - [ ] Test missing result_analysis prop (null handling)
  - **Target**: 10-12 tests, 100% passing

- [ ] Visual testing:
  - [ ] Verify gradient background contrast
  - [ ] Verify icon alignment and sizing
  - [ ] Verify responsive on mobile/tablet/desktop
  - [ ] Verify light/dark mode compatibility (if applicable)

**Completion Checklist**:
- [ ] ResultSummary component complete and styled
- [ ] Integrated into QueryResults successfully
- [ ] Settings toggle functional
- [ ] All 10-12 frontend tests passing
- [ ] Responsive design verified
- [ ] Accessibility checklist complete
- [ ] **🎉 MVP CHECKPOINT**: Basic narratives working end-to-end!

**Estimated Time**: 1.5 days

---

### Phase 4: Advanced Feature - Anomaly Detection (Day 6)
**Goal**: Detect and explain statistical outliers

- [ ] Add to `src/llm/result_narrator.py`:
  - [ ] `_detect_anomalies()` method with:
    - [ ] Z-score calculation for numeric outliers (threshold: |z| > 2.5)
    - [ ] Interquartile Range (IQR) method as alternative
    - [ ] Historical comparison: fetch min/max/avg from last 30 days of similar queries
    - [ ] Return: list of anomalies with type, column, value, and explanation
  - [ ] `_get_historical_stats()` helper to query historical data
  - [ ] Integration into `generate_narrative()` with `enable_anomaly_detection=True`
  - [ ] Update prompt to include anomaly context in narrative

- [ ] Update `src/models/schemas.py`:
  - [ ] Add optional fields to `ResultAnalysis`:
    - [ ] `anomalies: Optional[List[Dict[str, Any]]]` - detected outliers

- [ ] Write unit tests in `tests/test_result_narrator.py`:
  - [ ] Test Z-score detection on clear outliers
  - [ ] Test IQR method detection
  - [ ] Test no anomalies detected (normal data)
  - [ ] Test all values are outliers edge case
  - [ ] Test historical context retrieval
  - **Target**: 5 tests added, total 20 tests

**Completion Checklist**:
- [ ] Anomaly detection implemented
- [ ] 5 new tests passing
- [ ] LLM prompt updated to reference anomalies
- [ ] Frontend updated to display anomalies (if present)
- [ ] Tested with edge cases

**Estimated Time**: 1 day

---

### Phase 5: Advanced Feature - Comparative Analysis (Day 7)
**Goal**: Compare to historical queries for context

- [ ] Add to `src/llm/result_narrator.py`:
  - [ ] `_get_historical_context()` method to:
    - [ ] Query `query_history` table for similar questions (fuzzy match on question text)
    - [ ] Filter to last 30 days
    - [ ] Calculate percentage changes (current vs historical)
    - [ ] Return: previous result, date, percentage change
  - [ ] `_compare_to_history()` method to:
    - [ ] Find most recent similar query result
    - [ ] Calculate deltas (percentage change, absolute change)
    - [ ] Generate comparison insights
  - [ ] Integration into `generate_narrative()` with `enable_comparison=True`
  - [ ] Update prompt to include historical comparison

- [ ] Update `src/models/schemas.py`:
  - [ ] Add optional to `ResultAnalysis`:
    - [ ] `historical_comparison: Optional[Dict[str, Any]]` - comparison to past results

- [ ] Write unit tests in `tests/test_result_narrator.py`:
  - [ ] Test similar query lookup
  - [ ] Test percentage change calculation
  - [ ] Test no similar queries found
  - [ ] Test with multiple historical options
  - [ ] Test comparison with real query_history data
  - [ ] Test edge case: very old previous result
  - **Target**: 6 tests added, total 26 tests

**Completion Checklist**:
- [ ] Historical lookup implemented
- [ ] Comparison logic working
- [ ] 6 new tests passing
- [ ] LLM prompt updated with comparison context
- [ ] Frontend displays comparison insights
- [ ] Tested with real query history

**Estimated Time**: 1 day

---

### Phase 6: Advanced Feature - Trend Detection (Day 8)
**Goal**: Identify time-series patterns

- [ ] Add to `src/llm/result_narrator.py`:
  - [ ] `_detect_temporal_columns()` method to:
    - [ ] Identify date/timestamp columns in results
    - [ ] Parse and sort by time
  - [ ] `_detect_trends()` method to:
    - [ ] Linear regression on time-series data
    - [ ] Calculate slope (trend direction and strength)
    - [ ] Calculate R² (goodness of fit)
    - [ ] Classify: upward/downward/flat trend
    - [ ] Calculate percentage change per period (daily/weekly/monthly)
  - [ ] Use `numpy.polyfit()` for regression
  - [ ] Integration into `generate_narrative()` with `enable_trends=True`
  - [ ] Update prompt to include trend insights

- [ ] Add dependency:
  - [ ] Add `numpy` to requirements.txt (if not already there)

- [ ] Update `src/models/schemas.py`:
  - [ ] Add optional to `ResultAnalysis`:
    - [ ] `trends: Optional[List[Dict[str, Any]]]` - detected trends by column

- [ ] Write unit tests in `tests/test_result_narrator.py`:
  - [ ] Test upward trend detection
  - [ ] Test downward trend detection
  - [ ] Test flat trend detection
  - [ ] Test temporal column detection
  - [ ] Test regression calculation
  - **Target**: 5 tests added, total 31 tests

**Completion Checklist**:
- [ ] Trend detection implemented
- [ ] Temporal column detection working
- [ ] 5 new tests passing
- [ ] LLM prompt updated with trend context
- [ ] Frontend displays trend insights
- [ ] Tested with various time-series patterns

**Estimated Time**: 1 day

---

### Phase 7: Advanced Feature - Correlation Analysis (Day 9 Morning)
**Goal**: Detect relationships between numeric columns

- [ ] Add to `src/llm/result_narrator.py`:
  - [ ] `_calculate_correlations()` method to:
    - [ ] Build correlation matrix for numeric columns
    - [ ] Use Pearson correlation
    - [ ] Filter to significant correlations (|r| > 0.7)
    - [ ] Return pairs with correlation coefficient and interpretation
  - [ ] Use `scipy.stats.pearsonr()` for calculation
  - [ ] Integration into `generate_narrative()` with `enable_correlations=True`
  - [ ] Update prompt to include correlation insights

- [ ] Add dependency:
  - [ ] Add `scipy` to requirements.txt

- [ ] Update `src/models/schemas.py`:
  - [ ] Add optional to `ResultAnalysis`:
    - [ ] `correlations: Optional[List[Dict[str, Any]]]` - detected correlations

- [ ] Write unit tests in `tests/test_result_narrator.py`:
  - [ ] Test strong positive correlation
  - [ ] Test strong negative correlation
  - [ ] Test no significant correlations
  - [ ] Test with single numeric column
  - [ ] Test correlation matrix calculation
  - **Target**: 5 tests added, total 36 tests

**Completion Checklist**:
- [ ] Correlation analysis implemented
- [ ] 5 new tests passing
- [ ] LLM prompt updated with correlation context
- [ ] Frontend displays correlation insights
- [ ] Tested with multi-column datasets
- [ ] All dependencies added

**Estimated Time**: 0.5 day

---

### Phase 8: Integration & Polish (Day 9 Afternoon)
**Goal**: Complete implementation, test, document

- [ ] Enable all advanced features:
  - [ ] Set all enable_* flags to True by default
  - [ ] Verify all features work together

- [ ] Frontend enhancements:
  - [ ] Add distinct styling for anomalies, trends, correlations
  - [ ] Update ResultSummary to display all insight types
  - [ ] Add visual indicators (badges, icons) for each insight type

- [ ] End-to-end testing:
  - [ ] Run 10+ complex real-world query scenarios
  - [ ] Verify narratives make sense for each
  - [ ] Test all feature combinations
  - [ ] Cross-browser testing

- [ ] Performance optimization:
  - [ ] Measure latency with all features enabled
  - [ ] Optimize statistical calculations (parallel execution with `asyncio.gather()`)
  - [ ] Cache historical lookups (30-second TTL)
  - [ ] Target: <3 seconds latency for 95% of queries

- [ ] Documentation:
  - [ ] Update `CLAUDE.md` with new feature section
  - [ ] Create `docs/DATA_NARRATIVES_GUIDE.md` with:
    - [ ] Feature overview
    - [ ] Configuration options
    - [ ] Example outputs
    - [ ] Troubleshooting guide
  - [ ] Update API documentation with new fields
  - [ ] Add implementation notes for future maintainers

- [ ] Code quality:
  - [ ] Run linter and fix any issues
  - [ ] Add docstrings to all public methods
  - [ ] Remove any TODOs or FIXMEs
  - [ ] Verify test coverage > 90%

- [ ] Final verification:
  - [ ] All 36+ tests passing
  - [ ] All frontend tests passing
  - [ ] No broken functionality
  - [ ] Performance acceptable
  - [ ] Documentation complete

**Completion Checklist**:
- [ ] All features integrated and working
- [ ] 36+ backend tests passing
- [ ] 12+ frontend tests passing
- [ ] <3 second latency verified
- [ ] Documentation complete
- [ ] Code review ready
- [ ] 🎉 **FEATURE COMPLETE!**

**Estimated Time**: 0.5 day

---

## 📊 Test Summary

### Backend Tests (36+ total)

**Core Narratives (15 tests)**:
- [ ] Basic count queries
- [ ] Aggregation queries
- [ ] Filter queries
- [ ] Multi-column results
- [ ] Empty results
- [ ] Numeric statistics extraction
- [ ] String statistics extraction
- [ ] Temporal statistics extraction
- [ ] LLM timeout handling
- [ ] Invalid JSON response
- [ ] Missing response fields
- [ ] Large result sampling
- [ ] Graceful degradation
- [ ] Mocked Ollama responses
- [ ] Confidence scoring

**Anomaly Detection (5 tests)**:
- [ ] Z-score outlier detection
- [ ] IQR method detection
- [ ] No anomalies case
- [ ] All outliers case
- [ ] Historical context retrieval

**Comparative Analysis (6 tests)**:
- [ ] Similar query lookup
- [ ] Percentage change calculation
- [ ] No similar queries
- [ ] Multiple historical options
- [ ] Real query_history data
- [ ] Old previous result edge case

**Trend Detection (5 tests)**:
- [ ] Upward trend
- [ ] Downward trend
- [ ] Flat trend
- [ ] Temporal column detection
- [ ] Regression calculation

**Correlation Analysis (5 tests)**:
- [ ] Strong positive correlation
- [ ] Strong negative correlation
- [ ] No significant correlations
- [ ] Single numeric column
- [ ] Correlation matrix calculation

**API Integration Tests (4-6 tests)**:
- [ ] Query with narratives enabled
- [ ] Query with narratives disabled
- [ ] Multiple query types
- [ ] Query succeeds if narrative fails
- [ ] Semantic cache integration

### Frontend Tests (12+ total)

**ResultSummary Component (10-12 tests)**:
- [ ] Summary text renders
- [ ] Direct answer displays
- [ ] Key insights render
- [ ] Confidence badge percentage
- [ ] Confidence badge colors
- [ ] Statistics expandable
- [ ] Accessibility compliance
- [ ] Responsive layout
- [ ] Edge cases handling
- [ ] Missing analysis handling

---

## 🔧 Critical Files to Create/Modify

### New Files (3):
1. **`src/llm/result_narrator.py`** (800-1000 lines)
   - Core narrative generation engine
   - Statistical analysis
   - LLM integration
   - Advanced feature methods

2. **`frontend/src/components/ResultSummary.tsx`** (250-300 lines)
   - Narrative display component
   - Confidence badge
   - Expandable statistics
   - Tailwind styling

3. **`tests/test_result_narrator.py`** (400-500 lines)
   - Unit tests for ResultNarrator
   - Mock Ollama responses
   - Edge case testing

4. **`frontend/tests/ResultSummary.test.tsx`** (300-400 lines)
   - Component tests
   - Rendering tests
   - Accessibility tests

### Modified Files (5):

1. **`src/api/endpoints/query.py`**
   - Lines ~290-310: Add narrative generation logic
   - Import ResultNarrator
   - Integration with execute_query result

2. **`src/models/schemas.py`**
   - Lines ~94-210: Add ResultAnalysis model
   - Extend QueryRequest with enable_narratives
   - Extend QueryResponse with result_analysis

3. **`src/llm/prompts.py`**
   - Add NARRATIVE_GENERATION_PROMPT template
   - Add few-shot examples
   - Add JSON schema guidance

4. **`src/config/settings.py`**
   - Add ENABLE_NARRATIVES flag
   - Add NARRATIVE_TIMEOUT_SECONDS
   - Add NARRATIVE_MAX_SAMPLE_ROWS

5. **`frontend/src/components/QueryResults.tsx`**
   - Line ~85: Conditional ResultSummary render
   - Import ResultSummary
   - Add resultAnalysis prop

6. **`frontend/src/types/api.ts`**
   - Add ResultAnalysis interface
   - Update QueryResponse interface

7. **`tests/test_query_endpoints.py`**
   - Add 4-6 narrative integration tests

8. **`src/core/settings` (if separate from config/settings.py)**
   - Add narrative-related configuration

### Documentation Files (2 new):
1. **`docs/DATA_NARRATIVES_GUIDE.md`**
   - Feature overview
   - Configuration
   - Examples
   - Troubleshooting

2. **`DATA_NARRATIVES_IMPLEMENTATION.md`** (this file)
   - Implementation tracking
   - Phase breakdown
   - Test summary

---

## 📈 Metrics & Success Criteria

### Performance Targets
- [ ] Narrative generation: <2 seconds (MVP)
- [ ] With all features: <3 seconds
- [ ] Cache hit: instant (<50ms)
- [ ] 95% of queries under target latency

### Quality Targets
- [ ] Test coverage: >90%
- [ ] Backend tests: 36+ passing
- [ ] Frontend tests: 12+ passing
- [ ] Zero critical bugs
- [ ] Graceful degradation on failures

### Accuracy Targets
- [ ] Anomaly detection: >90% accuracy for clear outliers
- [ ] Historical comparison: >80% match rate
- [ ] Trend detection: >85% accuracy on direction
- [ ] Correlation detection: accurate for |r| > 0.7

### UX Targets
- [ ] Narratives display within 100ms of ready
- [ ] Mobile responsive (100% verified)
- [ ] Accessibility compliant (WCAG 2.1 AA)
- [ ] User can disable feature (settings toggle)

---

## 🚀 Getting Started

### Prerequisites
- [ ] Python 3.11+
- [ ] Node.js/npm for frontend
- [ ] Ollama running locally
- [ ] SQLite/PostgreSQL for testing

### Dependencies to Add
```
numpy>=1.21.0
scipy>=1.7.0
```

### Branch
`Intelligent-Data-Narratives-and-Human-Insights`

### Next Steps
1. Review plan in `/Users/sam/.claude/plans/graceful-moseying-rabin.md`
2. Start Phase 1: Backend Foundation
3. Update this file as you complete each checkpoint
4. Commit frequently with descriptive messages

---

## 📝 Phase Completion Log

### Phase 1: Backend Foundation - MVP
**Status**: 🟢 IN PROGRESS
**Start**: 2025-12-13
**Estimated Completion**: 2025-12-14

- [ ] ResultNarrator class created
- [ ] Prompt template added
- [ ] 15 unit tests written and passing
- [ ] **Phase 1 Complete** ✅

### Phase 2: API Integration - MVP
**Status**: ⚪ PENDING
**Start**: 2025-12-15
**Estimated Completion**: 2025-12-15

- [ ] Schemas extended
- [ ] API integration complete
- [ ] Configuration added
- [ ] Integration tests passing
- [ ] **Phase 2 Complete** ✅

### Phase 3: Frontend Components - MVP
**Status**: ⚪ PENDING
**Start**: 2025-12-16
**Estimated Completion**: 2025-12-17

- [ ] ResultSummary component created
- [ ] TypeScript types added
- [ ] QueryResults integration
- [ ] Settings toggle added
- [ ] Frontend tests passing
- [ ] **🎉 MVP CHECKPOINT** ✅

### Phase 4: Anomaly Detection
**Status**: ⚪ PENDING
**Start**: 2025-12-18
**Estimated Completion**: 2025-12-18

- [ ] Anomaly detection implemented
- [ ] Tests passing
- [ ] **Phase 4 Complete** ✅

### Phase 5: Comparative Analysis
**Status**: ⚪ PENDING
**Start**: 2025-12-19
**Estimated Completion**: 2025-12-19

- [ ] Historical comparison implemented
- [ ] Tests passing
- [ ] **Phase 5 Complete** ✅

### Phase 6: Trend Detection
**Status**: ⚪ PENDING
**Start**: 2025-12-20
**Estimated Completion**: 2025-12-20

- [ ] Trend detection implemented
- [ ] Tests passing
- [ ] **Phase 6 Complete** ✅

### Phase 7: Correlation Analysis
**Status**: ⚪ PENDING
**Start**: 2025-12-21
**Estimated Completion**: 2025-12-21

- [ ] Correlation analysis implemented
- [ ] Tests passing
- [ ] **Phase 7 Complete** ✅

### Phase 8: Integration & Polish
**Status**: ⚪ PENDING
**Start**: 2025-12-21
**Estimated Completion**: 2025-12-22

- [ ] All features integrated
- [ ] E2E testing complete
- [ ] Performance optimized
- [ ] Documentation written
- [ ] **🎉 FEATURE COMPLETE** ✅

---

## 📞 Notes & Decisions

**User Preferences Applied**:
- ✅ Caching: Narratives cached WITH query results in semantic cache
- ✅ Fallback: Show basic stats only when disabled/failed
- ✅ UI Control: Global toggle in settings panel

**Architecture Decisions**:
- ResultNarrator follows existing agent patterns (ResultVerificationAgent model)
- Statistical calculations run in parallel with asyncio.gather()
- Advanced features are optional and can be disabled individually
- Graceful degradation: query succeeds even if narrative fails
- Maximum result size: 1000 rows (larger sets skipped)

**Deferred Features** (Post-Implementation):
- Business Glossary integration
- Multi-query synthesis
- Predictive insights with ML models

---

**Last Updated**: 2025-12-13
**Last Updated By**: Claude Code
