#!/usr/bin/env python3
"""
Модуль для создания умной выжимки исторических данных
Извлекает ключевые метрики для AI анализа без перегрузки токенов
"""
import pandas as pd
import numpy as np
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Добавляем путь к корневой папке
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.historical_data_manager import HistoricalDataManager
from src.historical_data.database_manager import DatabaseManager
from src.seasonal_analyzer import SeasonalAnalyzer

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class HistoricalDataSummarizer:
    """Создает умную выжимку исторических данных для AI анализа"""
    
    def __init__(self):
        self.config = Config()
        
        # Инициализируем менеджеры данных
        try:
            self.bitcoin_manager = HistoricalDataManager()
            self.db_manager = DatabaseManager()
            self.seasonal_analyzer = SeasonalAnalyzer()
        except Exception as e:
            logger.warning(f"Не удалось инициализировать менеджеры данных: {e}")
            self.bitcoin_manager = None
            self.db_manager = None
            self.seasonal_analyzer = None
    
    def get_bitcoin_summary(self) -> Dict[str, Any]:
        """Создает умную выжимку данных Bitcoin для AI"""
        if not self.bitcoin_manager:
            return {}
        
        try:
            # Загружаем данные
            df = self.bitcoin_manager.load_data()
            
            if df.empty:
                return {}
            
            # Рассчитываем технические индикаторы
            df_with_indicators = self.bitcoin_manager.calculate_technical_indicators()
            
            # Получаем последние данные
            latest = df_with_indicators.iloc[-1]
            
            # Ключевые исторические моменты
            key_moments = self._get_key_historical_moments(df)
            
            # Текущие технические индикаторы
            current_indicators = {
                'price': latest['close'],
                'rsi': latest['rsi'],
                'macd': latest['macd'],
                'sma_20': latest['sma_20'],
                'sma_50': latest['sma_50'],
                'sma_200': latest['sma_200'],
                'bb_upper': latest['bb_upper'],
                'bb_lower': latest['bb_lower'],
                'volume': latest['volume']
            }
            
            # Анализ трендов
            trend_analysis = self.bitcoin_manager.get_trend_analysis()
            
            # Анализ волатильности
            volatility_analysis = self.bitcoin_manager.get_volatility_analysis()
            
            # Историческое сравнение
            historical_comparison = self.bitcoin_manager.get_current_position_stats()
            
            # Статистика за разные периоды
            period_stats = self._get_period_statistics(df)
            
            # Сезонный анализ
            seasonal_analysis = {}
            if self.seasonal_analyzer:
                try:
                    seasonal_analysis = self.seasonal_analyzer.get_current_seasonal_analysis('bitcoin')
                except Exception as e:
                    logger.warning(f"Ошибка сезонного анализа Bitcoin: {e}")
            
            return {
                'current_indicators': current_indicators,
                'trend_analysis': trend_analysis,
                'volatility_analysis': volatility_analysis,
                'historical_comparison': historical_comparison,
                'key_moments': key_moments,
                'period_stats': period_stats,
                'seasonal_analysis': seasonal_analysis,
                'metadata': {
                    'total_records': len(df),
                    'start_date': df['date'].min().strftime('%Y-%m-%d'),
                    'end_date': df['date'].max().strftime('%Y-%m-%d'),
                    'price_range': {
                        'min': df['close'].min(),
                        'max': df['close'].max(),
                        'current': latest['close']
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания выжимки Bitcoin: {e}")
            return {}
    
    def get_ethereum_summary(self) -> Dict[str, Any]:
        """Создает умную выжимку данных Ethereum для AI"""
        if not self.db_manager:
            return {}
        
        try:
            # Получаем данные Ethereum из БД
            eth_data = self.db_manager.get_daily_data('ethereum')
            
            if eth_data.empty:
                return {}
            
            # Рассчитываем технические индикаторы
            df_with_indicators = self._calculate_ethereum_indicators(eth_data)
            
            # Получаем последние данные
            latest = df_with_indicators.iloc[-1]
            
            # Ключевые исторические моменты
            key_moments = self._get_key_historical_moments(eth_data)
            
            # Текущие технические индикаторы
            current_indicators = {
                'price': latest['close'],
                'rsi': latest.get('rsi', 0),
                'macd': latest.get('macd', 0),
                'sma_20': latest.get('sma_20', 0),
                'sma_50': latest.get('sma_50', 0),
                'volume': latest.get('volume', 0)
            }
            
            # Анализ трендов
            trend_analysis = self._analyze_ethereum_trends(df_with_indicators)
            
            # Анализ волатильности
            volatility_analysis = self._analyze_ethereum_volatility(df_with_indicators)
            
            # Статистика за разные периоды
            period_stats = self._get_period_statistics(eth_data)
            
            # Сезонный анализ
            seasonal_analysis = {}
            if self.seasonal_analyzer:
                try:
                    seasonal_analysis = self.seasonal_analyzer.get_current_seasonal_analysis('ethereum')
                except Exception as e:
                    logger.warning(f"Ошибка сезонного анализа Ethereum: {e}")
            
            return {
                'current_indicators': current_indicators,
                'trend_analysis': trend_analysis,
                'volatility_analysis': volatility_analysis,
                'key_moments': key_moments,
                'period_stats': period_stats,
                'seasonal_analysis': seasonal_analysis,
                'metadata': {
                    'total_records': len(eth_data),
                    'start_date': eth_data['date'].min().strftime('%Y-%m-%d'),
                    'end_date': eth_data['date'].max().strftime('%Y-%m-%d'),
                    'price_range': {
                        'min': eth_data['close'].min(),
                        'max': eth_data['close'].max(),
                        'current': latest['close']
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания выжимки Ethereum: {e}")
            return {}
    
    def _calculate_ethereum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Рассчитывает технические индикаторы для Ethereum"""
        if len(df) < 20:
            return df
        
        df = df.copy()
        
        # Скользящие средние
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    def _analyze_ethereum_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализирует тренды Ethereum"""
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        return {
            'price_trend': 'bullish' if latest['close'] > latest['sma_20'] else 'bearish',
            'sma_trend': 'bullish' if latest['sma_20'] > latest['sma_50'] else 'bearish',
            'macd_signal': 'bullish' if latest['macd'] > latest['macd_signal'] else 'bearish',
            'rsi_level': latest.get('rsi', 0),
            'rsi_signal': 'oversold' if latest.get('rsi', 0) < 30 else 'overbought' if latest.get('rsi', 0) > 70 else 'neutral'
        }
    
    def _analyze_ethereum_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализирует волатильность Ethereum"""
        if df.empty:
            return {}
        
        # Рассчитываем волатильность за последние 30 дней
        recent_data = df.tail(30)
        
        if len(recent_data) < 10:
            return {}
        
        daily_returns = recent_data['close'].pct_change().dropna()
        
        return {
            'current_volatility': daily_returns.std() * np.sqrt(252),  # Годовая волатильность
            'avg_volume': recent_data['volume'].mean(),
            'max_price': recent_data['close'].max(),
            'min_price': recent_data['close'].min(),
            'price_range': recent_data['close'].max() - recent_data['close'].min()
        }
    
    def _get_key_historical_moments(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Извлекает ключевые исторические моменты"""
        if df.empty:
            return []
        
        moments = []
        
        # Максимальная и минимальная цены
        max_price_row = df.loc[df['close'].idxmax()]
        min_price_row = df.loc[df['close'].idxmin()]
        
        # Безопасная функция для форматирования цен
        def safe_price_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"${float(value):,.2f}"
            except (ValueError, TypeError):
                return default
        
        moments.append({
            'type': 'all_time_high',
            'date': max_price_row['date'].strftime('%Y-%m-%d'),
            'price': max_price_row['close'],
            'description': f"Исторический максимум: {safe_price_format(max_price_row['close'])}"
        })
        
        moments.append({
            'type': 'all_time_low',
            'date': min_price_row['date'].strftime('%Y-%m-%d'),
            'price': min_price_row['close'],
            'description': f"Исторический минимум: {safe_price_format(min_price_row['close'])}"
        })
        
        # Крупные движения за последний год
        recent_data = df.tail(365).copy()  # Создаем копию для избежания SettingWithCopyWarning
        if len(recent_data) > 30:
            # Находим дни с наибольшими изменениями
            recent_data.loc[:, 'price_change'] = recent_data['close'].pct_change()
            biggest_gains = recent_data.nlargest(3, 'price_change')
            biggest_losses = recent_data.nsmallest(3, 'price_change')
            
            for _, row in biggest_gains.iterrows():
                if not pd.isna(row['price_change']):
                    moments.append({
                        'type': 'major_gain',
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'change': row['price_change'] * 100,
                        'description': f"Крупный рост: +{row['price_change']*100:.2f}%"
                    })
            
            for _, row in biggest_losses.iterrows():
                if not pd.isna(row['price_change']):
                    moments.append({
                        'type': 'major_loss',
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'change': row['price_change'] * 100,
                        'description': f"Крупное падение: {row['price_change']*100:.2f}%"
                    })
        
        return moments[:10]  # Ограничиваем 10 ключевыми моментами
    
    def _get_period_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Получает статистику за разные периоды"""
        if df.empty:
            return {}
        
        current_price = df['close'].iloc[-1]
        
        # Статистика за разные периоды
        periods = {
            '1_week': 7,
            '1_month': 30,
            '3_months': 90,
            '6_months': 180,
            '1_year': 365,
            'all_time': len(df)
        }
        
        stats = {}
        for period_name, days in periods.items():
            if len(df) >= days:
                period_data = df.tail(days)
                start_price = period_data['close'].iloc[0]
                end_price = period_data['close'].iloc[-1]
                change_pct = ((end_price - start_price) / start_price) * 100
                
                stats[period_name] = {
                    'start_price': start_price,
                    'end_price': end_price,
                    'change_pct': change_pct,
                    'max_price': period_data['close'].max(),
                    'min_price': period_data['close'].min(),
                    'avg_volume': period_data['volume'].mean()
                }
        
        return stats
    
    def create_ai_summary(self) -> Dict[str, Any]:
        """Создает умную выжимку для AI анализа"""
        bitcoin_summary = self.get_bitcoin_summary()
        ethereum_summary = self.get_ethereum_summary()
        
        # Создаем краткую выжимку для AI
        ai_summary = {
            'bitcoin': {
                'current_price': bitcoin_summary.get('current_indicators', {}).get('price', 0),
                'rsi': bitcoin_summary.get('current_indicators', {}).get('rsi', 0),
                'trend': bitcoin_summary.get('trend_analysis', {}).get('price_trend', 'neutral'),
                'volatility': bitcoin_summary.get('volatility_analysis', {}).get('current_volatility', 0),
                'key_moments': bitcoin_summary.get('key_moments', [])[:3],  # Только 3 ключевых момента
                'period_stats': bitcoin_summary.get('period_stats', {}),
                'seasonal_analysis': bitcoin_summary.get('seasonal_analysis', {})
            },
            'ethereum': {
                'current_price': ethereum_summary.get('current_indicators', {}).get('price', 0),
                'rsi': ethereum_summary.get('current_indicators', {}).get('rsi', 0),
                'trend': ethereum_summary.get('trend_analysis', {}).get('price_trend', 'neutral'),
                'volatility': ethereum_summary.get('volatility_analysis', {}).get('current_volatility', 0),
                'key_moments': ethereum_summary.get('key_moments', [])[:3],  # Только 3 ключевых момента
                'period_stats': ethereum_summary.get('period_stats', {}),
                'seasonal_analysis': ethereum_summary.get('seasonal_analysis', {})
            },
            'market_sentiment': self._calculate_market_sentiment(bitcoin_summary, ethereum_summary),
            'historical_context': {
                'bitcoin_records': bitcoin_summary.get('metadata', {}).get('total_records', 0),
                'ethereum_records': ethereum_summary.get('metadata', {}).get('total_records', 0),
                'bitcoin_period': f"{bitcoin_summary.get('metadata', {}).get('start_date', 'N/A')} - {bitcoin_summary.get('metadata', {}).get('end_date', 'N/A')}",
                'ethereum_period': f"{ethereum_summary.get('metadata', {}).get('start_date', 'N/A')} - {ethereum_summary.get('metadata', {}).get('end_date', 'N/A')}"
            }
        }
        
        return ai_summary
    
    def _calculate_market_sentiment(self, bitcoin_summary: Dict[str, Any], ethereum_summary: Dict[str, Any]) -> str:
        """Рассчитывает общее настроение рынка"""
        btc_trend = bitcoin_summary.get('trend_analysis', {}).get('price_trend', 'neutral')
        eth_trend = ethereum_summary.get('trend_analysis', {}).get('price_trend', 'neutral')
        
        btc_rsi = bitcoin_summary.get('current_indicators', {}).get('rsi', 50)
        eth_rsi = ethereum_summary.get('current_indicators', {}).get('rsi', 50)
        
        # Определяем настроение на основе трендов и RSI
        if btc_trend == 'bullish' and eth_trend == 'bullish':
            if btc_rsi < 70 and eth_rsi < 70:
                return "strong_bullish"
            else:
                return "bullish_overbought"
        elif btc_trend == 'bearish' and eth_trend == 'bearish':
            if btc_rsi > 30 and eth_rsi > 30:
                return "strong_bearish"
            else:
                return "bearish_oversold"
        else:
            return "mixed_signals"
    
    def format_summary_for_ai(self, summary: Dict[str, Any]) -> str:
        """Форматирует выжимку для передачи в AI"""
        if not summary:
            return ""
        
        parts = []
        parts.append("📈 ИСТОРИЧЕСКИЕ ДАННЫЕ ДЛЯ AI АНАЛИЗА")
        parts.append("=" * 50)
        
        # Безопасные функции для форматирования
        def safe_price_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"${float(value):,.2f}"
            except (ValueError, TypeError):
                return default
        
        def safe_rsi_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"{float(value):.1f}"
            except (ValueError, TypeError):
                return default
        
        def safe_volatility_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"{float(value):.2f}"
            except (ValueError, TypeError):
                return default
        
        # Bitcoin данные
        btc = summary.get('bitcoin', {})
        if btc:
            parts.append(f"\n🪙 BITCOIN:")
            parts.append(f"💰 Текущая цена: {safe_price_format(btc.get('current_price', 0))}")
            parts.append(f"📊 RSI: {safe_rsi_format(btc.get('rsi', 0))}")
            parts.append(f"🎯 Тренд: {btc.get('trend', 'neutral').upper()}")
            parts.append(f"📊 Волатильность: {safe_volatility_format(btc.get('volatility', 0))}%")
            
            # Ключевые моменты
            key_moments = btc.get('key_moments', [])
            if key_moments:
                parts.append("📅 Ключевые моменты:")
                for moment in key_moments[:2]:  # Только 2 самых важных
                    parts.append(f"  • {moment['description']} ({moment['date']})")
        
        # Ethereum данные
        eth = summary.get('ethereum', {})
        if eth:
            parts.append(f"\n💎 ETHEREUM:")
            parts.append(f"💰 Текущая цена: {safe_price_format(eth.get('current_price', 0))}")
            parts.append(f"📊 RSI: {safe_rsi_format(eth.get('rsi', 0))}")
            parts.append(f"🎯 Тренд: {eth.get('trend', 'neutral').upper()}")
            parts.append(f"📊 Волатильность: {safe_volatility_format(eth.get('volatility', 0))}%")
            
            # Ключевые моменты
            key_moments = eth.get('key_moments', [])
            if key_moments:
                parts.append("📅 Ключевые моменты:")
                for moment in key_moments[:2]:  # Только 2 самых важных
                    parts.append(f"  • {moment['description']} ({moment['date']})")
        
        # Настроение рынка
        sentiment = summary.get('market_sentiment', 'unknown')
        sentiment_map = {
            'strong_bullish': '🟢 Сильный бычий тренд',
            'bullish_overbought': '🟡 Бычий тренд, но перекуплен',
            'strong_bearish': '🔴 Сильный медвежий тренд',
            'bearish_oversold': '🟡 Медвежий тренд, но перепродан',
            'mixed_signals': '🟡 Смешанные сигналы'
        }
        
        parts.append(f"\n📊 НАСТРОЕНИЕ РЫНКА: {sentiment_map.get(sentiment, 'Неизвестно')}")
        
        # Сезонные данные
        btc_seasonal = btc.get('seasonal_analysis', {}) if btc else {}
        eth_seasonal = eth.get('seasonal_analysis', {}) if eth else {}
        
        if btc_seasonal or eth_seasonal:
            parts.append(f"\n📅 СЕЗОННЫЕ ДАННЫЕ:")
            
            # Bitcoin сезонные данные
            if btc_seasonal:
                btc_trend = btc_seasonal.get('seasonal_trend', 'neutral')
                btc_strength = btc_seasonal.get('seasonal_indicators', {}).get('seasonal_strength', 0)
                parts.append(f"  🪙 Bitcoin сезонный тренд: {btc_trend} (сила: {btc_strength:.1%})")
                
                next_event = btc_seasonal.get('seasonal_indicators', {}).get('next_important_event')
                if next_event:
                    parts.append(f"  🎯 Следующее событие: {next_event.get('event_name', '')} (через {next_event.get('days_until_event', 0)} дней)")
            
            # Ethereum сезонные данные
            if eth_seasonal:
                eth_trend = eth_seasonal.get('seasonal_trend', 'neutral')
                eth_strength = eth_seasonal.get('seasonal_indicators', {}).get('seasonal_strength', 0)
                parts.append(f"  💎 Ethereum сезонный тренд: {eth_trend} (сила: {eth_strength:.1%})")
                
                next_event = eth_seasonal.get('seasonal_indicators', {}).get('next_important_event')
                if next_event:
                    parts.append(f"  🎯 Следующее событие: {next_event.get('event_name', '')} (через {next_event.get('days_until_event', 0)} дней)")
        
        # Исторический контекст
        context = summary.get('historical_context', {})
        parts.append(f"\n📚 ИСТОРИЧЕСКИЙ КОНТЕКСТ:")
        parts.append(f"  • Bitcoin: {context.get('bitcoin_records', 0):,} записей ({context.get('bitcoin_period', 'N/A')})")
        parts.append(f"  • Ethereum: {context.get('ethereum_records', 0):,} записей ({context.get('ethereum_period', 'N/A')})")
        
        return "\n".join(parts)

 