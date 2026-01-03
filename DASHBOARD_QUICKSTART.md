# Dashboard Quick Start - ETL Insights

## ✅ Current Status

**Backend:** Running on http://localhost:8000
**Database:** `repo_src/backend/data/exocortex.db`
**Data:** 32 tasks, 17 interactions, 31 files processed

## 🚀 Viewing Your Dashboard

### 1. Make Sure Backend is Running

```bash
# Check if it's running
curl http://localhost:8000/api/dashboard/health

# If not running, start it:
cd /Users/starsong/Central/Projects/interactives/exocortex
./start_backend.sh
```

### 2. Start Frontend (if not already running)

```bash
cd repo_src/frontend
npm run dev
```

### 3. Open Dashboard

- Go to: http://localhost:5173
- Click: **"Dashboard"** tab in the header
- **Hard refresh** your browser: `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows)

## 📊 What You Should See

### ETL Insights Section (Left Panel)

```
ETL INSIGHTS
┌─────────────────┬─────────────────┬─────────────────┐
│ TASKS EXTRACTED │  INTERACTIONS   │ FILES PROCESSED │
│       32        │       17        │       31        │
└─────────────────┴─────────────────┴─────────────────┘
```

### Insights Section (Right Panel)

**Recent Highlights:**
- "Develop sci-mind basis" [learning, personal-development]
- "Write short story on superworld" [writing, creative]
- "Use larger screen or take breaks" [health, technology]

**Emerging Topics:**
- work: 100%
- resume: 88%
- learning: 75%
- writing: 63%
- personal-development: 50%

**Knowledge Gaps:**
- "Only 32 tasks extracted - process more documents"
- "Only 17 interactions logged - more social context needed"
- "31 files processed - run ETL on full dataset"

## 🔄 Using the Refresh Button

The "Refresh →" button in the Insights section:
1. Clears the backend cache
2. Recomputes metrics from database
3. Updates the dashboard

**To refresh manually:**
```bash
curl -X POST http://localhost:8000/api/dashboard/refresh
```

## 🐛 Troubleshooting

### Dashboard Shows 0 for Everything

**Solution 1: Hard Refresh Browser**
- Mac: `Cmd + Shift + R`
- Windows: `Ctrl + Shift + R`
- Or: Clear browser cache

**Solution 2: Check Backend Database**
```bash
# Verify backend is using correct database
curl http://localhost:8000/api/dashboard/metrics | grep tasks_extracted

# Should show: "tasks_extracted": 32
```

**Solution 3: Restart Backend**
```bash
lsof -ti:8000 | xargs kill -9
cd /Users/starsong/Central/Projects/interactives/exocortex
./start_backend.sh
```

### Backend Won't Start

**Check .env file:**
```bash
cat repo_src/backend/.env | grep DATABASE_URL
# Should show: DATABASE_URL=sqlite:///./repo_src/backend/data/exocortex.db
```

**Check database exists:**
```bash
ls -la repo_src/backend/data/exocortex.db
# Should exist and be ~400KB
```

## 📈 Next Steps

### Process More Files

```bash
# Process 50 more files
python -m repo_src.backend.pipelines.reflect \
  --path datalake/processed/current \
  --max-files 50

# Process all files (takes 2-3 hours)
python -m repo_src.backend.pipelines.reflect \
  --path datalake/processed/current
```

### Query Data Directly

```bash
# Get all tasks
curl http://localhost:8000/api/insights/tasks | jq

# Get task statistics
curl http://localhost:8000/api/insights/tasks/stats | jq

# Get people you've interacted with
curl http://localhost:8000/api/insights/interactions/people | jq

# Get daily metrics
curl http://localhost:8000/api/insights/metrics/daily | jq
```

### Add Custom Dashboard Panels

See: `docs/DASHBOARD_INTEGRATION.md` for extension points

## 🔗 API Endpoints

### Dashboard
- `GET /api/dashboard/metrics` - Get dashboard (cached)
- `GET /api/dashboard/metrics?force_refresh=true` - Force refresh
- `POST /api/dashboard/refresh` - Trigger refresh
- `DELETE /api/dashboard/cache` - Clear cache
- `GET /api/dashboard/health` - Health check

### Insights
- `GET /api/insights/tasks` - List tasks
- `GET /api/insights/tasks/stats` - Task statistics
- `GET /api/insights/interactions` - List interactions
- `GET /api/insights/interactions/people` - Social network
- `GET /api/insights/metrics/daily` - Daily metrics
- `GET /api/insights/metrics/summary` - Summary stats

## 📝 Files Changed

### Configuration
- ✅ `repo_src/backend/.env` - Updated DATABASE_URL to correct path

### Backend
- ✅ `repo_src/backend/pipelines/dashboard_metrics.py` - Pulls real ETL data
- ✅ `repo_src/backend/routers/insights.py` - NEW insights API

### Frontend
- ✅ `repo_src/frontend/src/components/DashboardView.tsx` - Shows ETL metrics

---

**Status:** ✅ Fully operational and serving real data!

**Last Updated:** 2026-01-02 21:50
