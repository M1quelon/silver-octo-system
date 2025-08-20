"""
Модуль для парсинга финансовых и криптовалютных новостей
Собирает новости из различных источников и анализирует их влияние на рынки
"""
import os
import sys
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
from urllib.parse import quote
import time

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger(__name__)


class NewsCategory(Enum):
    """Категории новостей"""
    CRYPTO = "crypto"
    STOCKS = "stocks"
    FOREX = "forex"
    COMMODITIES = "commodities"
    POLITICS = "politics"
    REGULATION = "regulation"
    MACRO = "macro"
    TECH = "tech"


class NewsImpact(Enum):
    """Уровень влияния новости на рынок"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEUTRAL = "neutral"


@dataclass
class NewsItem:
    """Структура новости"""
    title: str
    description: str
    url: str
    source: str
    published_at: datetime
    categories: List[NewsCategory]
    impact: NewsImpact
    sentiment: Optional[str] = None
    keywords: List[str] = None
    related_assets: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для сохранения"""
        return {
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'source': self.source,
            'published_at': self.published_at.isoformat(),
            'categories': [cat.value for cat in self.categories],
            'impact': self.impact.value,
            'sentiment': self.sentiment,
            'keywords': self.keywords or [],
            'related_assets': self.related_assets or []
        }


class NewsParser:
    """Основной класс для парсинга новостей"""
    
    def __init__(self):
        """Инициализация парсера"""
        self.config = Config()
        
        # API ключи для платных источников (добавьте в .env)
        self.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        self.alphavantage_key = os.getenv('ALPHAVANTAGE_KEY', '')
        self.finnhub_key = os.getenv('FINNHUB_KEY', '')
        self.cryptopanic_key = os.getenv('CRYPTOPANIC_KEY', '')
        
        # Кэш для избежания дубликатов
        self.seen_urls = set()
        self.news_cache = []
        
        # Ключевые слова для определения важности
        self.high_impact_keywords = [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'gdp',
            'war', 'sanctions', 'regulation', 'ban', 'sec', 'etf',
            'hack', 'exploit', 'bankruptcy', 'collapse', 'crisis',
            'bitcoin', 'ethereum', 'btc', 'eth', 'crypto regulation'
        ]
        
        self.medium_impact_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'merger', 'acquisition',
            'partnership', 'launch', 'update', 'upgrade', 'investment',
            'whale', 'institutional', 'adoption', 'integration'
        ]
        
        # Маппинг активов
        self.asset_mapping = {
            'bitcoin': ['BTC', 'XBT'],
            'ethereum': ['ETH'],
            'gold': ['XAU', 'GLD'],
            'oil': ['CL', 'WTI', 'BRENT'],
            'dollar': ['DXY', 'USD'],
            's&p': ['SPX', 'SPY'],
            'nasdaq': ['NDX', 'QQQ']
        }
    
    async def collect_all_news(self) -> List[NewsItem]:
        """Собирает новости из всех источников"""
        logger.info("Начинаем сбор новостей из всех источников...")
        
        all_news = []
        
        # Собираем новости параллельно
        tasks = [
            self._get_rss_news(),
            self._get_newsapi_news(),
            self._get_cryptopanic_news(),
            self._get_finnhub_news(),
            self._get_coindesk_news(),
            self._get_bloomberg_crypto_news(),
            self._get_reuters_news()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка при сборе новостей: {result}")
        
        # Фильтруем дубликаты
        unique_news = self._filter_duplicates(all_news)
        
        # Сортируем по времени и важности
        def sort_key(item):
            # Приводим все даты к UTC для корректного сравнения
            if item.published_at.tzinfo is None:
                # Если дата без часового пояса, считаем её UTC
                dt = item.published_at.replace(tzinfo=None)
            else:
                # Если дата с часовым поясом, конвертируем в UTC
                dt = item.published_at.astimezone().replace(tzinfo=None)
            return (dt, item.impact.value)
        
        sorted_news = sorted(
            unique_news,
            key=sort_key,
            reverse=True
        )
        
        logger.info(f"Собрано {len(sorted_news)} уникальных новостей")
        return sorted_news[:50]  # Возвращаем топ-50 новостей
    
    async def _get_rss_news(self) -> List[NewsItem]:
        """Получает новости из RSS фидов (бесплатно)"""
        news_items = []
        
        rss_feeds = {
            'CoinDesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'CoinTelegraph': 'https://cointelegraph.com/rss',
            'Bitcoin.com': 'https://news.bitcoin.com/feed/',
            'TheBlock': 'https://www.theblock.co/rss.xml',
            'Decrypt': 'https://decrypt.co/feed',
            'YahooFinance': 'https://finance.yahoo.com/rss/',
            'MarketWatch': 'https://feeds.marketwatch.com/marketwatch/topstories/',
            'WSJ Markets': 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml'
        }
        
        for source, url in rss_feeds.items():
            try:
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:10]:  # Берем последние 10 новостей
                    # Парсим дату
                    published = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        except Exception:
                            published = datetime.now()
                    elif hasattr(entry, 'published'):
                        try:
                            # Используем feedparser для парсинга даты
                            parsed_date = feedparser._parse_date(entry.published)
                            if parsed_date:
                                published = datetime.fromtimestamp(time.mktime(parsed_date))
                        except Exception:
                            published = datetime.now()
                    
                    # Определяем категории и важность
                    categories = self._determine_categories(entry.title + ' ' + entry.get('summary', ''))
                    impact = self._determine_impact(entry.title + ' ' + entry.get('summary', ''))
                    
                    news_item = NewsItem(
                        title=entry.title,
                        description=entry.get('summary', '')[:500],
                        url=entry.link,
                        source=source,
                        published_at=published,
                        categories=categories,
                        impact=impact,
                        keywords=self._extract_keywords(entry.title),
                        related_assets=self._extract_assets(entry.title + ' ' + entry.get('summary', ''))
                    )
                    
                    news_items.append(news_item)
                    
            except Exception as e:
                logger.error(f"Ошибка парсинга RSS {source}: {e}")
                continue
        
        return news_items
    
    async def _get_newsapi_news(self) -> List[NewsItem]:
        """Получает новости через NewsAPI (требует ключ)"""
        if not self.newsapi_key:
            logger.warning("NewsAPI ключ не настроен")
            return []
        
        news_items = []
        
        # Запросы для разных категорий
        queries = [
            'cryptocurrency OR bitcoin OR ethereum',
            'federal reserve OR interest rate',
            'stock market OR S&P 500',
            'gold price OR oil price',
            'inflation OR GDP'
        ]
        
        async with aiohttp.ClientSession() as session:
            for query in queries:
                try:
                    url = f"https://newsapi.org/v2/everything"
                    params = {
                        'q': query,
                        'apiKey': self.newsapi_key,
                        'language': 'en',
                        'sortBy': 'publishedAt',
                        'pageSize': 10
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for article in data.get('articles', []):
                                published = datetime.fromisoformat(
                                    article['publishedAt'].replace('Z', '+00:00')
                                )
                                
                                categories = self._determine_categories(
                                    article['title'] + ' ' + (article['description'] or '')
                                )
                                impact = self._determine_impact(
                                    article['title'] + ' ' + (article['description'] or '')
                                )
                                
                                news_item = NewsItem(
                                    title=article['title'],
                                    description=(article['description'] or '')[:500],
                                    url=article['url'],
                                    source=article['source']['name'],
                                    published_at=published,
                                    categories=categories,
                                    impact=impact,
                                    keywords=self._extract_keywords(article['title']),
                                    related_assets=self._extract_assets(
                                        article['title'] + ' ' + (article['description'] or '')
                                    )
                                )
                                
                                news_items.append(news_item)
                        
                except Exception as e:
                    logger.error(f"Ошибка NewsAPI для запроса '{query}': {e}")
                    continue
        
        return news_items
    
    async def _get_cryptopanic_news(self) -> List[NewsItem]:
        """Получает криптоновости с CryptoPanic (требует ключ)"""
        if not self.cryptopanic_key:
            logger.warning("CryptoPanic ключ не настроен")
            return []
        
        news_items = []
        
        try:
            url = f"https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': self.cryptopanic_key,
                'kind': 'news',
                'filter': 'important'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for result in data.get('results', [])[:20]:
                            published = datetime.fromisoformat(
                                result['published_at'].replace('Z', '+00:00')
                            )
                            
                            # CryptoPanic уже предоставляет оценку важности
                            impact_map = {
                                'positive': NewsImpact.MEDIUM,
                                'negative': NewsImpact.HIGH,
                                'important': NewsImpact.HIGH,
                                'neutral': NewsImpact.LOW
                            }
                            
                            impact = impact_map.get(
                                result.get('kind', 'neutral'),
                                NewsImpact.LOW
                            )
                            
                            # Извлекаем связанные валюты
                            related_assets = []
                            for currency in result.get('currencies', []):
                                related_assets.append(currency['code'])
                            
                            news_item = NewsItem(
                                title=result['title'],
                                description=result.get('summary', '')[:500],
                                url=result.get('url', ''),
                                source=result.get('source', {}).get('title', 'CryptoPanic'),
                                published_at=published,
                                categories=[NewsCategory.CRYPTO],
                                impact=impact,
                                sentiment=result.get('kind'),
                                keywords=self._extract_keywords(result['title']),
                                related_assets=related_assets
                            )
                            
                            news_items.append(news_item)
                    
        except Exception as e:
            logger.error(f"Ошибка CryptoPanic: {e}")
        
        return news_items
    
    async def _get_finnhub_news(self) -> List[NewsItem]:
        """Получает финансовые новости с Finnhub (требует ключ)"""
        if not self.finnhub_key:
            logger.warning("Finnhub ключ не настроен")
            return []
        
        news_items = []
        
        try:
            # Новости по категориям
            categories = ['general', 'forex', 'crypto', 'merger']
            
            async with aiohttp.ClientSession() as session:
                for category in categories:
                    url = f"https://finnhub.io/api/v1/news"
                    params = {
                        'category': category,
                        'token': self.finnhub_key
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for article in data[:10]:
                                published = datetime.fromtimestamp(article['datetime'])
                                
                                # Маппинг категорий Finnhub на наши
                                category_map = {
                                    'general': [NewsCategory.STOCKS, NewsCategory.MACRO],
                                    'forex': [NewsCategory.FOREX],
                                    'crypto': [NewsCategory.CRYPTO],
                                    'merger': [NewsCategory.STOCKS]
                                }
                                
                                news_categories = category_map.get(category, [NewsCategory.STOCKS])
                                impact = self._determine_impact(article['headline'] + ' ' + article['summary'])
                                
                                news_item = NewsItem(
                                    title=article['headline'],
                                    description=article['summary'][:500],
                                    url=article['url'],
                                    source=article['source'],
                                    published_at=published,
                                    categories=news_categories,
                                    impact=impact,
                                    keywords=self._extract_keywords(article['headline']),
                                    related_assets=self._extract_assets(
                                        article['headline'] + ' ' + article['summary']
                                    )
                                )
                                
                                news_items.append(news_item)
                        
        except Exception as e:
            logger.error(f"Ошибка Finnhub: {e}")
        
        return news_items
    
    async def _get_coindesk_news(self) -> List[NewsItem]:
        """Парсит новости с CoinDesk (без API)"""
        news_items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://www.coindesk.com/') as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Ищем новостные блоки (структура может меняться)
                        articles = soup.find_all('article', limit=10)
                        
                        for article in articles:
                            try:
                                # Извлекаем заголовок
                                title_elem = article.find(['h2', 'h3', 'h4'])
                                if not title_elem:
                                    continue
                                    
                                title = title_elem.get_text(strip=True)
                                
                                # Извлекаем ссылку
                                link_elem = article.find('a')
                                if not link_elem:
                                    continue
                                    
                                url = link_elem.get('href', '')
                                if not url.startswith('http'):
                                    url = f"https://www.coindesk.com{url}"
                                
                                # Извлекаем описание
                                desc_elem = article.find('p')
                                description = desc_elem.get_text(strip=True) if desc_elem else ''
                                
                                categories = self._determine_categories(title + ' ' + description)
                                impact = self._determine_impact(title + ' ' + description)
                                
                                news_item = NewsItem(
                                    title=title,
                                    description=description[:500],
                                    url=url,
                                    source='CoinDesk',
                                    published_at=datetime.now() - timedelta(hours=1),  # Примерное время
                                    categories=categories,
                                    impact=impact,
                                    keywords=self._extract_keywords(title),
                                    related_assets=self._extract_assets(title + ' ' + description)
                                )
                                
                                news_items.append(news_item)
                                
                            except Exception as e:
                                logger.debug(f"Ошибка парсинга статьи CoinDesk: {e}")
                                continue
                                
        except Exception as e:
            logger.error(f"Ошибка парсинга CoinDesk: {e}")
        
        return news_items
    
    async def _get_bloomberg_crypto_news(self) -> List[NewsItem]:
        """Парсит криптоновости Bloomberg (базовый парсинг)"""
        news_items = []
        
        try:
            # Bloomberg имеет защиту, используем их RSS если доступен
            rss_url = "https://www.bloomberg.com/crypto/rss"
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:10]:
                published = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    except Exception:
                        published = datetime.now()
                elif hasattr(entry, 'published'):
                    try:
                        parsed_date = feedparser._parse_date(entry.published)
                        if parsed_date:
                            published = datetime.fromtimestamp(time.mktime(parsed_date))
                    except Exception:
                        published = datetime.now()
                
                categories = [NewsCategory.CRYPTO, NewsCategory.MACRO]
                impact = self._determine_impact(entry.title + ' ' + entry.get('summary', ''))
                
                news_item = NewsItem(
                    title=entry.title,
                    description=entry.get('summary', '')[:500],
                    url=entry.link,
                    source='Bloomberg Crypto',
                    published_at=published,
                    categories=categories,
                    impact=impact,
                    keywords=self._extract_keywords(entry.title),
                    related_assets=self._extract_assets(entry.title + ' ' + entry.get('summary', ''))
                )
                
                news_items.append(news_item)
                
        except Exception as e:
            logger.error(f"Ошибка парсинга Bloomberg Crypto: {e}")
        
        return news_items
    
    async def _get_reuters_news(self) -> List[NewsItem]:
        """Получает новости Reuters через RSS"""
        news_items = []
        
        reuters_feeds = {
            'Business': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
            'Markets': 'https://www.reutersagency.com/feed/?best-categories=markets',
            'Finance': 'https://www.reutersagency.com/feed/?best-categories=finance'
        }
        
        for category, url in reuters_feeds.items():
            try:
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:5]:
                    published = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        except Exception:
                            published = datetime.now()
                    elif hasattr(entry, 'published'):
                        try:
                            parsed_date = feedparser._parse_date(entry.published)
                            if parsed_date:
                                published = datetime.fromtimestamp(time.mktime(parsed_date))
                        except Exception:
                            published = datetime.now()
                    
                    categories = self._determine_categories(entry.title + ' ' + entry.get('summary', ''))
                    impact = self._determine_impact(entry.title + ' ' + entry.get('summary', ''))
                    
                    news_item = NewsItem(
                        title=entry.title,
                        description=entry.get('summary', '')[:500],
                        url=entry.link,
                        source=f'Reuters {category}',
                        published_at=published,
                        categories=categories,
                        impact=impact,
                        keywords=self._extract_keywords(entry.title),
                        related_assets=self._extract_assets(entry.title + ' ' + entry.get('summary', ''))
                    )
                    
                    news_items.append(news_item)
                    
            except Exception as e:
                logger.error(f"Ошибка парсинга Reuters {category}: {e}")
                continue
        
        return news_items
    
    def _determine_categories(self, text: str) -> List[NewsCategory]:
        """Определяет категории новости по тексту"""
        text_lower = text.lower()
        categories = []
        
        # Криптовалюты
        crypto_keywords = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi', 'nft', 'altcoin']
        if any(keyword in text_lower for keyword in crypto_keywords):
            categories.append(NewsCategory.CRYPTO)
        
        # Акции
        stock_keywords = ['stock', 'share', 'nasdaq', 's&p', 'dow jones', 'equity', 'ipo']
        if any(keyword in text_lower for keyword in stock_keywords):
            categories.append(NewsCategory.STOCKS)
        
        # Форекс
        forex_keywords = ['forex', 'currency', 'dollar', 'euro', 'yen', 'pound', 'exchange rate']
        if any(keyword in text_lower for keyword in forex_keywords):
            categories.append(NewsCategory.FOREX)
        
        # Сырьевые товары
        commodity_keywords = ['gold', 'silver', 'oil', 'gas', 'commodity', 'metal', 'wheat', 'corn']
        if any(keyword in text_lower for keyword in commodity_keywords):
            categories.append(NewsCategory.COMMODITIES)
        
        # Политика
        politics_keywords = ['election', 'president', 'congress', 'senate', 'policy', 'government']
        if any(keyword in text_lower for keyword in politics_keywords):
            categories.append(NewsCategory.POLITICS)
        
        # Регулирование
        regulation_keywords = ['regulation', 'sec', 'cftc', 'ban', 'law', 'legal', 'compliance']
        if any(keyword in text_lower for keyword in regulation_keywords):
            categories.append(NewsCategory.REGULATION)
        
        # Макроэкономика
        macro_keywords = ['inflation', 'gdp', 'unemployment', 'interest rate', 'fed', 'central bank']
        if any(keyword in text_lower for keyword in macro_keywords):
            categories.append(NewsCategory.MACRO)
        
        # Технологии
        tech_keywords = ['technology', 'ai', 'software', 'hardware', 'innovation', 'startup']
        if any(keyword in text_lower for keyword in tech_keywords):
            categories.append(NewsCategory.TECH)
        
        # Если категории не определены, ставим MACRO по умолчанию
        if not categories:
            categories = [NewsCategory.MACRO]
        
        return list(set(categories))  # Убираем дубликаты
    
    def _determine_impact(self, text: str) -> NewsImpact:
        """Определяет уровень влияния новости на рынок"""
        text_lower = text.lower()
        
        # Проверяем высокий уровень влияния
        for keyword in self.high_impact_keywords:
            if keyword in text_lower:
                return NewsImpact.HIGH
        
        # Проверяем средний уровень влияния
        for keyword in self.medium_impact_keywords:
            if keyword in text_lower:
                return NewsImpact.MEDIUM
        
        # Дополнительные проверки
        if any(word in text_lower for word in ['breaking', 'urgent', 'alert', 'crash', 'surge']):
            return NewsImpact.HIGH
        
        if any(word in text_lower for word in ['update', 'report', 'analysis', 'forecast']):
            return NewsImpact.MEDIUM
        
        return NewsImpact.LOW
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста"""
        # Простая реализация - можно улучшить с помощью NLP
        words = text.lower().split()
        
        # Стоп-слова
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'been', 'be'}
        
        # Фильтруем и берем значимые слова
        keywords = []
        for word in words:
            word = word.strip('.,!?;:"')
            if len(word) > 3 and word not in stop_words:
                keywords.append(word)
        
        # Возвращаем топ-5 уникальных ключевых слов
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:5]
    
    def _extract_assets(self, text: str) -> List[str]:
        """Извлекает упоминания активов из текста"""
        text_lower = text.lower()
        assets = []
        
        for asset_name, symbols in self.asset_mapping.items():
            if asset_name in text_lower:
                assets.extend(symbols)
            for symbol in symbols:
                if symbol.lower() in text_lower:
                    assets.append(symbol)
        
        # Дополнительный поиск тикеров
        import re
        # Ищем паттерны типа BTC, ETH, AAPL и т.д.
        ticker_pattern = r'\b[A-Z]{2,5}\b'
        potential_tickers = re.findall(ticker_pattern, text)
        
        for ticker in potential_tickers:
            if len(ticker) >= 3 and ticker not in ['USD', 'EUR', 'GBP', 'JPY']:
                assets.append(ticker)
        
        return list(set(assets))[:5]  # Уникальные, максимум 5
    
    def _filter_duplicates(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Фильтрует дубликаты новостей"""
        unique_news = []
        
        for item in news_items:
            # Проверяем по URL
            if item.url in self.seen_urls:
                continue
            
            # Проверяем по схожести заголовков
            is_duplicate = False
            for existing in unique_news:
                # Простая проверка на схожесть (можно улучшить с помощью fuzzy matching)
                if (item.title.lower() == existing.title.lower() or
                    (len(item.title) > 20 and item.title[:20].lower() == existing.title[:20].lower())):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                self.seen_urls.add(item.url)
                unique_news.append(item)
        
        return unique_news
    
    def get_market_summary(self, news_items: List[NewsItem]) -> Dict[str, Any]:
        """Создает сводку по новостям для анализа"""
        summary = {
            'total_news': len(news_items),
            'by_category': {},
            'by_impact': {},
            'top_assets': {},
            'sentiment_distribution': {},
            'key_events': []
        }
        
        # Подсчет по категориям
        for item in news_items:
            for category in item.categories:
                summary['by_category'][category.value] = summary['by_category'].get(category.value, 0) + 1
        
        # Подсчет по влиянию
        for item in news_items:
            summary['by_impact'][item.impact.value] = summary['by_impact'].get(item.impact.value, 0) + 1
        
        # Топ упоминаемых активов
        asset_mentions = {}
        for item in news_items:
            if item.related_assets:
                for asset in item.related_assets:
                    asset_mentions[asset] = asset_mentions.get(asset, 0) + 1
        
        summary['top_assets'] = dict(sorted(asset_mentions.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Ключевые события (высокий impact)
        high_impact_news = [item for item in news_items if item.impact == NewsImpact.HIGH]
        summary['key_events'] = [
            {
                'title': item.title,
                'source': item.source,
                'categories': [cat.value for cat in item.categories],
                'assets': item.related_assets or []
            }
            for item in high_impact_news[:5]
        ]
        
        return summary


 