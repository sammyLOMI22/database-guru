# Confidence Scoring - Manual Verification Guide

**Date**: 2025-10-26
**Purpose**: Verify confidence scores appear correctly in the running application

---

## Prerequisites

- Backend server running
- Frontend dev server running
- Database configured with sample data

---

## Step-by-Step Verification

### Step 1: Start Backend Server

```bash
# Terminal 1
cd /Users/sam/database-guru
source venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

**Expected output**: Server running on http://localhost:8000

### Step 2: Start Frontend Dev Server

```bash
# Terminal 2
cd /Users/sam/database-guru/frontend
npm run dev
```

**Expected output**:
- Vite dev server running on http://localhost:3000
- No build errors

### Step 3: Open Application

1. Open browser to: **http://localhost:3000**
2. Application should load successfully

### Step 4: Trigger a Self-Correction

**Test Query 1: Simple Table Typo (HIGH Confidence Expected)**

Enter this query in the UI:
```
Show me all customers from custmers table
```

**Expected behavior**:
1. Query will fail on first attempt (table "custmers" doesn't exist)
2. Self-correcting agent will fix it to "customers"
3. Second attempt succeeds

**Expected UI elements**:
- ✨ "Auto-Corrected Query" section appears
- Expandable correction history showing 2 attempts
- **Attempt 1**: Failed, shows error "table custmers does not exist"
- **Attempt 2**: Success, shows:
  - ✅ "Confidence Score:" label
  - 🎯 Green badge showing "~90%+ HIGH"
  - Badge is clickable to expand

**Test Query 2: Column Name Fix (MEDIUM-HIGH Confidence Expected)**

```
Select id, nam, email from customers
```

**Expected behavior**:
1. First attempt fails (column "nam" doesn't exist)
2. Self-correction fixes to "name"
3. Second attempt succeeds

**Expected confidence badge**:
- ⚡ Yellow or Green badge
- ~80-90% confidence
- Level: MEDIUM or HIGH

**Test Query 3: Complex Error (LOWER Confidence Expected)**

```
SELECT * FROM users WHERE id = 'invalid_syntax
```

**Expected behavior**:
1. Syntax error detected
2. Self-correction attempts fix
3. May succeed or fail

**Expected confidence badge**:
- ⚡ Yellow or ⚠️ Orange badge
- ~50-70% confidence
- Level: MEDIUM or LOW

### Step 5: Verify Badge Interactivity

Click on the confidence badge to expand details.

**Expected expanded view**:
```
┌──────────────────────────────────────┐
│ 🎯  92.5%  HIGH  ▲                  │
└──────────────────────────────────────┘
┌──────────────────────────────────────┐
│ Analysis:                            │
│ This correction has high confidence  │
│ (92.5%). Table Not Found errors are  │
│ relatively easy to fix. The          │
│ correction references valid schema   │
│ objects.                             │
│                                      │
│ Recommendation:                      │
│ EXECUTE - High confidence, likely    │
│ to succeed                           │
│                                      │
│ Contributing Factors:                │
│ Error Type Difficulty      25.5%    │
│ ████████████░░░░░░░░░░░░            │
│ Schema Match               25.0%    │
│ ████████████░░░░░░░░░░░░            │
│ Historical Success         17.0%    │
│ ████████░░░░░░░░░░░░░░░░            │
│ Correction Complexity      15.0%    │
│ ███████░░░░░░░░░░░░░░░░░            │
│ Similarity to Original     10.0%    │
│ █████░░░░░░░░░░░░░░░░░░░            │
│                                      │
│ Overall Confidence         92.5%    │
│ ████████████████████████████░░      │
└──────────────────────────────────────┘
```

**Check for**:
- ✅ Analysis section with reasoning
- ✅ Recommendation section with action
- ✅ All 5 factors listed with percentages
- ✅ Progress bars for each factor
- ✅ Overall confidence bar at bottom
- ✅ Proper color coding (green for HIGH)

### Step 6: Verify API Response

Open browser DevTools (F12) → Network tab

Make another query that triggers self-correction.

**Check the API response** (e.g., `/api/query`):

```json
{
  "attempts": [
    {
      "attempt_number": 1,
      "sql": "SELECT * FROM custmers",
      "success": false,
      "error": "relation \"custmers\" does not exist",
      "confidence_prediction": null
    },
    {
      "attempt_number": 2,
      "sql": "SELECT * FROM customers",
      "success": true,
      "confidence_prediction": {
        "overall": 0.925,
        "level": "HIGH",
        "factors": {
          "error_type": 0.255,
          "schema_match": 0.250,
          "historical_success": 0.170,
          "correction_complexity": 0.150,
          "similarity": 0.100
        },
        "reasoning": "This correction has high confidence (92.5%)...",
        "recommendation": "EXECUTE - High confidence, likely to succeed"
      }
    }
  ]
}
```

**Verify**:
- ✅ First attempt has `confidence_prediction: null`
- ✅ Second attempt has complete `confidence_prediction` object
- ✅ All required fields present (overall, level, factors, reasoning, recommendation)
- ✅ Factor values sum to approximately `overall` value

---

## Verification Checklist

### Visual Display
- [ ] Confidence badge appears on corrected attempts
- [ ] Badge shows percentage (e.g., "92.5%")
- [ ] Badge shows level (HIGH/MEDIUM/LOW/VERY_LOW)
- [ ] Badge has correct icon (🎯/⚡/⚠️/🚫)
- [ ] Badge color matches level (green/yellow/orange/red)

### Interactivity
- [ ] Badge is clickable
- [ ] Clicking expands details
- [ ] Clicking again collapses details
- [ ] Chevron icon rotates on expand/collapse

### Expanded Details
- [ ] Analysis/reasoning displayed
- [ ] Recommendation displayed
- [ ] All 5 factors shown with labels
- [ ] Factor percentages displayed
- [ ] Progress bars rendered for each factor
- [ ] Overall confidence bar at bottom
- [ ] Proper styling and colors

### Data Accuracy
- [ ] Confidence scores match backend predictions
- [ ] First attempt has no confidence badge
- [ ] Correction attempts (2+) have confidence badges
- [ ] High confidence for simple fixes (table typos)
- [ ] Lower confidence for complex errors

### Browser Compatibility
- [ ] Works in Chrome
- [ ] Works in Firefox
- [ ] Works in Safari
- [ ] No console errors

### Accessibility
- [ ] Badge has proper aria-label
- [ ] Expandable has aria-expanded attribute
- [ ] Progress bars have aria attributes
- [ ] Keyboard navigable

---

## Troubleshooting

### Issue: No confidence badge appears

**Check**:
1. Is the query being self-corrected? (Check for "Auto-Corrected Query" section)
2. Open DevTools → Network → Check API response for `confidence_prediction`
3. Check browser console for JavaScript errors
4. Verify you're on attempt 2+ (attempt 1 never has confidence)

**Solution**:
- If `confidence_prediction` is in API but not displayed: Frontend issue, check component integration
- If `confidence_prediction` is null in API: Backend issue, check confidence scorer is enabled

### Issue: Badge shows but won't expand

**Check**:
1. Console for JavaScript errors
2. Badge `showDetails` prop (should be true by default)

**Solution**:
- Check `ConfidenceBadge` component receives `confidence` prop correctly
- Verify no CSS issues preventing clicks

### Issue: Wrong colors/styling

**Check**:
1. Tailwind CSS loaded correctly
2. Badge level matches expected (HIGH/MEDIUM/LOW/VERY_LOW)

**Solution**:
- Run `npm run build` to rebuild Tailwind classes
- Check `confidence.level` value in API response

### Issue: Factors don't add up

**Note**: Factors are weighted percentages, not direct percentages:
- Each factor contributes a portion (e.g., error_type is 30% weight)
- The displayed percentage is the weighted contribution
- Sum of all factor contributions ≈ overall confidence

**Example**:
```
error_type (30% weight): 0.85 base → 0.255 contribution (25.5%)
schema_match (25% weight): 1.0 score → 0.250 contribution (25.0%)
... etc ...
Overall: 0.925 (92.5%)
```

---

## Success Criteria

✅ **Verification Complete** when:
1. Confidence badges appear on all self-corrected queries
2. Badges display correct percentage and level
3. Badges are interactive (expand/collapse)
4. Expanded view shows all details correctly
5. Colors match confidence levels
6. No browser console errors
7. API responses include proper confidence_prediction data
8. Accessibility features work

---

## Quick Test Script

For rapid testing:

```bash
# Test 1: Table typo (HIGH confidence)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all data from custmers", "database_type": "postgresql", "execute": true}' \
  | jq '.attempts[].confidence_prediction'

# Expected: null for attempt 1, HIGH confidence object for attempt 2

# Test 2: Column typo (MEDIUM-HIGH confidence)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Select id, nam from customers", "database_type": "postgresql", "execute": true}' \
  | jq '.attempts[].confidence_prediction'
```

---

**Last Updated**: 2025-10-26
**Status**: Ready for testing
