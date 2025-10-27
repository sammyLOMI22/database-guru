# 🧙‍♂️ Database Guru - React Frontend

Modern, responsive React + TypeScript frontend for Database Guru.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **Tailwind CSS** - Styling
- **TanStack Query** - Server state management
- **Axios** - HTTP client
- **Lucide React** - Icons

## Features

✅ **Confidence Scoring UI** - Visual badges showing AI prediction confidence (NEW!)
✅ **Chat-style Interface** - Natural conversation flow
✅ **Real-time SQL Execution** - See results instantly
✅ **Auto-Correction Display** - See how queries are fixed
✅ **Model Selection** - Choose from available LLMs
✅ **Schema Browser** - Explore database structure
✅ **Query History** - Review past queries
✅ **Syntax Highlighting** - Pretty SQL display
✅ **Responsive Design** - Mobile & desktop support
✅ **Dark Mode Ready** - Easy to add dark theme

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Frontend runs on: http://localhost:3000
API proxy configured to: http://localhost:8000

### 3. Build for Production

```bash
npm run build
```

Output: `frontend/dist/`

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ChatInterface.tsx       # Main chat UI
│   │   ├── ConfidenceBadge.tsx     # Confidence scoring badge (NEW!)
│   │   ├── CorrectionHistory.tsx   # Auto-correction display
│   │   ├── Header.tsx              # Top navigation
│   │   ├── Sidebar.tsx             # Schema & history
│   │   ├── QueryInput.tsx          # Message input
│   │   ├── MessageList.tsx         # Chat messages
│   │   ├── QueryResults.tsx        # Result tables
│   │   ├── SchemaPanel.tsx         # Database schema
│   │   └── HistoryPanel.tsx        # Query history
│   ├── services/            # API layer
│   │   └── api.ts              # HTTP client
│   ├── types/               # TypeScript types
│   │   └── api.ts              # API types (includes ConfidencePrediction)
│   ├── hooks/               # Custom React hooks
│   │   ├── useQuery.ts         # Query management
│   │   ├── useModels.ts        # Model management
│   │   └── useSchema.ts        # Schema management
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── tests/                   # Component tests (NEW!)
│   └── ConfidenceBadge.test.tsx  # Confidence UI tests (23 tests)
├── public/                  # Static assets
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Key Components

### ConfidenceBadge (NEW!)
Visual confidence scoring with expandable details.

```tsx
<ConfidenceBadge
  confidence={{
    overall: 0.925,
    level: 'HIGH',
    factors: {
      error_type: 0.255,
      schema_match: 0.250,
      historical_success: 0.170,
      correction_complexity: 0.150,
      similarity: 0.100
    },
    reasoning: "This correction has high confidence...",
    recommendation: "EXECUTE - High confidence, likely to succeed"
  }}
  showDetails={true}  // Optional, default: true
/>
```

Features:
- 🎯 Color-coded badges (GREEN/YELLOW/ORANGE/RED)
- 📊 Expandable factor breakdown
- 📈 Progress bars for each factor
- ♿ Fully accessible (ARIA attributes)
- 📱 Responsive design

### CorrectionHistory
Display auto-corrected SQL attempts with confidence scores.

```tsx
<CorrectionHistory
  attempts={[
    { attempt_number: 1, sql: "SELECT * FROM custmers", success: false },
    {
      attempt_number: 2,
      sql: "SELECT * FROM customers",
      success: true,
      confidence_prediction: { /* confidence data */ }
    }
  ]}
  selfCorrected={true}
/>
```

### ChatInterface
Main chat component with message history and input.

```tsx
<ChatInterface />
```

### Sidebar
Schema browser and query history.

```tsx
<Sidebar onClose={() => {}} />
```

### QueryResults
Display SQL results in formatted tables.

```tsx
<QueryResults
  data={results}
  sql={generatedSQL}
  executionTime={42.5}
/>
```

## API Integration

### Using the API Service

```typescript
import { queryAPI, schemaAPI, modelsAPI } from '@/services/api';

// Process query
const response = await queryAPI.processQuery({
  question: "Show me all customers",
  model: "llama3"
});

// Get schema
const schema = await schemaAPI.getSchema();

// List models
const models = await modelsAPI.listModels();
```

### Using React Query

```typescript
import { useQuery } from '@tanstack/react-query';
import { schemaAPI } from '@/services/api';

function SchemaPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['schema'],
    queryFn: () => schemaAPI.getSchema(),
  });

  if (isLoading) return <div>Loading...</div>;

  return <div>{data.table_count} tables</div>;
}
```

## Styling

### Tailwind CSS

```tsx
// Example component
<div className="flex flex-col space-y-4 p-6 bg-white rounded-lg shadow-md">
  <h2 className="text-2xl font-bold text-gray-900">Title</h2>
  <p className="text-gray-600">Description</p>
</div>
```

### Custom Colors

```javascript
// tailwind.config.js
colors: {
  primary: {
    500: '#0ea5e9',
    600: '#0284c7',
  },
}
```

## Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

## Development

### Run with Hot Reload

```bash
npm run dev
```

### Type Check

```bash
npm run build  # TypeScript compilation included
```

### Lint

```bash
npm run lint
```

### Run Tests

```bash
# Run all tests
npm run test

# Run specific test file
npm run test:run -- tests/ConfidenceBadge.test.tsx

# Run with UI
npm run test:ui
```

**Test Coverage:**
- ✅ ConfidenceBadge: 23/23 tests passing (100% coverage)
- Badge display & color coding
- Expandable details & interactivity
- Accessibility features
- Edge cases

## Production Deployment

### Option 1: Serve with FastAPI

Build and copy to FastAPI static directory:

```bash
npm run build
cp -r dist/* ../src/frontend/static/
```

### Option 2: Deploy to Vercel/Netlify

```bash
npm run build
# Deploy dist/ folder
```

### Option 3: Docker

```dockerfile
FROM node:18 as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
```

## Features Roadmap

- [ ] Dark mode toggle
- [ ] Export results (CSV, JSON)
- [ ] Query templates
- [ ] Saved queries
- [ ] Query sharing
- [ ] Keyboard shortcuts
- [ ] Multi-tab support
- [ ] Result visualization (charts)

## Troubleshooting

### API Connection Issues

1. Check API is running: `http://localhost:8000/health`
2. Verify proxy config in `vite.config.ts`
3. Check CORS settings in FastAPI

### Build Errors

```bash
# Clear cache
rm -rf node_modules dist
npm install
npm run build
```

### Type Errors

Ensure TypeScript version matches:
```bash
npm install typescript@^5.3.3
```

## Contributing

1. Follow TypeScript best practices
2. Use functional components with hooks
3. Keep components small and focused
4. Add proper TypeScript types
5. Follow existing code style

## License

MIT
