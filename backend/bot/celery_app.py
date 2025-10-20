"""
HeartBeat.bot Celery Application
Task scheduling and orchestration for automated content generation
"""

from celery import Celery
from celery.schedules import crontab
from .config import CeleryConfig

# Create Celery app
app = Celery('heartbeat_bot')

# Load configuration
app.config_from_object(CeleryConfig)

# Define periodic task schedule
app.conf.beat_schedule = {
    'collect-transactions': {
        'task': 'bot.tasks.collect_transactions',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
        'options': {'expires': 1500}  # Expire after 25 minutes
    },
    'collect-injury-reports': {
        'task': 'bot.tasks.collect_injury_reports',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        'options': {'expires': 18000}
    },
    'collect-game-summaries': {
        'task': 'bot.tasks.collect_game_summaries',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily (EST)
        'options': {'expires': 3600}
    },
    'collect-team-news': {
        'task': 'bot.tasks.collect_team_news',
        'schedule': crontab(hour=6, minute=0),  # 6 AM daily (EST)
        'options': {'expires': 3600}
    },
    'collect-player-updates': {
        'task': 'bot.tasks.collect_player_updates',
        'schedule': crontab(hour=6, minute=30),  # 6:30 AM daily (EST)
        'options': {'expires': 3600}
    },
    'generate-daily-article': {
        'task': 'bot.tasks.generate_daily_article',
        'schedule': crontab(hour=7, minute=0),  # 7 AM daily (EST)
        'options': {'expires': 3600}
    },
    'aggregate-and-synthesize-news': {
        'task': 'bot.tasks.aggregate_and_synthesize_news',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
        'options': {'expires': 18000}  # Expire after 5 hours
    },
    # Ontology daily refresh (BigQuery/GCS pipelines + embeddings)
    'daily-ontology-refresh': {
        'task': 'ontology.daily_refresh',
        'schedule': crontab(hour=4, minute=0),  # 4 AM UTC daily
        'options': {'expires': 3600}
    },
}

# Additional Celery configuration
app.conf.update(
    task_routes={
        'bot.tasks.*': {'queue': 'heartbeat_bot'}
    },
    task_default_queue='heartbeat_bot',
    task_default_exchange='heartbeat_bot',
    task_default_routing_key='heartbeat.bot',
)

# Import tasks module to register all @app.task decorated functions
# This MUST be after all app configuration is complete
from . import tasks  # noqa: F401
# Ensure ontology tasks are registered
import orchestrator.tasks.ontology_refresh  # noqa: F401

if __name__ == '__main__':
    app.start()
