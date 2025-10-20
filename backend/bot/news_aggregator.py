"""
HeartBeat.bot News Aggregator
Intelligent multi-source news collection and synthesis
"""

import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract key entities from article text
    Returns: dict with players, teams, keywords
    """
    from .config import NHL_TEAMS
    
    entities = {
        'players': [],
        'teams': [],
        'keywords': []
    }
    
    text_lower = text.lower()
    
    # Extract team mentions
    for code, info in NHL_TEAMS.items():
        team_name = info['name'].lower()
        if team_name in text_lower or code.lower() in text_lower:
            entities['teams'].append(code)
    
    # Extract keywords (news categories)
    keyword_patterns = {
        'trade': ['trade', 'traded', 'acquire', 'deal'],
        'injury': ['injury', 'injured', 'ir', 'ltir', 'hurt'],
        'signing': ['sign', 'signed', 'contract', 'extension'],
        'milestone': ['milestone', 'record', 'career', 'first', 'hat trick'],
        'suspension': ['suspend', 'suspended', 'discipline'],
        'performance': ['score', 'goal', 'assist', 'win', 'shutout'],
        'coaching': ['coach', 'fire', 'hire', 'staff'],
        'playoff': ['playoff', 'postseason', 'elimination', 'clinch']
    }
    
    for category, patterns in keyword_patterns.items():
        if any(p in text_lower for p in patterns):
            entities['keywords'].append(category)
    
    # Extract player names (capitalized word pairs that aren't team names)
    # Simple heuristic: First Last pattern
    words = text.split()
    team_names_set = {info['name'] for info in NHL_TEAMS.values()}
    
    for i in range(len(words) - 1):
        word1 = words[i].strip(',.!?;:()[]')
        word2 = words[i + 1].strip(',.!?;:()[]')
        
        # Check if looks like a name (both capitalized, reasonable length)
        if (word1 and word2 and 
            word1[0].isupper() and word2[0].isupper() and
            2 <= len(word1) <= 15 and 2 <= len(word2) <= 15 and
            word1.isalpha() and word2.isalpha()):
            
            full_name = f"{word1} {word2}"
            
            # Don't include team names
            if full_name not in team_names_set:
                entities['players'].append(full_name)
    
    # Deduplicate
    entities['players'] = list(set(entities['players']))[:5]  # Top 5
    entities['teams'] = list(set(entities['teams']))
    entities['keywords'] = list(set(entities['keywords']))
    
    return entities


def calculate_similarity_score(article1: Dict[str, Any], article2: Dict[str, Any]) -> float:
    """
    Calculate similarity between two articles
    Returns: score from 0.0 to 1.0
    """
    score = 0.0
    weights = {
        'title': 0.3,
        'players': 0.25,
        'teams': 0.25,
        'keywords': 0.15,
        'time': 0.05
    }
    
    # 1. Title similarity
    title1 = article1.get('title', '').lower()
    title2 = article2.get('title', '').lower()
    if title1 and title2:
        title_similarity = SequenceMatcher(None, title1, title2).ratio()
        score += title_similarity * weights['title']
    
    # 2. Player overlap
    players1 = set(article1.get('entities', {}).get('players', []))
    players2 = set(article2.get('entities', {}).get('players', []))
    if players1 and players2:
        player_overlap = len(players1 & players2) / max(len(players1), len(players2))
        score += player_overlap * weights['players']
    elif not players1 and not players2:
        # Both have no players - slight bonus
        score += 0.1 * weights['players']
    
    # 3. Team overlap
    teams1 = set(article1.get('entities', {}).get('teams', []))
    teams2 = set(article2.get('entities', {}).get('teams', []))
    if teams1 and teams2:
        team_overlap = len(teams1 & teams2) / max(len(teams1), len(teams2))
        score += team_overlap * weights['teams']
    elif not teams1 and not teams2:
        score += 0.1 * weights['teams']
    
    # 4. Keyword overlap
    keywords1 = set(article1.get('entities', {}).get('keywords', []))
    keywords2 = set(article2.get('entities', {}).get('keywords', []))
    if keywords1 and keywords2:
        keyword_overlap = len(keywords1 & keywords2) / max(len(keywords1), len(keywords2))
        score += keyword_overlap * weights['keywords']
    
    # 5. Time proximity (articles within 24 hours)
    try:
        time1 = datetime.fromisoformat(article1.get('published_date', ''))
        time2 = datetime.fromisoformat(article2.get('published_date', ''))
        time_diff_hours = abs((time1 - time2).total_seconds()) / 3600
        if time_diff_hours <= 24:
            time_score = 1.0 - (time_diff_hours / 24)
            score += time_score * weights['time']
    except:
        pass
    
    return min(score, 1.0)


def cluster_articles(articles: List[Dict[str, Any]], similarity_threshold: float = 0.5) -> List[List[Dict[str, Any]]]:
    """
    Group articles by similarity using simple clustering
    Returns: list of article groups
    """
    if not articles:
        return []
    
    # Extract entities for all articles
    for article in articles:
        content = f"{article.get('title', '')} {article.get('summary', '')}"
        article['entities'] = extract_entities(content)
    
    clusters = []
    used = set()
    
    for i, article in enumerate(articles):
        if i in used:
            continue
        
        # Start new cluster
        cluster = [article]
        used.add(i)
        
        # Find similar articles
        for j, other_article in enumerate(articles):
            if j in used or i == j:
                continue
            
            similarity = calculate_similarity_score(article, other_article)
            
            if similarity >= similarity_threshold:
                cluster.append(other_article)
                used.add(j)
        
        clusters.append(cluster)
    
    # Sort clusters by size (largest first)
    clusters.sort(key=lambda x: len(x), reverse=True)
    
    logger.info(f"Clustered {len(articles)} articles into {len(clusters)} groups")
    
    return clusters


def prepare_synthesis_context(cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prepare context for LLM synthesis from a cluster of related articles
    """
    # Collect all information
    all_sources = []
    all_images = []
    all_teams = set()
    all_players = set()
    all_keywords = set()
    
    for article in cluster:
        source_info = {
            'source': article.get('source', 'Unknown'),
            'title': article.get('title', ''),
            'content': article.get('content', ''),
            'url': article.get('url', '')
        }
        all_sources.append(source_info)
        
        if article.get('image_url'):
            all_images.append(article['image_url'])
        
        entities = article.get('entities', {})
        all_teams.update(entities.get('teams', []))
        all_players.update(entities.get('players', []))
        all_keywords.update(entities.get('keywords', []))
    
    # Select best image (prefer Sportsnet, then NHL.com, then others)
    best_image = None
    for img in all_images:
        if 'sportsnet' in img.lower():
            best_image = img
            break
    if not best_image and all_images:
        for img in all_images:
            if 'nhl.com' in img.lower():
                best_image = img
                break
    if not best_image and all_images:
        best_image = all_images[0]
    
    # Determine primary category
    primary_category = list(all_keywords)[0] if all_keywords else 'general'
    
    return {
        'sources': all_sources,
        'source_count': len(all_sources),
        'image_url': best_image,
        'teams': list(all_teams),
        'players': list(all_players),
        'keywords': list(all_keywords),
        'category': primary_category,
        'published_date': cluster[0].get('published_date', datetime.now().isoformat())
    }


def select_article_category(keywords: List[str]) -> str:
    """
    Determine the best category for a synthesized article
    """
    # Priority order
    priority = ['trade', 'injury', 'signing', 'suspension', 'milestone', 'playoff', 'coaching', 'performance']
    
    for cat in priority:
        if cat in keywords:
            return cat
    
    return 'all'  # General news

