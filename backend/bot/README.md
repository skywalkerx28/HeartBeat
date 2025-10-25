# HeartBeat.bot - Automated Hockey Analytics Content System

## Overview

HeartBeat.bot is an autonomous agent that periodically gathers NHL information from trusted sources and synthesizes it into actionable content for the HeartBeat Engine platform. Inspired by Perplexity's automated research capabilities, the bot performs web data collection and uses AI to produce human-readable summaries, alerts, and daily league digests.

## Architecture

### Components

- **Data Collection** (`scrapers.py`): Web scraping from NHL.com, team pages, and trusted sources
- **Database Layer** (`db.py`): GCP PostgreSQL storage for all content types
- **Content Generation** (`generators.py`): LLM-powered article writing using Claude Sonnet 4.5 via OpenRouter
- **Task Scheduling**: Cloud Run Jobs on GCP for periodic automation
- **API Integration** (`api/routes/news.py`): FastAPI endpoints for frontend access

### Content Types

1. **Transaction Alerts**: Roster moves, trades, signings, waivers (every 30 minutes)
2. **Game Summaries**: Nightly recaps with scores and highlights (1 AM daily)
3. **Team News**: Daily updates for all 32 teams (6 AM daily)
4. **Player Updates**: Performance summaries and stats (6:30 AM daily)
5. **Daily Digest**: AI-generated league-wide article (7 AM daily)


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

Database: GCP PostgreSQL instance with optimized indexing and connection pooling

## Configuration

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=your_key_here

# GCP Configuration
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GCP_REGION=us-central1
DB_HOST=your_postgres_host
DB_NAME=heartbeat_news
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Optional (with defaults)
HEARTBEAT_ARTICLE_MODEL=anthropic/claude-3.5-sonnet
CLOUD_RUN_JOB_REGION=us-central1
```

### Cloud Run Jobs Schedule

- **Transactions**: Every 30 minutes
- **Game Summaries**: Daily at 1:00 AM EST
- **Team News**: Daily at 6:00 AM EST
- **Player Updates**: Daily at 6:30 AM EST
- **Daily Article**: Daily at 7:00 AM EST

## Setup & Installation

### Prerequisites

1. **Python 3.11+** with HeartBeat venv activated
2. **Google Cloud SDK** - For Cloud Run Jobs and PostgreSQL management
   ```bash
   # Install Google Cloud SDK
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   gcloud auth application-default login
   ```

### Install Dependencies

Dependencies are already added to `backend/requirements.txt`:
- google-cloud-run>=0.10.0
- google-cloud-sql-connector>=1.4.0
- psycopg2-binary>=2.9.0
- beautifulsoup4>=4.12.0
- lxml>=4.9.0
- sqlalchemy>=2.0.0

Install with:
```bash
cd backend
pip install -r requirements.txt
```

### Deployment

**Option 1: Use deployment script (recommended)**
```bash
bash scripts/gcp/deploy_heartbeat_bot.sh
```

This automatically deploys:
- Cloud Run Jobs for scheduled tasks
- Cloud SQL PostgreSQL database
- FastAPI backend on Cloud Run
- Next.js frontend

**Option 2: Manual deployment**
```bash
# Set GCP project
gcloud config set project your-gcp-project-id

# Deploy Cloud Run Jobs
gcloud run jobs create transaction-scraper \
  --image gcr.io/your-project/heartbeat-bot \
  --region us-central1 \
  --set-env-vars OPENROUTER_API_KEY=your_key_here \
  --schedule "*/30 * * * *"

# Deploy backend
gcloud run deploy heartbeat-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated

# Deploy frontend
cd frontend && npm run build && npm run deploy
```

### Stop Services

```bash
# Stop Cloud Run Jobs
gcloud run jobs delete transaction-scraper
gcloud run jobs delete game-summary-generator
gcloud run jobs delete team-news-scraper
gcloud run jobs delete player-update-generator
gcloud run jobs delete daily-article-generator

# Stop Cloud Run services
gcloud run services delete heartbeat-backend
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

Test individual Cloud Run Jobs:
```bash
# Test transaction collection job
gcloud run jobs execute transaction-scraper --region us-central1 --wait

# Test game fetching job
gcloud run jobs execute game-summary-generator --region us-central1 --wait

# Test article generation job
gcloud run jobs execute daily-article-generator --region us-central1 --wait
```

### Verify Running Tasks

```bash
# Check Cloud Run Jobs status
gcloud run jobs list --region us-central1

# Check job execution history
gcloud run jobs executions list transaction-scraper --region us-central1

# Monitor Cloud Run services
gcloud run services list --region us-central1

# Check Cloud SQL database status
gcloud sql instances list
```

## Monitoring & Logs

### Cloud Logging

All logs are centralized in Google Cloud Logging:
- Cloud Run Jobs execution logs
- Cloud Run service request logs
- Cloud SQL database operation logs
- Application error and performance logs

### View Logs

```bash
# View Cloud Run Job logs
gcloud logging read "resource.type=cloud_run_job" --limit 50

# View Cloud Run service logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# View database operation logs
gcloud logging read "resource.type=cloudsql_database" --limit 50

# Real-time log streaming
gcloud logging tail "resource.type=cloud_run_job"
```

### Database Inspection

```bash
# Connect to Cloud SQL PostgreSQL
gcloud sql connect heartbeat-news --user=your_db_user

# Query database from local environment
psql "postgresql://your_db_user:your_password@your_host:5432/heartbeat_news" -c "SELECT COUNT(*) FROM daily_articles;"

# Export data for analysis
pg_dump "postgresql://your_db_user:your_password@your_host:5432/heartbeat_news" --table=daily_articles --format=custom > articles.backup
```

## Content Publishing Flow

1. **Automated Collection**: Cloud Run Jobs run on schedule, scraping NHL sources
2. **AI Generation**: Claude Sonnet 4.5 synthesizes content into articles
3. **Immediate Publishing**: Content goes live in GCP PostgreSQL immediately
4. **Human Review**: Team reviews content after publication by browsing the app
5. **Optional Editing**: Can update database directly if corrections needed

## Troubleshooting

### Issue: Cloud Run Jobs not executing
```bash
# Check job status
gcloud run jobs list --region us-central1

# Check job execution history
gcloud run jobs executions list transaction-scraper --region us-central1 --limit 5

# Check Cloud Run service account permissions
gcloud run jobs describe transaction-scraper --region us-central1 --format "value(spec.template.spec.template.spec.serviceAccountName)"

# Restart job execution (manual trigger)
gcloud run jobs execute transaction-scraper --region us-central1 --wait
```

### Issue: Database errors
```bash
# Check Cloud SQL instance status
gcloud sql instances describe heartbeat-news

# Check database connectivity
gcloud sql connect heartbeat-news --user=your_db_user

# Verify database schema
psql "postgresql://your_db_user:your_password@your_host:5432/heartbeat_news" -c "\dt"

# Reinitialize database schema (if needed)
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
6. Create Cloud Run Job configuration
7. Deploy job with scheduling via `gcloud run jobs create`

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

- **Database**: GCP PostgreSQL with connection pooling and optimized indexing
- **API Response**: <100ms for most queries with Cloud CDN caching
- **Scraping**: ~30s for all 32 teams with parallel job execution
- **Article Generation**: ~5-10s with Claude Sonnet 4.5
- **Cloud Run Jobs**: Auto-scaling with sub-second cold starts

## Security

- All API keys stored in Google Cloud Secret Manager
- Database access restricted to authorized Cloud Run services
- Public API endpoints read-only with Cloud Armor protection
- No sensitive player/team data exposed
- Rate limiting on external API calls
- VPC-native networking for secure database connections
- Cloud IAM roles for service-to-service authentication

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

