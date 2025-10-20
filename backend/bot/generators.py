"""
HeartBeat.bot Content Generators
LLM-powered content generation using OpenRouter + Claude Sonnet 4.5
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add orchestrator to path for OpenRouter provider
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'orchestrator'))

from providers.openrouter_provider import OpenRouterProvider
from .config import BOT_CONFIG

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Manages LLM-based content generation"""
    
    def __init__(self):
        try:
            self.provider = OpenRouterProvider()
            self.model = BOT_CONFIG['openrouter_model']
            self.temperature = BOT_CONFIG['article_generation_temp']
            self.max_tokens = BOT_CONFIG['article_max_tokens']
            logger.info(f"ContentGenerator initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter provider: {e}")
            self.provider = None
    
    async def generate_daily_article(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate daily NHL digest article from aggregated content
        
        Args:
            content_data: Dict with transactions, games, team_news
        
        Returns:
            Dict with date, title, content, metadata
        """
        if not self.provider:
            return self._fallback_daily_article(content_data)
        
        try:
            # Build context from content data
            context_parts = []
            
            # Transactions
            transactions = content_data.get('transactions', [])
            if transactions:
                context_parts.append("TRANSACTIONS:")
                for t in transactions[:10]:  # Top 10
                    context_parts.append(f"- {t.get('description', 'Unknown transaction')}")
            
            # Games
            games = content_data.get('games', [])
            if games:
                context_parts.append("\nGAME RESULTS:")
                for g in games:
                    winner = g['home_team'] if g['home_score'] > g['away_score'] else g['away_team']
                    context_parts.append(
                        f"- {g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']} "
                        f"({winner} wins). Top performers: {g.get('highlights', 'N/A')}"
                    )
            
            # Team news
            team_news = content_data.get('team_news', [])
            if team_news:
                context_parts.append("\nTEAM NEWS HIGHLIGHTS:")
                for news in team_news[:10]:
                    context_parts.append(f"- {news.get('team', 'UNK')}: {news.get('title', 'No title')}")
            
            context = '\n'.join(context_parts)
            
            if not context.strip():
                logger.warning("No content available for article generation")
                return self._fallback_daily_article(content_data)
            
            # Build prompt
            system_prompt = """You are a professional hockey journalist writing for an advanced analytics platform. 
Your writing style is concise, factual, and analytical. Focus on the most significant storylines and provide 
context that hockey analysts would find valuable. Do not use emojis or casual language."""
            
            user_prompt = f"""Write a daily NHL summary article based on the following information from yesterday:

{context}

Write 3-4 concise paragraphs covering the most significant events. Focus on major storylines, notable performances, 
and important transactions. Write in a professional, analytical tone suitable for a hockey analytics platform."""
            
            # Generate article
            response = await self.provider.generate(
                model=self.model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            article_content = response.get('text', '').strip()
            
            if not article_content:
                logger.warning("LLM returned empty article, using fallback")
                return self._fallback_daily_article(content_data)
            
            # Generate title from first sentence or use default
            title = self._extract_title(article_content) or f"NHL Daily Digest - {datetime.now().strftime('%B %d, %Y')}"
            
            # Convert usage object to dict if needed
            usage = response.get('usage', {})
            if hasattr(usage, '__dict__'):
                usage = {
                    'completion_tokens': getattr(usage, 'completion_tokens', 0),
                    'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                    'total_tokens': getattr(usage, 'total_tokens', 0)
                }
            
            # Select a representative image from the content
            image_url = None
            
            # Prefer game images (most visual)
            if games:
                for game in games:
                    if game.get('image_url'):
                        image_url = game['image_url']
                        break
            
            # Fallback to team news images
            if not image_url and team_news:
                for news in team_news:
                    if news.get('image_url'):
                        image_url = news['image_url']
                        break
            
            # Final fallback: NHL logo or a generic hockey image
            if not image_url:
                image_url = "https://assets.nhle.com/logos/nhl/svg/NHL_light.svg"
            
            return {
                'date': datetime.now().date(),
                'title': title,
                'content': article_content,
                'summary': article_content[:200] + '...' if len(article_content) > 200 else article_content,
                'metadata': {
                    'model': self.model,
                    'temperature': self.temperature,
                    'transactions_count': len(transactions),
                    'games_count': len(games),
                    'news_count': len(team_news),
                    'tokens_used': usage
                },
                'source_count': len(transactions) + len(games) + len(team_news),
                'image_url': image_url
            }
            
        except Exception as e:
            logger.error(f"Error generating daily article: {e}")
            return self._fallback_daily_article(content_data)
    
    def _fallback_daily_article(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate templated article when LLM fails"""
        transactions = content_data.get('transactions', [])
        games = content_data.get('games', [])
        team_news = content_data.get('team_news', [])
        
        parts = []
        parts.append(f"NHL Daily Update - {datetime.now().strftime('%B %d, %Y')}\n")
        
        if games:
            parts.append(f"\n{len(games)} games were completed yesterday:")
            for g in games[:5]:
                parts.append(f"- {g['away_team']} {g['away_score']} @ {g['home_team']} {g['home_score']}")
        
        if transactions:
            parts.append(f"\n{len(transactions)} transactions were reported:")
            for t in transactions[:5]:
                parts.append(f"- {t.get('description', 'Transaction')}")
        
        if team_news:
            parts.append(f"\n{len(team_news)} team news items:")
            for n in team_news[:5]:
                parts.append(f"- {n.get('team', 'NHL')}: {n.get('title', 'News')}")
        
        content = '\n'.join(parts)
        
        # Select a representative image
        image_url = None
        if games and games[0].get('image_url'):
            image_url = games[0]['image_url']
        elif team_news and team_news[0].get('image_url'):
            image_url = team_news[0]['image_url']
        else:
            image_url = "https://assets.nhle.com/logos/nhl/svg/NHL_light.svg"
        
        return {
            'date': datetime.now().date(),
            'title': f"NHL Daily Digest - {datetime.now().strftime('%B %d, %Y')}",
            'content': content,
            'summary': content[:200] + '...' if len(content) > 200 else content,
            'metadata': {'generated_by': 'fallback_template'},
            'source_count': len(transactions) + len(games) + len(team_news),
            'image_url': image_url
        }
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract a title from article content"""
        lines = content.split('\n')
        first_line = lines[0].strip() if lines else ''
        
        # If first line looks like a title (short, no period at end)
        if first_line and len(first_line) < 100 and not first_line.endswith('.'):
            return first_line
        
        # Use first sentence as title
        sentences = content.split('.')
        if sentences:
            title = sentences[0].strip()
            if len(title) < 150:
                return title
        
        return None
    
    async def synthesize_multi_source_article(
        self,
        synthesis_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize multiple source articles into one comprehensive article
        
        Args:
            synthesis_context: Dict with 'sources', 'teams', 'players', 'keywords', 'category'
        
        Returns:
            Synthesized article dict
        """
        try:
            sources = synthesis_context.get('sources', [])
            
            if not sources:
                raise ValueError("No sources provided for synthesis")
            
            # Build prompt for multi-source synthesis
            prompt_parts = []
            prompt_parts.append("You are a professional NHL journalist. You have received multiple news articles about the same NHL event from different sources.")
            prompt_parts.append("\nYour task: Create ONE comprehensive, well-written article that combines all the facts from these sources.")
            prompt_parts.append("\nImportant:")
            prompt_parts.append("- Include ALL unique facts and details from every source")
            prompt_parts.append("- Avoid repetition - don't state the same fact twice")
            prompt_parts.append("- Write in a professional, journalistic tone")
            prompt_parts.append("- Start with the most important information")
            prompt_parts.append("- Be factual and objective")
            prompt_parts.append("- Do NOT mention the source names in the article itself")
            prompt_parts.append(f"\nNumber of sources: {len(sources)}")
            prompt_parts.append("\n---\n")
            
            # Add each source
            for i, source in enumerate(sources, 1):
                prompt_parts.append(f"\nSource {i} ({source['source']}):")
                prompt_parts.append(f"Title: {source['title']}")
                prompt_parts.append(f"Content: {source['content'][:1000]}")  # Limit content length
                prompt_parts.append("")
            
            prompt_parts.append("\n---\n")
            prompt_parts.append("Write a comprehensive NHL news article combining all the above information:")
            
            prompt = '\n'.join(prompt_parts)
            
            # Generate with LLM
            response = await self.provider.generate(
                model=self.model,
                system_prompt="You are a professional NHL journalist creating comprehensive news articles.",
                user_prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            article_content = response.get('text', '').strip()
            
            if not article_content:
                raise ValueError("LLM returned empty content")
            
            # Extract title from first line or generate one
            lines = article_content.split('\n')
            title = lines[0].strip() if lines else synthesis_context.get('sources', [{}])[0].get('title', 'NHL News Update')
            
            # If title looks like content, generate a title
            if len(title) > 100 or '.' in title:
                title = f"{synthesis_context.get('category', 'News').title()} Update"
                if synthesis_context.get('teams'):
                    title = f"{synthesis_context['teams'][0]} {title}"
            
            # Handle token usage
            usage = response.get('usage', {})
            if hasattr(usage, '__dict__'):
                usage = {
                    'completion_tokens': getattr(usage, 'completion_tokens', 0),
                    'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                    'total_tokens': getattr(usage, 'total_tokens', 0)
                }
            
            logger.info(f"Synthesized article from {len(sources)} sources: {title}")
            
            return {
                'title': title,
                'content': article_content,
                'summary': article_content[:300] + '...' if len(article_content) > 300 else article_content,
                'source_urls': [s.get('url') for s in sources if s.get('url')],
                'source_count': len(sources),
                'source_names': list(set(s.get('source') for s in sources)),
                'image_url': synthesis_context.get('image_url'),
                'category': synthesis_context.get('category', 'all'),
                'teams': synthesis_context.get('teams', []),
                'players': synthesis_context.get('players', []),
                'keywords': synthesis_context.get('keywords', []),
                'published_date': synthesis_context.get('published_date'),
                'metadata': {
                    'model': self.model,
                    'temperature': self.temperature,
                    'synthesized': True,
                    'tokens_used': usage
                }
            }
            
        except Exception as e:
            logger.error(f"Error synthesizing multi-source article: {e}")
            # Fallback: use the first source
            if sources:
                first = sources[0]
                return {
                    'title': first.get('title', 'NHL News'),
                    'content': first.get('content', ''),
                    'summary': first.get('content', '')[:300] + '...',
                    'source_urls': [first.get('url')],
                    'source_count': 1,
                    'source_names': [first.get('source')],
                    'image_url': synthesis_context.get('image_url'),
                    'category': synthesis_context.get('category', 'all'),
                    'published_date': synthesis_context.get('published_date'),
                    'metadata': {'synthesized': False, 'error': str(e)}
                }
            raise
    
    async def generate_player_summary(
        self, 
        player_name: str, 
        stats: Dict[str, Any], 
        achievements: List[str] = None
    ) -> str:
        """
        Generate player performance summary
        
        Args:
            player_name: Player's name
            stats: Recent statistics dict
            achievements: Notable achievements (hat tricks, milestones, etc.)
        
        Returns:
            Summary text
        """
        achievements = achievements or []
        
        # Template-first approach
        games = stats.get('games_played', 0)
        goals = stats.get('goals', 0)
        assists = stats.get('assists', 0)
        points = stats.get('points', 0)
        
        if achievements:
            # Use LLM for notable achievements
            if self.provider:
                try:
                    prompt = f"""Write a 1-2 sentence summary for {player_name}'s recent performance:
Stats: {games} games, {goals} goals, {assists} assists, {points} points
Notable: {', '.join(achievements)}

Keep it concise and analytical."""
                    
                    response = await self.provider.generate(
                        model=self.model,
                        system_prompt="You are a hockey analyst writing player summaries.",
                        user_prompt=prompt,
                        temperature=0.2,
                        max_tokens=150
                    )
                    
                    return response.get('text', '').strip()
                except Exception as e:
                    logger.error(f"Error generating player summary: {e}")
        
        # Fallback template
        if points > 0:
            return f"{player_name} recorded {points} points ({goals}G, {assists}A) over the last {games} games."
        else:
            return f"{player_name} has played {games} games recently without recording a point."
    
    async def enhance_game_summary(self, game_data: Dict[str, Any]) -> str:
        """
        Enhance game summary with LLM (optional)
        
        Args:
            game_data: Game information dict
        
        Returns:
            Enhanced summary text
        """
        # For most games, templated summary is sufficient
        home = game_data.get('home_team', 'HOME')
        away = game_data.get('away_team', 'AWAY')
        home_score = game_data.get('home_score', 0)
        away_score = game_data.get('away_score', 0)
        
        winner = home if home_score > away_score else away
        
        template = f"{winner} defeated {away if winner == home else home} {max(home_score, away_score)}-{min(home_score, away_score)}."
        
        highlights = game_data.get('highlights', '')
        if highlights:
            template += f" {highlights}"
        
        return template


# Singleton instance
_generator = None

def get_generator() -> ContentGenerator:
    """Get or create ContentGenerator singleton"""
    global _generator
    if _generator is None:
        _generator = ContentGenerator()
    return _generator

