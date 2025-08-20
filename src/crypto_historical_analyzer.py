#!/usr/bin/env python3
"""
Модуль для анализа криптовалют с использованием исторических данных
Интегрирует данные Bitcoin и Ethereum с техническими индикаторами
"""
import pandas as pd
import numpy as np
import logging
import sys
import os
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Tuple, Optional

# Добавляем путь к корневой папке
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.historical_data_manager import HistoricalDataManager
from src.historical_data.database_manager import DatabaseManager
from pycoingecko import CoinGeckoAPI

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class CryptoHistoricalAnalyzer:
    """Анализатор криптовалют с использованием исторических данных"""
    
    def __init__(self):
        self.config = Config()
        
        # Инициализируем менеджеры данных
        try:
            self.bitcoin_manager = HistoricalDataManager()
            self.db_manager = DatabaseManager()
            self._cg = CoinGeckoAPI()
        except Exception as e:
            logger.warning(f"Не удалось инициализировать менеджеры данных: {e}")
            self.bitcoin_manager = None
            self.db_manager = None
            self._cg = None
    
    def get_bitcoin_analysis(self) -> Dict[str, Any]:
        """Получает анализ Bitcoin с историческими данными"""
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
            
            # Анализ трендов
            trend_analysis = self.bitcoin_manager.get_trend_analysis()
            
            # Анализ волатильности
            volatility_analysis = self.bitcoin_manager.get_volatility_analysis()
            
            # Статистика позиции
            position_stats = self.bitcoin_manager.get_current_position_stats()
            
            # Историческое сравнение
            historical_comparison = self.bitcoin_manager.get_historical_comparison(latest['close'])
            
            return {
                'current_price': latest['close'],
                'price_change_24h': self._calculate_24h_change(df),
                'trend_analysis': trend_analysis,
                'volatility_analysis': volatility_analysis,
                'position_stats': position_stats,
                'historical_comparison': historical_comparison,
                'technical_indicators': {
                    'rsi': latest['rsi'],
                    'macd': latest['macd'],
                    'macd_signal': latest['macd_signal'],
                    'sma_20': latest['sma_20'],
                    'sma_50': latest['sma_50'],
                    'sma_200': latest['sma_200'],
                    'bb_upper': latest['bb_upper'],
                    'bb_lower': latest['bb_lower'],
                    'volume': latest['volume'],
                    'volume_sma': latest['volume_sma']
                },
                'metadata': self.bitcoin_manager.get_metadata()
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа Bitcoin: {e}")
            return {}
    
    def get_ethereum_analysis(self) -> Dict[str, Any]:
        """Получает анализ Ethereum с историческими данными"""
        if not self.db_manager:
            return {}
        
        try:
            # Обеспечиваем лёгкое инкрементальное обновление ETH в БД без перегруза API
            try:
                last_date: Optional[date] = self.db_manager.get_last_daily_date('ethereum')  # type: ignore[attr-defined]
            except Exception:
                last_date = None
            
            need_update = False
            days_to_fetch = 0
            today = datetime.utcnow().date()
            
            if last_date is None:
                # Нет данных — забираем экономно последний год
                need_update = True
                days_to_fetch = 365
            else:
                gap_days = (today - last_date).days
                if gap_days >= 1:
                    need_update = True
                    # Инкрементальный догон только по недостающим дням, но не более 90
                    days_to_fetch = min(90, gap_days + 1)
            
            if need_update and self._cg is not None:
                try:
                    history = self._cg.get_coin_market_chart_by_id(
                        id='ethereum', vs_currency='usd', days=days_to_fetch, interval='daily'
                    )
                    prices = history.get('prices', [])
                    market_caps = history.get('market_caps', [])
                    volumes = history.get('total_volumes', [])
                    records: List[Dict[str, Any]] = []
                    prev_close = None
                    prev_volume = None
                    for i in range(len(prices)):
                        ts_ms, price = prices[i]
                        rec_date = datetime.fromtimestamp(ts_ms / 1000).date().isoformat()
                        market_cap = market_caps[i][1] if i < len(market_caps) else None
                        volume = volumes[i][1] if i < len(volumes) else None
                        price_change_24h = None
                        volume_change_24h = None
                        if prev_close not in (None, 0):
                            try:
                                price_change_24h = ((price - prev_close) / prev_close) * 100
                            except Exception:
                                price_change_24h = None
                        if prev_volume not in (None, 0) and volume not in (None, 0):
                            try:
                                volume_change_24h = ((volume - prev_volume) / prev_volume) * 100
                            except Exception:
                                volume_change_24h = None
                        records.append({
                            'date': rec_date,
                            'open': price,
                            'high': price,
                            'low': price,
                            'close': price,
                            'volume': volume,
                            'market_cap': market_cap,
                            'circulating_supply': None,
                            'total_supply': None,
                            'fdv': None,
                            'price_change_24h': price_change_24h,
                            'volume_change_24h': volume_change_24h,
                        })
                        prev_close = price
                        prev_volume = volume
                    if records:
                        self.db_manager.save_daily_data('ethereum', records)
                        logger.info(f"Инкрементально обновлены данные ETH: {len(records)} записей")
                except Exception as upd_err:
                    logger.warning(f"Не удалось выполнить инкрементальное обновление ETH: {upd_err}")
            
            # Получаем данные Ethereum из БД
            eth_data = self.db_manager.get_daily_data('ethereum')
            
            if eth_data.empty:
                return {}
            
            # Рассчитываем технические индикаторы
            df_with_indicators = self._calculate_ethereum_indicators(eth_data)
            
            # Получаем последние данные
            latest = df_with_indicators.iloc[-1]
            
            # Анализ трендов
            trend_analysis = self._analyze_ethereum_trends(df_with_indicators)
            
            # Анализ волатильности
            volatility_analysis = self._analyze_ethereum_volatility(df_with_indicators)
            
            return {
                'current_price': latest['close'],
                'price_change_24h': self._calculate_24h_change(eth_data),
                'trend_analysis': trend_analysis,
                'volatility_analysis': volatility_analysis,
                'technical_indicators': {
                    'rsi': latest.get('rsi', 0),
                    'macd': latest.get('macd', 0),
                    'macd_signal': latest.get('macd_signal', 0),
                    'sma_20': latest.get('sma_20', 0),
                    'sma_50': latest.get('sma_50', 0),
                    'volume': latest.get('volume', 0),
                    'volume_sma': latest.get('volume_sma', 0)
                },
                'metadata': {
                    'total_records': len(eth_data),
                    'start_date': eth_data['date'].min().strftime('%Y-%m-%d'),
                    'end_date': eth_data['date'].max().strftime('%Y-%m-%d')
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа Ethereum: {e}")
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
        
        # Объемная скользящая средняя
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
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
            'rsi_signal': 'oversold' if latest.get('rsi', 0) < 30 else 'overbought' if latest.get('rsi', 0) > 70 else 'neutral',
            'volume_trend': 'high' if latest['volume'] > latest['volume_sma'] else 'low'
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
    
    def _calculate_24h_change(self, df: pd.DataFrame) -> float:
        """Рассчитывает изменение цены за 24 часа"""
        if len(df) < 2:
            return 0.0
        
        current_price = df['close'].iloc[-1]
        previous_price = df['close'].iloc[-2]
        
        return ((current_price - previous_price) / previous_price) * 100
    
    def get_comprehensive_crypto_analysis(self) -> Dict[str, Any]:
        """Получает комплексный анализ криптовалют"""
        bitcoin_analysis = self.get_bitcoin_analysis()
        ethereum_analysis = self.get_ethereum_analysis()
        
        # Создаем краткий анализ
        short_analysis = self._create_short_analysis(bitcoin_analysis, ethereum_analysis)
        
        # Создаем полный анализ
        full_analysis = self._create_full_analysis(bitcoin_analysis, ethereum_analysis)
        
        return {
            'short_analysis': short_analysis,
            'full_analysis': full_analysis,
            'bitcoin_data': bitcoin_analysis,
            'ethereum_data': ethereum_analysis,
            'timestamp': datetime.now()
        }

    def get_ai_historical_points(self, max_points: int = 180) -> List[Dict[str, Any]]:
        """Возвращает экономную подвыборку исторических точек для AI.
        Пытаемся взять последние 60 дней + равномерную выборку по остальному периоду из БД ETH,
        а также smart-сэмпл из локального менеджера BTC (если доступен)."""
        points: List[Dict[str, Any]] = []
        try:
            # ETH из БД (если есть)
            if self.db_manager:
                df = self.db_manager.get_daily_data('ethereum')
                if not df.empty:
                    recent = df.tail(60)
                    points.extend(recent[['date', 'close', 'volume']].to_dict('records'))
                    # Равномерная выборка по остатку
                    remain = df.iloc[:-60]
                    if not remain.empty:
                        # Берём ещё до max_points, без дубликатов
                        remaining_slots = max(0, max_points - len(points))
                        if remaining_slots > 0:
                            step = max(1, len(remain) // remaining_slots)
                            sampled = remain.iloc[::step][['date', 'close', 'volume']].head(remaining_slots)
                            points.extend(sampled.to_dict('records'))
        except Exception as e:
            logger.warning(f"Ошибка выборки ETH точек для AI: {e}")
        try:
            # BTC smart sample (локальный CSV менеджер) — очень экономно
            if self.bitcoin_manager:
                btc_df = self.bitcoin_manager.get_smart_sample_data(max_points=min(100, max_points // 2))
                if not btc_df.empty:
                    points.extend(btc_df[['date', 'close', 'volume']].to_dict('records'))
        except Exception as e:
            logger.warning(f"Ошибка выборки BTC smart sample: {e}")
        # Ограничиваем размер
        if len(points) > max_points:
            points = points[-max_points:]
        return points
    
    def _create_short_analysis(self, bitcoin_data: Dict[str, Any], ethereum_data: Dict[str, Any]) -> str:
        """Создает краткий анализ криптовалют"""
        analysis_parts = []
        
        # Bitcoin анализ
        if bitcoin_data:
            btc_price = bitcoin_data.get('current_price', 0)
            btc_change = bitcoin_data.get('price_change_24h', 0)
            btc_rsi = bitcoin_data.get('technical_indicators', {}).get('rsi', 0)
            btc_trend = bitcoin_data.get('trend_analysis', {}).get('price_trend', 'neutral')
            
            btc_emoji = "📈" if btc_change > 0 else "📉" if btc_change < 0 else "➡️"
            trend_emoji = "🟢" if btc_trend == 'bullish' else "🔴" if btc_trend == 'bearish' else "🟡"
            
            analysis_parts.append(f"🪙 BITCOIN {trend_emoji}")
            analysis_parts.append(f"Цена: ${btc_price:,.2f} ({btc_emoji} {btc_change:+.2f}%)")
            analysis_parts.append(f"RSI: {btc_rsi:.1f} ({'Перекуплен' if btc_rsi > 70 else 'Перепродан' if btc_rsi < 30 else 'Нейтральный'})")
        
        # Ethereum анализ
        if ethereum_data:
            eth_price = ethereum_data.get('current_price', 0)
            eth_change = ethereum_data.get('price_change_24h', 0)
            eth_rsi = ethereum_data.get('technical_indicators', {}).get('rsi', 0)
            eth_trend = ethereum_data.get('trend_analysis', {}).get('price_trend', 'neutral')
            
            eth_emoji = "📈" if eth_change > 0 else "📉" if eth_change < 0 else "➡️"
            trend_emoji = "🟢" if eth_trend == 'bullish' else "🔴" if eth_trend == 'bearish' else "🟡"
            
            analysis_parts.append(f"\n💎 ETHEREUM {trend_emoji}")
            analysis_parts.append(f"Цена: ${eth_price:,.2f} ({eth_emoji} {eth_change:+.2f}%)")
            analysis_parts.append(f"RSI: {eth_rsi:.1f} ({'Перекуплен' if eth_rsi > 70 else 'Перепродан' if eth_rsi < 30 else 'Нейтральный'})")
        
        # Общий анализ рынка
        if bitcoin_data and ethereum_data:
            btc_trend = bitcoin_data.get('trend_analysis', {}).get('price_trend', 'neutral')
            eth_trend = ethereum_data.get('trend_analysis', {}).get('price_trend', 'neutral')
            
            if btc_trend == 'bullish' and eth_trend == 'bullish':
                market_sentiment = "🟢 Бычий рынок"
            elif btc_trend == 'bearish' and eth_trend == 'bearish':
                market_sentiment = "🔴 Медвежий рынок"
            else:
                market_sentiment = "🟡 Смешанные сигналы"
            
            analysis_parts.append(f"\n📊 НАСТРОЕНИЕ РЫНКА: {market_sentiment}")
        
        return "\n".join(analysis_parts)
    
    def _create_full_analysis(self, bitcoin_data: Dict[str, Any], ethereum_data: Dict[str, Any]) -> str:
        """Создает полный анализ криптовалют"""
        
        # Безопасные функции для форматирования
        def safe_price_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"${float(value):,.2f}"
            except (ValueError, TypeError):
                return default
        
        def safe_change_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"{float(value):+.2f}"
            except (ValueError, TypeError):
                return default
        
        def safe_rsi_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"{float(value):.1f}"
            except (ValueError, TypeError):
                return default
        
        def safe_macd_format(value, default='N/A'):
            if value is None or value == 'N/A':
                return default
            try:
                return f"{float(value):.2f}"
            except (ValueError, TypeError):
                return default
        
        analysis_parts = []
        
        analysis_parts.append("🔍 ПОЛНЫЙ АНАЛИЗ КРИПТОВАЛЮТ")
        analysis_parts.append("=" * 50)
        
        # Bitcoin детальный анализ
        if bitcoin_data:
            analysis_parts.append("\n🪙 BITCOIN - ДЕТАЛЬНЫЙ АНАЛИЗ")
            analysis_parts.append("-" * 30)
            
            btc_price = bitcoin_data.get('current_price', 0)
            btc_change = bitcoin_data.get('price_change_24h', 0)
            btc_indicators = bitcoin_data.get('technical_indicators', {})
            btc_trend = bitcoin_data.get('trend_analysis', {})
            btc_volatility = bitcoin_data.get('volatility_analysis', {})
            
            analysis_parts.append(f"💰 Текущая цена: {safe_price_format(btc_price)}")
            analysis_parts.append(f"📈 Изменение 24ч: {safe_change_format(btc_change)}%")
            analysis_parts.append(f"📊 RSI: {safe_rsi_format(btc_indicators.get('rsi', 0))}")
            analysis_parts.append(f"📊 MACD: {safe_macd_format(btc_indicators.get('macd', 0))}")
            analysis_parts.append(f"📊 SMA 20: {safe_price_format(btc_indicators.get('sma_20', 0))}")
            analysis_parts.append(f"📊 SMA 50: {safe_price_format(btc_indicators.get('sma_50', 0))}")
            analysis_parts.append(f"📊 SMA 200: {safe_price_format(btc_indicators.get('sma_200', 0))}")
            
            # Тренд анализ
            trend_signal = btc_trend.get('price_trend', 'neutral')
            analysis_parts.append(f"🎯 Тренд цены: {trend_signal.upper()}")
            
            # Волатильность
            if btc_volatility:
                analysis_parts.append(f"📊 Волатильность: {btc_volatility.get('current_volatility', 0):.2f}%")
        
        # Ethereum детальный анализ
        if ethereum_data:
            analysis_parts.append("\n💎 ETHEREUM - ДЕТАЛЬНЫЙ АНАЛИЗ")
            analysis_parts.append("-" * 30)
            
            eth_price = ethereum_data.get('current_price', 0)
            eth_change = ethereum_data.get('price_change_24h', 0)
            eth_indicators = ethereum_data.get('technical_indicators', {})
            eth_trend = ethereum_data.get('trend_analysis', {})
            eth_volatility = ethereum_data.get('volatility_analysis', {})
            
            analysis_parts.append(f"💰 Текущая цена: {safe_price_format(eth_price)}")
            analysis_parts.append(f"📈 Изменение 24ч: {safe_change_format(eth_change)}%")
            analysis_parts.append(f"📊 RSI: {safe_rsi_format(eth_indicators.get('rsi', 0))}")
            analysis_parts.append(f"📊 MACD: {safe_macd_format(eth_indicators.get('macd', 0))}")
            analysis_parts.append(f"📊 SMA 20: {safe_price_format(eth_indicators.get('sma_20', 0))}")
            analysis_parts.append(f"📊 SMA 50: {safe_price_format(eth_indicators.get('sma_50', 0))}")
            
            # Тренд анализ
            trend_signal = eth_trend.get('price_trend', 'neutral')
            analysis_parts.append(f"🎯 Тренд цены: {trend_signal.upper()}")
            
            # Волатильность
            if eth_volatility:
                analysis_parts.append(f"📊 Волатильность: {eth_volatility.get('current_volatility', 0):.2f}%")
        
        # Рекомендации
        analysis_parts.append("\n💡 РЕКОМЕНДАЦИИ")
        analysis_parts.append("-" * 20)
        
        if bitcoin_data and ethereum_data:
            btc_rsi = bitcoin_data.get('technical_indicators', {}).get('rsi', 50)
            eth_rsi = ethereum_data.get('technical_indicators', {}).get('rsi', 50)
            
            if btc_rsi < 30 and eth_rsi < 30:
                analysis_parts.append("🟢 Оба актива перепроданы - возможен отскок")
            elif btc_rsi > 70 and eth_rsi > 70:
                analysis_parts.append("🔴 Оба актива перекуплены - возможна коррекция")
            else:
                analysis_parts.append("🟡 Смешанные сигналы - осторожность")
        
        return "\n".join(analysis_parts)

    def get_ai_prompt_context(self, symbol: str) -> str:
        """Создает полный контекст для AI промпта (замена historical_analyzer)"""
        try:
            if symbol.upper() == "BTC":
                bitcoin_data = self.get_bitcoin_analysis()
                if not bitcoin_data:
                    return f"Исторический контекст для {symbol} недоступен"
                
                current_price = bitcoin_data.get('current_price', 0)
                price_change = bitcoin_data.get('price_change_24h', 0)
                indicators = bitcoin_data.get('technical_indicators', {})
                trend_analysis = bitcoin_data.get('trend_analysis', {})
                volatility_analysis = bitcoin_data.get('volatility_analysis', {})
                
                # Безопасные функции для форматирования (уже определены выше)
                context_parts = [
                    "📈 ИСТОРИЧЕСКИЙ КОНТЕКСТ ДЛЯ AI АНАЛИЗА",
                    "=" * 50,
                    f"\n🪙 {symbol.upper()} АНАЛИЗ:",
                    f"\n💰 ТЕКУЩАЯ ПОЗИЦИЯ:",
                    f"  Цена: {safe_price_format(current_price)} ({safe_change_format(price_change)}%)",
                    f"  RSI: {safe_rsi_format(indicators.get('rsi', 0))}",
                    f"  MACD: {safe_macd_format(indicators.get('macd', 0))}",
                    f"  SMA 20: {safe_price_format(indicators.get('sma_20', 0))}",
                    f"  SMA 50: {safe_price_format(indicators.get('sma_50', 0))}",
                    f"  SMA 200: {safe_price_format(indicators.get('sma_200', 0))}",
                    f"\n📊 ТЕХНИЧЕСКИЙ АНАЛИЗ:",
                    f"  Тренд: {trend_analysis.get('price_trend', 'neutral')}",
                    f"  Волатильность: {safe_rsi_format(volatility_analysis.get('current_volatility', 0))}%",
                    f"  Bollinger Bands: {safe_price_format(indicators.get('bb_lower', 0))} - {safe_price_format(indicators.get('bb_upper', 0))}"
                ]
                
                # Позиция относительно уровней
                if indicators.get('sma_20', 0) > 0:
                    above_sma_20 = current_price > indicators['sma_20']
                    above_sma_50 = current_price > indicators['sma_50']
                    above_sma_200 = current_price > indicators['sma_200']
                    
                    position_notes = []
                    if above_sma_20:
                        position_notes.append("выше SMA 20")
                    if above_sma_50:
                        position_notes.append("выше SMA 50")
                    if above_sma_200:
                        position_notes.append("выше SMA 200")
                    
                    if position_notes:
                        context_parts.append(f"  📍 Позиция: {', '.join(position_notes)}")
                
                return "\n".join(context_parts)
                
            elif symbol.upper() == "ETH":
                ethereum_data = self.get_ethereum_analysis()
                if not ethereum_data:
                    return f"Исторический контекст для {symbol} недоступен"
                
                current_price = ethereum_data.get('current_price', 0)
                price_change = ethereum_data.get('price_change_24h', 0)
                indicators = ethereum_data.get('technical_indicators', {})
                trend_analysis = ethereum_data.get('trend_analysis', {})
                volatility_analysis = ethereum_data.get('volatility_analysis', {})
                
                context_parts = [
                    "📈 ИСТОРИЧЕСКИЙ КОНТЕКСТ ДЛЯ AI АНАЛИЗА",
                    "=" * 50,
                    f"\n💎 {symbol.upper()} АНАЛИЗ:",
                    f"\n💰 ТЕКУЩАЯ ПОЗИЦИЯ:",
                    f"  Цена: {safe_price_format(current_price)} ({safe_change_format(price_change)}%)",
                    f"  RSI: {safe_rsi_format(indicators.get('rsi', 0))}",
                    f"  MACD: {safe_macd_format(indicators.get('macd', 0))}",
                    f"  SMA 20: {safe_price_format(indicators.get('sma_20', 0))}",
                    f"  SMA 50: {safe_price_format(indicators.get('sma_50', 0))}",
                    f"\n📊 ТЕХНИЧЕСКИЙ АНАЛИЗ:",
                    f"  Тренд: {trend_analysis.get('price_trend', 'neutral')}",
                    f"  Волатильность: {safe_rsi_format(volatility_analysis.get('current_volatility', 0))}%"
                ]
                
                return "\n".join(context_parts)
            
            else:
                return f"Исторический контекст для {symbol} недоступен"
                
        except Exception as e:
            logger.error(f"Ошибка создания AI контекста для {symbol}: {e}")
            return f"Исторический контекст для {symbol} недоступен"

 