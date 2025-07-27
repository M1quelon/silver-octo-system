"""
Сборщик данных для криптовалют
Получает данные с CoinGecko API и Binance API
"""
import os
import sys
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from binance.client import Client
from pycoingecko import CoinGeckoAPI

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

class CryptoDataCollector:
    """Сборщик данных для криптовалют"""
    
    def __init__(self):
        """Инициализация API клиентов"""
        
        # CoinGecko API (бесплатный)
        self.cg = CoinGeckoAPI()
        
        # Binance API (для деривативов, можно без ключей для публичных данных)
        try:
            # Если есть ключи Binance - используем их, если нет - публичные данные
            binance_api_key = os.getenv('BINANCE_API_KEY', '')
            binance_secret = os.getenv('BINANCE_SECRET_KEY', '')
            
            if binance_api_key and binance_secret:
                self.binance_client = Client(binance_api_key, binance_secret)
                logger.info("Binance API инициализирован с ключами")
            else:
                self.binance_client = Client()  # Публичный доступ
                logger.info("Binance API инициализирован без ключей (публичные данные)")
                
        except Exception as e:
            logger.warning(f"Ошибка инициализации Binance API: {e}")
            self.binance_client = None
        
        # Список стейблкоинов для исключения
        self.excluded_stables = ['usdt', 'usdc', 'busd', 'dai', 'tusd', 'usdp', 'frax']
    
    def get_top_cryptocurrencies(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Получает топ криптовалют с CoinGecko (исключая стейблкоины)
        
        Args:
            limit: Сколько монет запросить (берем с запасом, чтобы после фильтрации получить топ-10)
        
        Returns:
            Список с данными топ-10 криптовалют
        """
        try:
            logger.info("Получение данных топ криптовалют с CoinGecko...")
            
            # Получаем топ криптовалюты
            data = self.cg.get_coins_markets(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=limit,
                page=1,
                sparkline=False,
                price_change_percentage='1h,24h,7d'
            )
            
            if not data:
                logger.error("CoinGecko вернул пустые данные")
                return []
            
            # Фильтруем стейблкоины и берем топ-10
            filtered_coins = []
            for coin in data:
                if coin['id'].lower() not in self.excluded_stables and len(filtered_coins) < 10:
                    
                    coin_data = {
                        'id': coin['id'],
                        'symbol': coin['symbol'].upper(),
                        'name': coin['name'],
                        'rank': coin['market_cap_rank'],
                        'price_usd': coin['current_price'],
                        'market_cap': coin['market_cap'],
                        'volume_24h': coin['total_volume'],
                        'price_change_1h': coin.get('price_change_percentage_1h_in_currency'),
                        'price_change_24h': coin.get('price_change_percentage_24h_in_currency'),
                        'price_change_7d': coin.get('price_change_percentage_7d_in_currency'),
                        'circulating_supply': coin.get('circulating_supply'),
                        'total_supply': coin.get('total_supply'),
                        'ath': coin.get('ath'),
                        'atl': coin.get('atl'),
                        'ath_change_percentage': coin.get('ath_change_percentage'),
                        'last_updated': coin.get('last_updated')
                    }
                    
                    filtered_coins.append(coin_data)
            
            logger.info(f"Получено {len(filtered_coins)} криптовалют (исключены стейблкоины)")
            return filtered_coins
            
        except Exception as e:
            logger.error(f"Ошибка получения данных с CoinGecko: {e}")
            return []
    
    def get_derivatives_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Получает данные по деривативам с Binance
        
        Args:
            symbols: Список символов монет для получения данных по деривативам
        
        Returns:
            Словарь с данными по деривативам
        """
        
        if not self.binance_client:
            logger.warning("Binance API недоступен для получения данных по деривативам")
            return {}
        
        try:
            logger.info("Получение данных по деривативам с Binance...")
            
            derivatives_data = {}
            
            for symbol in symbols[:5]:  # Берем только топ-5
                try:
                    binance_symbol = f"{symbol.upper()}USDT"
                    
                    # Пробуем разные методы Binance API (совместимость с разными версиями)
                    try:
                        # Новая версия API
                        futures_stats = self.binance_client.futures_ticker(symbol=binance_symbol)
                    except AttributeError:
                        try:
                            # Старая версия API
                            futures_stats = self.binance_client.futures_24hr_ticker(symbol=binance_symbol)
                        except:
                            # Альтернативный метод
                            futures_stats = self.binance_client.get_ticker(symbol=binance_symbol)
                    
                    # Получаем открытый интерес (безопасно)
                    try:
                        open_interest = self.binance_client.futures_open_interest(symbol=binance_symbol)
                        oi_value = float(open_interest.get('openInterest', 0))
                    except:
                        oi_value = 0
                    
                    # Получаем фандинг рейт (безопасно)
                    try:
                        funding_rate = self.binance_client.futures_funding_rate(symbol=binance_symbol, limit=1)
                        funding_rate_value = float(funding_rate[0]['fundingRate']) if funding_rate else 0
                        funding_time = funding_rate[0]['fundingTime'] if funding_rate else None
                    except:
                        funding_rate_value = 0
                        funding_time = None
                    
                    # Парсим данные фьючерсов
                    last_price = float(futures_stats.get('lastPrice', futures_stats.get('price', 0)))
                    volume = float(futures_stats.get('volume', futures_stats.get('quoteVolume', 0)))
                    price_change = float(futures_stats.get('priceChangePercent', futures_stats.get('priceChangePercent', 0)))
                    
                    derivatives_data[symbol] = {
                        'futures_price': last_price,
                        'futures_volume_24h': volume,
                        'price_change_24h': price_change,
                        'open_interest_value': oi_value,
                        'open_interest_usd': oi_value * last_price,
                        'funding_rate': funding_rate_value,
                        'funding_countdown': funding_time,
                        'long_short_ratio': self._get_long_short_ratio(binance_symbol)
                    }
                    
                    logger.info(f"Получены деривативы для {symbol}: цена=${last_price:.2f}, funding={funding_rate_value:.4f}%")
                    
                except Exception as e:
                    logger.warning(f"Ошибка получения деривативов для {symbol}: {e}")
                    continue
            
            logger.info(f"Получены данные по деривативам для {len(derivatives_data)} монет")
            return derivatives_data
            
        except Exception as e:
            logger.error(f"Общая ошибка получения данных по деривативам: {e}")
            return {}
    
    def _get_long_short_ratio(self, symbol: str) -> Optional[float]:
        """Получает соотношение лонг/шорт позиций"""
        try:
            # Данные по соотношению лонг/шорт (топ трейдеры)
            ratio_data = self.binance_client.futures_top_longshort_account_ratio(
                symbol=symbol,
                period='1d',
                limit=1
            )
            
            if ratio_data:
                return float(ratio_data[0]['longShortRatio'])
                
        except Exception as e:
            logger.debug(f"Не удалось получить long/short ratio для {symbol}: {e}")
            
        return None
    
    def get_market_fear_greed_crypto(self) -> Dict[str, Any]:
        """Получает индекс страха и жадности для крипторынка"""
        try:
            logger.info("Получение индекса страха и жадности...")
            
            response = requests.get(
                "https://api.alternative.me/fng/",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data and 'data' in data and len(data['data']) > 0:
                fng_data = data['data'][0]
                
                return {
                    'value': int(fng_data['value']),
                    'classification': fng_data['value_classification'],
                    'timestamp': fng_data['timestamp'],
                    'time_until_update': fng_data.get('time_until_update')
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка получения индекса страха и жадности: {e}")
            return {}
    
    def collect_all_crypto_data(self) -> Dict[str, Any]:
        """
        Собирает все криптоданные в один объект
        
        Returns:
            Полный набор данных по криптовалютам
        """
        logger.info("Начало сбора всех криптоданных...")
        
        # Получаем топ криптовалюты
        top_coins = self.get_top_cryptocurrencies()
        
        # Извлекаем символы для получения деривативов
        top_symbols = [coin['symbol'] for coin in top_coins[:5]]
        
        # Получаем данные по деривативам
        derivatives = self.get_derivatives_data(top_symbols)
        
        # Получаем индекс страха и жадности
        fear_greed = self.get_market_fear_greed_crypto()
        
        crypto_data = {
            'top_cryptocurrencies': top_coins,
            'derivatives_data': derivatives,
            'fear_greed_index': fear_greed,
            'last_updated': datetime.now().isoformat(),
            'data_sources': {
                'coingecko': len(top_coins) > 0,
                'binance_derivatives': len(derivatives) > 0,
                'fear_greed': len(fear_greed) > 0
            }
        }
        
        logger.info("Сбор криптоданных завершен")
        return crypto_data

# Функция тестирования
def test_crypto_data_collection():
    """Тестирование сбора криптоданных"""
    print("🧪 Тестирование сбора криптоданных...")
    
    collector = CryptoDataCollector()
    
    # Тест получения топ криптовалют
    print("\n📊 Тестирование CoinGecko API...")
    coins = collector.get_top_cryptocurrencies()
    if coins:
        print(f"✅ Получено {len(coins)} криптовалют")
        for i, coin in enumerate(coins[:3], 1):
            print(f"  {i}. {coin['name']} ({coin['symbol']}) - ${coin['price_usd']}")
    else:
        print("❌ Ошибка получения данных с CoinGecko")
    
    # Тест получения деривативов
    print("\n📈 Тестирование Binance API...")
    if coins:
        top_symbols = [coin['symbol'] for coin in coins[:3]]
        derivatives = collector.get_derivatives_data(top_symbols)
        if derivatives:
            print(f"✅ Получены данные по деривативам для {len(derivatives)} монет")
            for symbol, data in derivatives.items():
                print(f"  {symbol}: Funding Rate: {data['funding_rate']:.4f}%")
        else:
            print("❌ Ошибка получения данных по деривативам")
    
    # Тест индекса страха и жадности
    print("\n😱 Тестирование Fear & Greed Index...")
    fear_greed = collector.get_market_fear_greed_crypto()
    if fear_greed:
        print(f"✅ Индекс страха и жадности: {fear_greed['value']}/100 ({fear_greed['classification']})")
    else:
        print("❌ Ошибка получения индекса страха и жадности")
    
    # Полный тест
    print("\n🔄 Полный тест сбора данных...")
    all_data = collector.collect_all_crypto_data()
    sources = all_data['data_sources']
    working_sources = sum(sources.values())
    print(f"✅ Работает {working_sources}/3 источников данных")
    
    return all_data

if __name__ == "__main__":
    test_crypto_data_collection() 