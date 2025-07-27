#!/usr/bin/env python3
"""
Тестирование системы Crypto Finance Bot
Проверка всех компонентов без запуска Telegram бота
"""
import sys
import os
from datetime import datetime

# Добавляем src в path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_collectors import DataCollector, test_data_collection
from src.ai_analyzer import AIAnalyzer, test_ai_analysis
from config import Config

def test_configuration():
    """Тест конфигурации"""
    print("🔧 ТЕСТ КОНФИГУРАЦИИ")
    print("-" * 30)
    
    try:
        config = Config()
        
        # Проверяем основные параметры
        print(f"AI Provider: {config.AI_PROVIDER}")
        print(f"AI Model: {config.AI_MODEL}")
        print(f"Cache Expire: {config.CACHE_EXPIRE_MINUTES} мин")
        print(f"Data Update Interval: {config.DATA_UPDATE_INTERVAL} мин")
        
        # Проверяем символы Yahoo Finance
        print(f"Yahoo Finance символов: {len(config.YAHOO_SYMBOLS)}")
        for name, symbol in list(config.YAHOO_SYMBOLS.items())[:3]:
            print(f"  {name}: {symbol}")
        print("  ...")
        
        print("✅ Конфигурация загружена успешно")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False

def test_data_sources():
    """Тест источников данных"""
    print("\n📊 ТЕСТ ИСТОЧНИКОВ ДАННЫХ")
    print("-" * 30)
    
    try:
        collector = DataCollector()
        
        # Тест Yahoo Finance
        print("🔍 Тестирую Yahoo Finance...")
        yahoo_data = collector.get_yahoo_finance_data()
        print(f"  Получено инструментов: {len(yahoo_data)}")
        
        # Тест ФРС
        print("🔍 Тестирую данные ФРС...")
        fed_data = collector.get_fed_interest_rate()
        print(f"  Текущая ставка: {fed_data.get('current_rate', 'N/A')}%")
        
        # Тест Fear & Greed
        print("🔍 Тестирую Fear & Greed Index...")
        fear_greed = collector.get_fear_greed_index()
        print(f"  Индекс: {fear_greed.get('value', 'N/A')} ({fear_greed.get('interpretation', 'N/A')})")
        
        # Полный сбор
        print("🔍 Полный сбор данных...")
        all_data = collector.collect_all_metrics()
        success_rate = all_data.get('data_quality', {}).get('sources_available', 0)
        print(f"  Успешно получено: {success_rate}/3 источников")
        
        if success_rate >= 2:
            print("✅ Источники данных работают корректно")
            return True, all_data
        else:
            print("⚠️ Некоторые источники недоступны")
            return False, all_data
            
    except Exception as e:
        print(f"❌ Ошибка тестирования источников: {e}")
        return False, None

def test_ai_integration():
    """Тест AI интеграции"""
    print("\n🤖 ТЕСТ AI ИНТЕГРАЦИИ")
    print("-" * 30)
    
    try:
        # Примерные данные для тестирования
        test_data = {
            'yahoo_finance': {
                'sp500': {'current_price': 4500, 'change_percent': 1.2},
                'bitcoin': {'current_price': 45000, 'change_percent': -2.1},
                'ethereum': {'current_price': 3200, 'change_percent': -1.8},
                'vix': {'current_price': 15.5},
                'dxy': {'current_price': 103.2, 'change_percent': 0.3}
            },
            'fed_rates': {
                'current_rate': 5.25,
                'ten_year_yield': 4.8,
                'yield_curve_spread': -0.45
            },
            'fear_greed_index': {
                'value': 35,
                'interpretation': 'Страх'
            }
        }
        
        analyzer = AIAnalyzer()
        
        print("🔍 Создание промпта...")
        prompt = analyzer.create_analysis_prompt(test_data)
        print(f"  Длина промпта: {len(prompt)} символов")
        
        print("🔍 Выполнение AI анализа...")
        short_analysis, full_analysis = analyzer.analyze_market_data(test_data)
        
        print(f"  Краткий анализ: {len(short_analysis)} символов")
        print(f"  Полный анализ: {len(full_analysis)} символов")
        
        print("✅ AI анализ выполнен успешно")
        return True, short_analysis, full_analysis
        
    except Exception as e:
        print(f"❌ Ошибка AI анализа: {e}")
        print("🔧 Попробуйте проверить API ключи в .env файле")
        return False, None, None

def test_system_integration():
    """Интеграционный тест всей системы"""
    print("\n🎯 ИНТЕГРАЦИОННЫЙ ТЕСТ")
    print("-" * 30)
    
    try:
        print("🔍 Запуск полного цикла...")
        
        # Собираем реальные данные
        collector = DataCollector()
        market_data = collector.collect_all_metrics()
        
        # Анализируем с помощью AI
        analyzer = AIAnalyzer()
        short_analysis, full_analysis = analyzer.analyze_market_data(market_data)
        
        print("📊 РЕЗУЛЬТАТ ИНТЕГРАЦИОННОГО ТЕСТА:")
        print(f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}")
        print(f"📈 Источников данных: {market_data.get('data_quality', {}).get('sources_available', 0)}/3")
        print(f"📝 Краткий анализ: {len(short_analysis)} символов")
        print(f"📄 Полный анализ: {len(full_analysis)} символов")
        
        print("\n🔍 ПРИМЕР КРАТКОГО АНАЛИЗА:")
        print("-" * 30)
        print(short_analysis)
        
        print("\n✅ Интеграционный тест пройден успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграционного теста: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ CRYPTO FINANCE BOT")
    print("=" * 50)
    print(f"Время запуска: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    
    tests_passed = 0
    total_tests = 4
    
    # Тест 1: Конфигурация
    if test_configuration():
        tests_passed += 1
    
    # Тест 2: Источники данных
    data_success, market_data = test_data_sources()
    if data_success:
        tests_passed += 1
    
    # Тест 3: AI интеграция
    ai_success, short, full = test_ai_integration()
    if ai_success:
        tests_passed += 1
    
    # Тест 4: Интеграционный тест
    if test_system_integration():
        tests_passed += 1
    
    # Итоги
    print("\n📋 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 50)
    print(f"Пройдено тестов: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к запуску")
        print("\n🚀 Для запуска бота выполните:")
        print("   python main.py")
    elif tests_passed >= 2:
        print("⚠️ Система частично готова. Некоторые компоненты могут не работать")
    else:
        print("❌ Критические ошибки. Проверьте конфигурацию")
        print("\n💡 Инструкции:")
        print("1. Создайте файл .env")
        print("2. Добавьте TELEGRAM_BOT_TOKEN и OPENAI_API_KEY")
        print("3. Проверьте интернет-соединение")

if __name__ == "__main__":
    main() 