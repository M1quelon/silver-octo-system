"""
Модуль для сбора данных из различных источников
"""
import yfinance as yf
import requests
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import logging

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class DataCollector:
    """Основной класс для сбора данных из всех источников"""
    
    def __init__(self):
        self.config = Config()
    
    def get_yahoo_finance_data(self) -> Dict[str, Any]:
        """
        Получение данных с Yahoo Finance (ТОЛЬКО традиционные рынки)
        Возвращает основные рыночные индикаторы без криптовалют
        """
        try:
            data = {}
            symbols = self.config.YAHOO_SYMBOLS  # Только традиционные рынки
            
            # Получаем данные за последний день
            for name, symbol in symbols.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")  # 2 дня для расчета изменений
                info = ticker.info
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change_pct = ((current_price - prev_price) / prev_price) * 100
                    
                    data[name] = {
                        'symbol': symbol,
                        'current_price': round(current_price, 2),
                        'previous_close': round(prev_price, 2),
                        'change_percent': round(change_pct, 2),
                        'volume': hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0,
                        'high_52w': info.get('fiftyTwoWeekHigh', 'N/A'),
                        'low_52w': info.get('fiftyTwoWeekLow', 'N/A'),
                        'timestamp': datetime.now().isoformat()
                    }
            
            logger.info(f"Yahoo Finance данные получены для {len(data)} традиционных инструментов")
            return data
            
        except Exception as e:
            logger.error(f"Ошибка получения данных Yahoo Finance: {e}")
            return {}
    
    def get_crypto_data(self) -> Dict[str, Any]:
        """
        Получение данных по криптовалютам (отдельный метод)
        """
        try:
            data = {}
            symbols = self.config.CRYPTO_SYMBOLS
            
            # Получаем данные за последний день
            for name, symbol in symbols.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                info = ticker.info
                
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change_pct = ((current_price - prev_price) / prev_price) * 100
                    
                    data[name] = {
                        'symbol': symbol,
                        'current_price': round(current_price, 2),
                        'previous_close': round(prev_price, 2),
                        'change_percent': round(change_pct, 2),
                        'volume': hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0,
                        'market_cap': info.get('marketCap', 'N/A'),
                        'high_52w': info.get('fiftyTwoWeekHigh', 'N/A'),
                        'low_52w': info.get('fiftyTwoWeekLow', 'N/A'),
                        'timestamp': datetime.now().isoformat()
                    }
            
            logger.info(f"Криптовалютные данные получены для {len(data)} монет")
            return data
            
        except Exception as e:
            logger.error(f"Ошибка получения данных криптовалют: {e}")
            return {}
    
    def get_fed_interest_rate(self) -> Dict[str, Any]:
        """
        Получение данных о процентной ставке ФРС
        Используем 3-месячные Treasury Bills как прокси для ставки ФРС
        """
        try:
            ticker = yf.Ticker(self.config.FED_INTEREST_RATE_SYMBOL)
            hist = ticker.history(period="5d")
            
            if not hist.empty:
                current_rate = hist['Close'].iloc[-1]
                prev_rate = hist['Close'].iloc[-2] if len(hist) > 1 else current_rate
                change = current_rate - prev_rate
                
                # Дополнительно получаем 10-летние облигации для контекста
                ten_year_ticker = yf.Ticker("^TNX")
                ten_year_hist = ten_year_ticker.history(period="2d")
                ten_year_rate = ten_year_hist['Close'].iloc[-1] if not ten_year_hist.empty else 0
                
                data = {
                    'current_rate': round(current_rate, 3),
                    'previous_rate': round(prev_rate, 3),
                    'change': round(change, 3),
                    'ten_year_yield': round(ten_year_rate, 3),
                    'yield_curve_spread': round(ten_year_rate - current_rate, 3),
                    'timestamp': datetime.now().isoformat(),
                    'source': '3-Month Treasury Bills (^IRX)'
                }
                
                logger.info("Данные по ставкам ФРС получены")
                return data
                
        except Exception as e:
            logger.error(f"Ошибка получения данных ФРС: {e}")
            return {}
    
    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Получение индекса страха и жадности для криптовалют
        """
        try:
            response = requests.get(self.config.FEAR_GREED_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                current_data = data['data'][0]
                
                # Интерпретация значений
                value = int(current_data['value'])
                if value <= 25:
                    interpretation = "Крайний страх"
                elif value <= 45:
                    interpretation = "Страх"
                elif value <= 55:
                    interpretation = "Нейтральное состояние"
                elif value <= 75:
                    interpretation = "Жадность"
                else:
                    interpretation = "Крайняя жадность"
                
                result = {
                    'value': value,
                    'value_classification': current_data['value_classification'],
                    'interpretation': interpretation,
                    'timestamp': current_data['timestamp'],
                    'time_until_update': current_data.get('time_until_update', 'N/A'),
                    'description': f"Индекс страха и жадности показывает {interpretation.lower()} на рынке криптовалют"
                }
                
                logger.info(f"Fear & Greed Index получен: {value} ({interpretation})")
                return result
                
        except Exception as e:
            logger.error(f"Ошибка получения Fear & Greed Index: {e}")
            return {}
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Сбор всех метрик для команды /metric (БЕЗ криптовалют)
        """
        logger.info("Начинаем сбор метрик для традиционных рынков...")
        
        all_data = {
            'collection_timestamp': datetime.now().isoformat(),
            'yahoo_finance': self.get_yahoo_finance_data(),
            'fed_rates': self.get_fed_interest_rate(),
            'fear_greed_index': self.get_fear_greed_index()
        }
        
        # Проверяем, что получили данные
        successful_sources = sum(1 for source, data in all_data.items() 
                               if source != 'collection_timestamp' and data)
        
        all_data['data_quality'] = {
            'sources_available': successful_sources,
            'total_sources': 3,
            'collection_success_rate': f"{(successful_sources/3)*100:.1f}%"
        }
        
        logger.info(f"Сбор метрик завершен. Успешно получено {successful_sources}/3 источников")
        return all_data
    
    def collect_crypto_metrics(self) -> Dict[str, Any]:
        """
        Сбор криптовалютных метрик для команды /crypto
        """
        logger.info("Начинаем сбор криптовалютных метрик...")
        
        all_data = {
            'collection_timestamp': datetime.now().isoformat(),
            'crypto_data': self.get_crypto_data(),
            'fear_greed_index': self.get_fear_greed_index()
        }
        
        # Проверяем, что получили данные
        successful_sources = sum(1 for source, data in all_data.items() 
                               if source != 'collection_timestamp' and data)
        
        all_data['data_quality'] = {
            'sources_available': successful_sources,
            'total_sources': 2,
            'collection_success_rate': f"{(successful_sources/2)*100:.1f}%"
        }
        
        logger.info(f"Сбор криптометрик завершен. Успешно получено {successful_sources}/2 источников")
        return all_data

# Функция для быстрого тестирования
def test_data_collection():
    """Тестирование сбора данных"""
    collector = DataCollector()
    
    print("=== ТЕСТ СБОРА ТРАДИЦИОННЫХ ДАННЫХ ===")
    data = collector.collect_all_metrics()
    
    print(f"Время сбора: {data['collection_timestamp']}")
    print(f"Качество данных: {data['data_quality']['collection_success_rate']}")
    print(f"\n--- Yahoo Finance (традиционные) ---")
    print(f"Получено инструментов: {len(data['yahoo_finance'])}")
    print("\n--- ФРС ---")
    print(f"Текущая ставка: {data['fed_rates'].get('current_rate', 'N/A')}%")
    print("\n--- Fear & Greed ---")
    print(f"Индекс: {data['fear_greed_index'].get('value', 'N/A')} ({data['fear_greed_index'].get('interpretation', 'N/A')})")
    
    print("\n=== ТЕСТ СБОРА КРИПТОВАЛЮТНЫХ ДАННЫХ ===")
    crypto_data = collector.collect_crypto_metrics()
    
    print(f"Время сбора: {crypto_data['collection_timestamp']}")
    print(f"Качество данных: {crypto_data['data_quality']['collection_success_rate']}")
    print(f"\n--- Криптовалюты ---")
    print(f"Получено монет: {len(crypto_data['crypto_data'])}")
    
    return data, crypto_data

if __name__ == "__main__":
    test_data_collection() 