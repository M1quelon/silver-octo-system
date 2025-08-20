"""
Основной сборщик исторических данных криптовалют
"""
import os
import sys
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pycoingecko import CoinGeckoAPI

# Добавляем путь к корневой папке
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/historical/historical_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CollectionProgress:
    """Класс для отслеживания прогресса сбора данных"""
    coin_id: str
    total_days: int
    collected_days: int
    start_date: datetime
    end_date: datetime
    current_date: datetime
    status: str  # 'pending', 'in_progress', 'completed', 'error'
    errors: List[str]
    last_error: Optional[str]
    collection_start: Optional[datetime]
    collection_end: Optional[datetime]
    
    @property
    def progress_percentage(self) -> float:
        """Процент выполнения"""
        if self.total_days == 0:
            return 0.0
        return (self.collected_days / self.total_days) * 100
    
    @property
    def estimated_time_remaining(self) -> Optional[timedelta]:
        """Оставшееся время (если в процессе)"""
        if self.status != 'in_progress' or not self.collection_start:
            return None
        
        elapsed = datetime.now() - self.collection_start
        if self.collected_days == 0:
            return None
        
        avg_time_per_day = elapsed / self.collected_days
        remaining_days = self.total_days - self.collected_days
        return avg_time_per_day * remaining_days

class HistoricalCollector:
    """Основной сборщик исторических данных"""
    
    def __init__(self):
        self.config = Config()
        self.cg = CoinGeckoAPI()
        
        # Приоритет сбора монет
        self.collection_priority = [
            'bitcoin', 'ethereum', 'binancecoin', 'solana', 'cardano',
            'avalanche-2', 'ripple', 'polkadot', 'chainlink', 'polygon'
        ]
        
        # Даты начала сбора для каждой монеты (с 2017 года)
        self.start_dates = {
            'bitcoin': datetime(2017, 1, 1),
            'ethereum': datetime(2017, 1, 1),
            'binancecoin': datetime(2017, 7, 1),
            'solana': datetime(2020, 3, 1),
            'cardano': datetime(2017, 10, 1),
            'avalanche-2': datetime(2020, 9, 1),
            'ripple': datetime(2017, 1, 1),
            'polkadot': datetime(2020, 5, 1),
            'chainlink': datetime(2019, 5, 1),
            'polygon': datetime(2019, 4, 1)
        }
        
        # Прогресс сбора для каждой монеты
        self.progress: Dict[str, CollectionProgress] = {}
        
        # Статистика API запросов
        self.api_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limit_hits': 0,
            'start_time': None
        }
        
        # Создаем папки если их нет
        os.makedirs('data/historical', exist_ok=True)
        os.makedirs('logs/historical', exist_ok=True)
        
        # Загружаем сохраненный прогресс
        self._load_progress()
    
    def _load_progress(self):
        """Загружает сохраненный прогресс сбора"""
        progress_file = 'data/historical/collection_progress.json'
        
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for coin_id, progress_data in data.items():
                    self.progress[coin_id] = CollectionProgress(
                        coin_id=progress_data['coin_id'],
                        total_days=progress_data['total_days'],
                        collected_days=progress_data['collected_days'],
                        start_date=datetime.fromisoformat(progress_data['start_date']),
                        end_date=datetime.fromisoformat(progress_data['end_date']),
                        current_date=datetime.fromisoformat(progress_data['current_date']),
                        status=progress_data['status'],
                        errors=progress_data.get('errors', []),
                        last_error=progress_data.get('last_error'),
                        collection_start=datetime.fromisoformat(progress_data['collection_start']) if progress_data.get('collection_start') else None,
                        collection_end=datetime.fromisoformat(progress_data['collection_end']) if progress_data.get('collection_end') else None
                    )
                
                logger.info(f"Загружен прогресс для {len(self.progress)} монет")
                
            except Exception as e:
                logger.error(f"Ошибка загрузки прогресса: {e}")
    
    def _save_progress(self):
        """Сохраняет текущий прогресс"""
        progress_file = 'data/historical/collection_progress.json'
        
        try:
            data = {}
            for coin_id, progress in self.progress.items():
                data[coin_id] = {
                    'coin_id': progress.coin_id,
                    'total_days': progress.total_days,
                    'collected_days': progress.collected_days,
                    'start_date': progress.start_date.isoformat(),
                    'end_date': progress.end_date.isoformat(),
                    'current_date': progress.current_date.isoformat(),
                    'status': progress.status,
                    'errors': progress.errors,
                    'last_error': progress.last_error,
                    'collection_start': progress.collection_start.isoformat() if progress.collection_start else None,
                    'collection_end': progress.collection_end.isoformat() if progress.collection_end else None
                }
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Ошибка сохранения прогресса: {e}")
    
    def initialize_collection(self, coin_id: str) -> CollectionProgress:
        """Инициализирует сбор данных для монеты"""
        
        if coin_id not in self.start_dates:
            raise ValueError(f"Монета {coin_id} не поддерживается")
        
        start_date = self.start_dates[coin_id]
        end_date = datetime.now()
        total_days = (end_date - start_date).days
        
        progress = CollectionProgress(
            coin_id=coin_id,
            total_days=total_days,
            collected_days=0,
            start_date=start_date,
            end_date=end_date,
            current_date=start_date,
            status='pending',
            errors=[],
            last_error=None,
            collection_start=None,
            collection_end=None
        )
        
        self.progress[coin_id] = progress
        self._save_progress()
        
        logger.info(f"Инициализирован сбор для {coin_id}: {total_days} дней с {start_date.date()}")
        return progress
    
    def get_collection_status(self) -> Dict[str, Any]:
        """Возвращает статус сбора данных"""
        status = {
            'total_coins': len(self.collection_priority),
            'completed_coins': 0,
            'in_progress_coins': 0,
            'pending_coins': 0,
            'error_coins': 0,
            'api_stats': self.api_stats,
            'coins': {}
        }
        
        for coin_id in self.collection_priority:
            if coin_id in self.progress:
                progress = self.progress[coin_id]
                status['coins'][coin_id] = {
                    'status': progress.status,
                    'progress_percentage': progress.progress_percentage,
                    'collected_days': progress.collected_days,
                    'total_days': progress.total_days,
                    'errors_count': len(progress.errors),
                    'last_error': progress.last_error,
                    'estimated_time_remaining': progress.estimated_time_remaining.total_seconds() if progress.estimated_time_remaining else None
                }
                
                if progress.status == 'completed':
                    status['completed_coins'] += 1
                elif progress.status == 'in_progress':
                    status['in_progress_coins'] += 1
                elif progress.status == 'error':
                    status['error_coins'] += 1
                else:
                    status['pending_coins'] += 1
            else:
                status['coins'][coin_id] = {
                    'status': 'not_started',
                    'progress_percentage': 0.0,
                    'collected_days': 0,
                    'total_days': 0,
                    'errors_count': 0,
                    'last_error': None,
                    'estimated_time_remaining': None
                }
                status['pending_coins'] += 1
        
        return status
    
    def estimate_total_collection_time(self) -> Dict[str, Any]:
        """Оценивает общее время сбора всех данных"""
        
        # Примерные оценки времени на день данных
        time_per_day = 0.1  # секунд на день (с учетом задержек API)
        
        total_days = 0
        for coin_id in self.collection_priority:
            if coin_id in self.start_dates:
                start_date = self.start_dates[coin_id]
                end_date = datetime.now()
                days = (end_date - start_date).days
                total_days += days
        
        estimated_seconds = total_days * time_per_day
        estimated_hours = estimated_seconds / 3600
        estimated_days = estimated_hours / 24
        
        return {
            'total_days_to_collect': total_days,
            'estimated_seconds': estimated_seconds,
            'estimated_hours': estimated_hours,
            'estimated_days': estimated_days,
            'time_per_day_seconds': time_per_day
        }
    
    def start_bitcoin_collection(self) -> CollectionProgress:
        """Начинает сбор данных для Bitcoin"""
        logger.info("🚀 Начинаем сбор исторических данных для Bitcoin...")
        
        # Инициализируем прогресс
        progress = self.initialize_collection('bitcoin')
        progress.status = 'in_progress'
        progress.collection_start = datetime.now()
        
        # Оцениваем время
        time_estimate = self.estimate_total_collection_time()
        logger.info(f"📊 Оценка времени сбора Bitcoin: {time_estimate['estimated_hours']:.2f} часов")
        
        self._save_progress()
        return progress
    
    def start_ethereum_collection(self) -> CollectionProgress:
        """Начинает сбор данных для Ethereum"""
        logger.info("🚀 Начинаем сбор исторических данных для Ethereum...")
        
        # Инициализируем прогресс
        progress = self.initialize_collection('ethereum')
        progress.status = 'in_progress'
        progress.collection_start = datetime.now()
        
        # Оцениваем время
        time_estimate = self.estimate_total_collection_time()
        logger.info(f"📊 Оценка времени сбора Ethereum: {time_estimate['estimated_hours']:.2f} часов")
        
        self._save_progress()
        return progress
    
    def _make_api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Выполняет API запрос с обработкой ошибок"""
        
        self.api_stats['total_requests'] += 1
        
        try:
            # Добавляем задержку для соблюдения лимитов
            time.sleep(0.1)  # 100ms между запросами
            
            if endpoint == 'market_chart':
                response = self.cg.get_coin_market_chart_by_id(
                    id=params['coin_id'],
                    vs_currency='usd',
                    days=params['days']
                )
            elif endpoint == 'coin_info':
                response = self.cg.get_coin_by_id(params['coin_id'])
            else:
                raise ValueError(f"Неизвестный endpoint: {endpoint}")
            
            self.api_stats['successful_requests'] += 1
            return response
            
        except Exception as e:
            self.api_stats['failed_requests'] += 1
            error_msg = str(e)
            
            if 'rate limit' in error_msg.lower():
                self.api_stats['rate_limit_hits'] += 1
                logger.warning(f"Достигнут лимит API запросов: {error_msg}")
                time.sleep(60)  # Ждем минуту при превышении лимита
            else:
                logger.error(f"Ошибка API запроса {endpoint}: {error_msg}")
            
            return None

    def collect_bitcoin_data(self) -> bool:
        """Собирает исторические данные для Bitcoin"""
        
        if 'bitcoin' not in self.progress:
            self.start_bitcoin_collection()
        
        progress = self.progress['bitcoin']
        
        if progress.status == 'completed':
            logger.info("Bitcoin данные уже собраны")
            return True
        
        logger.info("🚀 Начинаем сбор исторических данных Bitcoin...")
        
        # Инициализируем БД менеджер
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database_manager import DatabaseManager
        db_manager = DatabaseManager()
        
        # Получаем метаданные Bitcoin
        logger.info("📋 Получение метаданных Bitcoin...")
        coin_info = self._make_api_request('coin_info', {'coin_id': 'bitcoin'})
        
        if coin_info:
            metadata = {
                'name': coin_info.get('name', 'Bitcoin'),
                'symbol': coin_info.get('symbol', 'BTC').upper(),
                'launch_date': '2009-01-03',  # Дата создания Bitcoin
                'max_supply': coin_info.get('market_data', {}).get('max_supply'),
                'current_supply': coin_info.get('market_data', {}).get('circulating_supply'),
                'algorithm': 'SHA-256',
                'consensus': 'Proof of Work',
                'description': coin_info.get('description', {}).get('en', '')[:500],
                'website': coin_info.get('links', {}).get('homepage', [None])[0]
            }
            
            db_manager.save_coin_metadata('bitcoin', metadata)
            logger.info("✅ Метаданные Bitcoin сохранены")
        
        # Собираем исторические данные
        logger.info("📊 Сбор исторических данных Bitcoin...")
        
        # Получаем данные за весь период (с 2017 года)
        days_to_collect = (progress.end_date - progress.start_date).days
        
        # CoinGecko API возвращает данные за последние N дней
        # Поэтому запрашиваем максимальное количество дней (максимум 365 дней за раз)
        max_days_per_request = 365
        
        # Вычисляем сколько запросов нужно сделать
        total_days_needed = days_to_collect
        requests_needed = (total_days_needed + max_days_per_request - 1) // max_days_per_request
        
        logger.info(f"📅 Нужно собрать {total_days_needed} дней за {requests_needed} запросов")
        
        total_collected = 0
        current_request = 0
        
        while current_request < requests_needed:
            current_request += 1
            days_for_this_request = min(max_days_per_request, total_days_needed - total_collected)
            
            logger.info(f"📅 Запрос {current_request}/{requests_needed}: {days_for_this_request} дней")
            
            # Получаем данные с CoinGecko
            response = self._make_api_request('market_chart', {
                'coin_id': 'bitcoin',
                'days': days_for_this_request
            })
            
            if response and 'prices' in response:
                # Обрабатываем данные
                daily_data = self._process_market_chart_data(response, progress.start_date)
                
                if daily_data:
                    # Сохраняем в БД
                    saved_count = db_manager.save_daily_data('bitcoin', daily_data)
                    total_collected += saved_count
                    
                    # Обновляем прогресс
                    progress.collected_days += len(daily_data)
                    self._save_progress()
                    
                    logger.info(f"✅ Сохранено {saved_count} записей (всего: {total_collected})")
                else:
                    logger.warning(f"⚠️ Нет данных для запроса {current_request}")
                    progress.errors.append(f"Нет данных для запроса {current_request}")
            else:
                error_msg = f"Ошибка получения данных для запроса {current_request}"
                logger.error(error_msg)
                progress.errors.append(error_msg)
                progress.last_error = error_msg
            
            # Пауза между запросами
            time.sleep(2)
        
        # Проверяем завершение
        if progress.collected_days >= progress.total_days * 0.95:  # 95% считаем завершенным
            progress.status = 'completed'
            progress.collection_end = datetime.now()
            self._save_progress()
            
            logger.info(f"✅ Сбор Bitcoin завершен! Собрано {total_collected} записей")
            
            # Сохраняем статистику
            collection_time = (progress.collection_end - progress.collection_start).total_seconds()
            stats = {
                'collection_date': datetime.now().date().isoformat(),
                'records_added': total_collected,
                'records_updated': 0,
                'errors_count': len(progress.errors),
                'collection_time_seconds': collection_time,
                'status': 'completed'
            }
            db_manager.save_collection_stats('bitcoin', stats)
            
            return True
        else:
            progress.status = 'error'
            progress.last_error = f"Собрано только {progress.collected_days}/{progress.total_days} дней"
            self._save_progress()
            
            logger.error(f"❌ Сбор Bitcoin не завершен: {progress.last_error}")
            return False
    
    def collect_ethereum_data(self) -> bool:
        """Собирает исторические данные для Ethereum"""
        
        if 'ethereum' not in self.progress:
            self.start_ethereum_collection()
        
        progress = self.progress['ethereum']
        
        if progress.status == 'completed':
            logger.info("Ethereum данные уже собраны")
            return True
        
        logger.info("🚀 Начинаем сбор исторических данных Ethereum...")
        
        # Инициализируем БД менеджер
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from database_manager import DatabaseManager
        db_manager = DatabaseManager()
        
        # Получаем метаданные Ethereum
        logger.info("📋 Получение метаданных Ethereum...")
        coin_info = self._make_api_request('coin_info', {'coin_id': 'ethereum'})
        
        if coin_info:
            metadata = {
                'name': coin_info.get('name', 'Ethereum'),
                'symbol': coin_info.get('symbol', 'ETH').upper(),
                'launch_date': '2015-07-30',  # Дата создания Ethereum
                'max_supply': coin_info.get('market_data', {}).get('max_supply'),
                'current_supply': coin_info.get('market_data', {}).get('circulating_supply'),
                'algorithm': 'Ethash (PoW) -> PoS',
                'consensus': 'Proof of Stake (с 2022)',
                'description': coin_info.get('description', {}).get('en', '')[:500],
                'website': coin_info.get('links', {}).get('homepage', [None])[0]
            }
            
            db_manager.save_coin_metadata('ethereum', metadata)
            logger.info("✅ Метаданные Ethereum сохранены")
        
        # Собираем исторические данные
        logger.info("📊 Сбор исторических данных Ethereum...")
        
        # Получаем данные за весь период (с 2017 года)
        days_to_collect = (progress.end_date - progress.start_date).days
        
        # CoinGecko API возвращает данные за последние N дней
        # Поэтому запрашиваем максимальное количество дней (максимум 365 дней за раз)
        max_days_per_request = 365
        
        # Вычисляем сколько запросов нужно сделать
        total_days_needed = days_to_collect
        requests_needed = (total_days_needed + max_days_per_request - 1) // max_days_per_request
        
        logger.info(f"📅 Нужно собрать {total_days_needed} дней за {requests_needed} запросов")
        
        total_collected = 0
        current_request = 0
        
        while current_request < requests_needed:
            current_request += 1
            days_for_this_request = min(max_days_per_request, total_days_needed - total_collected)
            
            logger.info(f"📅 Запрос {current_request}/{requests_needed}: {days_for_this_request} дней")
            
            # Получаем данные с CoinGecko
            response = self._make_api_request('market_chart', {
                'coin_id': 'ethereum',
                'days': days_for_this_request
            })
            
            if response and 'prices' in response:
                # Обрабатываем данные
                daily_data = self._process_market_chart_data(response, progress.start_date)
                
                if daily_data:
                    # Сохраняем в БД
                    saved_count = db_manager.save_daily_data('ethereum', daily_data)
                    total_collected += saved_count
                    
                    # Обновляем прогресс
                    progress.collected_days += len(daily_data)
                    self._save_progress()
                    
                    logger.info(f"✅ Сохранено {saved_count} записей (всего: {total_collected})")
                else:
                    logger.warning(f"⚠️ Нет данных для запроса {current_request}")
                    progress.errors.append(f"Нет данных для запроса {current_request}")
            else:
                error_msg = f"Ошибка получения данных для запроса {current_request}"
                logger.error(error_msg)
                progress.errors.append(error_msg)
                progress.last_error = error_msg
            
            # Пауза между запросами
            time.sleep(2)
        
        # Проверяем завершение
        if progress.collected_days >= progress.total_days * 0.95:  # 95% считаем завершенным
            progress.status = 'completed'
            progress.collection_end = datetime.now()
            self._save_progress()
            
            logger.info(f"✅ Сбор Ethereum завершен! Собрано {total_collected} записей")
            
            # Сохраняем статистику
            collection_time = (progress.collection_end - progress.collection_start).total_seconds()
            stats = {
                'collection_date': datetime.now().date().isoformat(),
                'records_added': total_collected,
                'records_updated': 0,
                'errors_count': len(progress.errors),
                'collection_time_seconds': collection_time,
                'status': 'completed'
            }
            db_manager.save_collection_stats('ethereum', stats)
            
            return True
        else:
            progress.status = 'error'
            progress.last_error = f"Собрано только {progress.collected_days}/{progress.total_days} дней"
            self._save_progress()
            
            logger.error(f"❌ Сбор Ethereum не завершен: {progress.last_error}")
            return False
    
    def _process_market_chart_data(self, response: Dict[str, Any], start_date: datetime) -> List[Dict[str, Any]]:
        """Обрабатывает данные из CoinGecko market_chart API"""
        
        daily_data = []
        
        prices = response.get('prices', [])
        market_caps = response.get('market_caps', [])
        volumes = response.get('total_volumes', [])
        
        for i in range(len(prices)):
            try:
                timestamp = prices[i][0] / 1000  # Конвертируем из миллисекунд
                record_date = datetime.fromtimestamp(timestamp).date()
                
                # Пропускаем записи до нашей начальной даты
                if record_date < start_date.date():
                    continue
                
                price = prices[i][1]
                
                # Получаем market cap и volume
                market_cap = None
                volume = None
                
                if i < len(market_caps):
                    market_cap = market_caps[i][1]
                
                if i < len(volumes):
                    volume = volumes[i][1]
                
                # Вычисляем изменение цены (если есть предыдущая запись)
                price_change_24h = None
                if i > 0 and len(daily_data) > 0:
                    prev_price = daily_data[-1]['close']
                    if prev_price and prev_price > 0:
                        price_change_24h = ((price - prev_price) / prev_price) * 100
                
                # Вычисляем изменение объема
                volume_change_24h = None
                if i > 0 and len(daily_data) > 0:
                    prev_volume = daily_data[-1]['volume']
                    if prev_volume and prev_volume > 0 and volume:
                        volume_change_24h = ((volume - prev_volume) / prev_volume) * 100
                
                # Создаем запись
                record = {
                    'date': record_date.isoformat(),
                    'open': price,  # CoinGecko не предоставляет OHLC, используем close
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume,
                    'market_cap': market_cap,
                    'circulating_supply': None,  # Будет добавлено позже
                    'total_supply': None,
                    'fdv': None,
                    'price_change_24h': price_change_24h,
                    'volume_change_24h': volume_change_24h
                }
                
                daily_data.append(record)
                
            except Exception as e:
                logger.error(f"Ошибка обработки записи {i}: {e}")
                continue
        
        return daily_data

 