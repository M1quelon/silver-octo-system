#!/usr/bin/env python3
"""
Модуль для работы с историческими данными Bitcoin
"""
import pandas as pd
import numpy as np
import json
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import sqlite3

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class HistoricalDataManager:
    """Класс для работы с историческими данными Bitcoin"""
    
    def __init__(self):
        self.config = Config()
        self.data_file = 'data/historical/bitcoin_complete_history_enhanced.csv'
        self.metadata_file = 'data/historical/bitcoin_history_metadata.json'
        self.db_file = 'data/historical/crypto_history.db'
        
        # Кеш для загруженных данных
        self._data_cache = None
        self._metadata_cache = None
        self._last_load_time = None
        
        # Проверяем наличие файлов
        self._validate_files()
    
    def _validate_files(self):
        """Проверяет наличие необходимых файлов"""
        if not os.path.exists(self.data_file):
            raise FileNotFoundError(f"Файл с историческими данными не найден: {self.data_file}")
        
        if not os.path.exists(self.metadata_file):
            logger.warning(f"Файл метаданных не найден: {self.metadata_file}")
    
    def load_data(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Загружает исторические данные из CSV файла
        
        Args:
            force_reload: Принудительная перезагрузка данных
            
        Returns:
            DataFrame с историческими данными
        """
        current_time = datetime.now()
        
        # Проверяем кеш
        if (self._data_cache is not None and 
            self._last_load_time is not None and
            not force_reload and
            (current_time - self._last_load_time).total_seconds() < 3600):  # 1 час
            return self._data_cache
        
        try:
            logger.info("Загрузка исторических данных...")
            
            # Загружаем данные
            df = pd.read_csv(self.data_file)
            
            # Конвертируем дату
            df['date'] = pd.to_datetime(df['date'])
            
            # Сортируем по дате
            df = df.sort_values('date')
            
            # Удаляем дубликаты
            df = df.drop_duplicates(subset=['date'], keep='first')
            
            # Фильтруем нулевые цены (ранние данные)
            df = df[df['close'] > 0]
            
            # Сбрасываем индекс
            df = df.reset_index(drop=True)
            
            # Обновляем кеш
            self._data_cache = df
            self._last_load_time = current_time
            
            logger.info(f"Загружено {len(df):,} записей исторических данных")
            logger.info(f"Период: {df['date'].min().strftime('%Y-%m-%d')} - {df['date'].max().strftime('%Y-%m-%d')}")
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных: {e}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Загружает метаданные исторических данных"""
        if self._metadata_cache is not None:
            return self._metadata_cache
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            self._metadata_cache = metadata
            return metadata
        except Exception as e:
            logger.error(f"Ошибка загрузки метаданных: {e}")
            return {}
    
    def get_data_for_period(self, days: int = 30) -> pd.DataFrame:
        """
        Получает данные за указанный период
        
        Args:
            days: Количество дней назад
            
        Returns:
            DataFrame с данными за период
        """
        df = self.load_data()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Фильтруем данные по периоду
        mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        period_data = df[mask].copy()
        
        return period_data
    
    def get_current_position_stats(self) -> Dict[str, Any]:
        """
        Рассчитывает текущую позицию относительно исторических уровней
        
        Returns:
            Словарь со статистикой текущей позиции
        """
        df = self.load_data()
        
        if df.empty:
            return {}
        
        # Получаем последнюю цену
        latest_price = df['close'].iloc[-1]
        
        # Рассчитываем статистику
        stats = {
            'current_price': latest_price,
            'historical_max': df['close'].max(),
            'historical_min': df['close'].min(),
            'all_time_high': df['close'].max(),
            'all_time_low': df['close'].min(),
            'percent_from_ath': ((latest_price - df['close'].max()) / df['close'].max()) * 100,
            'percent_from_atl': ((latest_price - df['close'].min()) / df['close'].min()) * 100,
            'current_rank': len(df[df['close'] <= latest_price]),
            'total_records': len(df),
            'percentile': (len(df[df['close'] <= latest_price]) / len(df)) * 100
        }
        
        return stats
    
    def calculate_technical_indicators(self, period: int = 14) -> pd.DataFrame:
        """
        Рассчитывает технические индикаторы
        
        Args:
            period: Период для расчета индикаторов
            
        Returns:
            DataFrame с техническими индикаторами
        """
        df = self.load_data().copy()
        
        if len(df) < period:
            return df
        
        # Простая скользящая средняя
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Экспоненциальная скользящая средняя
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Волатильность
        df['volatility'] = df['close'].rolling(window=period).std()
        
        # Объемная скользящая средняя
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def get_trend_analysis(self, days: int = 30) -> Dict[str, Any]:
        """
        Анализ трендов за указанный период
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь с анализом трендов
        """
        df = self.get_data_for_period(days)
        
        if df.empty:
            return {}
        
        # Рассчитываем индикаторы
        df_with_indicators = self.calculate_technical_indicators()
        
        # Получаем последние значения
        latest = df_with_indicators.iloc[-1]
        
        # Анализ трендов
        trend_analysis = {
            'price_trend': 'bullish' if latest['close'] > latest['sma_20'] else 'bearish',
            'sma_trend': 'bullish' if latest['sma_20'] > latest['sma_50'] else 'bearish',
            'macd_signal': 'bullish' if latest['macd'] > latest['macd_signal'] else 'bearish',
            'rsi_level': latest['rsi'],
            'rsi_signal': 'oversold' if latest['rsi'] < 30 else 'overbought' if latest['rsi'] > 70 else 'neutral',
            'bb_position': 'upper' if latest['close'] > latest['bb_upper'] else 'lower' if latest['close'] < latest['bb_lower'] else 'middle',
            'volume_trend': 'high' if latest['volume'] > latest['volume_sma'] else 'low'
        }
        
        return trend_analysis
    
    def get_volatility_analysis(self, days: int = 30) -> Dict[str, Any]:
        """
        Анализ волатильности
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь с анализом волатильности
        """
        df = self.get_data_for_period(days)
        
        if df.empty:
            return {}
        
        # Рассчитываем волатильность
        returns = df['close'].pct_change()
        
        # Рассчитываем дневной диапазон
        daily_range = (df['high'] - df['low']) / df['close']
        
        volatility_analysis = {
            'current_volatility': returns.std() * np.sqrt(252),  # Годовая волатильность
            'avg_daily_range': daily_range.mean(),
            'max_daily_range': daily_range.max(),
            'volatility_percentile': len(df[returns <= returns.iloc[-1]]) / len(df) * 100 if len(df) > 0 else 0
        }
        
        return volatility_analysis
    
    def get_historical_comparison(self, current_price: float) -> Dict[str, Any]:
        """
        Сравнение текущей цены с историческими периодами
        
        Args:
            current_price: Текущая цена Bitcoin
            
        Returns:
            Словарь с историческими сравнениями
        """
        df = self.load_data()
        
        if df.empty:
            return {}
        
        # Находим похожие ценовые уровни
        similar_prices = df[abs(df['close'] - current_price) / current_price < 0.1]  # ±10%
        
        comparison = {
            'similar_periods': len(similar_prices),
            'price_levels': similar_prices['close'].tolist()[-10:],  # Последние 10
            'dates': similar_prices['date'].dt.strftime('%Y-%m-%d').tolist()[-10:],
            'avg_price_at_level': similar_prices['close'].mean() if not similar_prices.empty else 0
        }
        
        return comparison
    
    def get_seasonality_analysis(self) -> Dict[str, Any]:
        """
        Анализ сезонности
        
        Returns:
            Словарь с анализом сезонности
        """
        df = self.load_data()
        
        if df.empty:
            return {}
        
        # Добавляем месяц и день недели
        df['month'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.dayofweek
        
        # Анализ по месяцам
        monthly_returns = df.groupby('month')['close'].pct_change().mean()
        monthly_volatility = df.groupby('month')['close'].pct_change().std()
        
        # Анализ по дням недели
        daily_returns = df.groupby('day_of_week')['close'].pct_change().mean()
        daily_volatility = df.groupby('day_of_week')['close'].pct_change().std()
        
        # Проверяем, что это Series, а не скаляр
        if isinstance(monthly_returns, pd.Series) and monthly_returns.size > 0:
            best_month = int(monthly_returns.idxmax())
            worst_month = int(monthly_returns.idxmin())
        else:
            best_month = 1
            worst_month = 1
            
        if isinstance(daily_returns, pd.Series) and daily_returns.size > 0:
            best_day = int(daily_returns.idxmax())
            worst_day = int(daily_returns.idxmin())
        else:
            best_day = 0
            worst_day = 0
        
        seasonality = {
            'best_month': best_month,
            'worst_month': worst_month,
            'best_day': best_day,
            'worst_day': worst_day,
            'monthly_returns': monthly_returns.to_dict() if isinstance(monthly_returns, pd.Series) else {},
            'daily_returns': daily_returns.to_dict() if isinstance(daily_returns, pd.Series) else {}
        }
        
        return seasonality
    
    def get_market_cycles(self) -> Dict[str, Any]:
        """
        Анализ рыночных циклов
        
        Returns:
            Словарь с анализом циклов
        """
        df = self.load_data()
        
        if df.empty:
            return {}
        
        # Находим пики и впадины
        df['is_peak'] = (df['close'] > df['close'].shift(1)) & (df['close'] > df['close'].shift(-1))
        df['is_trough'] = (df['close'] < df['close'].shift(1)) & (df['close'] < df['close'].shift(-1))
        
        peaks = df[df['is_peak']]
        troughs = df[df['is_trough']]
        
        cycles = {
            'total_peaks': len(peaks),
            'total_troughs': len(troughs),
            'last_peak_date': peaks['date'].iloc[-1].strftime('%Y-%m-%d') if not peaks.empty else None,
            'last_trough_date': troughs['date'].iloc[-1].strftime('%Y-%m-%d') if not troughs.empty else None,
            'avg_cycle_length': len(df) / max(len(peaks), len(troughs)) if max(len(peaks), len(troughs)) > 0 else 0
        }
        
        return cycles
    
    def export_analysis_report(self) -> Dict[str, Any]:
        """
        Создает полный отчет анализа исторических данных
        
        Returns:
            Словарь с полным отчетом
        """
        try:
            # Загружаем данные
            df = self.load_data()
            
            if df.empty:
                return {'error': 'Нет данных для анализа'}
            
            # Получаем текущую позицию
            position_stats = self.get_current_position_stats()
            
            # Анализ трендов
            trend_analysis = self.get_trend_analysis(30)
            
            # Анализ волатильности
            volatility_analysis = self.get_volatility_analysis(30)
            
            # Сезонность
            seasonality = self.get_seasonality_analysis()
            
            # Рыночные циклы
            cycles = self.get_market_cycles()
            
            # Метаданные
            metadata = self.get_metadata()
            
            report = {
                'metadata': metadata,
                'position_stats': position_stats,
                'trend_analysis': trend_analysis,
                'volatility_analysis': volatility_analysis,
                'seasonality': seasonality,
                'market_cycles': cycles,
                'generated_at': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Ошибка создания отчета: {e}")
            return {'error': str(e)}
    
    def save_analysis_cache(self, report: Dict[str, Any], filename: str = None):
        """
        Сохраняет отчет анализа в кеш
        
        Args:
            report: Отчет для сохранения
            filename: Имя файла (опционально)
        """
        if filename is None:
            filename = f"historical_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        cache_dir = 'cache'
        os.makedirs(cache_dir, exist_ok=True)
        
        filepath = os.path.join(cache_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Отчет сохранен в кеш: {filepath}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения отчета: {e}")

    def get_smart_sample_data(self, max_points: int = 50) -> pd.DataFrame:
        """
        Создает умную выборку данных для экономичного анализа
        
        Args:
            max_points: Максимальное количество точек для анализа
            
        Returns:
            DataFrame с умной выборкой данных
        """
        df = self.load_data()
        
        if len(df) <= max_points:
            return df
        
        # Стратегия выборки:
        # 1. Всегда включаем последние 30 дней (текущий тренд)
        # 2. Ключевые исторические моменты (ATH, важные уровни)
        # 3. Равномерно распределенные точки по всей истории
        # 4. Дополнительные ключевые периоды (каждые 5 лет)
        
        sample_data = []
        
        # 1. Последние 30 дней (если есть)
        recent_days = min(30, len(df))
        sample_data.extend(df.tail(recent_days).to_dict('records'))
        
        # 2. Ключевые исторические моменты
        key_moments = self._get_key_historical_moments(df)
        for moment in key_moments:
            if moment not in sample_data:
                sample_data.append(moment)
        
        # 3. Дополнительные ключевые периоды (каждые 5 лет)
        years = df['date'].dt.year.unique()
        for year in years[::5]:  # Каждые 5 лет
            year_data = df[df['date'].dt.year == year]
            if not year_data.empty:
                # Берем середину года
                mid_year = year_data.iloc[len(year_data)//2]
                record = mid_year.to_dict()
                if record not in sample_data:
                    sample_data.append(record)
        
        # 4. Равномерно распределенные точки по всей истории
        remaining_slots = max_points - len(sample_data)
        if remaining_slots > 0:
            # Берем равномерно распределенные точки
            step = len(df) // remaining_slots
            for i in range(0, len(df), step):
                if len(sample_data) >= max_points:
                    break
                record = df.iloc[i].to_dict()
                if record not in sample_data:
                    sample_data.append(record)
        
        # Сортируем по дате
        sample_df = pd.DataFrame(sample_data)
        sample_df = sample_df.sort_values('date')
        
        logger.info(f"Создана умная выборка: {len(sample_df)} точек из {len(df)} записей")
        logger.info(f"Период выборки: {sample_df['date'].min().strftime('%Y-%m-%d')} - {sample_df['date'].max().strftime('%Y-%m-%d')}")
        
        return sample_df
    
    def _get_key_historical_moments(self, df: pd.DataFrame) -> List[Dict]:
        """
        Находит ключевые исторические моменты
        
        Args:
            df: DataFrame с данными
            
        Returns:
            Список ключевых моментов
        """
        moments = []
        
        # ATH (All Time High)
        ath_idx = df['close'].idxmax()
        moments.append(df.loc[ath_idx].to_dict())
        
        # ATL (All Time Low) - исключая нулевые цены
        valid_data = df[df['close'] > 0]
        if not valid_data.empty:
            atl_idx = valid_data['close'].idxmin()
            moments.append(valid_data.loc[atl_idx].to_dict())
        
        # Ключевые ценовые уровни
        price_levels = [1, 100, 1000, 10000, 50000, 100000]
        for level in price_levels:
            # Находим первое достижение уровня
            above_level = df[df['close'] >= level]
            if not above_level.empty:
                first_achievement = above_level.iloc[0]
                moments.append(first_achievement.to_dict())
        
        # Важные периоды (каждые 2 года)
        years = df['date'].dt.year.unique()
        for year in years[::2]:  # Каждые 2 года
            year_data = df[df['date'].dt.year == year]
            if not year_data.empty:
                # Берем середину года
                mid_year = year_data.iloc[len(year_data)//2]
                moments.append(mid_year.to_dict())
        
        return moments
    
    def get_efficient_analysis_data(self, days: int = 365) -> pd.DataFrame:
        """
        Получает данные для экономичного анализа
        
        Args:
            days: Количество дней для анализа (по умолчанию год)
            
        Returns:
            DataFrame с данными для анализа
        """
        if days <= 365:
            # Для короткого периода используем все данные
            return self.get_data_for_period(days)
        else:
            # Для длинного периода используем умную выборку с увеличенным количеством точек
            return self.get_smart_sample_data(max_points=150)  # Увеличили с 100 до 150 для лучшего покрытия

 