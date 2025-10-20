# HeartBeat.bot Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat/backend
source ../venv/bin/activate
pip install -r requirements.txt
```

**What this installs:**
- celery[redis] - Task scheduling
- redis - Message broker (already installed ✅)
- beautifulsoup4, lxml - Web scraping
- duckdb - Database

### Step 2: Verify Configuration

Ensure your `.env` file has:
```bash
OPENROUTER_API_KEY=your_key_here
```

Check Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

If Redis is not running:
```bash
redis-server --daemonize yes
```

### Step 3: Start HeartBeat Engine

```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
bash start_heartbeat.sh
```

This automatically starts:
- ✅ Redis server
- ✅ FastAPI backend (port 8000)
- ✅ Celery worker
- ✅ Celery beat scheduler
- ✅ Next.js frontend (port 3000)

---

## 🧪 Test the System

### Option 1: Run Full Test Suite
```bash
cd backend
python bot/test_bot.py
```

Expected: All 5 tests pass ✅

### Option 2: Test API Endpoints

```bash
# Get news stats
curl http://localhost:8000/api/v1/news/stats

# Get latest daily article (may be empty initially)
curl http://localhost:8000/api/v1/news/daily-article

# Get recent transactions
curl http://localhost:8000/api/v1/news/transactions?hours=24

# Get team news
curl http://localhost:8000/api/v1/news/team/MTL/news
```

### Option 3: Manual Task Trigger

```bash
cd backend

# Fetch recent games (uses yesterday's date)
celery -A bot.celery_app call bot.tasks.test_game_fetch

# Generate daily article
celery -A bot.celery_app call bot.tasks.test_article_generation
```

---

## 📊 Monitor Content Generation

### View Celery Logs
```bash
# Worker logs (task execution)
tail -f celery_worker.log

# Beat logs (scheduling)
tail -f celery_beat.log
```

### Check Scheduled Tasks
```bash
cd backend
celery -A bot.celery_app inspect scheduled
```

### Check Active Tasks
```bash
cd backend
celery -A bot.celery_app inspect active
```

### Query Database
```bash
# Count articles
python -c "import duckdb; con = duckdb.connect('data/heartbeat_news.duckdb'); print('Articles:', con.execute('SELECT COUNT(*) FROM daily_articles').fetchone()[0])"

# Count games
python -c "import duckdb; con = duckdb.connect('data/heartbeat_news.duckdb'); print('Games:', con.execute('SELECT COUNT(*) FROM game_summaries').fetchone()[0])"

# Count transactions
python -c "import duckdb; con = duckdb.connect('data/heartbeat_news.duckdb'); print('Transactions:', con.execute('SELECT COUNT(*) FROM transactions').fetchone()[0])"
```

---

## 📅 Content Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| **Transactions** | Every 30 min | NHL roster moves, trades, signings |
| **Game Summaries** | 1:00 AM daily | Yesterday's game recaps |
| **Team News** | 6:00 AM daily | Updates for all 32 teams |
| **Player Updates** | 6:30 AM daily | Performance summaries |
| **Daily Digest** | 7:00 AM daily | AI-generated article (Claude Sonnet 4.5) |

---

## 🔗 API Endpoints

Base URL: `http://localhost:8000/api/v1/news`

| Endpoint | Description |
|----------|-------------|
| `GET /daily-article` | Latest AI digest |
| `GET /daily-article?date=2025-10-16` | Specific date |
| `GET /transactions?hours=24` | Recent transactions |
| `GET /team/{code}/news?days=7` | Team news (MTL, TOR, etc.) |
| `GET /games/recent?days=1` | Recent games |
| `GET /player/{id}/update` | Player performance |
| `GET /stats` | Content statistics |
| `GET /articles/archive?days=7` | Article history |

**Interactive Docs**: http://localhost:8000/docs

---

## 🛠 Troubleshooting

### Issue: "Import could not be resolved"
This is a linter warning, not an error. The import works at runtime because we add the path dynamically.

### Issue: Celery tasks not running
```bash
# Check Redis
redis-cli ping

# Check Celery worker
celery -A bot.celery_app inspect ping

# Restart Celery
pkill -f celery
cd backend
celery -A bot.celery_app worker -l info &
celery -A bot.celery_app beat -l info &
```

### Issue: Database not found
```bash
# Initialize database
python -c "from backend.bot import db; db.initialize_database()"
```

### Issue: LLM generation fails
- Verify: `echo $OPENROUTER_API_KEY`
- Check model in `backend/bot/config.py` (should be `anthropic/claude-3.5-sonnet`)
- Review fallback templates in logs

---

## 📂 Key Files

### Configuration
- `backend/bot/config.py` - NHL teams, sources, settings
- `backend/requirements.txt` - Dependencies

### Core System
- `backend/bot/db.py` - Database operations
- `backend/bot/scrapers.py` - Data collection
- `backend/bot/generators.py` - AI content generation
- `backend/bot/tasks.py` - Scheduled tasks

### API
- `backend/api/models/news.py` - Data models
- `backend/api/routes/news.py` - Endpoints

### Database
- `data/heartbeat_news.duckdb` - Content storage

---

## 🎯 What Happens First Run?

1. **Database Creation**: `data/heartbeat_news.duckdb` created automatically
2. **First Scrape**: Celery tasks run immediately, then on schedule
3. **First Article**: Generated at 7 AM next morning (or trigger manually)
4. **Content Available**: Via API immediately after tasks complete

---

## 📖 Full Documentation

- **System Documentation**: `backend/bot/README.md`
- **Implementation Summary**: `HEARTBEAT_BOT_IMPLEMENTATION_COMPLETE.md`
- **This Quick Start**: `HEARTBEAT_BOT_QUICKSTART.md`

---

## 🚦 Status Check

**System Ready When:**
- ✅ Redis responds to `redis-cli ping`
- ✅ Backend returns 200 from `/api/v1/health`
- ✅ News stats endpoint works: `/api/v1/news/stats`
- ✅ Celery worker responds: `celery -A bot.celery_app inspect ping`

**Test Command:**
```bash
# All-in-one status check
redis-cli ping && \
curl -s http://localhost:8000/api/v1/health | jq && \
curl -s http://localhost:8000/api/v1/news/stats | jq && \
cd backend && celery -A bot.celery_app inspect ping
```

---

## ⏹ Stop the System

```bash
bash stop_heartbeat.sh
```

This stops:
- Backend server
- Frontend server
- Celery worker
- Celery beat
- (Redis continues running - stop manually if needed)

---

**Ready to Go!** 🎉

Your HeartBeat Engine now has an autonomous content generation system. It will automatically collect NHL data, generate AI-powered articles, and serve fresh content via the API every day.

Questions? Check the full docs in `backend/bot/README.md`

