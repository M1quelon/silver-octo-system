"""
Модуль для сбора и хранения исторических данных криптовалют
"""
import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
from pycoingecko import CoinGeckoAPI

# Добавляем путь к корневой папке
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

class CryptoHistoryCollector:
    """Сборщик исторических данных криптовалют"""
    
    def __init__(self, db_path: str = "data/historical/crypto_history.db"):
        """
        Инициализация сборщика
        
        Args:
            db_path: Путь к базе данных SQLite
        """
        self.cg = CoinGeckoAPI()
        self.db_path = db_path
        
        # Создаем папку data если её нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Инициализируем базу данных
        self._init_database()
        
        # Список топ-10 монет (ID из CoinGecko)
        self.top_coins = [
            'bitcoin', 'ethereum', 'ripple', 'binancecoin', 'solana',
            'cardano', 'avalanche-2', 'dogecoin', 'tron', 'chainlink'
        ]
    
    def _init_database(self):
        """Создание таблиц в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для дневных данных
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                coin_symbol TEXT NOT NULL,
                date DATE NOT NULL,
                price_usd REAL,
                market_cap REAL,
                volume_24h REAL,
                price_change_24h REAL,
                high_24h REAL,
                low_24h REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin_id, date)
            )
        """)
        
        # Таблица для часовых данных (последние 7 дней)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                coin_symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                price_usd REAL,
                volume_hourly REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin_id, timestamp)
            )
        """)
        
        # Таблица для технических индикаторов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                date DATE NOT NULL,
                rsi_14 REAL,
                ma_7 REAL,
                ma_25 REAL,
                ma_99 REAL,
                volatility_30d REAL,
                trend TEXT,
                support_level REAL,
                resistance_level REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin_id, date)
            )
        """)
        
        # Создаем индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_coin_date ON daily_prices(coin_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hourly_coin_time ON hourly_prices(coin_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_coin_date ON technical_indicators(coin_id, date)")
        
        conn.commit()
        conn.close()
        
        logger.info("База данных инициализирована")
    
    def collect_historical_data(self, days: int = 30) -> Dict[str, Any]:
        """
        Собирает исторические данные за указанное количество дней
        
        Args:
            days: Количество дней истории (по умолчанию 30)
            
        Returns:
            Словарь с результатами сбора
        """
        logger.info(f"Начинаем сбор исторических данных за {days} дней...")
        
        results = {
            'success': [],
            'failed': [],
            'total_records': 0
        }
        
        for coin_id in self.top_coins:
            try:
                logger.info(f"Получаем данные для {coin_id}...")
                
                # Получаем исторические данные с CoinGecko
                history = self.cg.get_coin_market_chart_by_id(
                    id=coin_id,
                    vs_currency='usd',
                    days=days,
                    interval='daily'
                )
                
                # Получаем детальную информацию о монете
                coin_info = self.cg.get_coin_by_id(coin_id)
                symbol = coin_info['symbol'].upper()
                
                # Сохраняем дневные данные
                saved_count = self._save_daily_data(coin_id, symbol, history)
                
                # Вычисляем и сохраняем технические индикаторы
                self._calculate_and_save_indicators(coin_id)
                
                results['success'].append(coin_id)
                results['total_records'] += saved_count
                
                logger.info(f"✅ {coin_id}: сохранено {saved_count} записей")
                
            except Exception as e:
                logger.error(f"❌ Ошибка для {coin_id}: {e}")
                results['failed'].append({'coin': coin_id, 'error': str(e)})
        
        # Собираем часовые данные за последние 7 дней (экономим API: только если собрали дневные успешно)
        if results['success']:
            self._collect_hourly_data(7)
        
        logger.info(f"Сбор завершен. Успешно: {len(results['success'])}, Ошибок: {len(results['failed'])}")
        return results
    
    def _save_daily_data(self, coin_id: str, symbol: str, history: Dict) -> int:
        """Сохраняет дневные данные в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved_count = 0
        
        prices = history.get('prices', [])
        market_caps = history.get('market_caps', [])
        volumes = history.get('total_volumes', [])
        
        for i in range(len(prices)):
            try:
                timestamp = prices[i][0] / 1000  # Конвертируем из миллисекунд
                date = datetime.fromtimestamp(timestamp).date().isoformat()  # Конвертируем в строку
                price = prices[i][1]
                market_cap = market_caps[i][1] if i < len(market_caps) else None
                volume = volumes[i][1] if i < len(volumes) else None
                
                # Вычисляем изменение цены за 24ч
                price_change = None
                if i > 0:
                    prev_price = prices[i-1][1]
                    price_change = ((price - prev_price) / prev_price) * 100
                
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_prices 
                    (coin_id, coin_symbol, date, price_usd, market_cap, volume_24h, price_change_24h)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (coin_id, symbol, date, price, market_cap, volume, price_change))
                
                saved_count += 1
                
            except Exception as e:
                logger.debug(f"Ошибка сохранения записи: {e}")
                continue
        
        conn.commit()
        conn.close()
        return saved_count
    
    def _collect_hourly_data(self, days: int = 7):
        """Собирает часовые данные за последние N дней"""
        logger.info(f"Собираем часовые данные за последние {days} дней...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for coin_id in self.top_coins[:5]:  # Только для топ-5 чтобы не перегружать API
            try:
                # Получаем часовые данные
                history = self.cg.get_coin_market_chart_by_id(
                    id=coin_id,
                    vs_currency='usd',
                    days=days,
                    interval='hourly'
                )
                
                coin_info = self.cg.get_coin_by_id(coin_id)
                symbol = coin_info['symbol'].upper()
                
                prices = history.get('prices', [])
                volumes = history.get('total_volumes', [])
                
                for i in range(len(prices)):
                    timestamp = datetime.fromtimestamp(prices[i][0] / 1000)
                    price = prices[i][1]
                    volume = volumes[i][1] if i < len(volumes) else None
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO hourly_prices 
                        (coin_id, coin_symbol, timestamp, price_usd, volume_hourly)
                        VALUES (?, ?, ?, ?, ?)
                    """, (coin_id, symbol, timestamp, price, volume))
                
            except Exception as e:
                logger.error(f"Ошибка сбора часовых данных для {coin_id}: {e}")
        
        conn.commit()
        conn.close()
    
    def _calculate_and_save_indicators(self, coin_id: str):
        """Вычисляет и сохраняет технические индикаторы"""
        conn = sqlite3.connect(self.db_path)
        
        # Получаем исторические цены
        df = pd.read_sql_query(
            "SELECT date, price_usd FROM daily_prices WHERE coin_id = ? ORDER BY date",
            conn, params=(coin_id,), parse_dates=['date']
        )
        
        if len(df) < 30:
            conn.close()
            return
        
        # Вычисляем скользящие средние
        df['ma_7'] = df['price_usd'].rolling(window=7).mean()
        df['ma_25'] = df['price_usd'].rolling(window=25).mean()
        df['ma_99'] = df['price_usd'].rolling(window=99).mean()
        
        # RSI
        df['rsi_14'] = self._calculate_rsi(df['price_usd'], 14)
        
        # Волатильность (30-дневная)
        df['returns'] = df['price_usd'].pct_change()
        df['volatility_30d'] = df['returns'].rolling(window=30).std() * (365 ** 0.5) * 100
        
        # Определяем тренд
        df['trend'] = df.apply(lambda row: self._determine_trend(row), axis=1)
        
        # Уровни поддержки и сопротивления (простой метод)
        df['support_level'] = df['price_usd'].rolling(window=20).min()
        df['resistance_level'] = df['price_usd'].rolling(window=20).max()
        
        # Сохраняем индикаторы
        cursor = conn.cursor()
        for _, row in df.iterrows():
            if pd.notna(row['ma_7']):  # Пропускаем строки с NaN
                # Конвертируем дату в строку
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                
                cursor.execute("""
                    INSERT OR REPLACE INTO technical_indicators 
                    (coin_id, date, rsi_14, ma_7, ma_25, ma_99, volatility_30d, 
                     trend, support_level, resistance_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    coin_id, date_str, row['rsi_14'], row['ma_7'], 
                    row['ma_25'], row['ma_99'], row['volatility_30d'],
                    row['trend'], row['support_level'], row['resistance_level']
                ))
        
        conn.commit()
        conn.close()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Вычисляет RSI (Relative Strength Index)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _determine_trend(self, row) -> str:
        """Определяет тренд на основе скользящих средних"""
        if pd.isna(row['ma_7']) or pd.isna(row['ma_25']):
            return 'neutral'
        
        price = row['price_usd']
        ma7 = row['ma_7']
        ma25 = row['ma_25']
        
        if price > ma7 > ma25:
            return 'strong_bullish'
        elif price > ma7:
            return 'bullish'
        elif price < ma7 < ma25:
            return 'strong_bearish'
        elif price < ma7:
            return 'bearish'
        else:
            return 'neutral'
    
    def get_historical_summary(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Получает сводку исторических данных для монеты
        
        Args:
            coin_id: ID монеты
            days: Количество дней для анализа
            
        Returns:
            Словарь со сводкой данных
        """
        conn = sqlite3.connect(self.db_path)
        
        # Получаем последние N дней данных
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Основные метрики
        query = """
            SELECT 
                MIN(price_usd) as min_price,
                MAX(price_usd) as max_price,
                AVG(price_usd) as avg_price,
                AVG(volume_24h) as avg_volume,
                MAX(price_usd) - MIN(price_usd) as price_range
            FROM daily_prices
            WHERE coin_id = ? AND date >= ? AND date <= ?
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (coin_id, start_date, end_date))
        metrics = cursor.fetchone()
        
        # Последние индикаторы
        cursor.execute("""
            SELECT * FROM technical_indicators 
            WHERE coin_id = ? 
            ORDER BY date DESC 
            LIMIT 1
        """, (coin_id,))
        
        latest_indicators = cursor.fetchone()
        
        # Тренд за период
        cursor.execute("""
            SELECT 
                date, price_usd, price_change_24h
            FROM daily_prices
            WHERE coin_id = ? AND date >= ? AND date <= ?
            ORDER BY date
        """, (coin_id, start_date, end_date))
        
        price_history = cursor.fetchall()
        
        conn.close()
        
        # Формируем сводку
        summary = {
            'coin_id': coin_id,
            'period_days': days,
            'metrics': {
                'min_price': metrics[0] if metrics else None,
                'max_price': metrics[1] if metrics else None,
                'avg_price': metrics[2] if metrics else None,
                'avg_volume': metrics[3] if metrics else None,
                'price_range': metrics[4] if metrics else None
            },
            'latest_indicators': {
                'rsi_14': latest_indicators[3] if latest_indicators else None,
                'ma_7': latest_indicators[4] if latest_indicators else None,
                'ma_25': latest_indicators[5] if latest_indicators else None,
                'trend': latest_indicators[8] if latest_indicators else None,
                'support': latest_indicators[9] if latest_indicators else None,
                'resistance': latest_indicators[10] if latest_indicators else None
            } if latest_indicators else {},
            'price_history': [
                {
                    'date': row[0],
                    'price': row[1],
                    'change_24h': row[2]
                } for row in price_history
            ] if price_history else []
        }
        
        return summary
    
    def get_all_coins_summary(self) -> List[Dict[str, Any]]:
        """Получает сводку по всем топ-10 монетам"""
        summaries = []
        
        for coin_id in self.top_coins:
            summary = self.get_historical_summary(coin_id, days=30)
            summaries.append(summary)
        
        return summaries


