#!/usr/bin/env python3
"""
Быстрая проверка API ключей
Запуск: python quick_test.py
"""
import os
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

def check_env_file():
    """Проверка наличия и содержимого .env файла"""
    
    print("🔍 ПРОВЕРКА ФАЙЛА .env")
    print("=" * 40)
    
    # Проверяем файл
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("💡 Создайте файл .env в корне проекта")
        return False
    
    print("✅ Файл .env найден")
    
    # Проверяем переменные
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    openai_key = os.getenv('OPENAI_API_KEY', '')
    channel_id = os.getenv('TELEGRAM_CHANNEL_ID', '')
    
    print(f"\n📊 СОДЕРЖИМОЕ:")
    print(f"🤖 Bot Token: {'✅ Заполнен' if bot_token and bot_token != 'ваш_токен_telegram_бота' else '❌ Не заполнен'}")
    print(f"🧠 OpenAI Key: {'✅ Заполнен' if openai_key and openai_key != 'ваш_ключ_openai' else '❌ Не заполнен'}")
    print(f"📺 Channel ID: {'✅ Заполнен' if channel_id and channel_id != '@ваш_канал' else '⚠️ Не заполнен (опционально)'}")
    
    # Проверяем формат
    errors = []
    
    if not bot_token or bot_token == 'ваш_токен_telegram_бота':
        errors.append("TELEGRAM_BOT_TOKEN не заполнен")
    elif not bot_token.count(':') == 1:
        errors.append("TELEGRAM_BOT_TOKEN неправильный формат (должен содержать ':')")
    
    if not openai_key or openai_key == 'ваш_ключ_openai':
        errors.append("OPENAI_API_KEY не заполнен")
    elif not openai_key.startswith('sk-'):
        errors.append("OPENAI_API_KEY должен начинаться с 'sk-'")
    
    if errors:
        print(f"\n❌ ОШИБКИ:")
        for error in errors:
            print(f"   • {error}")
        print(f"\n💡 ИСПРАВЬТЕ ОШИБКИ И ЗАПУСТИТЕ СНОВА")
        return False
    else:
        print(f"\n🎉 ВСЁ ГОТОВО!")
        print(f"✅ Ключи заполнены правильно")
        print(f"🚀 Можете запускать: python main.py")
        return True

def test_imports():
    """Проверка что все библиотеки установлены"""
    
    print(f"\n🔍 ПРОВЕРКА БИБЛИОТЕК")
    print("=" * 40)
    
    missing = []
    
    try:
        import telegram
        print("✅ python-telegram-bot")
    except ImportError:
        missing.append("python-telegram-bot")
        print("❌ python-telegram-bot")
    
    try:
        import openai
        print("✅ openai")
    except ImportError:
        missing.append("openai")
        print("❌ openai")
        
    try:
        import yfinance
        print("✅ yfinance")
    except ImportError:
        missing.append("yfinance")
        print("❌ yfinance")
    
    try:
        import requests
        print("✅ requests")
    except ImportError:
        missing.append("requests")
        print("❌ requests")
    
    if missing:
        print(f"\n❌ ОТСУТСТВУЮТ БИБЛИОТЕКИ:")
        for lib in missing:
            print(f"   • {lib}")
        print(f"\n💡 УСТАНОВИТЕ: pip install {' '.join(missing)}")
        return False
    else:
        print(f"\n✅ Все библиотеки установлены")
        return True

def main():
    """Основная функция"""
    
    print("🧪 БЫСТРАЯ ПРОВЕРКА СИСТЕМЫ")
    print("=" * 50)
    
    # Проверяем библиотеки
    libs_ok = test_imports()
    
    # Проверяем конфигурацию
    config_ok = check_env_file()
    
    print("\n📋 ИТОГИ:")
    print("=" * 50)
    
    if libs_ok and config_ok:
        print("🎉 ВСЁ ГОТОВО К ЗАПУСКУ!")
        print("🚀 Выполните: python main.py")
    elif config_ok:
        print("⚠️ Установите недостающие библиотеки")
        print("📦 pip install -r requirements.txt")
    elif libs_ok:
        print("⚠️ Заполните файл .env правильными ключами")
    else:
        print("❌ Нужно установить библиотеки И заполнить .env")
        print("1️⃣ pip install -r requirements.txt")
        print("2️⃣ Заполните .env файл")

if __name__ == "__main__":
    main() 