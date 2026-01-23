# UI Glassmorphism Upgrade Plan

## Overview

This document outlines the plan to update remaining components to match the new glassmorphism design system introduced in the `ui_upgrades_v2` branch.

**Branch:** `ui_upgrades_v2`
**Created:** January 17, 2026
**Status:** In Progress

---

## Design System Reference

### CSS Classes (from `index.css`)

| Class | Usage |
|-------|-------|
| `glass-panel` | Base glass effect with blur and border |
| `glass-card` | Interactive glass card with hover effects |
| `text-gradient` | Blue-to-purple gradient text |
| `glow-blue` | Subtle blue glow shadow |
| `animate-fadeIn` | Fade in with slight upward movement |
| `animate-slideInLeft` | Slide in from left |
| `animate-scaleUp` | Scale up entrance |

### Design Tokens

```css
--glass-bg: rgba(255, 255, 255, 0.65);        /* Light mode */
--glass-bg: rgba(15, 23, 42, 0.65);           /* Dark mode */
--glass-border: rgba(255, 255, 255, 0.4);     /* Light mode */
--glass-border: rgba(255, 255, 255, 0.08);    /* Dark mode */
--card-shadow: 0 8px 30px 0 rgba(0, 0, 0, 0.04);
```

### Typography Patterns

- Headers: `text-[11px] font-black uppercase tracking-[0.2em]`
- Labels: `text-xs font-bold uppercase tracking-widest`
- Body: `text-sm font-medium`

### Common Patterns

```tsx
// Panel header
<div className="p-6 border-b border-white/5 bg-white/5 dark:bg-black/20">
  <h2 className="text-sm font-black uppercase tracking-[0.2em]">Title</h2>
</div>

// Card container
<div className="glass-card rounded-2xl p-6 border-white/10">
  {/* content */}
</div>

// Tab buttons
<button className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wide
  ${active ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:bg-white/10'}`}>
```

---

## Phase 1: Main Tab Panels (High Priority)

These components are directly visible when switching main navigation tabs.

### 1.1 ToolsPanel.tsx & Sub-components
**Files:**
- `frontend/src/components/ToolsPanel.tsx`
- `frontend/src/components/ToolsOverview.tsx`
- `frontend/src/components/ToolDirectory.tsx`
- `frontend/src/components/ToolUsageStats.tsx`

**Changes:**
- [ ] Replace header with glass-panel styling
- [ ] Update tab navigation to match Header.tsx pattern
- [ ] Convert stat cards to glass-card
- [ ] Update icon containers to use glass-panel with rounded-2xl
- [ ] Apply consistent typography (font-black, uppercase, tracking)

**Estimated effort:** Medium

### 1.2 SemanticCachePanel.tsx & Sub-components
**Files:**
- `frontend/src/components/SemanticCachePanel.tsx`
- `frontend/src/components/CacheOverview.tsx`
- `frontend/src/components/CacheStatistics.tsx`
- `frontend/src/components/RecentCachedQueries.tsx`

**Changes:**
- [ ] Mirror ToolsPanel updates
- [ ] Update cache stat cards with glassmorphism
- [ ] Style query list items with glass-card hover effects
- [ ] Add subtle animations for cache hit indicators

**Estimated effort:** Medium

### 1.3 ConnectionPoolMetrics.tsx
**File:** `frontend/src/components/ConnectionPoolMetrics.tsx`

**Changes:**
- [ ] Wrap in glass-panel container
- [ ] Update pool status table with glass styling
- [ ] Convert health indicators to glass badges
- [ ] Style action buttons consistently

**Estimated effort:** Small

### 1.4 FeedbackStats.tsx
**File:** `frontend/src/components/FeedbackStats.tsx`

**Changes:**
- [ ] Add glass-panel wrapper
- [ ] Update stat cards layout
- [ ] Style feedback list items
- [ ] Update pagination controls

**Estimated effort:** Small

---

## Phase 2: Secondary Components (Medium Priority)

Components used within the main interface but not primary views.

### 2.1 QueryResults.tsx
**File:** `frontend/src/components/QueryResults.tsx`

**Changes:**
- [ ] Update table container styling
- [ ] Add glass effects to pagination
- [ ] Style SQL display area
- [ ] Update copy button styling

**Estimated effort:** Medium

### 2.2 ResultSummary.tsx
**File:** `frontend/src/components/ResultSummary.tsx`

**Changes:**
- [ ] Update narrative container
- [ ] Style insight bullets
- [ ] Add glass effects to anomaly/trend alerts

**Estimated effort:** Small

### 2.3 FeedbackModal.tsx
**File:** `frontend/src/components/FeedbackModal.tsx`

**Changes:**
- [ ] Update modal overlay to match DatabaseConnectionModal
- [ ] Apply glass-card to modal content
- [ ] Style form inputs consistently
- [ ] Update button styling

**Estimated effort:** Small

### 2.4 ConversationContextPanel.tsx
**File:** `frontend/src/components/ConversationContextPanel.tsx`

**Changes:**
- [ ] Apply glass-panel styling
- [ ] Update context item cards
- [ ] Style clear button

**Estimated effort:** Small

### 2.5 ModelConfigPanel.tsx
**File:** `frontend/src/components/ModelConfigPanel.tsx`

**Changes:**
- [ ] Update model selection cards
- [ ] Style slider controls
- [ ] Apply consistent toggle styling

**Estimated effort:** Medium

### 2.6 LearnedMappingsPanel.tsx & Sub-components
**Files:**
- `frontend/src/components/LearnedMappingsPanel.tsx`
- `frontend/src/components/ColumnMappingsList.tsx`
- `frontend/src/components/TableMappingsList.tsx`
- `frontend/src/components/ResultPatternsList.tsx`
- `frontend/src/components/MappingStatsDisplay.tsx`

**Changes:**
- [ ] Apply glass-panel to main container
- [ ] Update list item styling
- [ ] Style filter controls
- [ ] Update stats display cards

**Estimated effort:** Medium

---

## Phase 3: Observability Components (Lower Priority)

Components for debugging and advanced users.

### 3.1 QueryPlanVisualization.tsx
- [ ] Update plan step cards
- [ ] Style connection lines
- [ ] Add glass effects to nodes

### 3.2 CorrectionHistory.tsx
- [ ] Update history item styling
- [ ] Style diff display

### 3.3 VerificationWarnings.tsx
- [ ] Update warning badges
- [ ] Style warning containers

### 3.4 ParallelExecutionMetrics.tsx
- [ ] Update metric cards
- [ ] Style progress indicators

### 3.5 ConfidenceBadge.tsx
- [ ] Update badge styling to glass effect

### 3.6 MultiDatabaseAssessment.tsx & QueryFeasibilityBadge.tsx
- [ ] Update assessment cards
- [ ] Style capability badges

---

## Phase 4: Utility Components (Optional)

### 4.1 SQLEditor.tsx
- [ ] Update editor container
- [ ] Style toolbar

### 4.2 SchemaComparison.tsx
- [ ] Update comparison view

### 4.3 ObservabilityDemo.tsx
- [ ] Update demo layout (if still used)

---

## Implementation Order

1. **Phase 1.1** - ToolsPanel (establishes pattern for tab panels)
2. **Phase 1.2** - SemanticCachePanel (follow ToolsPanel pattern)
3. **Phase 1.3** - ConnectionPoolMetrics
4. **Phase 1.4** - FeedbackStats
5. **Phase 2.1-2.2** - QueryResults, ResultSummary (most visible)
6. **Phase 2.3-2.6** - Remaining secondary components
7. **Phase 3** - Observability components (as time permits)
8. **Phase 4** - Utility components (optional)

---

## Testing Checklist

After each component update:
- [ ] Light mode appearance
- [ ] Dark mode appearance
- [ ] Hover/focus states
- [ ] Animation smoothness
- [ ] Mobile responsiveness (if applicable)
- [ ] No TypeScript errors
- [ ] Build passes

---

## Notes

- Maintain consistency with existing updated components
- Preserve all existing functionality
- Test dark mode thoroughly (glassmorphism can look different)
- Keep animations subtle and performant
- Use `animate-fadeIn` sparingly to avoid slow-feeling UI
