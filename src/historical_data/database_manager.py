"""
Менеджер базы данных для исторических данных криптовалют
"""
import os
import sys
import sqlite3
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

# Добавляем путь к корневой папке
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных для исторических данных"""
    
    def __init__(self, db_path: str = "data/historical/crypto_history.db"):
        self.db_path = db_path
        
        # Создаем папку если её нет
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Инициализируем базу данных
        self._init_database()
        
        logger.info(f"База данных инициализирована: {db_path}")
    
    def _init_database(self):
        """Создает таблицы в базе данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица дневных данных
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                market_cap REAL,
                circulating_supply REAL,
                total_supply REAL,
                fdv REAL,
                price_change_24h REAL,
                volume_change_24h REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin_id, date)
            )
        """)
        
        # Таблица метаданных монет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_metadata (
                coin_id TEXT PRIMARY KEY,
                name TEXT,
                symbol TEXT,
                launch_date DATE,
                max_supply REAL,
                current_supply REAL,
                algorithm TEXT,
                consensus TEXT,
                description TEXT,
                website TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица технических индикаторов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                date DATE NOT NULL,
                rsi_14 REAL,
                ma_7 REAL,
                ma_25 REAL,
                ma_99 REAL,
                bollinger_upper REAL,
                bollinger_lower REAL,
                bollinger_middle REAL,
                atr_14 REAL,
                macd_line REAL,
                macd_signal REAL,
                macd_histogram REAL,
                volatility_30d REAL,
                support_level REAL,
                resistance_level REAL,
                trend TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin_id, date)
            )
        """)
        
        # Таблица корреляций
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin1_id TEXT NOT NULL,
                coin2_id TEXT NOT NULL,
                date DATE NOT NULL,
                correlation_30d REAL,
                correlation_90d REAL,
                correlation_365d REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin1_id, coin2_id, date)
            )
        """)
        
        # Таблица статистики сбора
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                collection_date DATE NOT NULL,
                records_added INTEGER,
                records_updated INTEGER,
                errors_count INTEGER,
                collection_time_seconds REAL,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индексы для быстрого поиска
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_coin_date ON daily_prices(coin_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_indicators_coin_date ON technical_indicators(coin_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_correlations_coins_date ON correlations(coin1_id, coin2_id, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_coin_date ON collection_stats(coin_id, collection_date)")
        
        conn.commit()
        conn.close()
        
        logger.info("Таблицы и индексы созданы")
    
    def save_daily_data(self, coin_id: str, data: List[Dict[str, Any]]) -> int:
        """Сохраняет дневные данные в БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        updated_count = 0
        
        for record in data:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO daily_prices 
                    (coin_id, date, open, high, low, close, volume, market_cap, 
                     circulating_supply, total_supply, fdv, price_change_24h, volume_change_24h)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    coin_id,
                    record['date'],
                    record.get('open'),
                    record.get('high'),
                    record.get('low'),
                    record.get('close'),
                    record.get('volume'),
                    record.get('market_cap'),
                    record.get('circulating_supply'),
                    record.get('total_supply'),
                    record.get('fdv'),
                    record.get('price_change_24h'),
                    record.get('volume_change_24h')
                ))
                
                if cursor.rowcount > 0:
                    saved_count += 1
                else:
                    updated_count += 1
                    
            except Exception as e:
                logger.error(f"Ошибка сохранения записи для {coin_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Сохранено {saved_count} новых и обновлено {updated_count} записей для {coin_id}")
        return saved_count + updated_count
    
    def save_coin_metadata(self, coin_id: str, metadata: Dict[str, Any]) -> bool:
        """Сохраняет метаданные монеты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO coin_metadata 
                (coin_id, name, symbol, launch_date, max_supply, current_supply, 
                 algorithm, consensus, description, website)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coin_id,
                metadata.get('name'),
                metadata.get('symbol'),
                metadata.get('launch_date'),
                metadata.get('max_supply'),
                metadata.get('current_supply'),
                metadata.get('algorithm'),
                metadata.get('consensus'),
                metadata.get('description'),
                metadata.get('website')
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Метаданные сохранены для {coin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения метаданных для {coin_id}: {e}")
            conn.close()
            return False
    
    def save_technical_indicators(self, coin_id: str, indicators: List[Dict[str, Any]]) -> int:
        """Сохраняет технические индикаторы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        
        for indicator in indicators:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO technical_indicators 
                    (coin_id, date, rsi_14, ma_7, ma_25, ma_99, bollinger_upper, 
                     bollinger_lower, bollinger_middle, atr_14, macd_line, 
                     macd_signal, macd_histogram, volatility_30d, support_level, 
                     resistance_level, trend)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    coin_id,
                    indicator['date'],
                    indicator.get('rsi_14'),
                    indicator.get('ma_7'),
                    indicator.get('ma_25'),
                    indicator.get('ma_99'),
                    indicator.get('bollinger_upper'),
                    indicator.get('bollinger_lower'),
                    indicator.get('bollinger_middle'),
                    indicator.get('atr_14'),
                    indicator.get('macd_line'),
                    indicator.get('macd_signal'),
                    indicator.get('macd_histogram'),
                    indicator.get('volatility_30d'),
                    indicator.get('support_level'),
                    indicator.get('resistance_level'),
                    indicator.get('trend')
                ))
                
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Ошибка сохранения индикатора для {coin_id}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Сохранено {saved_count} технических индикаторов для {coin_id}")
        return saved_count
    
    def save_collection_stats(self, coin_id: str, stats: Dict[str, Any]) -> bool:
        """Сохраняет статистику сбора данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO collection_stats 
                (coin_id, collection_date, records_added, records_updated, 
                 errors_count, collection_time_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                coin_id,
                stats.get('collection_date'),
                stats.get('records_added', 0),
                stats.get('records_updated', 0),
                stats.get('errors_count', 0),
                stats.get('collection_time_seconds', 0),
                stats.get('status', 'unknown')
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Статистика сбора сохранена для {coin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики для {coin_id}: {e}")
            conn.close()
            return False
    
    def get_daily_data(self, coin_id: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """Получает дневные данные из БД"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM daily_prices WHERE coin_id = ?"
        params = [coin_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        conn.close()
        
        return df
    
    def get_technical_indicators(self, coin_id: str, start_date: date = None, end_date: date = None) -> pd.DataFrame:
        """Получает технические индикаторы из БД"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM technical_indicators WHERE coin_id = ?"
        params = [coin_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['date'])
        conn.close()
        
        return df
    
    def get_daily_data_compact(
        self,
        coin_id: str,
        start_date: date = None,
        end_date: date = None,
        columns: Tuple[str, ...] = ("date", "close", "volume"),
    ) -> pd.DataFrame:
        """Возвращает компактные дневные данные (только нужные колонки)"""
        conn = sqlite3.connect(self.db_path)
        # Безопасная фильтрация допустимых колонок
        allowed = {"date", "open", "high", "low", "close", "volume", "market_cap"}
        cols = [c for c in columns if c in allowed]
        if not cols:
            cols = ["date", "close", "volume"]
        cols_sql = ", ".join(cols)
        
        query = f"SELECT {cols_sql} FROM daily_prices WHERE coin_id = ?"
        params = [coin_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])  # type: ignore[arg-type]
        conn.close()
        return df

    def get_coin_metadata(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """Получает метаданные монеты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM coin_metadata WHERE coin_id = ?", (coin_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            columns = ['coin_id', 'name', 'symbol', 'launch_date', 'max_supply', 
                      'current_supply', 'algorithm', 'consensus', 'description', 'website', 'last_updated']
            return dict(zip(columns, row))
        
        return None
    
    def get_collection_stats(self, coin_id: str = None) -> pd.DataFrame:
        """Получает статистику сбора данных"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM collection_stats"
        params = []
        
        if coin_id:
            query += " WHERE coin_id = ?"
            params.append(coin_id)
        
        query += " ORDER BY created_at DESC"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['created_at', 'collection_date'])
        conn.close()
        
        return df
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Получает общую статистику базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Количество записей в каждой таблице
        tables = ['daily_prices', 'technical_indicators', 'correlations', 'collection_stats', 'seasonal_events', 'holiday_performance', 'seasonal_patterns']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f'{table}_count'] = cursor.fetchone()[0]
        
        # Количество уникальных монет
        cursor.execute("SELECT COUNT(DISTINCT coin_id) FROM daily_prices")
        stats['unique_coins'] = cursor.fetchone()[0]
        
        # Диапазон дат
        cursor.execute("SELECT MIN(date), MAX(date) FROM daily_prices")
        date_range = cursor.fetchone()
        if date_range[0]:
            stats['date_range'] = {
                'start': date_range[0],
                'end': date_range[1]
            }
        
        # Размер базы данных
        cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
        size_bytes = cursor.fetchone()[0]
        stats['database_size_mb'] = size_bytes / (1024 * 1024)
        
        conn.close()
        
        return stats
    
    def get_last_daily_date(self, coin_id: str) -> Optional[date]:
        """Возвращает последнюю дату, сохранённую для указанной монеты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT MAX(date) FROM daily_prices WHERE coin_id = ?", (coin_id,))
            row = cursor.fetchone()
            if row and row[0]:
                # Дата хранится как TEXT (YYYY-MM-DD), конвертируем в date
                return datetime.fromisoformat(row[0]).date()
            return None
        finally:
            conn.close()

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С СЕЗОННЫМИ ДАННЫМИ =====
    
    def get_current_seasonal_events(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Получает текущие и ближайшие сезонные события"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем события на сегодня и ближайшие дни
        query = """
        SELECT 
            event_name,
            event_type,
            date_pattern,
            description,
            expected_impact,
            region,
            importance_level,
            CASE 
                WHEN strftime('%m-%d', 'now') = date_pattern THEN 0
                ELSE julianday(strftime('%Y-%m-%d', 'now', '+' || date_pattern || ' days')) - julianday('now')
            END as days_until_event
        FROM seasonal_events 
        WHERE date_pattern = strftime('%m-%d', 'now')
           OR julianday(strftime('%Y-%m-%d', 'now', '+' || date_pattern || ' days')) - julianday('now') <= ?
        ORDER BY importance_level DESC, days_until_event ASC
        """
        
        cursor.execute(query, (days_ahead,))
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            events.append({
                'event_name': row[0],
                'event_type': row[1],
                'date_pattern': row[2],
                'description': row[3],
                'expected_impact': row[4],
                'region': row[5],
                'importance_level': row[6],
                'days_until_event': row[7]
            })
        
        conn.close()
        return events
    
    def get_holiday_performance(self, coin_id: str, event_name: str = None, years_back: int = 5) -> pd.DataFrame:
        """Получает исторические данные по праздничным дням"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            hp.*,
            se.event_name,
            se.event_type,
            se.expected_impact
        FROM holiday_performance hp
        JOIN seasonal_events se ON hp.event_id = se.id
        WHERE hp.coin_id = ?
        """
        params = [coin_id]
        
        if event_name:
            query += " AND se.event_name = ?"
            params.append(event_name)
        
        query += " AND hp.year >= strftime('%Y', 'now') - ?"
        params.append(years_back)
        
        query += " ORDER BY hp.year DESC, hp.date DESC"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['date', 'created_at'])
        conn.close()
        
        return df
    
    def save_holiday_performance(self, coin_id: str, event_name: str, year: int, 
                                performance_data: Dict[str, Any]) -> bool:
        """Сохраняет данные о производительности в праздничный день"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Получаем ID события
            cursor.execute("SELECT id FROM seasonal_events WHERE event_name = ?", (event_name,))
            event_id = cursor.fetchone()
            
            if not event_id:
                logger.warning(f"Событие '{event_name}' не найдено в базе")
                return False
            
            event_id = event_id[0]
            
            # Вставляем или обновляем данные
            cursor.execute("""
                INSERT OR REPLACE INTO holiday_performance 
                (event_id, coin_id, year, date, price_before, price_after, price_change_percent,
                 volume_before, volume_after, volume_change_percent, volatility_before, 
                 volatility_after, trend_before, trend_after, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, coin_id, year, performance_data.get('date'),
                performance_data.get('price_before'), performance_data.get('price_after'),
                performance_data.get('price_change_percent'), performance_data.get('volume_before'),
                performance_data.get('volume_after'), performance_data.get('volume_change_percent'),
                performance_data.get('volatility_before'), performance_data.get('volatility_after'),
                performance_data.get('trend_before'), performance_data.get('trend_after'),
                performance_data.get('notes')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения holiday_performance: {e}")
            conn.close()
            return False
    
    def get_seasonal_patterns(self, coin_id: str, pattern_type: str = None) -> pd.DataFrame:
        """Получает сезонные паттерны для монеты"""
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM seasonal_patterns WHERE coin_id = ?"
        params = [coin_id]
        
        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)
        
        query += " ORDER BY confidence_level DESC, success_rate DESC"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['created_at'])
        conn.close()
        
        return df
    
    def save_seasonal_pattern(self, coin_id: str, pattern_data: Dict[str, Any]) -> bool:
        """Сохраняет сезонный паттерн"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO seasonal_patterns 
                (coin_id, pattern_type, period_start, period_end, avg_price_change,
                 avg_volume_change, success_rate, sample_size, confidence_level, pattern_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coin_id, pattern_data.get('pattern_type'), pattern_data.get('period_start'),
                pattern_data.get('period_end'), pattern_data.get('avg_price_change'),
                pattern_data.get('avg_volume_change'), pattern_data.get('success_rate'),
                pattern_data.get('sample_size'), pattern_data.get('confidence_level'),
                pattern_data.get('pattern_description')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения seasonal_pattern: {e}")
            conn.close()
            return False
    
    def get_current_seasonal_indicators(self, coin_id: str, date: str = None) -> Optional[Dict[str, Any]]:
        """Получает текущие сезонные индикаторы для монеты"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT * FROM current_seasonal_indicators 
            WHERE coin_id = ? AND date = ?
        """, (coin_id, date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = ['id', 'coin_id', 'date', 'current_event', 'days_to_event',
                      'historical_avg_change', 'historical_success_rate', 'seasonal_trend',
                      'seasonal_strength', 'next_important_date', 'seasonal_notes', 'created_at']
            return dict(zip(columns, row))
        
        return None
    
    def save_current_seasonal_indicators(self, coin_id: str, indicators: Dict[str, Any]) -> bool:
        """Сохраняет текущие сезонные индикаторы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO current_seasonal_indicators 
                (coin_id, date, current_event, days_to_event, historical_avg_change,
                 historical_success_rate, seasonal_trend, seasonal_strength, 
                 next_important_date, seasonal_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coin_id, indicators.get('date'), indicators.get('current_event'),
                indicators.get('days_to_event'), indicators.get('historical_avg_change'),
                indicators.get('historical_success_rate'), indicators.get('seasonal_trend'),
                indicators.get('seasonal_strength'), indicators.get('next_important_date'),
                indicators.get('seasonal_notes')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения current_seasonal_indicators: {e}")
            conn.close()
            return False

 