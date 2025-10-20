"""
HeartBeat.bot Web Scrapers
Data collection from NHL official sources and trusted media
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from .config import NHL_API_BASE_URL, NHL_TEAMS, REQUEST_DELAY, NHL_ENDPOINTS

logger = logging.getLogger(__name__)


def extract_date_from_text(text: str) -> datetime.date:
    """
    Extract actual event date from transaction text
    Looks for patterns like: "Oct 15", "October 15, 2024", "2024-10-15", etc.
    Falls back to today if no date found
    """
    import re
    from datetime import datetime, timedelta
    
    text_lower = text.lower()
    
    # Pattern 1: "Oct 15", "October 15"
    month_day_pattern = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})'
    match = re.search(month_day_pattern, text_lower)
    if match:
        try:
            month_str = match.group(1)
            day = int(match.group(2))
            current_year = datetime.now().year
            
            # Map month abbreviations
            month_map = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = month_map.get(month_str[:3])
            
            if month:
                # Try current year first
                try:
                    date = datetime(current_year, month, day).date()
                    # If date is in the future, use previous year
                    if date > datetime.now().date():
                        date = datetime(current_year - 1, month, day).date()
                    return date
                except ValueError:
                    pass
        except:
            pass
    
    # Pattern 2: "YYYY-MM-DD"
    iso_pattern = r'20\d{2}-\d{2}-\d{2}'
    match = re.search(iso_pattern, text)
    if match:
        try:
            return datetime.strptime(match.group(), '%Y-%m-%d').date()
        except:
            pass
    
    # Pattern 3: Relative dates like "yesterday", "2 days ago"
    if 'yesterday' in text_lower:
        return (datetime.now() - timedelta(days=1)).date()
    
    days_ago_pattern = r'(\d+)\s+days?\s+ago'
    match = re.search(days_ago_pattern, text_lower)
    if match:
        try:
            days = int(match.group(1))
            return (datetime.now() - timedelta(days=days)).date()
        except:
            pass
    
    # Fallback: use today's date
    return datetime.now().date()


def extract_image_from_html(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """
    Extract the best image from HTML content
    Looks for: og:image, Twitter card images, article images, featured images
    """
    try:
        # 1. Try Open Graph image (most reliable)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            if img_url.startswith('http'):
                return img_url
            elif img_url.startswith('/'):
                return f"{base_url.rstrip('/')}{img_url}"
        
        # 2. Try Twitter card image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            img_url = twitter_image.get('content')
            if img_url.startswith('http'):
                return img_url
            elif img_url.startswith('/'):
                return f"{base_url.rstrip('/')}{img_url}"
        
        # 3. Try article image (news sites)
        article_img = soup.find('article')
        if article_img:
            img_tag = article_img.find('img')
            if img_tag:
                src = img_tag.get('src') or img_tag.get('data-src')
                if src:
                    if src.startswith('http'):
                        return src
                    elif src.startswith('/'):
                        return f"{base_url.rstrip('/')}{src}"
        
        # 4. Try any prominent image with good size
        for img in soup.find_all('img', limit=10):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
            
            # Skip small images, icons, logos
            width = img.get('width')
            height = img.get('height')
            if width and height:
                try:
                    if int(width) < 200 or int(height) < 200:
                        continue
                except (ValueError, TypeError):
                    pass
            
            # Skip common icon/logo patterns
            if any(x in src.lower() for x in ['logo', 'icon', 'avatar', 'thumbnail', 'sprite']):
                continue
            
            if src.startswith('http'):
                return src
            elif src.startswith('/'):
                return f"{base_url.rstrip('/')}{src}"
        
        return None
    except Exception as e:
        logger.error(f"Error extracting image: {e}")
        return None


def create_session() -> requests.Session:
    """Create a requests session with retry logic and proper headers"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    session.headers.update({
        'User-Agent': 'HeartBeat-Engine-Bot/1.0',
        'Accept': 'application/json'
    })
    
    return session


def scrape_news_articles(limit_per_source: int = 10) -> List[Dict[str, Any]]:
    """
    Scrape full news articles from all sources
    Returns list of article dicts with: title, content, summary, url, source, image_url, published_date
    
    Sources:
    - NHL.com main site
    - All 32 individual team websites (nhl.com/bruins/, nhl.com/leafs/, etc.)
    - Sportsnet.ca
    - DailyFaceoff
    """
    all_articles = []
    
    try:
        session = create_session()
        
        logger.info("Scraping news articles from multiple sources...")
        
        # 1. NHL.com main site (league-wide news)
        logger.info("Scraping NHL.com main site...")
        all_articles.extend(_scrape_nhl_articles(session, limit_per_source))
        time.sleep(REQUEST_DELAY)
        
        # 2. All 32 team websites (rich team-specific content)
        logger.info("Scraping all 32 team websites...")
        all_articles.extend(_scrape_all_team_news(session, limit_per_team=3))
        time.sleep(REQUEST_DELAY)
        
        # 3. Sportsnet.ca (Canadian perspective, quality journalism)
        logger.info("Scraping Sportsnet.ca...")
        all_articles.extend(_scrape_sportsnet_articles(session, limit_per_source))
        time.sleep(REQUEST_DELAY)
        
        # 4. DailyFaceoff (fantasy/analytics focus)
        logger.info("Scraping DailyFaceoff...")
        all_articles.extend(_scrape_dailyfaceoff_articles(session, limit_per_source))
        time.sleep(REQUEST_DELAY)
        
        logger.info(f"Scraped {len(all_articles)} total articles from all sources")
        
    except Exception as e:
        logger.error(f"Error scraping news articles: {e}")
    
    return all_articles


def _scrape_all_team_news(session: requests.Session, limit_per_team: int = 3) -> List[Dict[str, Any]]:
    """
    Scrape news articles from all 32 NHL team websites
    Each team has rich content at nhl.com/{team-slug}/news
    This is a goldmine of team-specific stories, player features, game recaps
    """
    all_team_articles = []
    
    # Team slug mapping (team code -> URL slug)
    team_slugs = {
        'MTL': 'canadiens',
        'TOR': 'mapleleafs',
        'BOS': 'bruins',
        'BUF': 'sabres',
        'OTT': 'senators',
        'DET': 'redwings',
        'FLA': 'panthers',
        'TBL': 'lightning',
        'NYR': 'rangers',
        'NYI': 'islanders',
        'PHI': 'flyers',
        'PIT': 'penguins',
        'NJD': 'devils',
        'CAR': 'hurricanes',
        'CBJ': 'bluejackets',
        'WSH': 'capitals',
        'CHI': 'blackhawks',
        'COL': 'avalanche',
        'DAL': 'stars',
        'MIN': 'wild',
        'NSH': 'predators',
        'STL': 'blues',
        'WPG': 'jets',
        'ANA': 'ducks',
        'CGY': 'flames',
        'EDM': 'oilers',
        'LAK': 'kings',
        'SJS': 'sharks',
        'SEA': 'kraken',
        'VAN': 'canucks',
        'VGK': 'goldenknights',
        'UTA': 'utahhockeyclub'
    }
    
    logger.info(f"Scraping news from all 32 team websites (limit: {limit_per_team} articles per team)...")
    
    teams_scraped = 0
    
    for team_code, slug in team_slugs.items():
        try:
            # Each team has news at nhl.com/{slug}/news
            team_url = f"https://www.nhl.com/{slug}/news"
            
            response = session.get(team_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                base_url = "https://www.nhl.com"
                
                # Extract team page image (usually team logo or featured image)
                team_page_image = extract_image_from_html(soup, base_url)
                
                # Find article cards/links
                # NHL team pages typically use <article> tags or specific classes
                article_elements = soup.find_all(['article', 'div'], class_=['article', 'news-item', 'content-card'], limit=limit_per_team * 3)
                
                articles_found = 0
                
                for elem in article_elements:
                    if articles_found >= limit_per_team:
                        break
                    
                    try:
                        # Find title and link
                        title_elem = elem.find(['h1', 'h2', 'h3', 'h4'])
                        link_elem = elem.find('a', href=True)
                        
                        if not title_elem or not link_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        href = link_elem.get('href', '')
                        
                        # Skip if title is too short or looks like navigation
                        if len(title) < 20 or len(title) > 200:
                            continue
                        
                        # Build full URL
                        article_url = href if href.startswith('http') else f"{base_url}{href}"
                        
                        # Extract summary from element
                        summary_elem = elem.find(['p', 'div'], class_=['summary', 'description', 'excerpt'])
                        summary = summary_elem.get_text(strip=True) if summary_elem else title
                        
                        # Extract image from article card
                        img_elem = elem.find('img', src=True)
                        image_url = team_page_image
                        if img_elem:
                            img_src = img_elem.get('src', '')
                            if img_src.startswith('http'):
                                image_url = img_src
                            elif img_src.startswith('/'):
                                image_url = f"{base_url}{img_src}"
                        
                        # Add article
                        all_team_articles.append({
                            'title': title,
                            'content': summary,  # For team pages, we'll use summary as content
                            'summary': summary[:200] + '...' if len(summary) > 200 else summary,
                            'url': article_url,
                            'source': f'{team_code.lower()}_team',
                            'team_code': team_code,
                            'image_url': image_url,
                            'published_date': datetime.now().isoformat()
                        })
                        
                        articles_found += 1
                    
                    except Exception as e:
                        logger.debug(f"Error parsing article element for {team_code}: {e}")
                        continue
                
                teams_scraped += 1
                
                # Rate limiting: Small delay between teams
                time.sleep(0.3)
            
        except Exception as e:
            logger.debug(f"Error scraping {team_code} website: {e}")
            continue
    
    logger.info(f"Team websites: Scraped {len(all_team_articles)} articles from {teams_scraped}/32 teams")
    
    return all_team_articles


def _scrape_sportsnet_articles(session: requests.Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Scrape full articles from Sportsnet.ca"""
    articles = []
    
    try:
        url = "https://www.sportsnet.ca/hockey/nhl/"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            base_url = "https://www.sportsnet.ca"
            
            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True, limit=50):
                href = link.get('href', '')
                if 'hockey' in href.lower() and 'nhl' in href.lower():
                    full_url = href if href.startswith('http') else f"{base_url}{href}"
                    title = link.get_text(strip=True)
                    if title and len(title) > 20 and full_url not in [a[0] for a in article_links]:
                        article_links.append((full_url, title))
            
            # Fetch article content
            for article_url, title in article_links[:limit]:
                try:
                    article_resp = session.get(article_url, timeout=10)
                    if article_resp.status_code == 200:
                        article_soup = BeautifulSoup(article_resp.content, 'lxml')
                        
                        # Extract image
                        image_url = extract_image_from_html(article_soup, base_url)
                        
                        # Extract article content
                        content_parts = []
                        for p in article_soup.find_all('p', limit=10):
                            text = p.get_text(strip=True)
                            if len(text) > 50:
                                content_parts.append(text)
                        
                        content = ' '.join(content_parts)
                        
                        if content and len(content) > 100:
                            articles.append({
                                'title': title,
                                'content': content,
                                'summary': content[:300] + '...' if len(content) > 300 else content,
                                'url': article_url,
                                'source': 'sportsnet',
                                'image_url': image_url,
                                'published_date': datetime.now().isoformat()
                            })
                    
                    time.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.debug(f"Error fetching Sportsnet article {article_url}: {e}")
                    continue
        
        logger.info(f"Sportsnet: Scraped {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Error scraping Sportsnet articles: {e}")
    
    return articles


def _scrape_nhl_articles(session: requests.Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Scrape full articles from NHL.com"""
    articles = []
    
    try:
        url = "https://www.nhl.com/news"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            base_url = "https://www.nhl.com"
            
            # Find article links
            article_links = []
            for link in soup.find_all('a', href=True, limit=50):
                href = link.get('href', '')
                if '/news/' in href:
                    full_url = href if href.startswith('http') else f"{base_url}{href}"
                    title = link.get_text(strip=True)
                    if title and len(title) > 20 and full_url not in [a[0] for a in article_links]:
                        article_links.append((full_url, title))
            
            # Fetch article content
            for article_url, title in article_links[:limit]:
                try:
                    article_resp = session.get(article_url, timeout=10)
                    if article_resp.status_code == 200:
                        article_soup = BeautifulSoup(article_resp.content, 'lxml')
                        
                        # Extract image
                        image_url = extract_image_from_html(article_soup, base_url)
                        
                        # Extract content
                        content_parts = []
                        for p in article_soup.find_all('p', limit=10):
                            text = p.get_text(strip=True)
                            if len(text) > 50:
                                content_parts.append(text)
                        
                        content = ' '.join(content_parts)
                        
                        if content and len(content) > 100:
                            articles.append({
                                'title': title,
                                'content': content,
                                'summary': content[:300] + '...' if len(content) > 300 else content,
                                'url': article_url,
                                'source': 'nhl',
                                'image_url': image_url,
                                'published_date': datetime.now().isoformat()
                            })
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.debug(f"Error fetching NHL article {article_url}: {e}")
                    continue
        
        logger.info(f"NHL.com: Scraped {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Error scraping NHL.com articles: {e}")
    
    return articles


def _scrape_dailyfaceoff_articles(session: requests.Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Scrape articles from DailyFaceoff"""
    articles = []
    
    try:
        urls_to_try = [
            "https://www.dailyfaceoff.com/",
            "https://www.dailyfaceoff.com/hockey-player-news"
        ]
        
        for url in urls_to_try:
            response = session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                base_url = "https://www.dailyfaceoff.com"
                
                # Find article links
                for link in soup.find_all('a', href=True, limit=30):
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    if len(title) > 20 and ('nhl' in href.lower() or 'hockey' in href.lower()):
                        full_url = href if href.startswith('http') else f"{base_url}{href}"
                        
                        # Simple content extraction
                        articles.append({
                            'title': title,
                            'content': title,  # Simplified for now
                            'summary': title,
                            'url': full_url,
                            'source': 'dailyfaceoff',
                            'image_url': None,
                            'published_date': datetime.now().isoformat()
                        })
                        
                        if len(articles) >= limit:
                            break
            
            if len(articles) >= limit:
                break
            
            time.sleep(0.5)
        
        logger.info(f"DailyFaceoff: Scraped {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Error scraping DailyFaceoff articles: {e}")
    
    return articles


def scrape_puckpedia_injuries() -> List[Dict[str, Any]]:
    """
    Scrape NHL injury reports from PuckPedia
    Returns list of injury updates with player details
    """
    injuries = []
    
    try:
        # Use enhanced headers to avoid 403 blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        session = create_session()
        url = "https://puckpedia.com/injuries"
        
        logger.info("Scraping PuckPedia for injury reports...")
        response = session.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # PuckPedia uses a table structure for injuries
            injury_tables = soup.find_all('table')
            
            for table in injury_tables:
                rows = table.find_all('tr')
                
                # Skip header row
                for row in rows[1:]:
                    try:
                        cells = row.find_all(['td', 'th'])
                        
                        if len(cells) < 3:
                            continue
                        
                        # Extract player name (usually first column with link)
                        player_elem = row.find('a', href=lambda x: x and '/player/' in str(x))
                        if not player_elem:
                            continue
                        
                        player_name = player_elem.get_text(strip=True)
                        player_link = player_elem.get('href', '')
                        
                        # Extract team
                        team_elem = row.find('a', href=lambda x: x and '/team/' in str(x))
                        team_code = None
                        if team_elem:
                            team_name = team_elem.get_text(strip=True).upper()
                            # Try to match to our team codes
                            for code, info in NHL_TEAMS.items():
                                if code in team_name or info['name'].upper() in team_name:
                                    team_code = code
                                    break
                        
                        # Extract injury info from cells
                        injury_desc = None
                        status = None
                        return_date = None
                        
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            
                            # Look for injury keywords
                            if any(kw in text.lower() for kw in ['knee', 'shoulder', 'ankle', 'concussion', 'back', 'groin', 'upper body', 'lower body', 'illness', 'undisclosed']):
                                injury_desc = text
                            elif any(kw in text.lower() for kw in ['ir', 'ltir', 'day-to-day', 'week-to-week', 'out', 'questionable', 'injured reserve']):
                                status = text
                            elif '/' in text or 'week' in text.lower() or 'month' in text.lower() or 'indefinite' in text.lower():
                                return_date = text
                        
                        if player_name:
                            # Build description
                            desc_parts = []
                            if team_code:
                                desc_parts.append(f"{player_name} ({team_code})")
                            else:
                                desc_parts.append(player_name)
                            
                            if injury_desc:
                                desc_parts.append(injury_desc)
                            if status:
                                desc_parts.append(f"Status: {status}")
                            
                            # Create unique source URL for each player
                            if player_link and player_link.startswith('/'):
                                source_url = f"https://puckpedia.com{player_link}"
                            else:
                                # Generate unique URL using player name and team
                                import urllib.parse
                                player_slug = urllib.parse.quote(player_name.lower().replace(' ', '-'))
                                source_url = f"{url}#{team_code or 'nhl'}-{player_slug}"
                            
                            injuries.append({
                                'date': datetime.now().date(),
                                'player_name': player_name,
                                'player_id': None,
                                'team_code': team_code,
                                'injury_status': status or 'Injured',
                                'injury_description': injury_desc or 'Injury',
                                'return_estimate': return_date,
                                'description': ' - '.join(desc_parts),
                                'source_url': source_url,
                                'image_url': None,
                                'source': 'puckpedia'
                            })
                    
                    except Exception as e:
                        logger.debug(f"Error parsing PuckPedia injury row: {e}")
                        continue
        
        logger.info(f"PuckPedia: Found {len(injuries)} injury reports")
        
    except Exception as e:
        logger.error(f"Error scraping PuckPedia injuries: {e}")
    
    return injuries


def scrape_espn_injuries() -> List[Dict[str, Any]]:
    """
    Scrape NHL injury reports from ESPN
    Returns list of injury updates with player details
    """
    injuries = []
    
    try:
        session = create_session()
        url = "https://www.espn.com/nhl/injuries"
        
        logger.info("Scraping ESPN for injury reports...")
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            base_url = "https://www.espn.com"
            
            # Extract page image
            page_image = extract_image_from_html(soup, base_url)
            
            # ESPN uses Table__TBODY structure (32 tables, one per team)
            team_tables = soup.find_all('tbody', class_=lambda x: x and 'Table__TBODY' in str(x))
            
            for table in team_tables:
                # Find team name from parent structure
                team_code = None
                team_container = table.find_parent('div', class_=lambda x: x and 'ResponsiveTable' in str(x))
                if team_container:
                    team_header = team_container.find_previous(['h2', 'h3', 'div'], class_=lambda x: x and 'Table__Title' in str(x))
                    if team_header:
                        team_name = team_header.get_text(strip=True).upper()
                        # Match to our team codes
                        for code, info in NHL_TEAMS.items():
                            if code in team_name or info['name'].upper() in team_name:
                                team_code = code
                                break
                
                # Parse injury rows in this team's table
                rows = table.find_all('tr', class_=lambda x: x and 'Table__TR' in str(x))
                
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        
                        if len(cells) < 3:
                            continue
                        
                        # Cell 0: Player name
                        player_name = cells[0].get_text(strip=True)
                        player_link = cells[0].find('a')
                        player_url = player_link.get('href') if player_link else None
                        
                        # Cell 1: Position
                        position = cells[1].get_text(strip=True)
                        
                        # Cell 2: Date/Status
                        status_date = cells[2].get_text(strip=True)
                        
                        # Cell 3+: Injury details (if available)
                        injury_desc = ''
                        if len(cells) > 3:
                            injury_desc = cells[3].get_text(strip=True)
                        
                        # Cell 4+: Additional status
                        injury_status = 'Out'
                        if len(cells) > 4:
                            injury_status = cells[4].get_text(strip=True) or 'Out'
                        
                        if player_name and player_name not in ['Name', 'Player']:
                            # Create unique source URL for each player to avoid deduplication conflicts
                            if player_url and player_url.startswith('/'):
                                source_url = f"{base_url}{player_url}"
                            else:
                                # Generate unique URL using player name and team to prevent hash collisions
                                import urllib.parse
                                player_slug = urllib.parse.quote(player_name.lower().replace(' ', '-'))
                                source_url = f"{url}#{team_code or 'nhl'}-{player_slug}"
                            
                            injuries.append({
                                'date': datetime.now().date(),
                                'player_name': player_name,
                                'player_id': None,
                                'team_code': team_code,
                                'injury_status': injury_status,
                                'injury_description': injury_desc or status_date,
                                'return_estimate': status_date,
                                'description': f"{player_name} ({team_code or 'NHL'}): {injury_desc or status_date} - {injury_status}",
                                'source_url': source_url,
                                'image_url': page_image,
                                'source': 'espn'
                            })
                    
                    except Exception as e:
                        logger.debug(f"Error parsing ESPN injury row: {e}")
                        continue
            
        
        logger.info(f"ESPN: Found {len(injuries)} injury reports")
        
    except Exception as e:
        logger.error(f"Error scraping ESPN injuries: {e}")
    
    return injuries


def scrape_injury_reports() -> List[Dict[str, Any]]:
    """
    Aggregate NHL injury reports from multiple sources (ESPN and PuckPedia)
    Cross-references data and returns deduplicated list
    """
    logger.info("Collecting injury reports from multiple sources...")
    
    all_injuries = []
    
    # Scrape from both sources
    espn_injuries = scrape_espn_injuries()
    puckpedia_injuries = scrape_puckpedia_injuries()
    
    # Combine all sources
    all_injuries.extend(espn_injuries)
    all_injuries.extend(puckpedia_injuries)
    
    # Deduplicate by player name (keep entry with most detail)
    player_injuries = {}
    
    for injury in all_injuries:
        player_key = injury.get('player_name', '').lower().strip()
        
        if not player_key or player_key == 'multiple players':
            # Keep generic entries separate
            continue
        
        # If player not in dict yet, add them
        if player_key not in player_injuries:
            player_injuries[player_key] = injury
        else:
            # Player already exists - merge data from both sources
            existing = player_injuries[player_key]
            
            # Keep more detailed injury description
            if injury.get('injury_description') and len(str(injury.get('injury_description', ''))) > len(str(existing.get('injury_description', ''))):
                existing['injury_description'] = injury['injury_description']
            
            # Keep more specific status
            if injury.get('injury_status') and injury['injury_status'] != 'Unknown' and existing.get('injury_status') == 'Unknown':
                existing['injury_status'] = injury['injury_status']
            
            # Keep return estimate if not present
            if injury.get('return_estimate') and not existing.get('return_estimate'):
                existing['return_estimate'] = injury['return_estimate']
            
            # Add source to description to show cross-referenced
            if 'source' in injury and injury['source'] != existing.get('source'):
                sources = [existing.get('source'), injury['source']]
                existing['sources'] = sources
                existing['verified'] = True  # Confirmed by multiple sources
            
            # Update description with merged info
            desc_parts = []
            if existing.get('team_code'):
                desc_parts.append(f"{existing['player_name']} ({existing['team_code']})")
            else:
                desc_parts.append(existing['player_name'])
            
            if existing.get('injury_description'):
                desc_parts.append(existing['injury_description'])
            if existing.get('injury_status'):
                desc_parts.append(f"Status: {existing['injury_status']}")
            if existing.get('verified'):
                desc_parts.append("(Verified by multiple sources)")
            
            existing['description'] = ' - '.join(desc_parts)
    
    # Convert back to list
    deduplicated_injuries = list(player_injuries.values())
    
    logger.info(f"Total injuries aggregated: {len(all_injuries)} raw, {len(deduplicated_injuries)} after deduplication")
    logger.info(f"  ESPN: {len(espn_injuries)}, PuckPedia: {len(puckpedia_injuries)}")
    
    verified_count = sum(1 for i in deduplicated_injuries if i.get('verified'))
    if verified_count:
        logger.info(f"  Cross-referenced/verified: {verified_count} injuries")
    
    return deduplicated_injuries


def _scrape_tsn(session: requests.Session, keywords: Dict) -> List[Dict[str, Any]]:
    """
    Scrape TSN.ca for NHL transactions (trades and free agency)
    Excellent Canadian source with dedicated transaction pages
    """
    transactions = []
    
    try:
        # 1. TSN Trade Tracker
        trade_url = "https://www.tsn.ca/nhl/tradecentre/trade-tracker/"
        response = session.get(trade_url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            base_url = "https://www.tsn.ca"
            
            # Extract page image
            page_image = extract_image_from_html(soup, base_url)
            
            # Find trade items - TSN typically uses article or list structures
            trade_items = soup.find_all(['article', 'div', 'li'], class_=['trade-item', 'transaction-item', 'article-item'], limit=30)
            
            for item in trade_items:
                # Look for headlines and descriptions
                title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                title_lower = title.lower()
                
                # Check if it's a trade
                if any(kw in title_lower for kw in keywords.get('trade', [])):
                    link_elem = item.find('a', href=True)
                    source_url = None
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        source_url = f"{base_url}{href}" if href.startswith('/') else href
                    
                    # Parse trade details
                    parsed = _parse_transaction_text(title, keywords)
                    
                    if parsed['player_name'] != 'Unknown Player':
                        # Extract date from title or use today
                        event_date = extract_date_from_text(title)
                        
                        transactions.append({
                            'date': event_date,
                            'player_name': parsed['player_name'],
                            'player_id': None,
                            'team_from': parsed['team_from'],
                            'team_to': parsed['team_to'],
                            'type': 'trade',
                            'description': title,
                            'source_url': source_url or trade_url,
                            'image_url': page_image,
                            'source': 'tsn'
                        })
        
        time.sleep(REQUEST_DELAY)
        
        # 2. TSN Free Agency Tracker
        fa_url = "https://www.tsn.ca/nhl/free-agency/"
        response = session.get(fa_url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract page image
            page_image = extract_image_from_html(soup, base_url)
            
            # Find signing items
            signing_items = soup.find_all(['article', 'div', 'li'], class_=['signing-item', 'fa-item', 'article-item'], limit=30)
            
            for item in signing_items:
                title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                title_lower = title.lower()
                
                # Check if it's a signing
                if any(kw in title_lower for kw in keywords.get('signing', [])):
                    link_elem = item.find('a', href=True)
                    source_url = None
                    if link_elem and link_elem.get('href'):
                        href = link_elem['href']
                        source_url = f"{base_url}{href}" if href.startswith('/') else href
                    
                    # Parse signing details
                    parsed = _parse_transaction_text(title, keywords)
                    
                    if parsed['player_name'] != 'Unknown Player':
                        # Extract date from title or use today
                        event_date = extract_date_from_text(title)
                        
                        transactions.append({
                            'date': event_date,
                            'player_name': parsed['player_name'],
                            'player_id': None,
                            'team_from': parsed['team_from'],
                            'team_to': parsed['team_to'],
                            'type': 'signing',
                            'description': title,
                            'source_url': source_url or fa_url,
                            'image_url': page_image,
                            'source': 'tsn'
                        })
        
        logger.info(f"TSN scraped: {len(transactions)} transactions")
        
    except Exception as e:
        logger.error(f"Error scraping TSN: {e}")
    
    return transactions


def _scrape_sportsnet(session: requests.Session, keywords: Dict) -> List[Dict[str, Any]]:
    """
    Scrape Sportsnet.ca for NHL news, transactions, and articles
    Excellent Canadian source with professional coverage and images
    """
    transactions = []
    
    try:
        url = "https://www.sportsnet.ca/hockey/nhl/"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract images using Open Graph and article structure
            base_url = "https://www.sportsnet.ca"
            page_image = extract_image_from_html(soup, base_url)
            
            # Find all article links and headings
            articles = soup.find_all(['article', 'div'], class_=['card', 'article', 'story', 'news-item'], limit=30)
            
            # Also look for direct links with hockey/nhl in the URL
            all_links = soup.find_all('a', href=True, limit=50)
            
            for link in all_links:
                href = link.get('href', '')
                
                # Only process NHL-related URLs
                if 'hockey' not in href.lower() and 'nhl' not in href.lower():
                    continue
                
                # Get the link text
                text = link.get_text(strip=True)
                if not text or len(text) < 20:
                    continue
                
                text_lower = text.lower()
                
                # Check if it's transaction-related
                transaction_type = None
                for ttype, keywords_list in keywords.items():
                    if any(kw in text_lower for kw in keywords_list):
                        transaction_type = ttype
                        break
                
                if transaction_type:
                    # Build full URL
                    full_url = href if href.startswith('http') else f"{base_url}{href}"
                    
                    # Try to extract player name
                    parsed = _parse_transaction_text(text)
                    
                    if parsed['player_name'] != 'Unknown Player':
                        # Try to fetch article image
                        article_image = page_image  # Default to page image
                        try:
                            article_resp = session.get(full_url, timeout=5)
                            if article_resp.status_code == 200:
                                article_soup = BeautifulSoup(article_resp.content, 'lxml')
                                article_image = extract_image_from_html(article_soup, base_url) or page_image
                        except Exception:
                            pass
                        
                        # Extract date from text
                        event_date = extract_date_from_text(text)
                        
                        transactions.append({
                            'date': event_date,
                            'player_name': parsed['player_name'],
                            'player_id': None,
                            'team_from': parsed['team_from'],
                            'team_to': parsed['team_to'],
                            'type': transaction_type,
                            'description': text,
                            'source_url': full_url,
                            'source': 'sportsnet',
                            'image_url': article_image
                        })
        
        logger.info(f"Sportsnet.ca: Found {len(transactions)} transactions")
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        logger.error(f"Error scraping Sportsnet: {e}")
    
    return transactions


def fetch_transactions() -> List[Dict[str, Any]]:
    """
    Fetch recent NHL transactions from multiple sources with cross-validation
    Scrapes: CapWages, TSN.ca, Sportsnet.ca, NHL.com, DailyFaceoff, and all 32 team sites
    ONLY returns transactions found in 2+ sources for accuracy (except routine roster moves from CapWages)
    """
    all_transactions = []
    
    try:
        session = create_session()
        
        # Transaction keywords to identify roster moves
        transaction_keywords = {
            'trade': ['trade', 'traded', 'acquire', 'acquired', 'exchange'],
            'signing': ['sign', 'signed', 'signing', 'contract'],
            'waiver': ['waiver', 'claimed', 'clear waivers', 'cleared waivers'],
            'recall': ['recall', 'recalled', 'call-up', 'called up'],
            'assign': ['assign', 'assigned', 'sent to', 'reassign', 'loaned'],
            'loan': ['loan', 'loaned', 'conditioning'],
            'injury': ['injured reserve', 'IR', 'LTIR'],
            'release': ['release', 'released', 'terminate']
        }
        
        # 1. Scrape CapWages (most reliable structured data)
        logger.info("Scraping CapWages for transactions...")
        all_transactions.extend(_scrape_capwages(session))
        time.sleep(REQUEST_DELAY)
        
        # 2. Scrape TSN.ca (Canadian source - Trade Tracker + Free Agency)
        logger.info("Scraping TSN.ca for transactions...")
        all_transactions.extend(_scrape_tsn(session, transaction_keywords))
        time.sleep(REQUEST_DELAY)
        
        # 3. Scrape Sportsnet.ca (Canadian source with quality images and articles)
        logger.info("Scraping Sportsnet.ca for transactions...")
        all_transactions.extend(_scrape_sportsnet(session, transaction_keywords))
        time.sleep(REQUEST_DELAY)
        
        # 4. Scrape NHL.com main news
        logger.info("Scraping NHL.com for transactions...")
        all_transactions.extend(_scrape_nhl_main(session, transaction_keywords))
        time.sleep(REQUEST_DELAY)
        
        # 5. Scrape DailyFaceoff
        logger.info("Scraping DailyFaceoff for transactions...")
        all_transactions.extend(_scrape_dailyfaceoff(session, transaction_keywords))
        time.sleep(REQUEST_DELAY)
        
        # 6. Scrape ALL 32 team pages
        logger.info("Scraping all 32 team websites for transactions...")
        teams_scraped = 0
        
        for team_code, team_info in NHL_TEAMS.items():
            try:
                team_transactions = _scrape_team_transactions(session, team_code, transaction_keywords)
                if team_transactions:
                    logger.info(f"  {team_code}: Found {len(team_transactions)} transactions")
                all_transactions.extend(team_transactions)
                teams_scraped += 1
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                logger.error(f"Error scraping {team_code}: {e}")
        
        logger.info(f"Scraped {teams_scraped}/32 team websites")
        
        # Cross-validate: Only keep transactions found in 2+ sources
        validated_transactions = _cross_validate_transactions(all_transactions)
        
        logger.info(f"Cross-validation: {len(all_transactions)} total → {len(validated_transactions)} verified (2+ sources)")
        
        return validated_transactions
        
    except Exception as e:
        logger.error(f"Error in fetch_transactions: {e}")
        return []


def _scrape_nhl_main(session: requests.Session, keywords: Dict) -> List[Dict[str, Any]]:
    """Scrape NHL.com main news page for transactions"""
    transactions = []
    
    try:
        # Try multiple NHL.com endpoints
        urls = [
            "https://www.nhl.com/news",
            "https://www.nhl.com/info/transactions"
        ]
        
        for url in urls:
            try:
                response = session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'lxml')
                    
                    # Find all possible article/news containers
                    # NHL.com uses various structures
                    articles = soup.find_all(['article', 'div', 'li'], limit=50)
                    
                    for article in articles:
                        # Try multiple heading tags
                        title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'a'])
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        
                        # Skip if too short or too long
                        if len(title) < 10 or len(title) > 200:
                            continue
                        
                        title_lower = title.lower()
                        
                        # Check if it matches transaction keywords
                        transaction_type = _detect_transaction_type(title_lower, keywords)
                        if transaction_type:
                            link_elem = article.find('a', href=True)
                            
                            # Try to parse player and teams from title
                            parsed = _parse_transaction_from_text(title, transaction_type)
                            
                            # Only add if we found at least a player name
                            if parsed['player_name'] != 'Unknown Player':
                                transactions.append({
                                    'date': datetime.now().date(),
                                    'player_name': parsed['player_name'],
                                    'player_id': None,
                                    'team_from': parsed['team_from'],
                                    'team_to': parsed['team_to'],
                                    'type': transaction_type,
                                    'description': title,
                                    'source_url': f"https://www.nhl.com{link_elem['href']}" if link_elem and link_elem.get('href', '').startswith('/') else link_elem.get('href') if link_elem else None,
                                    'source': 'nhl'
                                })
                
                time.sleep(0.1)  # Small delay between URLs
                
            except Exception as e:
                logger.debug(f"Error with URL {url}: {e}")
                continue
        
        logger.info(f"NHL.com: Found {len(transactions)} transactions")
        
    except Exception as e:
        logger.error(f"Error scraping NHL.com: {e}")
    
    return transactions


def _scrape_dailyfaceoff(session: requests.Session, keywords: Dict) -> List[Dict[str, Any]]:
    """Scrape DailyFaceoff for transactions"""
    transactions = []
    
    try:
        # Try multiple DailyFaceoff sections
        urls = [
            "https://www.dailyfaceoff.com/",  # Main page
            "https://www.dailyfaceoff.com/hockey-player-news",  # Player news
        ]
        
        for url in urls:
            try:
                response = session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'lxml')
                    
                    # DailyFaceoff uses various structures - cast a wide net
                    # Look for all links with transaction-related keywords
                    all_links = soup.find_all('a', href=True)
                    
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Skip if too short or just navigation
                        if len(text) < 15 or len(text) > 250:
                            continue
                        
                        text_lower = text.lower()
                        
                        # Look for transaction keywords
                        transaction_type = _detect_transaction_type(text_lower, keywords)
                        if transaction_type:
                            # Also check if href contains news or roster-moves
                            if '/news/' in href or 'roster' in href or transaction_type:
                                parsed = _parse_transaction_from_text(text, transaction_type)
                                
                                # Build full URL if relative
                                full_url = href
                                if href.startswith('/'):
                                    full_url = f"https://www.dailyfaceoff.com{href}"
                                
                                if parsed['player_name'] != 'Unknown Player':
                                    transactions.append({
                                        'date': datetime.now().date(),
                                        'player_name': parsed['player_name'],
                                        'player_id': None,
                                        'team_from': parsed['team_from'],
                                        'team_to': parsed['team_to'],
                                        'type': transaction_type,
                                        'description': text,
                                        'source_url': full_url,
                                        'source': 'dailyfaceoff'
                                    })
                
                time.sleep(0.2)
                
            except Exception as e:
                logger.debug(f"Error with DailyFaceoff URL {url}: {e}")
                continue
        
        logger.info(f"DailyFaceoff: Found {len(transactions)} transactions")
        
    except Exception as e:
        logger.error(f"Error scraping DailyFaceoff: {e}")
    
    return transactions


def _scrape_team_transactions(session: requests.Session, team_code: str, keywords: Dict) -> List[Dict[str, Any]]:
    """Scrape individual team website for transactions"""
    transactions = []
    
    try:
        team_name_slug = NHL_TEAMS[team_code]['name'].lower().replace(' ', '-')
        url = f"https://www.nhl.com/{team_name_slug}/news"
        
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            
            articles = soup.find_all(['article', 'div'], limit=10)
            
            for article in articles:
                title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                title_lower = title.lower()
                
                transaction_type = _detect_transaction_type(title_lower, keywords)
                if transaction_type:
                    link_elem = article.find('a', href=True)
                    parsed = _parse_transaction_from_text(title, transaction_type)
                    
                    # If team not specified, assume it's this team
                    if not parsed['team_from'] and not parsed['team_to']:
                        if 'sign' in transaction_type or 'acquire' in title_lower:
                            parsed['team_to'] = team_code
                        elif 'trade' in title_lower:
                            parsed['team_from'] = team_code
                    
                    transactions.append({
                        'date': datetime.now().date(),
                        'player_name': parsed['player_name'],
                        'player_id': None,
                        'team_from': parsed['team_from'],
                        'team_to': parsed['team_to'],
                        'type': transaction_type,
                        'description': title,
                        'source_url': f"https://www.nhl.com{link_elem['href']}" if link_elem and link_elem.get('href', '').startswith('/') else link_elem.get('href') if link_elem else None,
                        'source': 'team_site'
                    })
        
    except Exception as e:
        logger.error(f"Error scraping team {team_code}: {e}")
    
    return transactions


def _detect_transaction_type(text_lower: str, keywords: Dict) -> Optional[str]:
    """Detect transaction type from text"""
    for trans_type, keyword_list in keywords.items():
        if any(kw in text_lower for kw in keyword_list):
            return trans_type
    return None


def _parse_transaction_from_text(text: str, transaction_type: str) -> Dict[str, Optional[str]]:
    """
    Parse player name and teams from transaction text
    This is a basic implementation - could be enhanced with NER
    """
    import re
    
    # Look for team codes in text
    team_pattern = r'\b(' + '|'.join(NHL_TEAMS.keys()) + r')\b'
    teams_found = re.findall(team_pattern, text.upper())
    
    # Try to extract player name (usually capitalized words before transaction keyword)
    # This is simplified - in production would use NLP/NER
    words = text.split()
    potential_names = []
    
    for i, word in enumerate(words):
        # Look for capitalized words that aren't team names
        if word and word[0].isupper() and word.upper() not in NHL_TEAMS:
            # Check if next word is also capitalized (First Last name pattern)
            if i + 1 < len(words) and words[i + 1] and words[i + 1][0].isupper():
                potential_names.append(f"{word} {words[i + 1]}")
    
    player_name = potential_names[0] if potential_names else 'Unknown Player'
    
    # Assign teams based on transaction type and found teams
    team_from = None
    team_to = None
    
    if len(teams_found) >= 2:
        if transaction_type == 'trade':
            team_from = teams_found[0]
            team_to = teams_found[1]
        elif transaction_type in ['signing', 'recall', 'call-up']:
            team_to = teams_found[0]
        elif transaction_type in ['assign', 'waiver']:
            team_from = teams_found[0]
    elif len(teams_found) == 1:
        if transaction_type in ['signing', 'recall', 'call-up', 'acquire']:
            team_to = teams_found[0]
        else:
            team_from = teams_found[0]
    
    return {
        'player_name': player_name,
        'team_from': team_from,
        'team_to': team_to
    }


def _scrape_capwages(session: requests.Session) -> List[Dict[str, Any]]:
    """
    Scrape CapWages.com/moves for accurate transaction data
    This is the most reliable source with structured data
    """
    transactions = []
    
    try:
        url = "https://capwages.com/moves"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find all rows
            rows = soup.find_all('tr')
            
            # Track current date as we iterate (date headers group transactions)
            current_date = datetime.now().date()
            
            for row in rows:
                # Check for date header row (has TD with colspan attribute)
                date_header_cell = row.find('td', colspan=True)
                
                if date_header_cell:
                    # This is a date header row (blue row like "October 15, 2025")
                    date_text = date_header_cell.get_text(strip=True)
                    current_date = extract_date_from_text(date_text)
                    logger.debug(f"CapWages date header: {date_text} -> {current_date}")
                    continue
                
                # Get all regular TD cells
                cells = row.find_all('td')
                
                # Skip if not a transaction row (needs 3 cells: Team, Player, Type)
                if len(cells) < 3:
                    continue
                
                # Extract player name
                player_link = cells[1].find('a') if len(cells) > 1 else None
                if not player_link:
                    continue
                    
                player_name = player_link.get_text(strip=True)
                
                # Extract team
                team_link = cells[0].find('a') if len(cells) > 0 else None
                team_name = team_link.get_text(strip=True) if team_link else ''
                
                # Extract transaction type
                trans_type_text = cells[2].get_text(strip=True) if len(cells) > 2 else ''
                
                # Map CapWages terms to our types
                if 'waiver' in trans_type_text.lower():
                    if 'cleared' in trans_type_text.lower():
                        trans_type = 'waiver-clear'
                    elif 'claimed' in trans_type_text.lower():
                        trans_type = 'waiver-claim'
                    else:
                        trans_type = 'waiver'
                elif 'recall' in trans_type_text.lower():
                    trans_type = 'recall'
                elif 'loan' in trans_type_text.lower() or 'conditioning' in trans_type_text.lower():
                    trans_type = 'loan'
                elif 'injured reserve' in trans_type_text.lower() or ' IR' in trans_type_text:
                    trans_type = 'injury'
                elif 'LTIR' in trans_type_text or 'long-term' in trans_type_text.lower():
                    trans_type = 'injury'
                elif 'activated' in trans_type_text.lower():
                    trans_type = 'activate'
                else:
                    trans_type = 'other'
                
                # Extract team code from team name
                team_code = _map_team_name_to_code(team_name)
                
                # Build description
                description = f"{team_name} - {player_name}: {trans_type_text}"
                
                # Use the current_date from the most recent date header
                event_date = current_date
                
                transactions.append({
                    'date': event_date,
                    'player_name': player_name,
                    'player_id': None,
                    'team_from': team_code if trans_type in ['waiver', 'loan'] else None,
                    'team_to': team_code if trans_type in ['recall', 'signing', 'activate'] else team_code,
                    'type': trans_type,
                    'description': description,
                    'source_url': url,
                    'source': 'capwages'
                })
            
            logger.info(f"CapWages: Found {len(transactions)} transactions")
            
    except Exception as e:
        logger.error(f"Error scraping CapWages: {e}")
    
    return transactions


def _map_team_name_to_code(team_name: str) -> Optional[str]:
    """Map full team name to 3-letter code"""
    name_lower = team_name.lower()
    
    mapping = {
        'canadiens': 'MTL',
        'maple leafs': 'TOR',
        'bruins': 'BOS',
        'sabres': 'BUF',
        'senators': 'OTT',
        'red wings': 'DET',
        'panthers': 'FLA',
        'lightning': 'TBL',
        'rangers': 'NYR',
        'islanders': 'NYI',
        'flyers': 'PHI',
        'penguins': 'PIT',
        'devils': 'NJD',
        'blue jackets': 'CBJ',
        'hurricanes': 'CAR',
        'capitals': 'WSH',
        'blackhawks': 'CHI',
        'avalanche': 'COL',
        'stars': 'DAL',
        'wild': 'MIN',
        'predators': 'NSH',
        'blues': 'STL',
        'jets': 'WPG',
        'ducks': 'ANA',
        'flames': 'CGY',
        'oilers': 'EDM',
        'kings': 'LAK',
        'sharks': 'SJS',
        'kraken': 'SEA',
        'golden knights': 'VGK',
        'canucks': 'VAN',
        'utah': 'UTA',
        'mammoth': 'UTA'
    }
    
    for keyword, code in mapping.items():
        if keyword in name_lower:
            return code
    
    return None


def _cross_validate_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cross-validate transactions with intelligent filtering:
    - CapWages is trusted for routine roster moves (recalls, waivers, loans, IR)
    - Major transactions (trades, signings) require 2+ sources
    - Groups transactions by player name and date
    """
    if not transactions:
        return []
    
    # Group transactions by player + date combination
    from collections import defaultdict
    
    grouped = defaultdict(list)
    
    for trans in transactions:
        player = trans.get('player_name', '').lower().strip()
        date = trans.get('date')
        
        # Create a key for grouping (player name is primary identifier)
        if player and player != 'unknown player':
            key = f"{player}_{date}"
            grouped[key].append(trans)
    
    # Validate transactions based on type and sources
    validated = []
    
    # Routine transactions that CapWages alone is trusted for
    routine_types = {'recall', 'loan', 'waiver', 'waiver-clear', 'waiver-claim', 'injury', 'activate', 'assign'}
    # Major transactions requiring 2+ sources
    major_types = {'trade', 'signing', 'release'}
    
    for key, trans_group in grouped.items():
        # Get unique sources and transaction type
        sources = set()
        has_capwages = False
        transaction_type = trans_group[0].get('type', 'other')
        
        for trans in trans_group:
            source = trans.get('source', trans.get('source_url', 'unknown'))
            
            # Normalize source names
            if 'capwages' in source:
                sources.add('capwages')
                has_capwages = True
            elif 'nhl.com' in source or 'nhle' in source:
                sources.add('nhl')
            elif 'dailyfaceoff' in source:
                sources.add('dailyfaceoff')
            elif any(team in source for team in NHL_TEAMS.keys()):
                sources.add('team_site')
            else:
                sources.add('other')
        
        # Validation logic
        should_include = False
        
        # CapWages alone is trusted for routine roster moves
        if transaction_type in routine_types and has_capwages:
            should_include = True
            
        # Major transactions require 2+ sources
        elif transaction_type in major_types and len(sources) >= 2:
            should_include = True
            
        # Unknown types require 2+ sources
        elif transaction_type not in routine_types and len(sources) >= 2:
            should_include = True
        
        if should_include:
            # Take the most detailed transaction (longest description)
            best_trans = max(trans_group, key=lambda t: len(t.get('description', '')))
            best_trans['verified_sources'] = list(sources)
            best_trans['source_count'] = len(sources)
            validated.append(best_trans)
            
            reason = 'trusted source' if len(sources) == 1 else f'{len(sources)} sources'
            logger.info(f"✓ Verified: {best_trans['player_name']} - {transaction_type} ({reason}: {', '.join(sources)})")
        else:
            reason = 'major transaction needs 2+ sources' if transaction_type in major_types else 'insufficient sources'
            logger.debug(f"✗ Rejected: {trans_group[0].get('player_name')} ({reason}, {len(sources)} found)")
    
    return validated


def _deduplicate_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate transactions based on description similarity (DEPRECATED - use cross_validate)"""
    if not transactions:
        return []
    
    unique = []
    seen_descriptions = set()
    
    for trans in transactions:
        desc = trans.get('description', '').lower().strip()
        
        # Simple deduplication by exact description
        if desc and desc not in seen_descriptions:
            seen_descriptions.add(desc)
            unique.append(trans)
    
    return unique


def fetch_game_results(date_str: str) -> List[Dict[str, Any]]:
    """
    Fetch game results for a specific date using NHL API
    
    Args:
        date_str: Date in YYYY-MM-DD format
    
    Returns:
        List of game summary dicts
    """
    games = []
    
    try:
        session = create_session()
        
        # NHL scoreboard API
        url = f"{NHL_API_BASE_URL}/v1/score/{date_str}"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            for game in data.get('games', []):
                game_id = str(game.get('id'))
                game_state = game.get('gameState')
                
                # Only process completed games
                if game_state in ['OFF', 'FINAL']:
                    home_team = game.get('homeTeam', {})
                    away_team = game.get('awayTeam', {})
                    
                    # Get team codes from abbreviations
                    home_code = home_team.get('abbrev', 'UNK')
                    away_code = away_team.get('abbrev', 'UNK')
                    
                    # Extract scores
                    home_score = home_team.get('score', 0)
                    away_score = away_team.get('score', 0)
                    
                    # Build highlights from goal scorers
                    goals = game.get('goals', [])
                    highlights_parts = []
                    
                    for goal in goals[:5]:  # Top 5 goals
                        scorer = goal.get('name', {})
                        first = scorer.get('default', '').split()[0] if scorer.get('default') else ''
                        last = scorer.get('default', '').split()[-1] if scorer.get('default') else ''
                        
                        if last:
                            period = goal.get('period')
                            time = goal.get('timeInPeriod', '')
                            highlights_parts.append(f"{first[0]}. {last} (P{period} {time})")
                    
                    highlights = '; '.join(highlights_parts) if highlights_parts else 'No goals scored'
                    
                    # Identify top performers (goal scorers)
                    top_performers = []
                    scorer_counts = {}
                    
                    for goal in goals:
                        scorer_name = goal.get('name', {}).get('default', 'Unknown')
                        scorer_counts[scorer_name] = scorer_counts.get(scorer_name, 0) + 1
                    
                    for player, goals_count in sorted(scorer_counts.items(), key=lambda x: -x[1])[:3]:
                        top_performers.append({
                            'player': player,
                            'goals': goals_count
                        })
                    
                    # Try to get game image (team logo or game photo)
                    image_url = None
                    try:
                        # Try fetching game landing page for og:image
                        game_page_url = f"{NHL_API_BASE_URL.replace('/api-web', '')}/gamecenter/{game_id}"
                        game_resp = session.get(game_page_url, timeout=5)
                        if game_resp.status_code == 200:
                            game_soup = BeautifulSoup(game_resp.content, 'lxml')
                            image_url = extract_image_from_html(game_soup, NHL_API_BASE_URL.replace('/api-web', ''))
                    except Exception as e:
                        logger.debug(f"Could not fetch game image for {game_id}: {e}")
                    
                    # Fallback: Use team logo URL
                    if not image_url:
                        # NHL team logos pattern
                        image_url = f"https://assets.nhle.com/logos/nhl/svg/{home_code}_light.svg"
                    
                    games.append({
                        'game_id': game_id,
                        'date': datetime.strptime(date_str, '%Y-%m-%d').date(),
                        'home_team': home_code,
                        'away_team': away_code,
                        'home_score': home_score,
                        'away_score': away_score,
                        'highlights': highlights,
                        'top_performers': top_performers,
                        'period_summary': {},
                        'game_recap': f"{away_code} {away_score} @ {home_code} {home_score}",
                        'image_url': image_url
                    })
        
        logger.info(f"Fetched {len(games)} completed games for {date_str}")
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        logger.error(f"Error fetching game results for {date_str}: {e}")
    
    return games


def fetch_team_news(team_code: str) -> List[Dict[str, Any]]:
    """
    Fetch news for a specific team
    
    Args:
        team_code: Three-letter team code (e.g., 'MTL', 'TOR')
    
    Returns:
        List of news item dicts
    """
    news_items = []
    
    try:
        if team_code not in NHL_TEAMS:
            logger.warning(f"Unknown team code: {team_code}")
            return news_items
        
        session = create_session()
        team_name_slug = NHL_TEAMS[team_code]['name'].lower().replace(' ', '-')
        
        # NHL team news page
        url = f"https://www.nhl.com/{team_name_slug}/news"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find news articles
            articles = soup.find_all('article', limit=5)
            
            for article in articles:
                title_elem = article.find('h3') or article.find('h2')
                summary_elem = article.find('p')
                link_elem = article.find('a', href=True)
                
                if title_elem:
                    # Extract date from article
                    date_elem = article.find(['time', 'span'], class_=['date', 'published', 'timestamp'])
                    article_text = title_elem.get_text(strip=True) + ' ' + (summary_elem.get_text(strip=True) if summary_elem else '')
                    event_date = extract_date_from_text(date_elem.get_text(strip=True) if date_elem else article_text)
                    
                    news_items.append({
                        'team_code': team_code,
                        'date': event_date,
                        'title': title_elem.get_text(strip=True),
                        'summary': summary_elem.get_text(strip=True) if summary_elem else '',
                        'content': None,
                        'source_url': f"https://www.nhl.com{link_elem['href']}" if link_elem else None
                    })
        
        logger.info(f"Fetched {len(news_items)} news items for {team_code}")
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        logger.error(f"Error fetching team news for {team_code}: {e}")
    
    return news_items


def fetch_player_stats(player_id: str, last_n_games: int = 5) -> Optional[Dict[str, Any]]:
    """
    Fetch recent player statistics
    
    Args:
        player_id: NHL player ID
        last_n_games: Number of recent games to analyze
    
    Returns:
        Player stats dict or None
    """
    try:
        session = create_session()
        
        # NHL player landing page API
        url = f"{NHL_API_BASE_URL}/v1/player/{player_id}/landing"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            player_name = data.get('firstName', {}).get('default', '') + ' ' + data.get('lastName', {}).get('default', '')
            current_team = data.get('currentTeamAbbrev', 'UNK')
            
            # Get recent games stats
            season_stats = data.get('featuredStats', {}).get('regularSeason', {}).get('subSeason', {})
            
            stats = {
                'player_id': player_id,
                'player_name': player_name.strip(),
                'team_code': current_team,
                'games_played': season_stats.get('gamesPlayed', 0),
                'goals': season_stats.get('goals', 0),
                'assists': season_stats.get('assists', 0),
                'points': season_stats.get('points', 0),
                'plus_minus': season_stats.get('plusMinus', 0)
            }
            
            logger.info(f"Fetched stats for player {player_id}")
            time.sleep(REQUEST_DELAY)
            
            return stats
            
    except Exception as e:
        logger.error(f"Error fetching player stats for {player_id}: {e}")
    
    return None


def fetch_league_standings(date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch current NHL standings
    
    Args:
        date_str: Date in YYYY-MM-DD format (optional, defaults to today)
    
    Returns:
        Standings data dict
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    try:
        session = create_session()
        
        url = f"{NHL_API_BASE_URL}/v1/standings/{date_str}"
        response = session.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Fetched league standings for {date_str}")
            time.sleep(REQUEST_DELAY)
            return data
            
    except Exception as e:
        logger.error(f"Error fetching standings for {date_str}: {e}")
    
    return {}


def scrape_capwages_team_depth_chart(team_slug: str) -> Dict[str, Any]:
    """
    Scrape comprehensive team depth chart from CapWages team page
    
    Extracts:
    - Signed roster players (active roster)
    - Signed non-roster players (AHL, minor leagues)
    - Unsigned players (draft picks, rights owned)
    
    Args:
        team_slug: Team URL slug (e.g., 'vegas_golden_knights', 'montreal_canadiens')
    
    Returns:
        Dict containing team_code, team_name, and lists of players by status
    """
    import re
    
    data = {
        'team_slug': team_slug,
        'team_code': None,
        'team_name': None,
        'signed_roster': [],
        'signed_non_roster': [],
        'unsigned': [],
        'total_cap_hit': 0,
        'total_cap_percent': 0.0
    }
    
    try:
        session = create_session()
        session.headers.update({
            'User-Agent': 'HeartBeat-Engine-Bot/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        url = f"https://capwages.com/teams/{team_slug}"
        logger.info(f"Scraping CapWages team depth chart: {url}")
        
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {url}: Status {response.status_code}")
            return data
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract team name from page title or header
        team_name_elem = soup.find('h1')
        if team_name_elem:
            team_name_text = team_name_elem.get_text(strip=True)
            data['team_name'] = team_name_text.strip()
            data['team_code'] = _map_team_name_to_code(team_name_text)
        else:
            title_elem = soup.find('title')
            if title_elem:
                team_name_text = title_elem.get_text(strip=True)
                data['team_name'] = team_name_text.split('-')[0].strip()
                data['team_code'] = _map_team_name_to_code(team_name_text)
        
        logger.info(f"Parsing roster for: {data['team_name']} ({data['team_code']})")
        
        # CapWages structure:
        # - First table: cap summary (skip)
        # - Next few tables after "Draft Picks" header: MAIN ROSTER (forwards, defense, goalies)
        # - Tables after "non-roster" H2 header: NON-ROSTER (AHL/minors)
        # - Table after "Legend" header: UNSIGNED (draft picks/reserve list)
        
        all_tables = soup.find_all('table')
        logger.info(f"Found {len(all_tables)} tables on page")
        
        # Track which section we're in
        non_roster_header = soup.find('h2', string=lambda t: t and 'non-roster' in t.lower())
        legend_header = soup.find('h3', string=lambda t: t and 'legend' in t.lower())
        
        for idx, table in enumerate(all_tables):
            # Skip first table (cap summary)
            if idx == 0:
                continue
            
            # Check table header to identify position type
            rows = table.find_all('tr')
            if not rows or len(rows) < 2:
                continue
            
            # Get first cell text (usually contains position like "forwards (16 - $64M)")
            first_cell = rows[0].find(['th', 'td'])
            if not first_cell:
                continue
            
            header_text = first_cell.get_text(strip=True).lower()
            
            # Determine roster status based on position in page and header text
            roster_status = None
            
            # Check if this table is after "Legend" header (unsigned/draft picks)
            if legend_header and legend_header in table.find_all_previous():
                if 'reserve list' in header_text:
                    roster_status = 'unsigned'
                    logger.info(f"Found section: Unsigned/Reserve List")
            
            # Check if table is after "non-roster" header (non-roster players)
            elif non_roster_header and non_roster_header in table.find_all_previous():
                if any(pos in header_text for pos in ['forward', 'defense', 'goalie']):
                    roster_status = 'non_roster'
                    logger.info(f"Found section: Non-Roster - {header_text}")
            
            # Check for dead cap / retained salary / buyouts
            elif any(kw in header_text for kw in ['retained salary', 'buyout', 'dead cap', 'buried']):
                roster_status = 'dead_cap'
                logger.info(f"Found section: Dead Cap/Retained - {header_text}")
            
            # Otherwise, if it has position info, it's main roster
            elif any(pos in header_text for pos in ['forward', 'defense', 'goalie', 'injured reserve']):
                roster_status = 'roster'
                logger.info(f"Found section: Roster - {header_text}")
            
            # Parse the table if we identified it
            if roster_status:
                players = _parse_capwages_roster_table(table, roster_status, url)
                
                # Mark dead cap players
                if roster_status == 'dead_cap':
                    for player in players:
                        player['dead_cap'] = True
                        player['roster_status'] = 'roster'  # Still part of roster counts
                    data['signed_roster'].extend(players)
                elif roster_status == 'roster':
                    data['signed_roster'].extend(players)
                elif roster_status == 'non_roster':
                    data['signed_non_roster'].extend(players)
                elif roster_status == 'unsigned':
                    data['unsigned'].extend(players)
                
                logger.info(f"  Parsed {len(players)} players")
        
        # Calculate totals
        for player in data['signed_roster']:
            if player.get('cap_hit'):
                data['total_cap_hit'] += player['cap_hit']
            if player.get('cap_percent'):
                data['total_cap_percent'] += player['cap_percent']
        
        logger.info(f"CapWages depth chart complete for {team_slug}: "
                   f"{len(data['signed_roster'])} roster, "
                   f"{len(data['signed_non_roster'])} non-roster, "
                   f"{len(data['unsigned'])} unsigned")
        
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        logger.error(f"Error scraping CapWages team depth chart {team_slug}: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return data


def _parse_capwages_roster_table(table, roster_status: str, source_url: str) -> List[Dict[str, Any]]:
    """
    Parse a CapWages roster table to extract player information
    
    Args:
        table: BeautifulSoup table element
        roster_status: 'signed_roster', 'signed_non_roster', or 'unsigned'
        source_url: URL of the page being scraped
    
    Returns:
        List of player dicts
    """
    players = []
    
    try:
        rows = table.find_all('tr')
        
        if not rows or len(rows) < 2:
            return players
        
        # Get headers to understand column structure
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        logger.debug(f"Table headers: {headers}")
        
        # Parse each player row
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            
            if len(cells) < 2:
                continue
            
            player_data = {
                'roster_status': roster_status,
                'source_url': source_url
            }
            
            # Extract data based on column headers
            for idx, cell in enumerate(cells):
                if idx >= len(headers):
                    break
                
                # Headers may be doubled like "DRAFTED BYDRAFTED BY" or "ageage", clean them
                header = headers[idx].lower().strip()
                
                # Try character-level repetition first (e.g., "ageage" -> "age", "drafted bydrafted by" -> "drafted by")
                if len(header) % 2 == 0 and len(header) > 0:
                    mid = len(header) // 2
                    if header[:mid] == header[mid:]:
                        header = header[:mid]
                        # Clean up any trailing/leading spaces
                        header = header.strip()
                
                cell_text = cell.get_text(strip=True)
                
                # Player name (usually has a link)
                if 'player' in header or 'name' in header or idx == 0:
                    player_link = cell.find('a')
                    if player_link:
                        player_data['player_name'] = player_link.get_text(strip=True)
                        href = player_link.get('href', '')
                        if '/players/' in href:
                            player_data['player_slug'] = href.split('/players/')[-1].strip('/')
                    else:
                        player_data['player_name'] = cell_text
                
                # Position
                elif 'pos' in header or 'position' in header:
                    player_data['position'] = cell_text
                
                # Jersey number
                elif '#' in header or 'number' in header:
                    try:
                        player_data['jersey_number'] = int(cell_text) if cell_text.isdigit() else None
                    except:
                        pass
                
                # Age
                elif 'age' in header:
                    try:
                        player_data['age'] = int(cell_text) if cell_text.isdigit() else None
                    except:
                        pass
                
                # Cap % (appears before year columns)
                elif 'cap%' in header or 'cap %' in header or 'cap percent' in header:
                    cap_pct_str = cell_text.replace('%', '').strip()
                    try:
                        player_data['cap_percent'] = float(cap_pct_str) if cap_pct_str and cap_pct_str != '-' else None
                    except:
                        pass
                
                # Cap Hit from year columns (e.g., "2025-26")
                # Year columns contain the cap hit like "$12,000,000" (often repeated multiple times)
                elif header and len(header) == 7 and '-' in header:  # Matches "2025-26" format
                    # Extract cap hit from first year column if we don't have it yet
                    if not player_data.get('cap_hit'):
                        # The cell may have the value repeated like "$12M$12M$12M"
                        # Split by $ to get individual values
                        if '$' in cell_text:
                            parts = cell_text.split('$')
                            for part in parts:
                                if part.strip():
                                    # Take the first non-empty part
                                    cap_hit_str = part.replace(',', '').strip()
                                    try:
                                        player_data['cap_hit'] = int(cap_hit_str)
                                        break
                                    except:
                                        continue
                
                # Contract expiry
                elif 'expiry' in header or 'exp' in header or 'contract' in header:
                    player_data['contract_expiry'] = cell_text if cell_text and cell_text != '-' else None
                
                # Handed (L/R)
                elif 'hand' in header or 'shoots' in header or 'catches' in header:
                    player_data['handed'] = cell_text if cell_text in ['L', 'R'] else None
                
                # Birthplace
                elif 'birth' in header or 'place' in header:
                    player_data['birthplace'] = cell_text
                
                # Drafted By (team)
                if 'drafted by' in header:
                    player_data['drafted_by'] = cell_text
                
                # Draft Year
                if 'draft year' in header:
                    player_data['draft_year'] = cell_text
                
                # Draft Round
                if header == 'round' or 'round' in header:
                    player_data['draft_round'] = cell_text
                
                # Draft Overall pick
                if 'overall' in header:
                    player_data['draft_overall'] = cell_text
                
                # Must Sign By date (for unsigned players)
                if 'must sign' in header:
                    player_data['must_sign_date'] = cell_text
                
                # Draft info (generic fallback)
                elif 'draft' in header and not player_data.get('draft_year'):
                    player_data['draft_info'] = cell_text
            
            # Only add if we have a player name and it's not a summary/placeholder row
            player_name = player_data.get('player_name', '')
            if player_name:
                # Skip TOTAL rows (summary rows)
                if player_name.upper() == 'TOTAL':
                    continue
                
                # Skip draft pick year placeholders (2026, 2027, 2028, etc.)
                if player_name.isdigit() and len(player_name) == 4:
                    continue
                
                players.append(player_data)
        
    except Exception as e:
        logger.error(f"Error parsing roster table: {e}")
    
    return players


def scrape_capwages_player_profile(player_slug: str) -> Dict[str, Any]:
    """
    Scrape comprehensive player contract and career data from CapWages player profile
    
    Args:
        player_slug: Player URL slug (e.g., 'sidney-crosby')
    
    Returns:
        Dict containing contracts and contract_details (year-by-year breakdown)
    """
    import re
    
    data = {
        'player_name': None,
        'player_id': None,
        'contracts': [],
        'contract_details': []
    }
    
    try:
        session = create_session()
        session.headers.update({
            'User-Agent': 'HeartBeat-Engine-Bot/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        url = f"https://capwages.com/players/{player_slug}"
        logger.info(f"Scraping CapWages player profile: {url}")
        
        response = session.get(url, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {url}: Status {response.status_code}")
            return data
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract player name from page title or header
        player_name_elem = soup.find('h1')
        if player_name_elem:
            player_name_text = player_name_elem.get_text(strip=True)
            data['player_name'] = player_name_text.strip()
            if ',' in data['player_name']:
                parts = data['player_name'].split(',')
                if len(parts) == 2:
                    data['player_name'] = f"{parts[1].strip()} {parts[0].strip()}"
        else:
            title_elem = soup.find('title')
            if title_elem:
                player_name_text = title_elem.get_text(strip=True)
                data['player_name'] = player_name_text.split('-')[0].strip()
        
        # Find all contract sections by looking for section headers followed by tables
        # CapWages uses h3 headers like "35+ Contract (Extension)", "Standard Contract (Extension)"
        all_h3_headers = soup.find_all('h3')
        
        contract_sections = []
        for h3 in all_h3_headers:
            h3_text = h3.get_text(strip=True)
            if any(keyword in h3_text.lower() for keyword in ['contract', 'extension', '35+']):
                contract_sections.append(h3)
        
        logger.info(f"Found {len(contract_sections)} potential contract sections")
        
        for section_idx, section in enumerate(contract_sections):
            try:
                contract_header = section
                contract_type = contract_header.get_text(strip=True)
                
                logger.info(f"Processing contract section: {contract_type}")
                
                # Find the next sibling elements until we hit another h3 or run out
                contract_elements = []
                next_elem = section.find_next_sibling()
                
                while next_elem and next_elem.name != 'h3':
                    contract_elements.append(next_elem)
                    next_elem = next_elem.find_next_sibling()
                
                if not contract_elements:
                    logger.warning(f"No contract elements found for {contract_type}")
                    continue
                
                contract_meta = {}
                
                # Get all text from contract elements (not just <p> tags)
                all_text = '\n'.join([elem.get_text() for elem in contract_elements])
                
                # Extract signed by
                if 'Signed By:' in all_text:
                    signed_by_match = re.search(r'Signed By:\s*([^\n]+)', all_text)
                    if signed_by_match:
                        contract_meta['signed_by'] = signed_by_match.group(1).strip()
                
                # Extract length
                if 'Length:' in all_text:
                    length_match = re.search(r'Length:\s*(\d+)\s*years?', all_text)
                    if length_match:
                        contract_meta['length_years'] = int(length_match.group(1))
                
                # Extract value  
                if 'Value:' in all_text:
                    value_match = re.search(r'Value:\s*\$?([\d,]+)', all_text)
                    if value_match:
                        contract_meta['total_value'] = int(value_match.group(1).replace(',', ''))
                
                # Extract expiry status
                if 'Expiry Status:' in all_text:
                    expiry_match = re.search(r'Expiry Status:\s*([^\n]+)', all_text)
                    if expiry_match:
                        contract_meta['expiry_status'] = expiry_match.group(1).strip()
                
                # Extract signing team
                if 'Signing Team:' in all_text:
                    team_match = re.search(r'Signing Team:\s*([^\n]+)', all_text)
                    if team_match:
                        team_name = team_match.group(1).strip()
                        contract_meta['team_code'] = _map_team_name_to_code(team_name) or team_name[:3].upper()
                
                # Extract signing date
                if 'Signing Date:' in all_text:
                    date_match = re.search(r'Signing Date:\s*([^\n]+)', all_text)
                    if date_match:
                        date_str = date_match.group(1).strip()
                        try:
                            contract_meta['signing_date'] = datetime.strptime(date_str, '%b. %d, %Y').date()
                        except:
                            try:
                                contract_meta['signing_date'] = datetime.strptime(date_str, '%B %d, %Y').date()
                            except:
                                logger.warning(f"Could not parse signing date: {date_str}")
                                contract_meta['signing_date'] = None
                
                logger.info(f"Contract metadata: {contract_meta}")
                
                # Find the table in contract elements
                contract_table = None
                for elem in contract_elements:
                    if elem.name == 'table':
                        contract_table = elem
                        break
                
                contract_data = {
                    'player_name': data['player_name'],
                    'contract_type': contract_type,
                    'team_code': contract_meta.get('team_code') or 'UNK',
                    'signing_date': contract_meta.get('signing_date'),
                    'signed_by': contract_meta.get('signed_by'),
                    'length_years': contract_meta.get('length_years'),
                    'total_value': contract_meta.get('total_value'),
                    'expiry_status': contract_meta.get('expiry_status'),
                    'cap_hit': None,  # Will be populated from contract_details
                    'cap_percent': None,  # Will be populated from contract_details
                    'source_url': url
                }
                
                data['contracts'].append(contract_data)
                
            except Exception as e:
                logger.error(f"Error parsing contract section {section_idx}: {e}")
                continue
        
        # Find ALL tables and process each one appropriately
        all_tables = soup.find_all('table')
        logger.info(f"Found {len(all_tables)} total tables on page")
        
        for table_idx, table in enumerate(all_tables):
            rows = table.find_all('tr')
            
            if not rows or len(rows) < 2:
                continue
                
            headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
            
            # Determine table type
            is_contract_table = all(h in headers for h in ['Season', 'Cap Hit', 'AAV']) or all(h in headers for h in ['Season', 'Base Salary'])
            is_stats_table = all(h in headers for h in ['GP', 'G', 'A', 'P'])
            
            if is_contract_table:
                logger.info(f"Processing contract details table {table_idx} with headers: {headers}")
                # Process contract details - will link to contract_id later
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 3:
                        continue
                    
                    row_data = {}
                    for idx, cell in enumerate(cells):
                        if idx < len(headers):
                            row_data[headers[idx]] = cell.get_text(strip=True)
                    
                    if 'Season' in row_data:
                        season = row_data.get('Season', '')
                        
                        if season == 'TOTAL':
                            continue
                        
                        detail = {
                            'season': season,
                            'clause': row_data.get('Clause'),
                            'cap_hit': None,
                            'cap_percent': None,
                            'aav': None,
                            'performance_bonuses': None,
                            'signing_bonuses': None,
                            'base_salary': None,
                            'total_salary': None,
                            'minors_salary': None
                        }
                        
                        # Parse monetary values
                        if 'Cap Hit' in row_data:
                            cap_hit_str = row_data['Cap Hit'].replace('$', '').replace(',', '')
                            try:
                                detail['cap_hit'] = int(cap_hit_str) if cap_hit_str else None
                            except:
                                pass
                        
                        if 'Cap %' in row_data or 'Cap Percent' in row_data:
                            cap_pct_str = row_data.get('Cap %') or row_data.get('Cap Percent', '')
                            cap_pct_str = cap_pct_str.replace('%', '').strip()
                            try:
                                detail['cap_percent'] = float(cap_pct_str) if cap_pct_str and cap_pct_str != '-' else None
                            except:
                                pass
                        
                        if 'AAV' in row_data:
                            aav_str = row_data['AAV'].replace('$', '').replace(',', '')
                            try:
                                detail['aav'] = int(aav_str) if aav_str else None
                            except:
                                pass
                        
                        if 'P. Bonuses' in row_data:
                            pb_str = row_data['P. Bonuses'].replace('$', '').replace(',', '')
                            try:
                                detail['performance_bonuses'] = int(pb_str) if pb_str else 0
                            except:
                                detail['performance_bonuses'] = 0
                        
                        if 'S. Bonuses' in row_data:
                            sb_str = row_data['S. Bonuses'].replace('$', '').replace(',', '')
                            try:
                                detail['signing_bonuses'] = int(sb_str) if sb_str else 0
                            except:
                                detail['signing_bonuses'] = 0
                        
                        if 'Base Salary' in row_data:
                            bs_str = row_data['Base Salary'].replace('$', '').replace(',', '')
                            try:
                                detail['base_salary'] = int(bs_str) if bs_str else None
                            except:
                                pass
                        
                        if 'Total Salary' in row_data:
                            ts_str = row_data['Total Salary'].replace('$', '').replace(',', '')
                            try:
                                detail['total_salary'] = int(ts_str) if ts_str else None
                            except:
                                pass
                        
                        if 'Minors Salary' in row_data:
                            ms_str = row_data['Minors Salary'].replace('$', '').replace(',', '')
                            try:
                                detail['minors_salary'] = int(ms_str) if ms_str else None
                            except:
                                pass
                        
                        data['contract_details'].append(detail)
                
                continue  # Move to next table
            
            # Player stats scraping removed - focusing only on contract details
            if not is_stats_table:
                continue
        
        logger.info(f"CapWages scrape complete for {player_slug}: {len(data['contracts'])} contracts, {len(data['contract_details'])} details")
        
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        logger.error(f"Error scraping CapWages player profile {player_slug}: {e}")
    
    return data

