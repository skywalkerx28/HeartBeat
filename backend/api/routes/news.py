"""
HeartBeat Engine - News API Routes
Endpoints for automated hockey news and content
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import sys
from pathlib import Path
import logging
import json

# Add bot module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot import db
from api.models.news import (
    Transaction,
    TeamNews,
    GameSummary,
    PlayerUpdate,
    DailyArticle,
    NewsStats
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/news", tags=["news"])


@router.get("/daily-article", response_model=DailyArticle)
async def get_daily_article(date: Optional[str] = None):
    """
    Get daily AI-generated NHL digest
    
    Args:
        date: Optional date in YYYY-MM-DD format (defaults to latest)
    
    Returns:
        Daily article with title, content, and metadata
    """
    try:
        with db.get_connection(read_only=True) as conn:
            article = db.get_daily_article(conn, date)
        
        if not article:
            raise HTTPException(
                status_code=404, 
                detail=f"No article found for date: {date if date else 'latest'}"
            )
        
        return article
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching daily article: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(hours: int = Query(24, le=168, description="Hours to look back (max 168)")):
    """
    Get recent NHL transactions
    
    Args:
        hours: Number of hours to look back (default 24, max 168/7 days)
    
    Returns:
        List of recent transactions
    """
    try:
        with db.get_connection(read_only=True) as conn:
            transactions = db.get_latest_transactions(conn, hours)
        
        return transactions
        
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/team/{team_code}/news", response_model=List[TeamNews])
async def get_team_news(
    team_code: str, 
    days: int = Query(7, le=30, description="Days to look back (max 30)")
):
    """
    Get recent news for specific team
    
    Args:
        team_code: Three-letter team code (e.g., MTL, TOR, BOS)
        days: Number of days to look back (default 7, max 30)
    
    Returns:
        List of team news items
    """
    try:
        # Validate team code
        team_code = team_code.upper()
        from bot.config import NHL_TEAMS
        
        if team_code not in NHL_TEAMS:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid team code: {team_code}. Must be one of: {', '.join(NHL_TEAMS.keys())}"
            )
        
        with db.get_connection(read_only=True) as conn:
            news = db.get_team_news(conn, team_code, days)
        
        return news
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team news for {team_code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/team/{team_code}/tags/news", response_model=List[TeamNews])
async def get_team_tagged_news(
    team_code: str,
    days: int = Query(7, ge=1, le=30)
):
    """
    Get news articles tagged with this team (via news_entities), regardless of
    the article's `team_code`. Useful when multiple teams appear in a story.
    """
    try:
        team_code = team_code.upper()
        with db.get_connection(read_only=True) as conn:
            items = db.get_news_by_team_tag(conn, team_code, days)
        return items
    except Exception as e:
        logger.error(f"Error fetching tagged news for team {team_code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/player/{player_id}/news", response_model=List[TeamNews])
async def get_player_news(
    player_id: Optional[str] = None,
    player_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=60)
):
    """
    Get news articles tagged with this player (by id preferred, name fallback).
    """
    if not player_id and not player_name:
        raise HTTPException(status_code=400, detail="Supply player_id or player_name")
    try:
        with db.get_connection(read_only=True) as conn:
            items = db.get_news_by_player(conn, player_id=player_id, player_name=player_name, days=days)
        return items
    except Exception as e:
        logger.error(f"Error fetching news for player: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/player/{player_id}/transactions", response_model=List[Transaction])
async def get_player_transactions(
    player_id: Optional[str] = None,
    player_name: Optional[str] = None,
    days: int = Query(30, ge=1, le=730)  # Allow up to 2 years for career history
):
    """Get transactions for a player (id preferred, name fallback)."""
    if not player_id and not player_name:
        raise HTTPException(status_code=400, detail="Supply player_id or player_name")
    try:
        with db.get_connection(read_only=True) as conn:
            items = db.get_transactions_for_player(conn, player_id=player_id, player_name=player_name, days=days)
        return items
    except Exception as e:
        logger.error(f"Error fetching player transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/team/{team_code}/transactions", response_model=List[Transaction])
async def get_team_transactions(team_code: str, days: int = Query(14, ge=1, le=60)):
    """Get transactions involving the team (from or to)."""
    try:
        team_code = team_code.upper()
        with db.get_connection(read_only=True) as conn:
            items = db.get_transactions_for_team(conn, team_code=team_code, days=days)
        return items
    except Exception as e:
        logger.error(f"Error fetching team transactions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/games/recent", response_model=List[GameSummary])
async def get_recent_games(days: int = Query(1, le=7, description="Days to look back (max 7)")):
    """
    Get recent game summaries
    
    Args:
        days: Number of days to look back (default 1, max 7)
    
    Returns:
        List of game summaries with scores and highlights
    """
    try:
        with db.get_connection(read_only=True) as conn:
            games = db.get_game_summaries(conn, days)
        
        return games
        
    except Exception as e:
        logger.error(f"Error fetching game summaries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/player/{player_id}/update", response_model=PlayerUpdate)
async def get_player_update(player_id: str):
    """
    Get latest performance update for player
    
    Args:
        player_id: NHL player ID
    
    Returns:
        Latest player performance update
    """
    try:
        with db.get_connection(read_only=True) as conn:
            update = db.get_player_update(conn, player_id)
        
        if not update:
            raise HTTPException(
                status_code=404, 
                detail=f"No update found for player: {player_id}"
            )
        
        return update
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching player update for {player_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/synthesized-articles", response_model=List[TeamNews])
async def get_synthesized_articles(
    team_code: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=30, description="Days to look back")
):
    """
    Get AI-synthesized multi-source news articles
    
    Args:
        team_code: Optional filter by team (e.g., MTL, TOR)
        days: Days to look back (default 7)
    
    Returns:
        List of synthesized news articles with images and source citations
    """
    try:
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).date()
        
        with db.get_connection(read_only=True) as conn:
            if team_code:
                results = conn.execute("""
                    SELECT id, team_code, news_date as date, title, summary, content, source_url, image_url, metadata, created_at
                    FROM team_news
                    WHERE team_code = ? AND news_date >= ?
                    ORDER BY created_at DESC
                """, [team_code, cutoff_date]).fetchall()
            else:
                results = conn.execute("""
                    SELECT id, team_code, news_date as date, title, summary, content, source_url, image_url, metadata, created_at
                    FROM team_news
                    WHERE news_date >= ?
                    ORDER BY created_at DESC
                """, [cutoff_date]).fetchall()
            
            articles = []
            for row in results:
                # Parse metadata JSON
                metadata = json.loads(row[8]) if row[8] else None
                
                articles.append(TeamNews(
                    id=row[0],
                    team_code=row[1],
                    date=row[2],
                    title=row[3],
                    summary=row[4],
                    content=row[5],
                    source_url=row[6],
                    image_url=row[7],
                    metadata=metadata,
                    created_at=row[9]
                ))
            
            return articles
            
    except Exception as e:
        logger.error(f"Error fetching synthesized articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=NewsStats)
async def get_news_stats():
    """
    Get news content statistics
    
    Returns:
        Statistics about available news content
    """
    try:
        with db.get_connection(read_only=True) as conn:
            # Get counts
            transactions_count = len(db.get_latest_transactions(conn, 24))
            games_count = len(db.get_game_summaries(conn, 1))
            
            # Get latest article date
            latest_article = db.get_daily_article(conn)
            latest_article_date = latest_article.get('date') if latest_article else None
            
            # Count team news (approximate)
            team_news_result = conn.execute("""
                SELECT COUNT(*) FROM team_news 
                WHERE created_at >= ?
            """, [datetime.now() - timedelta(hours=24)]).fetchone()
            
            team_news_count = team_news_result[0] if team_news_result else 0
            
            # Database size
            from pathlib import Path
            db_path = Path(db.DB_PATH)
            db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0
        
        return NewsStats(
            transactions_24h=transactions_count,
            games_today=games_count,
            team_news_count=team_news_count,
            latest_article_date=latest_article_date,
            database_size_mb=round(db_size_mb, 2)
        )
        
    except Exception as e:
        logger.error(f"Error fetching news stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/articles/archive", response_model=List[DailyArticle])
async def get_articles_archive(days: int = Query(7, le=30, description="Days of archive to retrieve")):
    """
    Get archived daily articles
    
    Args:
        days: Number of days to look back (default 7, max 30)
    
    Returns:
        List of daily articles
    """
    try:
        cutoff = datetime.now() - timedelta(days=days)
        
        with db.get_connection(read_only=True) as conn:
            results = conn.execute("""
                SELECT article_date as date, title, content, summary, metadata, source_count, created_at
                FROM daily_articles
                WHERE article_date >= ?
                ORDER BY article_date DESC
            """, [cutoff.date()]).fetchall()
            
            import json
            articles = []
            for row in results:
                articles.append({
                    'date': row[0],
                    'title': row[1],
                    'content': row[2],
                    'summary': row[3],
                    'metadata': json.loads(row[4]) if row[4] else {},
                    'source_count': row[5],
                    'created_at': row[6]
                })
        
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching article archive: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/injuries")
async def get_injury_reports(
    team_code: Optional[str] = Query(None, description="Filter by team code (e.g., MTL, TOR)"),
    active_only: bool = Query(True, description="Only return active injuries (not cleared/healthy)")
):
    """
    Get NHL injury reports
    
    Returns injury reports from ESPN and PuckPedia, cross-referenced and deduplicated.
    Injuries are stored separately from team news.
    """
    try:
        from backend.bot import db
        
        with db.get_connection(read_only=True) as conn:
            injuries = db.get_team_injuries(conn, team_code=team_code, active_only=active_only)
        
        # Parse sources JSON if present
        for injury in injuries:
            if injury.get('sources') and isinstance(injury['sources'], str):
                import json
                try:
                    injury['sources'] = json.loads(injury['sources'])
                except:
                    injury['sources'] = []
        
        return {
            'success': True,
            'total': len(injuries),
            'team_filter': team_code,
            'active_only': active_only,
            'injuries': injuries
        }
        
    except Exception as e:
        logger.error(f"Error fetching injury reports: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

