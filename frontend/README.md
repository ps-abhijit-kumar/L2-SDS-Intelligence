# L2 SDS Intelligence — Frontend Command Center

The enterprise web interface for **L2 SDS Intelligence**, an AI-powered Safety Data Sheet discovery, verification, and intelligence platform.

---

## 🛠️ Technology Stack

* **Core Framework**: React 18 with TypeScript
* **Build System & Dev Server**: Vite 6
* **State Management & Server Cache**: TanStack React Query v5
* **Routing**: React Router v6
* **Design System & Styling**: Tailwind CSS (Dark Enterprise Command Center Theme)
* **Icons**: Lucide React
* **Data Visualization**: Recharts

---

## 🚀 Getting Started

### Prerequisites

* Node.js (v18.0.0 or higher)
* npm (v9.0.0 or higher)

### Installation

```bash
# Navigate to the frontend workspace:
cd frontend

# Install dependencies:
npm install
```

### Environment Configuration

The frontend comes with a pre-configured `.env.example`:

```bash
# Copy template to active .env:
cp .env.example .env
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base API proxy prefix routing to FastAPI backend | `/api` |

### Starting the Development Server

```bash
npm run dev
```

The application will be accessible at `http://127.0.0.1:5173`.

---

## 🏗️ Architecture & Project Structure

```text
frontend/
├── public/                 # Static assets & SVG favicon
├── src/
│   ├── components/         # Reusable UI & Domain Components
│   │   ├── common/         # Atomic primitives (Card, Button, Input, StatusBadge, etc.)
│   │   ├── dashboard/      # KPI Grid, Telemetry Cards, Distribution Charts
│   │   ├── search/         # AI Search Console, Timeline, Result Report Card
│   │   ├── history/        # Audit Tables, Search/Filter Bars, Trace Modal
│   │   ├── review/         # Human-in-the-Loop compliance queue & inspection drawer
│   │   └── trace/          # LangGraph state machine diagram & message inspector
│   ├── hooks/              # Custom React Query hooks (useSdsSearch, useStats, etc.)
│   ├── layouts/            # Application shell (MainLayout, Sidebar, Header)
│   ├── pages/              # Primary route views (Dashboard, Search, History, etc.)
│   ├── services/           # Typed REST API client (api.ts)
│   ├── types/              # TypeScript schema definitions (sds.ts)
│   ├── utils/              # Class merging, date formatters, and status color tokens
│   ├── App.tsx             # Root router & QueryClientProvider
│   ├── index.css           # Tailwind directives, glass utilities, & ambient glows
│   └── main.tsx            # Application entry point
├── package.json            # NPM manifest & dependencies
├── tailwind.config.js      # Custom theme colors, glows, and keyframe animations
├── tsconfig.json           # TypeScript configuration with @/ alias
└── vite.config.ts          # Vite build config with /api -> http://127.0.0.1:8000 proxy
```

---

## 🔌 API Proxy Configuration

During development, Vite automatically proxies all requests matching `/api/*` to the FastAPI backend running on port `8000`:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
```
