"""
Конфигурация проекта Crypto Finance Bot
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    """Основная конфигурация проекта"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Telegram Channel для публикации анализов
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')  # Например: @your_channel или -1001234567890
    
    # AI API (OpenAI или Anthropic)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    
    # Источники данных
    DATA_UPDATE_INTERVAL = 30  # минут
    
    # URLs для API
    FEAR_GREED_URL = "https://api.alternative.me/fng/"
    FED_INTEREST_RATE_SYMBOL = "^IRX"  # 3-месячные treasury bills
    
    # Yahoo Finance символы (традиционные рынки)
    YAHOO_SYMBOLS = {
        'sp500': '^GSPC',
        'nasdaq': '^IXIC', 
        'dow': '^DJI',
        'vix': '^VIX',  # Индекс волатильности
        'dxy': 'DX-Y.NYB',  # Индекс доллара
        'gold': 'GC=F',
        'oil': 'CL=F'
    }
    
    # Криптовалюты (отдельная команда /crypto)
    CRYPTO_SYMBOLS = {
        'bitcoin': 'BTC-USD',
        'ethereum': 'ETH-USD',
        'binance': 'BNB-USD',
        'cardano': 'ADA-USD',
        'solana': 'SOL-USD',
        'polkadot': 'DOT-USD',
        'chainlink': 'LINK-USD',
        'litecoin': 'LTC-USD',
        'polygon': 'MATIC-USD',
        'avalanche': 'AVAX-USD'
    }
    
    # Настройки кэша
    CACHE_EXPIRE_MINUTES = int(os.getenv('CACHE_EXPIRE_MINUTES', 30))
    
    # Логирование
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/bot.log'
    
    # Настройки AI
    AI_PROVIDER = 'openai'  # 'openai' или 'anthropic'
    AI_MODEL = 'gpt-4-turbo'  # или 'claude-3-sonnet-20240229'
    
    # Настройки публикации в канал
    ENABLE_AUTO_PUBLISH = os.getenv('ENABLE_AUTO_PUBLISH', 'false').lower() == 'true'
    # Автопубликация происходит ежедневно в 18:00 МСК (зафиксированное время)
    
    @classmethod
    def validate(cls):
        """Проверка наличия обязательных настроек"""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
            
        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY:
            errors.append("Нужен хотя бы один AI API ключ (OpenAI или Anthropic)")
        
        # Канал не обязателен, но рекомендуем
        if not cls.TELEGRAM_CHANNEL_ID:
            print("⚠️ TELEGRAM_CHANNEL_ID не установлен - публикация в канал отключена")
            
        if errors:
            raise ValueError(f"Ошибки конфигурации: {'; '.join(errors)}")
        
        return True 