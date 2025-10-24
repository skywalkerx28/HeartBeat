"""
HeartBeat.bot Tasks
Synchronous task functions for automated content collection and generation.
These are executed inline by `bot.runner` and scheduled via Cloud Run Jobs.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio

from . import scrapers, db
from .generators import get_generator
from .config import NHL_TEAMS, BOT_CONFIG
from . import tagging
from .news_aggregator import (
    cluster_articles,
    prepare_synthesis_context,
    select_article_category
)

logger = logging.getLogger(__name__)


def collect_injury_reports():
    """
    Fetch and store NHL injury reports from ESPN
    Runs every 6 hours
    """
    try:
        logger.info("Starting injury report collection task")
        
        injuries = scrapers.scrape_injury_reports()
        
        if not injuries:
            logger.info("No injury reports found")
            return {'status': 'success', 'count': 0}
        
        # Store injury reports in dedicated injuries table
        stored_count = 0
        with db.get_connection() as conn:
            for injury in injuries:
                try:
                    # Prepare injury data for database
                    injury_data = {
                        'player_name': injury.get('player_name'),
                        'player_id': injury.get('player_id'),
                        'team_code': injury.get('team_code') or 'NHL',
                        'position': injury.get('position'),
                        'injury_type': injury.get('injury_description'),
                        'injury_status': injury.get('injury_status'),
                        'injury_description': injury.get('description'),
                        'return_estimate': injury.get('return_estimate'),
                        'placed_on_ir_date': injury.get('date'),
                        'source_url': injury.get('source_url'),
                        'verified': injury.get('verified', False),
                        'sources': injury.get('sources', [])
                    }
                    
                    result = db.insert_injury_report(conn, injury_data)
                    if result:
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing injury report: {e}")
        
        logger.info(f"Injury reports collected: {stored_count} stored")
        return {'status': 'success', 'count': stored_count}
        
    except Exception as e:
        logger.error(f"Error in collect_injury_reports: {e}")
        raise


def collect_transactions():
    """
    Fetch and store new NHL transactions
    Runs every 30 minutes
    Scrapes: NHL.com, DailyFaceoff, and rotating team sites
    """
    try:
        logger.info("Starting transaction collection task - multi-source scraping")
        
        # This will scrape NHL.com, DailyFaceoff, and batch of team sites
        transactions = scrapers.fetch_transactions()
        
        if not transactions:
            logger.info("No new transactions found in this scrape cycle")
            return {'status': 'success', 'count': 0, 'note': 'No transactions this cycle'}
        
        # Store transactions in database (with deduplication)
        stored_count = 0
        skipped_count = 0
        
        with db.get_connection() as conn:
            for transaction in transactions:
                try:
                    result = db.insert_transaction(conn, transaction)
                    if result:
                        stored_count += 1
                        logger.info(f"New transaction: [{transaction['type']}] {transaction['player_name']}")
                    else:
                        skipped_count += 1
                except Exception as e:
                    logger.error(f"Error storing transaction: {e}")
        
        logger.info(f"Transaction collection complete: {stored_count} new, {skipped_count} duplicates")
        return {
            'status': 'success', 
            'new_count': stored_count,
            'duplicate_count': skipped_count,
            'total_scraped': len(transactions)
        }
        
    except Exception as exc:
        logger.error(f"Transaction collection failed: {exc}")
        raise


def collect_game_summaries():
    """
    Fetch and store yesterday's game results
    Runs at 1 AM daily (after all games complete)
    """
    try:
        logger.info("Starting game summaries collection task")
        
        # Get yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        games = scrapers.fetch_game_results(yesterday)
        
        if not games:
            logger.info(f"No games found for {yesterday}")
            return {'status': 'success', 'count': 0, 'date': yesterday}
        
        # Store game summaries
        stored_count = 0
        with db.get_connection() as conn:
            for game in games:
                try:
                    db.insert_game_summary(conn, game)
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Error storing game summary {game.get('game_id')}: {e}")
        
        logger.info(f"Collected {stored_count} game summaries for {yesterday}")
        return {'status': 'success', 'count': stored_count, 'date': yesterday}
        
    except Exception as exc:
        logger.error(f"Game summaries collection failed: {exc}")
        raise


def collect_team_news():
    """
    Fetch and store team-specific news for all 32 teams
    Runs at 6 AM daily
    """
    try:
        logger.info("Starting team news collection task")
        
        total_stored = 0
        teams_processed = 0
        
        with db.get_connection() as conn:
            for team_code in NHL_TEAMS.keys():
                try:
                    news_items = scrapers.fetch_team_news(team_code)
                    
                    for news in news_items:
                        try:
                            result = db.insert_team_news(conn, news)
                            if result:
                                total_stored += 1
                        except Exception as e:
                            logger.error(f"Error storing news for {team_code}: {e}")
                    
                    teams_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error fetching news for team {team_code}: {e}")
        
        logger.info(f"Collected {total_stored} news items from {teams_processed} teams")
        return {
            'status': 'success', 
            'news_count': total_stored, 
            'teams_processed': teams_processed
        }
        
    except Exception as exc:
        logger.error(f"Team news collection failed: {exc}")
        raise


def collect_player_updates():
    """
    Update player performance summaries for active players
    Runs at 6:30 AM daily
    """
    try:
        logger.info("Starting player updates collection task")
        
        # For MVP, we'll focus on players from recent games
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Get player IDs from recent games
        player_ids = set()
        
        with db.get_connection() as conn:
            # Get recent game summaries to identify active players
            games = db.get_game_summaries(conn, days=1)
            
            for game in games:
                # Extract player IDs from top performers
                for performer in game.get('top_performers', []):
                    # Note: We'd need player IDs from the API, for now skip
                    pass
        
        # For MVP, we'll skip detailed player updates
        # In production, this would query NHL API for each active player
        
        logger.info("Player updates task completed (MVP - placeholder)")
        return {'status': 'success', 'count': 0, 'note': 'MVP placeholder'}
        
    except Exception as exc:
        logger.error(f"Player updates collection failed: {exc}")
        raise


def aggregate_and_synthesize_news():
    """
    Scrape news articles, cluster related ones, and synthesize with LLM
    Runs every 6 hours to keep news fresh
    """
    try:
        logger.info("Starting news aggregation and synthesis task")
        
        # 1. Scrape articles from all sources
        logger.info("Step 1: Scraping articles from multiple sources...")
        all_articles = scrapers.scrape_news_articles(limit_per_source=10)
        
        if not all_articles:
            logger.info("No articles found to process")
            return {'status': 'success', 'articles_synthesized': 0}
        
        logger.info(f"Scraped {len(all_articles)} articles total")
        
        # Filter OUT transactions AND articles with insufficient content
        # Keep injury articles - they're newsworthy content!
        # Injury transactions (IR placements) are handled separately
        transaction_keywords = ['transaction', 'trade', 'signing', 'waiver', 'recall', 'loan', 'assign']
        
        articles = []
        filtered_out = 0
        
        for article in all_articles:
            title_lower = article.get('title', '').lower()
            content = article.get('content', '')
            summary = article.get('summary', '')
            content_lower = (content + summary).lower()
            
            # Skip if it's primarily about transactions (NOT injuries - those are news)
            is_transaction = any(kw in title_lower for kw in transaction_keywords)
            
            if is_transaction:
                filtered_out += 1
                logger.debug(f"Filtered: {article.get('title')} (transaction)")
                continue
            
            # Skip if article doesn't have enough content (just headlines with no body)
            # Require at least 150 characters of actual content
            total_content_length = len(content) + len(summary)
            if total_content_length < 150:
                filtered_out += 1
                logger.debug(f"Filtered: {article.get('title')} (insufficient content: {total_content_length} chars)")
                continue
            
            articles.append(article)
        
        logger.info(f"Filtered to {len(articles)} quality news articles (excluded {filtered_out} items)")
        
        if not articles:
            logger.info("No news articles to synthesize after filtering")
            return {'status': 'success', 'articles_synthesized': 0}
        
        # 2. Cluster related articles
        logger.info("Step 2: Clustering related articles...")
        clusters = cluster_articles(articles, similarity_threshold=0.5)
        
        logger.info(f"Created {len(clusters)} article clusters")
        
        # 3. Synthesize each cluster with LLM
        logger.info("Step 3: Synthesizing articles with LLM...")
        synthesized_count = 0
        
        generator = get_generator()
        
        for cluster in clusters:
            try:
                # Prepare synthesis context
                context = prepare_synthesis_context(cluster)
                
                # ALL articles get processed by LLM to make content unique to HeartBeat
                # Single-source: LLM rewrites in our voice and style
                # Multi-source: LLM synthesizes and cross-validates multiple sources
                
                logger.info(f"Synthesizing article with {context['source_count']} source(s)")
                
                # Synthesize with LLM (works for both single and multi-source)
                async def synthesize():
                    return await generator.synthesize_multi_source_article(context)
                
                synthesized_article = asyncio.run(synthesize())
                
                # Validate LLM response - reject if it's an apology/refusal or generic title
                article_content = synthesized_article.get('content', '')
                article_title = synthesized_article.get('title', '').lower()
                
                # Reject apology responses
                if ('apologize' in article_content.lower()[:100] or 
                    'cannot' in article_content.lower()[:100] or
                    'would need' in article_content.lower()[:100]):
                    logger.warning(f"Rejected LLM response (insufficient source content): {synthesized_article['title']}")
                    continue
                
                # Reject generic/placeholder titles
                if ('general update' in article_title or 
                    'performance update' in article_title or
                    article_title.strip() in ['update', 'news', 'article']):
                    logger.warning(f"Rejected generic title: {synthesized_article['title']}")
                    continue
                
                # Store in team_news table
                with db.get_connection() as conn:
                    # Use first team mentioned, or 'NHL' for league-wide
                    team_code = context['teams'][0] if context['teams'] else 'NHL'
                    
                    # Build source metadata for dynamic citations
                    sources_list = list(set([article.get('source', 'unknown') for article in cluster]))
                    source_urls = [article.get('url') for article in cluster if article.get('url')]
                    
                    article_data = {
                        'team_code': team_code,
                        'date': datetime.now().date(),
                        'title': synthesized_article['title'],
                        'summary': synthesized_article['summary'],
                        'content': synthesized_article['content'],
                        'source_url': synthesized_article['source_urls'][0] if synthesized_article['source_urls'] else None,
                        'image_url': synthesized_article.get('image_url'),
                        'metadata': {
                            'sources': sources_list,
                            'source_count': len(sources_list),
                            'source_urls': source_urls,
                            'is_multi_source': len(sources_list) > 1
                        }
                    }
                    
                    news_id = db.insert_team_news(conn, article_data)
                
                # Tag entities (teams/players) for cross-linking
                try:
                    tagging.tag_news_item(
                        news_id,
                        synthesized_article.get('title', ''),
                        synthesized_article.get('summary', ''),
                        synthesized_article.get('content', '')
                    )
                except Exception as e:
                    logger.warning(f"Tagging failed for news {news_id}: {e}")
                
                synthesized_count += 1
                source_label = 'multi-source' if len(sources_list) > 1 else 'single-source'
                logger.info(f"✓ Synthesized {source_label}: {synthesized_article['title']}")
                
            except Exception as e:
                logger.error(f"Error processing cluster: {e}")
                continue
        
        logger.info(f"News aggregation complete: {synthesized_count} articles synthesized")
        
        return {
            'status': 'success',
            'articles_scraped': len(articles),
            'clusters_created': len(clusters),
            'articles_synthesized': synthesized_count
        }
        
    except Exception as exc:
        logger.error(f"Error in news aggregation task: {exc}")
        raise


def generate_daily_article():
    """
    Generate AI-powered daily NHL digest article
    Runs at 7 AM daily (after all collection tasks complete)
    """
    try:
        logger.info("Starting daily article generation task")
        
        # Get recent content for article generation
        with db.get_connection() as conn:
            content_data = db.get_recent_content(conn, hours=24)
        
        # Check if we have any content
        if not any([
            content_data.get('transactions'),
            content_data.get('games'),
            content_data.get('team_news')
        ]):
            logger.warning("No content available for article generation")
            return {'status': 'skipped', 'reason': 'no_content'}
        
        # Generate article using LLM
        generator = get_generator()
        
        # Run async function in sync context
        article_data = asyncio.run(generator.generate_daily_article(content_data))
        
        # Store article (publishes immediately)
        with db.get_connection() as conn:
            db.insert_daily_article(conn, article_data)
        
        logger.info(f"Daily article generated and published: {article_data.get('title')}")
        return {
            'status': 'success',
            'title': article_data.get('title'),
            'date': str(article_data.get('date')),
            'source_count': article_data.get('source_count', 0)
        }
        
    except Exception as exc:
        logger.error(f"Daily article generation failed: {exc}")
        raise


# Manual trigger helpers for testing
def test_transaction_fetch():
    """Manual test task for transaction fetching"""
    return collect_transactions()


def test_game_fetch(date_str: str = None):
    """Manual test task for game fetching"""
    if not date_str:
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    games = scrapers.fetch_game_results(date_str)
    
    with db.get_connection() as conn:
        for game in games:
            db.insert_game_summary(conn, game)
    
    return {'status': 'success', 'games': len(games), 'date': date_str}


def test_article_generation():
    """Manual test task for article generation"""
    return generate_daily_article()


def scrape_player_contract(player_slug: str, output_dir: str = 'data/contracts'):
    """
    Scrape player contract data from CapWages and export to CSV
    
    Args:
        player_slug: Player URL slug (e.g., 'sidney-crosby')
        output_dir: Directory to save CSV files
    
    Returns:
        Dict with scrape results and CSV file paths
    """
    try:
        from .contract_exporter import export_to_database_and_csv
        
        logger.info(f"Starting contract scrape for player: {player_slug}")
        
        result = export_to_database_and_csv(player_slug, output_dir)
        
        if result.get('success'):
            logger.info(f"Contract scrape completed successfully for {result.get('player_name')}")
            logger.info(f"Database: {len(result.get('contract_ids', []))} contracts, "
                       f"{len(result.get('stat_ids', []))} stats stored")
            logger.info(f"CSV files: {list(result.get('csv_files', {}).values())}")
            
            return {
                'status': 'success',
                'player_name': result.get('player_name'),
                'player_slug': player_slug,
                'contracts_stored': len(result.get('contract_ids', [])),
                'stats_stored': len(result.get('stat_ids', [])),
                'csv_files': result.get('csv_files', {})
            }
        else:
            logger.error(f"Contract scrape failed for {player_slug}: {result.get('error')}")
            return {
                'status': 'failed',
                'player_slug': player_slug,
                'error': result.get('error')
            }
    
    except Exception as exc:
        logger.error(f"Error in contract scraping task for {player_slug}: {exc}")
        raise


def scrape_multiple_player_contracts(player_slugs: list, output_dir: str = 'data/contracts'):
    """
    Scrape multiple player contracts in batch
    
    Args:
        player_slugs: List of player URL slugs
        output_dir: Directory to save CSV files
    
    Returns:
        Summary of batch scrape results
    """
    results = []
    
    for player_slug in player_slugs:
        try:
            result = scrape_player_contract(player_slug, output_dir)
            results.append(result)
        except Exception as e:
            logger.error(f"Error scraping {player_slug}: {e}")
            results.append({
                'status': 'error',
                'player_slug': player_slug,
                'error': str(e)
            })
    
    success_count = sum(1 for r in results if r.get('status') == 'success')
    
    return {
        'total_players': len(player_slugs),
        'successful': success_count,
        'failed': len(player_slugs) - success_count,
        'results': results
    }

