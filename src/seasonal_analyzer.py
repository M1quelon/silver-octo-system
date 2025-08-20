#!/usr/bin/env python3
"""
Модуль для анализа сезонных данных и праздничных паттернов
Интегрирует исторические данные с календарными событиями
"""
import pandas as pd
import numpy as np
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Добавляем путь к корневой папке
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.historical_data.database_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class SeasonalAnalyzer:
    """Анализатор сезонных данных и праздничных паттернов"""
    
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        
        # Кеш для результатов анализа
        self._cache = {}
        self._cache_timeout = 3600  # 1 час
    
    def get_current_seasonal_analysis(self, coin_id: str) -> Dict[str, Any]:
        """Получает текущий сезонный анализ для монеты"""
        try:
            # Получаем текущие события
            current_events = self.db_manager.get_current_seasonal_events()
            
            # Получаем данные монеты за последний год
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)
            coin_data = self.db_manager.get_daily_data(coin_id, start_date=start_date, end_date=end_date)
            
            if coin_data.empty:
                return {}
            
            # Анализируем сезонные паттерны
            seasonal_patterns = self._analyze_seasonal_patterns(coin_data)
            
            # Анализируем ближайшие события
            upcoming_events = self._analyze_upcoming_events(coin_id, current_events)
            
            # Создаем сезонные индикаторы
            seasonal_indicators = self._create_seasonal_indicators(coin_id, seasonal_patterns, upcoming_events)
            
            return {
                'current_events': current_events,
                'seasonal_patterns': seasonal_patterns,
                'upcoming_events': upcoming_events,
                'seasonal_indicators': seasonal_indicators,
                'seasonal_trend': self._determine_seasonal_trend(seasonal_indicators),
                'next_important_date': self._get_next_important_date(current_events),
                'analysis_date': datetime.now().strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"Ошибка сезонного анализа для {coin_id}: {e}")
            return {}
    
    def _analyze_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Анализирует сезонные паттерны в данных"""
        if df.empty:
            return {}
        
        patterns = {}
        
        # Месячные паттерны
        df['month'] = pd.to_datetime(df['date']).dt.month
        monthly_stats = df.groupby('month')['close'].agg(['mean', 'std', 'count']).reset_index()
        
        patterns['monthly'] = {
            'best_month': monthly_stats.loc[monthly_stats['mean'].idxmax(), 'month'],
            'worst_month': monthly_stats.loc[monthly_stats['mean'].idxmin(), 'month'],
            'volatility_by_month': monthly_stats.to_dict('records')
        }
        
        # Недельные паттерны
        df['weekday'] = pd.to_datetime(df['date']).dt.dayofweek
        weekly_stats = df.groupby('weekday')['close'].agg(['mean', 'std']).reset_index()
        
        patterns['weekly'] = {
            'best_day': weekly_stats.loc[weekly_stats['mean'].idxmax(), 'weekday'],
            'worst_day': weekly_stats.loc[weekly_stats['mean'].idxmin(), 'weekday'],
            'volatility_by_day': weekly_stats.to_dict('records')
        }
        
        # Квартальные паттерны
        df['quarter'] = pd.to_datetime(df['date']).dt.quarter
        quarterly_stats = df.groupby('quarter')['close'].agg(['mean', 'std']).reset_index()
        
        patterns['quarterly'] = {
            'best_quarter': quarterly_stats.loc[quarterly_stats['mean'].idxmax(), 'quarter'],
            'worst_quarter': quarterly_stats.loc[quarterly_stats['mean'].idxmin(), 'quarter'],
            'quarterly_performance': quarterly_stats.to_dict('records')
        }
        
        return patterns
    
    def _analyze_upcoming_events(self, coin_id: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Анализирует влияние предстоящих событий"""
        analyzed_events = []
        
        for event in events:
            # Получаем исторические данные по этому событию
            holiday_data = self.db_manager.get_holiday_performance(coin_id, event['event_name'])
            
            if not holiday_data.empty:
                # Анализируем историческую производительность
                avg_change = holiday_data['price_change_percent'].mean()
                success_rate = (holiday_data['price_change_percent'] > 0).mean()
                volatility = holiday_data['price_change_percent'].std()
                
                analyzed_events.append({
                    'event_name': event['event_name'],
                    'event_type': event['event_type'],
                    'days_until_event': event['days_until_event'],
                    'expected_impact': event['expected_impact'],
                    'importance_level': event['importance_level'],
                    'historical_avg_change': avg_change,
                    'historical_success_rate': success_rate,
                    'historical_volatility': volatility,
                    'sample_size': len(holiday_data),
                    'confidence': min(len(holiday_data) / 10, 1.0)  # Уверенность на основе размера выборки
                })
            else:
                # Если нет исторических данных, используем ожидаемый эффект
                analyzed_events.append({
                    'event_name': event['event_name'],
                    'event_type': event['event_type'],
                    'days_until_event': event['days_until_event'],
                    'expected_impact': event['expected_impact'],
                    'importance_level': event['importance_level'],
                    'historical_avg_change': 0,
                    'historical_success_rate': 0.5,
                    'historical_volatility': 0,
                    'sample_size': 0,
                    'confidence': 0.1
                })
        
        return analyzed_events
    
    def _create_seasonal_indicators(self, coin_id: str, patterns: Dict[str, Any], 
                                   events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Создает сезонные индикаторы"""
        current_date = datetime.now()
        current_month = current_date.month
        current_weekday = current_date.weekday()
        
        # Текущий сезонный тренд
        monthly_pattern = patterns.get('monthly', {})
        current_month_performance = next(
            (item for item in monthly_pattern.get('volatility_by_month', []) 
             if item['month'] == current_month), None
        )
        
        # Ближайшие события
        upcoming_events = [e for e in events if e.get('days_until_event', 0) <= 30]
        
        # Рассчитываем сезонную силу
        seasonal_strength = self._calculate_seasonal_strength(patterns, events)
        
        # Определяем сезонный тренд
        seasonal_trend = self._determine_seasonal_trend_from_data(patterns, events)
        
        # Получаем следующее важное событие
        next_important_event = self._get_next_important_event(events)
        
        indicators = {
            'current_month_performance': current_month_performance,
            'current_weekday_performance': patterns.get('weekly', {}).get('volatility_by_day', []),
            'upcoming_events_count': len(upcoming_events),
            'seasonal_strength': seasonal_strength,
            'seasonal_trend': seasonal_trend,
            'next_important_event': next_important_event,
            'seasonal_notes': self._generate_seasonal_notes(patterns, events)
        }
        
        # Сохраняем индикаторы в базу
        save_data = {
            'date': current_date.strftime('%Y-%m-%d'),
            'current_event': next_important_event.get('event_name', '') if next_important_event else '',
            'days_to_event': next_important_event.get('days_until_event', 0) if next_important_event else 0,
            'historical_avg_change': next_important_event.get('historical_avg_change', 0) if next_important_event else 0,
            'historical_success_rate': next_important_event.get('historical_success_rate', 0) if next_important_event else 0,
            'seasonal_trend': seasonal_trend,
            'seasonal_strength': seasonal_strength,
            'next_important_date': next_important_event.get('event_name', '') if next_important_event else '',
            'seasonal_notes': indicators.get('seasonal_notes', '')
        }
        
        self.db_manager.save_current_seasonal_indicators(coin_id, save_data)
        
        return indicators
    
    def _calculate_seasonal_strength(self, patterns: Dict[str, Any], events: List[Dict[str, Any]]) -> float:
        """Рассчитывает силу сезонного сигнала"""
        strength = 0.0
        
        # Вклад от месячных паттернов
        if 'monthly' in patterns:
            monthly_data = patterns['monthly'].get('volatility_by_month', [])
            if monthly_data:
                current_month = datetime.now().month
                current_month_data = next((item for item in monthly_data if item['month'] == current_month), None)
                if current_month_data:
                    # Нормализуем среднее значение
                    all_means = [item['mean'] for item in monthly_data]
                    if all_means:
                        normalized_mean = (current_month_data['mean'] - min(all_means)) / (max(all_means) - min(all_means))
                        strength += normalized_mean * 0.3
        
        # Вклад от предстоящих событий
        if events:
            important_events = [e for e in events if e['importance_level'] >= 3]
            if important_events:
                avg_confidence = sum(e['confidence'] for e in important_events) / len(important_events)
                strength += avg_confidence * 0.4
        
        # Вклад от исторической успешности
        if events:
            avg_success_rate = sum(e['historical_success_rate'] for e in events) / len(events)
            strength += avg_success_rate * 0.3
        
        return min(strength, 1.0)
    
    def _determine_seasonal_trend_from_data(self, patterns: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
        """Определяет сезонный тренд на основе данных"""
        bullish_signals = 0
        bearish_signals = 0
        
        # Анализ месячных паттернов
        if 'monthly' in patterns:
            monthly_data = patterns['monthly'].get('volatility_by_month', [])
            if monthly_data:
                current_month = datetime.now().month
                current_month_data = next((item for item in monthly_data if item['month'] == current_month), None)
                if current_month_data:
                    all_means = [item['mean'] for item in monthly_data]
                    if all_means:
                        current_rank = sorted(all_means, reverse=True).index(current_month_data['mean'])
                        if current_rank < len(all_means) * 0.4:  # Топ 40%
                            bullish_signals += 1
                        elif current_rank > len(all_means) * 0.6:  # Нижние 40%
                            bearish_signals += 1
        
        # Анализ предстоящих событий
        for event in events:
            if event['historical_avg_change'] > 0 and event['historical_success_rate'] > 0.6:
                bullish_signals += 1
            elif event['historical_avg_change'] < 0 and event['historical_success_rate'] > 0.6:
                bearish_signals += 1
        
        if bullish_signals > bearish_signals:
            return 'bullish'
        elif bearish_signals > bullish_signals:
            return 'bearish'
        else:
            return 'neutral'
    
    def _get_next_important_event(self, events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Получает следующее важное событие"""
        if not events:
            return None
        
        # Сортируем по важности и времени
        sorted_events = sorted(events, key=lambda x: (x['importance_level'], x['days_until_event']), reverse=True)
        
        # Ищем ближайшее важное событие (уровень 3+)
        important_events = [e for e in sorted_events if e['importance_level'] >= 3]
        
        if important_events:
            return important_events[0]
        
        # Если нет важных событий, возвращаем ближайшее
        return sorted_events[0] if sorted_events else None
    
    def _get_next_important_date(self, events: List[Dict[str, Any]]) -> str:
        """Получает следующую важную дату"""
        next_event = self._get_next_important_event(events)
        if next_event:
            return f"{next_event['event_name']} (через {next_event['days_until_event']} дней)"
        return "Нет предстоящих важных событий"
    
    def _generate_seasonal_notes(self, patterns: Dict[str, Any], events: List[Dict[str, Any]]) -> str:
        """Генерирует заметки о сезонных паттернах"""
        notes = []
        
        # Месячные паттерны
        if 'monthly' in patterns:
            monthly = patterns['monthly']
            current_month = datetime.now().month
            best_month = monthly.get('best_month')
            worst_month = monthly.get('worst_month')
            
            if current_month == best_month:
                notes.append("Текущий месяц исторически сильный")
            elif current_month == worst_month:
                notes.append("Текущий месяц исторически слабый")
        
        # Предстоящие события
        if events:
            important_events = [e for e in events if e['importance_level'] >= 4]
            if important_events:
                event = important_events[0]
                notes.append(f"Ближайшее важное событие: {event['event_name']} (через {event['days_until_event']} дней)")
        
        return "; ".join(notes) if notes else "Нет особых сезонных факторов"
    
    def _determine_seasonal_trend(self, indicators: Dict[str, Any]) -> str:
        """Определяет общий сезонный тренд"""
        return indicators.get('seasonal_trend', 'neutral')
    
    def get_seasonal_summary_for_ai(self, coin_id: str) -> str:
        """Создает краткую сводку сезонных данных для AI"""
        analysis = self.get_current_seasonal_analysis(coin_id)
        
        if not analysis:
            return ""
        
        summary_parts = []
        
        # Текущие события
        if analysis.get('current_events'):
            events = analysis['current_events'][:3]  # Топ 3 события
            event_summary = "📅 Сезонные события: "
            event_summary += ", ".join([f"{e['event_name']} ({e['days_until_event']}д)" for e in events])
            summary_parts.append(event_summary)
        
        # Сезонный тренд
        seasonal_trend = analysis.get('seasonal_trend', 'neutral')
        trend_emoji = "📈" if seasonal_trend == 'bullish' else "📉" if seasonal_trend == 'bearish' else "➡️"
        summary_parts.append(f"{trend_emoji} Сезонный тренд: {seasonal_trend}")
        
        # Сезонная сила
        strength = analysis.get('seasonal_indicators', {}).get('seasonal_strength', 0)
        summary_parts.append(f"💪 Сезонная сила: {strength:.1%}")
        
        # Следующее важное событие
        next_event = analysis.get('seasonal_indicators', {}).get('next_important_event')
        if next_event:
            summary_parts.append(f"🎯 Следующее событие: {next_event['event_name']} (через {next_event['days_until_event']} дней)")
        
        return " | ".join(summary_parts)

 