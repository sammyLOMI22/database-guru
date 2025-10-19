# Testing Guide - Observability Features

## Quick Start

### 1. Start the Backend
```bash
cd /Users/sam/database-guru
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend
```bash
cd /Users/sam/database-guru/frontend
npm run dev
```

## Testing Options

### Option 1: View Demo with Mock Data (Recommended for Quick Testing)

Visit: **http://localhost:3000/?demo=true**

This will show:
- ✅ Complete observability demo with mock data
- ✅ Two scenarios:
  - **Scenario 1**: Auto-corrected query with verification warning
  - **Scenario 2**: Complex query with query planning
- ✅ All components in action
- ✅ No backend required

**What you'll see:**
1. **Agent Execution Trace** - Step-by-step timeline with icons
2. **Auto-Corrected Query** - Shows correction attempts with fix methods
3. **Query Plan** - Detailed plan visualization for complex queries
4. **Verification Warnings** - Prominent warning display
5. **Component Legend** - Explains each component

### Option 2: Test with Real Backend

Visit: **http://localhost:3000**

1. **Make sure backend is running** on port 8000
2. **Select or create a database connection**
3. **Ask a question** that will demonstrate observability:

**Test Queries:**

#### Simple Query (Minimal Observability)
```
Show all users
```
Expected: Basic execution, minimal trace

#### Query with Auto-Correction
```
SELECT * FROM users WHERE id = 1
```
If table name is wrong, you'll see:
- ✨ Auto-correction banner
- 📊 Agent trace showing error → fix → success
- Correction attempts with fix method (quick_fix, learned, or llm)

#### Complex Query (with Planning)
```
Show total sales by category for each month in 2024
```
Expected:
- 📋 Query plan visualization
- Complexity badge
- Tables, filters, aggregations breakdown

#### Query with Potential Issues
```
Show all transactions from last year
```
May trigger:
- ⚠️ Verification warnings if result set seems unusual

## What to Test

### ✅ Visual Components

1. **Agent Trace**
   - [ ] Expands/collapses on click
   - [ ] Shows all step types with correct icons
   - [ ] Displays elapsed time for each step
   - [ ] Metadata details are expandable
   - [ ] Total execution time shown

2. **Correction History**
   - [ ] Only shows when query was auto-corrected
   - [ ] Lists all attempts
   - [ ] Shows SQL for each attempt
   - [ ] Displays error messages
   - [ ] Fix method badges visible (Quick Fix, Learned, LLM)
   - [ ] Success/failure states clear

3. **Query Plan**
   - [ ] Only shows when planning was used
   - [ ] Complexity badge displayed correctly
   - [ ] Confidence score shown
   - [ ] Tables, joins, filters organized
   - [ ] All sections expandable

4. **Verification Warnings**
   - [ ] Only shows when warnings exist
   - [ ] Yellow warning theme
   - [ ] Clear warning messages
   - [ ] Help text displayed

### ✅ Responsive Design

Test on different screen sizes:

**Desktop (>1024px)**
- [ ] All panels display properly
- [ ] No horizontal scroll (except tables)
- [ ] Readable text sizes

**Tablet (768-1023px)**
- [ ] Components stack properly
- [ ] Touch-friendly expand/collapse
- [ ] Tables scroll horizontally

**Mobile (<768px)**
- [ ] Single column layout
- [ ] All text readable
- [ ] No content cut off
- [ ] Touch targets large enough

### ✅ Accessibility

**Keyboard Navigation:**
- [ ] Tab through all expand/collapse buttons
- [ ] Enter/Space to toggle panels
- [ ] Focus indicators visible

**Screen Reader:**
- [ ] ARIA labels present
- [ ] Proper heading structure
- [ ] States announced correctly

### ✅ Performance

- [ ] Components render quickly
- [ ] No lag when expanding panels
- [ ] Smooth animations
- [ ] No console errors

## Browser Testing

Test in:
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

## Expected Behavior

### Successful Query (No Issues)
```
Question: "Show all users"
Response includes:
- SQL display
- Results table
- Agent trace (minimal steps)
```

### Auto-Corrected Query
```
Question: "Show all users" (with wrong table name)
Response includes:
- SQL display
- ✨ Auto-correction warning
- 📊 Agent trace (shows error → fix → success)
- Correction History component
  - Attempt 1: Failed (table not found)
  - Attempt 2: Success (quick_fix)
- Results table
```

### Complex Query with Planning
```
Question: "Show total sales by category"
Response includes:
- SQL display
- 📋 Query Plan component
  - Complexity: medium/complex
  - Tables, aggregations, grouping
- Results table
- Agent trace (shows planning step)
```

### Query with Verification Warning
```
Question: "Show all transactions"
Response includes:
- SQL display
- Results table
- ⚠️ Verification Warnings component
- Agent trace (shows verification warning step)
```

## Troubleshooting

### Components Not Showing?

**Check 1: Backend is returning data**
```bash
curl http://localhost:8000/api/query/ \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Show all users"}'
```

Look for these fields in response:
- `agent_trace`
- `query_plan`
- `attempts`
- `self_corrected`
- `verification_warnings`

**Check 2: Frontend is receiving data**
Open browser DevTools → Network → Look for API response

**Check 3: TypeScript types match**
No TypeScript errors in console

### Styles Not Applied?

- Check Tailwind CSS is running
- Look for `className` errors in console
- Verify all imports are correct

### Demo Not Loading?

1. Make sure URL is: `http://localhost:3000/?demo=true`
2. Check browser console for errors
3. Verify ObservabilityDemo component imported correctly

## Success Criteria

✅ **Week 1 Complete** when:
1. All 4 components render correctly
2. Components show/hide based on data
3. Responsive on all screen sizes
4. Accessible via keyboard
5. No console errors
6. Smooth user experience

## Next Steps

After testing Week 1:
- **Week 2**: User feedback submission
- **Week 2**: SQL correction editor
- **Week 2**: Learning integration
- **Week 2**: Stats dashboard

## Need Help?

Common issues:
1. **"Cannot find module"** - Run `npm install` in frontend
2. **Backend not responding** - Check it's running on port 8000
3. **Components not styled** - Tailwind CSS might need rebuild
4. **TypeScript errors** - Check types in `frontend/src/types/api.ts`

---

**Happy Testing!** 🎉

For detailed implementation docs, see:
- [OPTION_2_FRONTEND_COMPLETE.md](OPTION_2_FRONTEND_COMPLETE.md)
- [OPTION_2_DAY_2_COMPLETE.md](OPTION_2_DAY_2_COMPLETE.md)
- [OPTION_2_PROGRESS.md](OPTION_2_PROGRESS.md)
