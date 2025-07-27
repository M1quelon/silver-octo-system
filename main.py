#!/usr/bin/env python3
"""
Crypto Finance Bot - Точка входа
Запуск: python main.py
"""
import os
import sys
import logging
from pathlib import Path

# Добавляем src в path для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.telegram_bot import FinanceBot
from config import Config

def setup_directories():
    """Создание необходимых директорий"""
    directories = ['logs', 'cache', 'data']
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(exist_ok=True)
            print(f"✓ Создана папка: {directory}")

def check_environment():
    """Проверка переменных окружения"""
    print("🔍 Проверка конфигурации...")
    
    try:
        Config.validate()
        print("✓ Конфигурация корректна")
        return True
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("\n💡 Инструкции по настройке:")
        print("1. Создайте файл .env в корне проекта")
        print("2. Добавьте следующие переменные:")
        print("   TELEGRAM_BOT_TOKEN=ваш_токен_бота")
        print("   OPENAI_API_KEY=ваш_ключ_openai")
        print("\n📖 Подробные инструкции в README.md")
        return False

def main():
    """Главная функция запуска"""
    
    print("🚀 Запуск Crypto Finance Bot")
    print("=" * 50)
    
    # Создаём необходимые директории
    setup_directories()
    
    # Проверяем конфигурацию
    if not check_environment():
        return 1
    
    try:
        # Настройка логирования
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        print("✓ Логирование настроено")
        
        # Запускаем бота
        print("🤖 Запуск Telegram бота...")
        
        bot = FinanceBot()
        bot.run()
        
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
        return 0
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logging.exception("Критическая ошибка при запуске бота")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 