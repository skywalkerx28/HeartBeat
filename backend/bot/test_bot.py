#!/usr/bin/env python3
"""
HeartBeat.bot Test Script
Validates all components of the automated content generation system
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.bot import db, scrapers
from backend.bot.generators import get_generator
from backend.bot.config import NHL_TEAMS

print("=" * 70)
print("HEARTBEAT.BOT - COMPONENT TESTING")
print("=" * 70)
print()


def test_database():
    """Test DuckDB database operations"""
    print("1. Testing Database Layer...")
    print("-" * 70)
    
    try:
        # Test connection
        with db.get_connection() as conn:
            print("  ✓ Database connection established")
            
            # Test transaction insert
            test_transaction = {
                'date': datetime.now().date(),
                'player_name': 'Test Player',
                'player_id': '8478463',
                'team_from': 'MTL',
                'team_to': 'TOR',
                'type': 'trade',
                'description': 'Test trade transaction',
                'source_url': 'https://nhl.com/test'
            }
            
            trans_id = db.insert_transaction(conn, test_transaction)
            print(f"  ✓ Transaction inserted (ID: {trans_id})")
            
            # Test team news insert
            test_news = {
                'team_code': 'MTL',
                'date': datetime.now().date(),
                'title': 'Test News Item',
                'summary': 'This is a test news summary',
                'content': None,
                'source_url': 'https://nhl.com/canadiens/test'
            }
            
            news_id = db.insert_team_news(conn, test_news)
            print(f"  ✓ Team news inserted (ID: {news_id})")
            
            # Test game summary insert
            test_game = {
                'game_id': '2024020001',
                'date': datetime.now().date(),
                'home_team': 'MTL',
                'away_team': 'TOR',
                'home_score': 3,
                'away_score': 2,
                'highlights': 'MTL wins 3-2',
                'top_performers': [{'player': 'N. Suzuki', 'goals': 2}],
                'period_summary': {},
                'game_recap': 'Exciting game'
            }
            
            game_id = db.insert_game_summary(conn, test_game)
            print(f"  ✓ Game summary inserted (ID: {game_id})")
            
            # Test retrieval
            transactions = db.get_latest_transactions(conn, hours=1)
            print(f"  ✓ Retrieved {len(transactions)} recent transactions")
            
            team_news = db.get_team_news(conn, 'MTL', days=1)
            print(f"  ✓ Retrieved {len(team_news)} team news items")
            
            games = db.get_game_summaries(conn, days=1)
            print(f"  ✓ Retrieved {len(games)} game summaries")
        
        print("  ✅ Database tests PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Database test FAILED: {e}")
        return False


def test_scrapers():
    """Test web scraping functions"""
    print("\n2. Testing Web Scrapers...")
    print("-" * 70)
    
    try:
        # Test game results scraper
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"  Testing game results for {yesterday}...")
        
        games = scrapers.fetch_game_results(yesterday)
        print(f"  ✓ Fetched {len(games)} games")
        
        if games:
            print(f"    Sample: {games[0]['away_team']} @ {games[0]['home_team']}: "
                  f"{games[0]['away_score']}-{games[0]['home_score']}")
        
        # Test team news scraper
        print("  Testing team news for MTL...")
        news = scrapers.fetch_team_news('MTL')
        print(f"  ✓ Fetched {len(news)} news items")
        
        if news:
            print(f"    Sample: {news[0].get('title', 'No title')[:60]}...")
        
        # Test transactions scraper
        print("  Testing transactions...")
        transactions = scrapers.fetch_transactions()
        print(f"  ✓ Fetched {len(transactions)} potential transactions")
        
        print("  ✅ Scraper tests PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Scraper test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_generators():
    """Test LLM content generation"""
    print("\n3. Testing Content Generators...")
    print("-" * 70)
    
    try:
        generator = get_generator()
        
        # Test daily article generation
        print("  Testing daily article generation...")
        
        sample_content = {
            'transactions': [
                {'description': 'Montreal acquired John Doe from Toronto for a 3rd round pick'}
            ],
            'games': [
                {
                    'away_team': 'TOR',
                    'home_team': 'MTL',
                    'away_score': 2,
                    'home_score': 3,
                    'highlights': 'N. Suzuki scored twice'
                }
            ],
            'team_news': [
                {'team': 'MTL', 'title': 'Canadiens prepare for home opener'}
            ]
        }
        
        article = await generator.generate_daily_article(sample_content)
        
        print(f"  ✓ Generated article: '{article['title']}'")
        print(f"    Content length: {len(article['content'])} chars")
        print(f"    Sources used: {article.get('source_count', 0)}")
        
        # Sample output
        content_preview = article['content'][:200] + '...' if len(article['content']) > 200 else article['content']
        print(f"    Preview: {content_preview}")
        
        print("  ✅ Generator tests PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Generator test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_models():
    """Test Pydantic models"""
    print("\n4. Testing API Models...")
    print("-" * 70)
    
    try:
        from backend.api.models.news import Transaction, TeamNews, GameSummary, DailyArticle
        
        # Test Transaction model
        trans = Transaction(
            id=1,
            date=datetime.now().date(),
            player_name='Test Player',
            transaction_type='trade',
            description='Test trade',
            created_at=datetime.now()
        )
        print(f"  ✓ Transaction model validated")
        
        # Test TeamNews model
        news = TeamNews(
            id=1,
            team_code='MTL',
            date=datetime.now().date(),
            title='Test News',
            created_at=datetime.now()
        )
        print(f"  ✓ TeamNews model validated")
        
        # Test GameSummary model
        game = GameSummary(
            game_id='2024020001',
            date=datetime.now().date(),
            home_team='MTL',
            away_team='TOR',
            home_score=3,
            away_score=2,
            created_at=datetime.now()
        )
        print(f"  ✓ GameSummary model validated")
        
        # Test DailyArticle model
        article = DailyArticle(
            date=datetime.now().date(),
            title='Test Article',
            content='This is test content',
            created_at=datetime.now()
        )
        print(f"  ✓ DailyArticle model validated")
        
        print("  ✅ Model tests PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Model test FAILED: {e}")
        return False


def test_configuration():
    """Test configuration"""
    print("\n5. Testing Configuration...")
    print("-" * 70)
    
    try:
        from backend.bot.config import BOT_CONFIG, NHL_TEAMS
        
        print(f"  ✓ NHL teams loaded: {len(NHL_TEAMS)} teams")
        print(f"  ✓ Database path: {BOT_CONFIG['db_path']}")
        print(f"  ✓ Redis URL: {BOT_CONFIG['redis_url']}")
        print(f"  ✓ LLM model: {BOT_CONFIG['openrouter_model']}")
        
        # Verify all 32 teams
        expected_teams = 32
        if len(NHL_TEAMS) == expected_teams:
            print(f"  ✓ All {expected_teams} NHL teams configured")
        else:
            print(f"  ⚠ Warning: Expected {expected_teams} teams, found {len(NHL_TEAMS)}")
        
        print("  ✅ Configuration tests PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test FAILED: {e}")
        return False


async def main():
    """Run all tests"""
    print("Starting HeartBeat.bot component tests...\n")
    
    results = []
    
    # Run tests
    results.append(("Configuration", test_configuration()))
    results.append(("Database", test_database()))
    results.append(("Scrapers", test_scrapers()))
    results.append(("Generators", await test_generators()))
    results.append(("API Models", test_api_models()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name:20} {status}")
    
    all_passed = all(r[1] for r in results)
    
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED - HeartBeat.bot is ready!")
    else:
        print("⚠️  SOME TESTS FAILED - Review errors above")
    
    print("=" * 70)
    print()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

