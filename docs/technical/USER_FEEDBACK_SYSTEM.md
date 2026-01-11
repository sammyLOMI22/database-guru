# User Feedback System - Implementation Guide

## Overview

The User Feedback System enables continuous learning by allowing users to correct queries, report issues, and help the system learn from mistakes. The system automatically applies learned corrections to future similar queries.

---

## Features Implemented

### ✅ Backend (Days 5-6)

1. **UserFeedback Database Model** (`src/database/models.py`)
   - Stores user corrections and feedback
   - Links to original queries and learned corrections
   - Tracks confidence scores and application status

2. **Feedback API Schemas** (`src/models/schemas.py`)
   - `FeedbackCreate` - Submit new feedback
   - `FeedbackResponse` - Feedback data response
   - `FeedbackApplyRequest` - Apply feedback to learning
   - `FeedbackStatsResponse` - Statistics dashboard data

3. **Feedback API Endpoints** (`src/api/endpoints/feedback.py`)
   - `POST /api/feedback/` - Submit user feedback
   - `POST /api/feedback/apply` - Apply feedback to learning system
   - `GET /api/feedback/query/{query_id}` - Get feedback for specific query
   - `GET /api/feedback/recent` - Get recent feedback submissions
   - `GET /api/feedback/stats` - Get feedback statistics
   - `DELETE /api/feedback/{feedback_id}` - Delete feedback entry

4. **Database Migration**
   - Auto-created via SQLAlchemy `Base.metadata.create_all()`
   - Table: `user_feedback` with full schema

### ✅ Frontend (Days 7-8)

1. **SQLEditor Component** (`frontend/src/components/SQLEditor.tsx`)
   - Reusable SQL editing textarea
   - Read-only and editable modes
   - Syntax highlighting support ready

2. **FeedbackModal Component** (`frontend/src/components/FeedbackModal.tsx`)
   - User-friendly feedback submission interface
   - Feedback type selector (SQL correction, column/table names, result issues)
   - Original SQL display (read-only)
   - Corrected SQL editor
   - Description and notes fields
   - Confidence slider (0-100%)
   - Validation and error handling

3. **QueryResults Integration** (`frontend/src/components/QueryResults.tsx`)
   - "Feedback" button added to SQL display
   - Opens FeedbackModal on click
   - Submits feedback to API

4. **Feedback API Service** (`frontend/src/services/api.ts`)
   - `feedbackAPI.submitFeedback()` - Submit feedback
   - `feedbackAPI.applyFeedback()` - Apply to learning
   - `feedbackAPI.getQueryFeedback()` - Get query feedback
   - `feedbackAPI.getRecentFeedback()` - Get recent feedback
   - `feedbackAPI.getStats()` - Get statistics
   - `feedbackAPI.deleteFeedback()` - Delete feedback

5. **FeedbackStats Dashboard** (`frontend/src/components/FeedbackStats.tsx`)
   - Total feedback count
   - Applied vs pending breakdown
   - Feedback by type visualization
   - Recent feedback list with "Apply to Learning" button

---

## Usage Guide

### For End Users

#### Submitting Feedback

1. **Execute a query** in the Database Guru interface
2. **Review the results** - if something is wrong, click the "Feedback" button next to the generated SQL
3. **Fill out the feedback form:**
   - Select feedback type:
     - **SQL Correction**: Provide a corrected version of the SQL
     - **Column Name**: Report incorrect column name
     - **Table Name**: Report incorrect table name
     - **Result Issue**: Report problems with query results
   - If SQL correction: Edit the SQL in the corrected SQL editor
   - Describe what's wrong and what should change
   - Add optional notes for context
   - Set your confidence level (0-100%)
4. **Submit** - Your feedback is saved for review

#### Applying Feedback to Learning

**Option 1: Via Dashboard**
- Navigate to the Feedback Stats dashboard
- Find your feedback in the "Recent Feedback" section
- Click "Apply to Learning" button
- The system will test the correction and add it to the learning database

**Option 2: Via API**
- Use the apply endpoint directly if integrating programmatically

### For Developers

#### Backend Setup

The feedback system is automatically initialized when the application starts:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application (tables auto-created)
python -m src.main
```

The `user_feedback` table will be created automatically via SQLAlchemy.

#### Frontend Integration

To add feedback capability to any component displaying query results:

```tsx
import { FeedbackModal, FeedbackData } from './components/FeedbackModal';
import { feedbackAPI } from './services/api';

// In your component:
const [showFeedbackModal, setShowFeedbackModal] = useState(false);

const handleFeedbackSubmit = async (feedback: FeedbackData) => {
  try {
    await feedbackAPI.submitFeedback(feedback);
    setShowFeedbackModal(false);
    // Optional: Show success notification
  } catch (error) {
    console.error('Failed to submit feedback:', error);
    throw error;
  }
};

// In JSX:
{showFeedbackModal && queryId && (
  <FeedbackModal
    queryId={queryId}
    originalSQL={sql}
    onSubmit={handleFeedbackSubmit}
    onClose={() => setShowFeedbackModal(false)}
  />
)}
```

#### API Examples

**Submit Feedback:**
```bash
curl -X POST http://localhost:8000/api/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": 123,
    "feedback_type": "sql_correction",
    "corrected_sql": "SELECT * FROM products WHERE category_name = '\''Electronics'\''",
    "correction_description": "Should use category_name instead of category",
    "user_confidence": 1.0
  }'
```

**Apply Feedback to Learning:**
```bash
curl -X POST http://localhost:8000/api/feedback/apply \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_id": 5,
    "test_before_learning": true
  }'
```

**Get Feedback Stats:**
```bash
curl http://localhost:8000/api/feedback/stats
```

**Get Recent Feedback:**
```bash
curl http://localhost:8000/api/feedback/recent?limit=10
```

---

## Database Schema

### `user_feedback` Table

```sql
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL REFERENCES query_history(id),
    feedback_type VARCHAR(50) NOT NULL,
    original_sql TEXT NOT NULL,
    corrected_sql TEXT,
    correction_description TEXT,
    correction_details JSONB,
    user_confidence REAL DEFAULT 1.0,
    applied_successfully BOOLEAN DEFAULT FALSE,
    learned_correction_id INTEGER REFERENCES learned_corrections(id),
    user_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_user_feedback_query_id ON user_feedback(query_id);
CREATE INDEX idx_user_feedback_type ON user_feedback(feedback_type);
CREATE INDEX idx_user_feedback_applied ON user_feedback(applied_successfully);
CREATE INDEX idx_user_feedback_created_at ON user_feedback(created_at);
```

---

## Learning System Integration

When feedback is applied to the learning system:

1. **Validation** (optional): The corrected SQL is tested against the active database
2. **Error Categorization**: The system determines the error type from the original query
3. **Learning**: A new entry is created in `learned_corrections` table
4. **Linking**: The feedback is linked to the learned correction
5. **Future Application**: Similar errors will automatically apply this correction

### Feedback Types

1. **sql_correction**: Complete SQL query correction
   - User provides both original and corrected SQL
   - System learns the pattern for auto-correction

2. **column_name**: Column name issue
   - Reports incorrect column name usage
   - Can include structured correction details

3. **table_name**: Table name issue
   - Reports incorrect table name usage
   - Helps improve schema understanding

4. **result_issue**: Result quality issue
   - Reports problems with query results
   - Helps improve verification logic

---

## Testing

### Backend Tests

```bash
source venv/bin/activate

# Test feedback module imports
python -c "from src.api.endpoints import feedback; print('✅ OK')"

# Start server and test via Swagger UI
python -m src.main
# Navigate to: http://localhost:8000/docs
# Test endpoints under "Feedback" section
```

### Frontend Tests

```bash
cd frontend

# Build check
npm run build

# Development server
npm run dev
```

### E2E Test Flow

1. Execute a query that produces an error or incorrect result
2. Click "Feedback" button on the query results
3. Fill out the feedback form with a correction
4. Submit the feedback
5. Navigate to Feedback Stats dashboard
6. Click "Apply to Learning" on your feedback
7. Execute a similar query - the correction should be auto-applied

---

## Files Modified/Created

### Backend
- ✅ `src/database/models.py` - UserFeedback model (updated)
- ✅ `src/models/schemas.py` - Feedback schemas (added)
- ✅ `src/api/endpoints/feedback.py` - Feedback endpoints (new)
- ✅ `src/main.py` - Router registration (updated)

### Frontend
- ✅ `frontend/src/components/SQLEditor.tsx` - SQL editor component (new)
- ✅ `frontend/src/components/FeedbackModal.tsx` - Feedback modal (new)
- ✅ `frontend/src/components/FeedbackStats.tsx` - Stats dashboard (new)
- ✅ `frontend/src/components/QueryResults.tsx` - Feedback button (updated)
- ✅ `frontend/src/services/api.ts` - Feedback API service (updated)

---

## Next Steps (Optional Enhancements)

1. **Notifications**: Add toast notifications for feedback submission success/failure
2. **Feedback Review UI**: Create admin interface for reviewing pending feedback
3. **Bulk Apply**: Allow applying multiple feedback items at once
4. **Feedback Analytics**: Add charts showing learning improvement over time
5. **User Reputation**: Track user feedback quality and accuracy
6. **Feedback Comments**: Allow discussion/comments on feedback items
7. **Export/Import**: Export learned corrections for sharing between instances

---

## Troubleshooting

### Issue: Feedback button not appearing
- **Solution**: Ensure `queryId` prop is passed to `QueryResults` component

### Issue: Apply to Learning fails
- **Solution**: Check that active database connection exists and corrected SQL is valid

### Issue: Stats not loading
- **Solution**: Verify backend is running and `/api/feedback/stats` endpoint is accessible

### Issue: CorrectionLearner not available
- **Solution**: This is expected if the learning system isn't fully configured. Feedback will still be saved for manual review.

---

## Support

For questions or issues:
1. Check the implementation plan: `OPTION_2_IMPLEMENTATION_PLAN.md`
2. Review API documentation: http://localhost:8000/docs
3. Check backend logs for error details

---

**Week 2 Implementation: COMPLETE ✅**

All planned features have been implemented and tested!
