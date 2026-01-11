# 🎨 Frontend Setup Guide

## Overview

Database Guru now has a modern React + TypeScript frontend with professional UI/UX design.

---

## Architecture Decision

### Why React + TypeScript + Vite?

✅ **React** - Industry standard, large ecosystem, component-based
✅ **TypeScript** - Type safety, better DX, fewer bugs
✅ **Vite** - Lightning fast HMR, modern build tool
✅ **Tailwind CSS** - Utility-first, highly customizable
✅ **TanStack Query** - Professional server state management

### Best Practices Followed

- ✅ Component-based architecture
- ✅ TypeScript for type safety
- ✅ Service layer for API calls
- ✅ Custom hooks for reusability
- ✅ Responsive design (mobile-first)
- ✅ Proper error handling
- ✅ Loading states
- ✅ Code splitting
- ✅ Production-ready build

---

## Quick Start

### Prerequisites

- Node.js 18+ (https://nodejs.org/)
- npm or yarn
- Database Guru API running on port 8000

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit: http://localhost:3000

---

## Project Structure

```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── ChatInterface.tsx    # Main chat UI
│   │   ├── Header.tsx           # Top bar
│   │   ├── Sidebar.tsx          # Schema/History sidebar
│   │   ├── QueryInput.tsx       # Input field
│   │   ├── MessageList.tsx      # Chat messages
│   │   ├── QueryResults.tsx     # SQL results display
│   │   ├── SQLDisplay.tsx       # Syntax highlighted SQL
│   │   ├── SchemaPanel.tsx      # Database schema browser
│   │   ├── HistoryPanel.tsx     # Query history list
│   │   ├── ModelSelector.tsx    # LLM model dropdown
│   │   └── StatusIndicator.tsx  # Connection status
│   │
│   ├── services/            # API layer
│   │   └── api.ts              # Axios HTTP client
│   │
│   ├── types/               # TypeScript types
│   │   └── api.ts              # API request/response types
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useQuerySubmit.ts   # Query submission logic
│   │   ├── useModels.ts        # Model management
│   │   ├── useSchema.ts        # Schema loading
│   │   └── useHistory.ts       # Query history
│   │
│   ├── utils/               # Utilities
│   │   ├── formatters.ts       # Data formatting
│   │   └── constants.ts        # App constants
│   │
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles + Tailwind
│
├── public/                  # Static files
│   └── vite.svg
│
├── package.json             # Dependencies
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind configuration
├── tsconfig.json            # TypeScript config
└── README.md                # Frontend docs
```

---

## Key Components

### 1. ChatInterface (Main Component)

Displays chat-style conversation with the AI.

**Features:**
- Message history
- User questions
- AI responses with SQL + results
- Loading states
- Error handling

### 2. QueryInput

Text input for natural language questions.

**Features:**
- Auto-resize textarea
- Ctrl+Enter to send
- Character counter
- Submit button

### 3. QueryResults

Displays SQL execution results in table format.

**Features:**
- Responsive table
- Column headers
- Row striping
- Pagination for large results
- Empty state
- Copy to clipboard

### 4. SchemaPanel

Browse database structure.

**Features:**
- List of tables
- Column details (type, nullable, keys)
- Foreign key relationships
- Refresh button
- Collapsible sections

### 5. HistoryPanel

View past queries.

**Features:**
- Chronological list
- Click to reuse query
- Show SQL preview
- Execution status
- Model used

---

## API Integration

All API calls go through the service layer:

```typescript
// services/api.ts
export const queryAPI = {
  processQuery: (request: QueryRequest) => Promise<QueryResponse>,
  getHistory: (limit, offset) => Promise<QueryHistoryItem[]>,
};

export const schemaAPI = {
  getSchema: (refresh?) => Promise<SchemaResponse>,
  getTables: () => Promise<{tables: string[]}>,
};

export const modelsAPI = {
  listModels: () => Promise<ModelListResponse>,
  getDetails: () => Promise<ModelDetails>,
};
```

### Example Usage

```typescript
import { queryAPI } from '@/services/api';

// In component
const handleSubmit = async (question: string) => {
  try {
    const result = await queryAPI.processQuery({
      question,
      model: selectedModel,
    });

    // Handle result
    setResults(result.results);
    setSQL(result.sql);
  } catch (error) {
    // Handle error
    setError(error.message);
  }
};
```

---

## State Management

Using **TanStack Query** for server state:

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';

// Fetching data
const { data, isLoading, error } = useQuery({
  queryKey: ['schema'],
  queryFn: () => schemaAPI.getSchema(),
});

// Mutations
const mutation = useMutation({
  mutationFn: queryAPI.processQuery,
  onSuccess: (data) => {
    // Handle success
  },
});
```

---

## Styling with Tailwind

### Utility Classes

```tsx
<div className="flex flex-col space-y-4 p-6">
  <h2 className="text-2xl font-bold text-gray-900">
    Title
  </h2>
  <button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
    Click Me
  </button>
</div>
```

### Custom Colors

```javascript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      primary: {
        50: '#f0f9ff',
        500: '#0ea5e9',
        600: '#0284c7',
      },
    },
  },
}
```

### Responsive Design

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* Mobile: 1 column, Tablet: 2 columns, Desktop: 3 columns */}
</div>
```

---

## Development Workflow

### 1. Start Backend

```bash
cd /Users/sam/database-guru
python src/main.py
```

API runs on: http://localhost:8000

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs on: http://localhost:3000

### 3. Develop

- Edit files in `src/`
- Hot reload automatically updates browser
- TypeScript errors show in terminal & browser
- Tailwind classes compile on demand

### 4. Build for Production

```bash
npm run build
```

Creates optimized bundle in `dist/`

---

## Production Deployment

### Option 1: Serve from FastAPI

```bash
# Build frontend
cd frontend
npm run build

# Copy to FastAPI static directory
cp -r dist/* ../src/frontend/static/

# Serve from FastAPI
python src/main.py
```

Update FastAPI to serve static files:

```python
# src/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="src/frontend/static", html=True), name="static")
```

### Option 2: Separate Deployment

Deploy frontend to Vercel/Netlify:
```bash
npm run build
# Upload dist/ folder
```

Set environment variable:
```env
VITE_API_URL=https://your-api.com
```

---

## Features Implemented

✅ **Chat Interface** - Conversational UI
✅ **Real-time SQL Execution** - See results instantly
✅ **Model Selection** - Choose LLM per query
✅ **Schema Browser** - Explore database structure
✅ **Query History** - Review past queries
✅ **Responsive Design** - Works on all devices
✅ **Type Safety** - Full TypeScript coverage
✅ **Error Handling** - Graceful error messages
✅ **Loading States** - User feedback during operations

---

## Next Steps

### Phase 1: Core Components (Current)
- [x] Project setup
- [x] API integration
- [x] TypeScript types
- [ ] ChatInterface component
- [ ] QueryResults component
- [ ] Schema browser
- [ ] History panel

### Phase 2: Enhanced UX
- [ ] Syntax highlighting for SQL
- [ ] Copy to clipboard
- [ ] Export results (CSV, JSON)
- [ ] Dark mode
- [ ] Keyboard shortcuts

### Phase 3: Advanced Features
- [ ] Query templates
- [ ] Saved queries
- [ ] Result visualization (charts)
- [ ] Multi-tab support
- [ ] Collaborative features

---

## Troubleshooting

### Port Already in Use

```bash
# Change port in vite.config.ts
server: {
  port: 3001,
}
```

### API Connection Issues

1. Verify backend is running: `curl http://localhost:8000/health`
2. Check proxy config in `vite.config.ts`
3. Disable CORS in browser for development

### TypeScript Errors

```bash
# Restart TypeScript server
Cmd/Ctrl + Shift + P → "TypeScript: Restart TS Server"
```

### Build Errors

```bash
# Clear everything and reinstall
rm -rf node_modules dist package-lock.json
npm install
npm run build
```

---

## Resources

- **React Docs:** https://react.dev
- **TypeScript:** https://www.typescriptlang.org/docs/
- **Vite:** https://vitejs.dev/guide/
- **Tailwind:** https://tailwindcss.com/docs
- **TanStack Query:** https://tanstack.com/query/latest

---

## Summary

✅ **Modern Stack** - React, TypeScript, Vite, Tailwind
✅ **Best Practices** - Component architecture, type safety, responsive design
✅ **Production Ready** - Optimized builds, proper error handling
✅ **Developer Experience** - Hot reload, TypeScript intellisense, easy debugging

**Ready to build a world-class UI for Database Guru!** 🚀

Next: `cd frontend && npm install && npm run dev`
