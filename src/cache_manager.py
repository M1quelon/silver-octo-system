"""
Модуль для управления кэшем рыночных данных
"""
import json
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from data_collectors import DataCollector
from crypto_data_collector import CryptoDataCollector

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class NumpyEncoder(json.JSONEncoder):
    """Кастомный энкодер для работы с numpy типами"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

class CacheManager:
    """Управление кэшем рыночных данных"""
    
    def __init__(self):
        self.config = Config()
        self.cache_dir = "cache"
        self.cache_file = os.path.join(self.cache_dir, "market_data.json")
        self.crypto_cache_file = os.path.join(self.cache_dir, "crypto_data.json")
        self.data_collector = DataCollector()
        self.crypto_data_collector = CryptoDataCollector()
        
        # Создаём папку кэша если её нет
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Время обновления кэша (2 раза в день: 9:00 и 21:00 МСК)
        self.update_hours = [9, 21]
        
        # Время обновления криптокэша (2 раза в день: 8:00 и 20:00 МСК)
        self.crypto_update_hours = [8, 20]
    
    def _convert_numpy_types(self, data: Any) -> Any:
        """Рекурсивно конвертирует numpy типы в обычные Python типы"""
        if isinstance(data, dict):
            return {key: self._convert_numpy_types(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_numpy_types(item) for item in data]
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        else:
            return data
    
    def _is_cache_valid(self) -> bool:
        """
        Проверяет валидность кэша
        Кэш валиден если он обновлялся сегодня в одно из времён обновления
        """
        if not os.path.exists(self.cache_file):
            return False
            
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            last_update_str = cache_data.get('last_update', '')
            if not last_update_str:
                return False
                
            last_update = datetime.fromisoformat(last_update_str)
            now = datetime.now()
            
            # Проверяем что последнее обновление было сегодня
            if last_update.date() != now.date():
                return False
            
            # Проверяем что обновление было в одно из плановых времён
            current_hour = now.hour
            last_update_hour = last_update.hour
            
            # Если прошло время следующего обновления, кэш устарел
            next_update_hour = None
            for hour in self.update_hours:
                if current_hour < hour:
                    next_update_hour = hour
                    break
            
            # Если нет следующего обновления сегодня, проверяем было ли вечернее
            if next_update_hour is None:
                return last_update_hour >= max(self.update_hours)
            
            # Проверяем было ли обновление в последнее плановое время
            last_planned_hour = None
            for hour in reversed(self.update_hours):
                if current_hour >= hour:
                    last_planned_hour = hour
                    break
            
            if last_planned_hour is None:
                # Если ещё не время первого обновления, проверяем вчерашнее вечернее
                yesterday = now - timedelta(days=1)
                return (last_update.date() == yesterday.date() and 
                       last_update_hour >= max(self.update_hours))
            
            return last_update_hour >= last_planned_hour
            
        except Exception as e:
            logger.error(f"Ошибка проверки кэша: {e}")
            return False
    
    def _save_cache(self, data: Dict[str, Any]) -> None:
        """Сохранение данных в кэш"""
        try:
            # Конвертируем numpy типы
            clean_data = self._convert_numpy_types(data)
            
            cache_data = {
                'last_update': datetime.now().isoformat(),
                'data': clean_data
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
            
            logger.info(f"Кэш обновлён: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша: {e}")
    
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Загрузка данных из кэша"""
        try:
            if not os.path.exists(self.cache_file):
                return None
                
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"Ошибка загрузки кэша: {e}")
            return None
    
    def get_market_data(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Получение рыночных данных (из кэша или обновление)
        
        Args:
            force_update: Принудительное обновление данных
        """
        
        # Проверяем валидность кэша
        if not force_update and self._is_cache_valid():
            cached_data = self._load_cache()
            if cached_data:
                logger.info("Данные получены из кэша")
                return cached_data
        
        # Обновляем данные
        logger.info("Обновление рыночных данных...")
        fresh_data = self.data_collector.collect_all_metrics()
        
        # Сохраняем в кэш
        self._save_cache(fresh_data)
        
        return fresh_data
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Информация о состоянии кэша"""
        try:
            if not os.path.exists(self.cache_file):
                return {
                    'exists': False,
                    'last_update': None,
                    'is_valid': False,
                    'next_update': self._get_next_update_time()
                }
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            last_update_str = cache_data.get('last_update', '')
            last_update = datetime.fromisoformat(last_update_str) if last_update_str else None
            
            return {
                'exists': True,
                'last_update': last_update,
                'is_valid': self._is_cache_valid(),
                'next_update': self._get_next_update_time(),
                'data_sources': cache_data.get('data', {}).get('data_quality', {}).get('sources_available', 0)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о кэше: {e}")
            return {'exists': False, 'error': str(e)}
    
    def _get_next_update_time(self) -> datetime:
        """Получение времени следующего обновления"""
        now = datetime.now()
        
        # Ищем следующее время обновления сегодня
        for hour in self.update_hours:
            next_update = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if next_update > now:
                return next_update
        
        # Если сегодня обновлений больше нет, берём первое время завтра
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=self.update_hours[0], minute=0, second=0, microsecond=0)
    
    # ================== МЕТОДЫ ДЛЯ КРИПТОДАННЫХ ==================
    
    def _is_crypto_cache_valid(self) -> bool:
        """
        Проверяет валидность криптокэша
        Кэш валиден если он обновлялся сегодня в одно из времён обновления
        """
        if not os.path.exists(self.crypto_cache_file):
            return False
            
        try:
            with open(self.crypto_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            last_update_str = cache_data.get('last_update', '')
            if not last_update_str:
                return False
                
            last_update = datetime.fromisoformat(last_update_str)
            now = datetime.now()
            
            # Проверяем, что последнее обновление было сегодня
            if last_update.date() != now.date():
                return False
            
            # Проверяем, что обновление было в одно из назначенных времён
            for hour in self.crypto_update_hours:
                scheduled_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
                
                # Даём 30 минут после назначенного времени
                if scheduled_time <= last_update <= scheduled_time + timedelta(minutes=30):
                    return True
                    
            return False
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Ошибка проверки валидности криптокэша: {e}")
            return False
    
    def _save_crypto_cache(self, data: Dict[str, Any]) -> None:
        """Сохраняет криптоданные в кэш"""
        try:
            # Конвертируем numpy типы
            clean_data = self._convert_numpy_types(data)
            
            cache_data = {
                'data': clean_data,
                'last_update': datetime.now().isoformat(),
                'update_count': 1
            }
            
            # Если файл уже существует, увеличиваем счётчик
            if os.path.exists(self.crypto_cache_file):
                try:
                    with open(self.crypto_cache_file, 'r', encoding='utf-8') as f:
                        existing_cache = json.load(f)
                        cache_data['update_count'] = existing_cache.get('update_count', 0) + 1
                except:
                    pass
            
            with open(self.crypto_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
                
            logger.info(f"Криптокэш сохранён, обновление #{cache_data['update_count']}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения криптокэша: {e}")
    
    def _load_crypto_cache(self) -> Optional[Dict[str, Any]]:
        """Загружает данные из криптокэша"""
        try:
            if not os.path.exists(self.crypto_cache_file):
                return None
                
            with open(self.crypto_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            logger.info("Криптоданные загружены из кэша")
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"Ошибка загрузки криптокэша: {e}")
            return None
    
    def get_crypto_data(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Получает криптоданные с учётом кэширования
        
        Args:
            force_update: Принудительно обновить данные
            
        Returns:
            Словарь с криптоданными
        """
        logger.info("Запрос криптоданных...")
        
        # Проверяем валидность кэша
        if not force_update and self._is_crypto_cache_valid():
            logger.info("Криптокэш валиден, возвращаем данные из кэша")
            cached_data = self._load_crypto_cache()
            if cached_data:
                return cached_data
        
        # Кэш не валиден или force_update, получаем свежие данные
        logger.info("Получение свежих криптоданных...")
        
        try:
            crypto_data = self.crypto_data_collector.collect_all_crypto_data()
            
            if crypto_data:
                # Сохраняем в кэш
                self._save_crypto_cache(crypto_data)
                logger.info("Свежие криптоданные получены и сохранены в кэш")
                return crypto_data
            else:
                logger.warning("Не удалось получить свежие криптоданные")
                
                # Пытаемся вернуть устаревшие данные из кэша
                cached_data = self._load_crypto_cache()
                if cached_data:
                    logger.info("Возвращаем устаревшие криптоданные из кэша")
                    return cached_data
                
                return {}
                
        except Exception as e:
            logger.error(f"Ошибка получения криптоданных: {e}")
            
            # В случае ошибки пытаемся вернуть кэшированные данные
            cached_data = self._load_crypto_cache()
            if cached_data:
                logger.info("Возвращаем кэшированные криптоданные после ошибки")
                return cached_data
                
            return {}
    
    def get_crypto_cache_info(self) -> Dict[str, Any]:
        """Возвращает информацию о состоянии криптокэша"""
        cache_exists = os.path.exists(self.crypto_cache_file)
        is_valid = self._is_crypto_cache_valid()
        
        info = {
            'exists': cache_exists,
            'is_valid': is_valid,
            'cache_file': self.crypto_cache_file
        }
        
        if cache_exists:
            try:
                with open(self.crypto_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                last_update_str = cache_data.get('last_update', '')
                if last_update_str:
                    last_update = datetime.fromisoformat(last_update_str)
                    info['last_update'] = last_update
                    info['next_update'] = self._get_next_crypto_update_time()
                
                # Считаем количество источников данных
                data = cache_data.get('data', {})
                sources = data.get('data_sources', {})
                info['data_sources'] = sum(sources.values()) if sources else 0
                info['update_count'] = cache_data.get('update_count', 0)
                
            except Exception as e:
                logger.error(f"Ошибка получения информации о криптокэше: {e}")
        
        return info
    
    def _get_next_crypto_update_time(self) -> datetime:
        """Возвращает время следующего обновления криптокэша"""
        now = datetime.now()
        
        # Ищем ближайшее время обновления сегодня
        for hour in sorted(self.crypto_update_hours):
            next_update = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if next_update > now:
                return next_update
        
        # Если сегодня обновлений больше нет, берём первое время завтра
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=self.crypto_update_hours[0], minute=0, second=0, microsecond=0)

def test_cache():
    """Тестирование кэша"""
    print("=== ТЕСТ СИСТЕМЫ КЭШИРОВАНИЯ ===")
    
    # Удаляем старый кэш для чистого теста
    cache_file = "cache/market_data.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print("🗑️ Старый кэш удалён")
    
    cache_manager = CacheManager()
    
    # Информация о кэше
    cache_info = cache_manager.get_cache_info()
    print(f"Кэш существует: {cache_info.get('exists', False)}")
    print(f"Кэш валиден: {cache_info.get('is_valid', False)}")
    print(f"Последнее обновление: {cache_info.get('last_update', 'Никогда')}")
    print(f"Следующее обновление: {cache_info.get('next_update', 'N/A')}")
    
    # Получение данных
    print("\n--- Получение данных ---")
    data = cache_manager.get_market_data()
    print(f"Источников данных: {data.get('data_quality', {}).get('sources_available', 0)}")
    print(f"Время сбора: {data.get('collection_timestamp', 'N/A')}")
    
    # Повторное получение (должно быть из кэша)
    print("\n--- Повторное получение (из кэша) ---")
    data2 = cache_manager.get_market_data()
    print(f"Время сбора: {data2.get('collection_timestamp', 'N/A')}")
    print(f"Данные одинаковые: {data2.get('collection_timestamp') == data.get('collection_timestamp')}")
    
    # Информация о кэше после создания
    cache_info_after = cache_manager.get_cache_info()
    print(f"\n--- После создания кэша ---")
    print(f"Кэш существует: {cache_info_after.get('exists', False)}")
    print(f"Кэш валиден: {cache_info_after.get('is_valid', False)}")
    
    return cache_manager

if __name__ == "__main__":
    test_cache() 