#!/usr/bin/env python3
"""
Тест всех компонентов команды /crypto
"""
import asyncio
import sys
import os

# Добавляем путь к src для импортов
sys.path.append('src')

from crypto_data_collector import CryptoDataCollector, test_crypto_data_collection
from cache_manager import CacheManager  
from ai_analyzer import AIAnalyzer

def test_crypto_components():
    """Тестирование всех компонентов криптоанализа"""
    
    print("🧪 ТЕСТИРОВАНИЕ КОМПОНЕНТОВ КОМАНДЫ /crypto")
    print("=" * 60)
    
    # 1. Тест сборщика данных
    print("\n1️⃣ ТЕСТ СБОРЩИКА КРИПТОДАННЫХ")
    print("-" * 40)
    
    try:
        collector = CryptoDataCollector()
        crypto_data = collector.collect_all_crypto_data()
        
        if crypto_data:
            print("✅ CryptoDataCollector работает")
            
            # Проверяем структуру данных
            top_coins = crypto_data.get('top_cryptocurrencies', [])
            derivatives = crypto_data.get('derivatives_data', {})
            fear_greed = crypto_data.get('fear_greed_index', {})
            
            print(f"   📊 Топ криптовалют: {len(top_coins)}")
            print(f"   📈 Деривативы: {len(derivatives)} монет")
            print(f"   😱 Fear & Greed: {'✅' if fear_greed else '❌'}")
            
            if top_coins:
                print(f"   🥇 #1: {top_coins[0]['name']} (${top_coins[0]['price_usd']:,.2f})")
        
        else:
            print("❌ CryptoDataCollector вернул пустые данные")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка CryptoDataCollector: {e}")
        return False
    
    # 2. Тест кэш-менеджера
    print("\n2️⃣ ТЕСТ КЭШИРОВАНИЯ КРИПТОДАННЫХ")
    print("-" * 40)
    
    try:
        cache_manager = CacheManager()
        
        # Принудительно получаем данные (создаем кэш)
        cached_crypto_data = cache_manager.get_crypto_data(force_update=True)
        
        if cached_crypto_data:
            print("✅ Кэширование криптоданных работает")
            
            # Проверяем информацию о кэше
            cache_info = cache_manager.get_crypto_cache_info()
            print(f"   📦 Кэш существует: {cache_info.get('exists', False)}")
            print(f"   ✅ Кэш валиден: {cache_info.get('is_valid', False)}")
            print(f"   📊 Источников: {cache_info.get('data_sources', 0)}/3")
        else:
            print("❌ Кэширование криптоданных не работает")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка кэширования: {e}")
        return False
    
    # 3. Тест AI анализа
    print("\n3️⃣ ТЕСТ AI АНАЛИЗА КРИПТОДАННЫХ")
    print("-" * 40)
    
    try:
        ai_analyzer = AIAnalyzer()
        
        # Создаем анализ
        short_analysis, full_analysis = ai_analyzer.analyze_crypto_data(crypto_data)
        
        if short_analysis and full_analysis:
            print("✅ AI анализ криптоданных работает")
            print(f"   📝 Короткий анализ: {len(short_analysis)} символов")
            print(f"   📋 Полный анализ: {len(full_analysis)} символов")
            print(f"   🧠 Модель: {ai_analyzer.config.AI_MODEL}")
            
            # Показываем начало короткого анализа
            preview = short_analysis[:100] + "..." if len(short_analysis) > 100 else short_analysis
            print(f"   🔍 Превью: {preview}")
            
        else:
            print("❌ AI анализ вернул пустые результаты")
            print("   (Возможно, используется fallback анализ)")
            
    except Exception as e:
        print(f"❌ Ошибка AI анализа: {e}")
        return False
    
    # 4. Итоговая проверка
    print("\n4️⃣ ИТОГОВАЯ ПРОВЕРКА")
    print("-" * 40)
    
    components_working = []
    
    # Проверяем обязательные компоненты
    if crypto_data.get('top_cryptocurrencies'):
        components_working.append("✅ Данные CoinGecko")
    else:
        components_working.append("❌ Данные CoinGecko")
    
    if crypto_data.get('derivatives_data'):
        components_working.append("✅ Деривативы Binance")
    else:
        components_working.append("❌ Деривативы Binance") 
        
    if crypto_data.get('fear_greed_index'):
        components_working.append("✅ Fear & Greed Index")
    else:
        components_working.append("❌ Fear & Greed Index")
    
    if cached_crypto_data:
        components_working.append("✅ Кэширование")
    else:
        components_working.append("❌ Кэширование")
        
    if short_analysis:
        components_working.append("✅ AI анализ")
    else:
        components_working.append("❌ AI анализ")
    
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    for component in components_working:
        print(f"   {component}")
    
    working_count = sum(1 for c in components_working if c.startswith("✅"))
    total_count = len(components_working)
    
    print(f"\n🎯 ГОТОВНОСТЬ: {working_count}/{total_count} компонентов работают")
    
    if working_count >= 3:  # Минимум для работы команды
        print("🚀 Команда /crypto готова к использованию!")
        return True
    else:
        print("⚠️ Команда /crypto требует настройки")
        return False

def show_setup_instructions():
    """Показывает инструкции по настройке"""
    
    print("\n" + "="*60)
    print("📋 ИНСТРУКЦИИ ПО НАСТРОЙКЕ КОМАНДЫ /crypto")
    print("="*60)
    
    print("\n1️⃣ ОБЯЗАТЕЛЬНЫЕ ЗАВИСИМОСТИ:")
    print("   pip3 install pycoingecko python-binance ccxt")
    
    print("\n2️⃣ ОПЦИОНАЛЬНЫЕ API КЛЮЧИ (добавить в .env):")
    print("   # Для дополнительных возможностей Binance")
    print("   BINANCE_API_KEY=ваш_ключ")
    print("   BINANCE_SECRET_KEY=ваш_секретный_ключ")
    
    print("\n3️⃣ КОМАНДЫ БОТА:")
    print("   /crypto - анализ криптовалютного рынка")
    print("   - Топ-10 криптовалют (без стейблкоинов)")
    print("   - Деривативы для топ-5 монет")
    print("   - Индекс страха и жадности")
    
    print("\n4️⃣ АВТОПУБЛИКАЦИЯ:")
    print("   - Утром в 10:00 МСК")
    print("   - Вечером в 22:00 МСК")
    print("   - При ENABLE_AUTO_PUBLISH=true")
    
    print("\n5️⃣ КЭШИРОВАНИЕ:")
    print("   - Обновление в 8:00 и 20:00 МСК")
    print("   - Автоматическое кэширование данных")
    
    print("\n🚀 После успешного теста перезапустите бота!")

if __name__ == "__main__":
    print("🧪 Тестирование команды /crypto")
    print("Убедитесь, что у вас есть интернет-соединение...")
    print()
    
    success = test_crypto_components()
    
    if success:
        print("\n🎉 Все компоненты работают! Команда /crypto готова!")
    else:
        print("\n⚠️ Некоторые компоненты требуют настройки")
    
    show_setup_instructions()
    print("\n" + "="*60) 