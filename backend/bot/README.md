# HeartBeat.bot - Automated Hockey Analytics Content System

## Overview

HeartBeat.bot is an autonomous agent that periodically gathers NHL information from trusted sources and synthesizes it into actionable content for the HeartBeat Engine platform. Inspired by Perplexity's automated research capabilities, the bot performs web data collection and uses AI to produce human-readable summaries, alerts, and daily league digests.

## Architecture

### Components

- **Data Collection** (`scrapers.py`): Web scraping from NHL.com, team pages, and trusted sources
- **Database Layer** (`db.py`): DuckDB storage for all content types
- **Content Generation** (`generators.py`): LLM-powered article writing using Claude Sonnet 4.5 via OpenRouter
- **Task Scheduling** (`celery_app.py`, `tasks.py`): Celery + Redis for periodic automation
- **API Integration** (`api/routes/news.py`): FastAPI endpoints for frontend access

### Content Types

1. **Transaction Alerts**: Roster moves, trades, signings, waivers (every 30 minutes)
2. **Game Summaries**: Nightly recaps with scores and highlights (1 AM daily)
3. **Team News**: Daily updates for all 32 teams (6 AM daily)
4. **Player Updates**: Performance summaries and stats (6:30 AM daily)
5. **Daily Digest**: AI-generated league-wide article (7 AM daily)

### Data Flow

```
NHL Sources → Scrapers → DuckDB → LLM Generator → API → Frontend
                ↓
         Celery Tasks (scheduled)
```

## Database Schema

### Tables

**transactions**
- id, transaction_date, player_name, player_id, team_from, team_to, transaction_type, description, source_url

**team_news**
- id, team_code, news_date, title, summary, content, source_url, url_hash (deduplication)

**game_summaries**
- game_id, game_date, home_team, away_team, home/away_score, highlights, top_performers (JSON), game_recap

**player_updates**
- id, player_id, player_name, team_code, update_date, summary, recent_stats (JSON), notable_achievements (JSON)

**daily_articles**
- article_date (PK), title, content, summary, metadata (JSON), source_count

Database file: `data/heartbeat_news.duckdb` (~10-50 MB compressed)

## Configuration

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=your_key_here

# Optional (with defaults)
REDIS_URL=redis://localhost:6379/0
HEARTBEAT_NEWS_DB_PATH=data/heartbeat_news.duckdb
HEARTBEAT_ARTICLE_MODEL=anthropic/claude-3.5-sonnet
```

### Celery Schedule

- **Transactions**: Every 30 minutes
- **Game Summaries**: Daily at 1:00 AM EST
- **Team News**: Daily at 6:00 AM EST
- **Player Updates**: Daily at 6:30 AM EST
- **Daily Article**: Daily at 7:00 AM EST

## Setup & Installation

### Prerequisites

1. **Python 3.11+** with HeartBeat venv activated
2. **Redis** - Message broker for Celery
   ```bash
   # macOS
   brew install redis
   
   # Linux
   sudo apt-get install redis-server
   ```

### Install Dependencies

Dependencies are already added to `backend/requirements.txt`:
- celery[redis]>=5.3.0
- redis>=5.0.0
- beautifulsoup4>=4.12.0
- lxml>=4.9.0
- duckdb>=0.10.0

Install with:
```bash
cd backend
pip install -r requirements.txt
```

### Start Services

**Option 1: Use startup script (recommended)**
```bash
bash start_heartbeat.sh
```

This automatically starts:
- Redis server
- FastAPI backend
- Celery worker
- Celery beat scheduler
- Next.js frontend

**Option 2: Manual start**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Backend
cd backend
python main.py

# Terminal 3: Celery Worker
cd backend
celery -A bot.celery_app worker --loglevel=info

# Terminal 4: Celery Beat
cd backend
celery -A bot.celery_app beat --loglevel=info

# Terminal 5: Frontend
cd frontend
npm run dev
```

### Stop Services

```bash
bash stop_heartbeat.sh
```

## API Endpoints

All endpoints are prefixed with `/api/v1/news`:

### GET /daily-article
Get latest AI-generated daily digest
- Query params: `date` (YYYY-MM-DD, optional)
- Response: DailyArticle model

### GET /transactions
Get recent NHL transactions
- Query params: `hours` (default 24, max 168)
- Response: List[Transaction]

### GET /team/{team_code}/news
Get team-specific news
- Path params: `team_code` (MTL, TOR, etc.)
- Query params: `days` (default 7, max 30)
- Response: List[TeamNews]

### GET /games/recent
Get recent game summaries
- Query params: `days` (default 1, max 7)
- Response: List[GameSummary]

### GET /player/{player_id}/update
Get player performance update
- Path params: `player_id` (NHL player ID)
- Response: PlayerUpdate model

### GET /stats
Get content statistics
- Response: NewsStats (counts, latest article date, DB size)

### GET /articles/archive
Get archived daily articles
- Query params: `days` (default 7, max 30)
- Response: List[DailyArticle]

## Testing

### Component Tests

Run the comprehensive test suite:
```bash
cd backend
python bot/test_bot.py
```

Tests validate:
- Database operations
- Web scrapers
- LLM generators
- API models
- Configuration

### Manual Task Testing

Test individual Celery tasks:
```bash
# Test transaction collection
celery -A bot.celery_app call bot.tasks.test_transaction_fetch

# Test game fetching
celery -A bot.celery_app call bot.tasks.test_game_fetch

# Test article generation
celery -A bot.celery_app call bot.tasks.test_article_generation
```

### Verify Running Tasks

```bash
# Check Celery worker status
celery -A bot.celery_app inspect active

# Check scheduled tasks
celery -A bot.celery_app inspect scheduled

# Monitor Redis
redis-cli monitor
```

## Monitoring & Logs

### Log Files

- `backend.log` - FastAPI backend
- `celery_worker.log` - Celery worker tasks
- `celery_beat.log` - Celery beat scheduler
- `frontend.log` - Next.js frontend

### View Logs

```bash
# Real-time backend logs
tail -f backend.log

# Real-time Celery worker
tail -f celery_worker.log

# Real-time Celery beat
tail -f celery_beat.log
```

### Database Inspection

```bash
# Connect to DuckDB
python -c "import duckdb; con = duckdb.connect('data/heartbeat_news.duckdb'); print(con.execute('SELECT COUNT(*) FROM daily_articles').fetchone())"

# Export to Parquet for analysis
python -c "import duckdb; con = duckdb.connect('data/heartbeat_news.duckdb'); con.execute('COPY daily_articles TO \"exports/articles.parquet\" (FORMAT PARQUET)')"
```

## Content Publishing Flow

1. **Automated Collection**: Celery tasks run on schedule, scraping NHL sources
2. **AI Generation**: Claude Sonnet 4.5 synthesizes content into articles
3. **Immediate Publishing**: Content goes live in database immediately
4. **Human Review**: Team reviews content after publication by browsing the app
5. **Optional Editing**: Can update database directly if corrections needed

## Troubleshooting

### Issue: Celery tasks not running
```bash
# Check Redis connection
redis-cli ping  # Should return PONG

# Check Celery worker
celery -A bot.celery_app inspect ping

# Restart Celery
pkill -f celery
celery -A bot.celery_app worker --loglevel=info &
celery -A bot.celery_app beat --loglevel=info &
```

### Issue: Database errors
```bash
# Verify database exists
ls -lh data/heartbeat_news.duckdb

# Reinitialize (will keep existing data)
python -c "from backend.bot import db; db.initialize_database()"
```

### Issue: LLM generation fails
- Check OpenRouter API key: `echo $OPENROUTER_API_KEY`
- Verify model name in config: `anthropic/claude-3.5-sonnet`
- Check fallback templates are working in logs

### Issue: Scrapers failing
- NHL API may change - update endpoints in `config.py`
- Check network connectivity to NHL.com
- Review scraper logs for specific errors

## Development

### Adding New Content Types

1. Add table schema in `db.py` (`initialize_database()`)
2. Create insert/query functions in `db.py`
3. Add scraper function in `scrapers.py`
4. Create Pydantic model in `api/models/news.py`
5. Add API endpoint in `api/routes/news.py`
6. Create Celery task in `tasks.py`
7. Schedule in `celery_app.py`

### Extending Scrapers

Add new sources in `config.py`:
```python
NEWS_SOURCES = {
    'MTL': [
        {
            'name': 'Custom Source',
            'url': 'https://example.com/canadiens',
            'type': 'custom'
        }
    ]
}
```

Update `fetch_team_news()` to handle new source types.

### Customizing Article Generation

Modify prompts in `generators.py`:
- System prompt: Sets tone and style
- User prompt: Provides context and instructions
- Temperature: Controls creativity (0.2-0.5 recommended)
- Max tokens: Limits output length

## Performance

- **Database**: DuckDB with ZSTD compression (~90% size reduction)
- **API Response**: <100ms for most queries
- **Scraping**: ~30s for all 32 teams
- **Article Generation**: ~5-10s with Claude Sonnet 4.5
- **Memory Usage**: ~200-500 MB total

## Security

- All API keys stored in environment variables (never committed)
- Database access restricted to backend only
- Public API endpoints read-only
- No sensitive player/team data exposed
- Rate limiting on external API calls

## Future Enhancements

- [ ] Video highlight integration
- [ ] Sentiment analysis on news
- [ ] Multi-language support
- [ ] Advanced player analytics
- [ ] Push notifications for breaking news
- [ ] Mobile app integration
- [ ] Machine learning for content prioritization

## Support

For issues or questions:
1. Check logs in `backend.log` and `celery_worker.log`
2. Run test suite: `python bot/test_bot.py`
3. Review this README
4. Contact HeartBeat Engine development team

---

**Version**: 1.0.0  
**Last Updated**: October 2025  
**License**: Proprietary - HeartBeat Engine

