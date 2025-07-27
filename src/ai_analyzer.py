"""
Модуль для AI анализа финансовых данных
"""
from openai import OpenAI
import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Tuple

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Настройка логирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class AIAnalyzer:
    """Класс для анализа финансовых данных с помощью AI"""
    
    def __init__(self):
        self.config = Config()
        
        # Настройка OpenAI API (новый синтаксис)
        if self.config.AI_PROVIDER == 'openai' and self.config.OPENAI_API_KEY:
            self.client = OpenAI(api_key=self.config.OPENAI_API_KEY)
        else:
            self.client = None
            logger.warning("AI API ключ не настроен")
    
    def create_analysis_prompt(self, market_data: Dict[str, Any]) -> str:
        """
        Создание промпта для анализа рыночных данных
        """
        
        # Извлекаем ключевые данные
        yahoo_data = market_data.get('yahoo_finance', {})
        fed_data = market_data.get('fed_rates', {})
        fear_greed = market_data.get('fear_greed_index', {})
        
        prompt = f"""
Ты опытный финансовый аналитик. Проанализируй данные и дай СТРУКТУРИРОВАННЫЙ анализ для обычных инвесторов.

ДАННЫЕ ДЛЯ АНАЛИЗА:

=== ОСНОВНЫЕ ИНДЕКСЫ ===
S&P 500: {yahoo_data.get('sp500', {}).get('current_price', 'N/A')} (изменение: {yahoo_data.get('sp500', {}).get('change_percent', 'N/A')}%)
NASDAQ: {yahoo_data.get('nasdaq', {}).get('current_price', 'N/A')} (изменение: {yahoo_data.get('nasdaq', {}).get('change_percent', 'N/A')}%)
Dow Jones: {yahoo_data.get('dow', {}).get('current_price', 'N/A')} (изменение: {yahoo_data.get('dow', {}).get('change_percent', 'N/A')}%)
VIX (волатильность): {yahoo_data.get('vix', {}).get('current_price', 'N/A')}
DXY (индекс доллара): {yahoo_data.get('dxy', {}).get('current_price', 'N/A')} ({yahoo_data.get('dxy', {}).get('change_percent', 'N/A')}%)

=== СЫРЬЕВЫЕ ТОВАРЫ ===
Золото: ${yahoo_data.get('gold', {}).get('current_price', 'N/A')} (изменение: {yahoo_data.get('gold', {}).get('change_percent', 'N/A')}%)
Нефть: ${yahoo_data.get('oil', {}).get('current_price', 'N/A')} (изменение: {yahoo_data.get('oil', {}).get('change_percent', 'N/A')}%)

=== ПРОЦЕНТНЫЕ СТАВКИ ФРС ===
3-месячные облигации: {fed_data.get('current_rate', 'N/A')}%
10-летние облигации: {fed_data.get('ten_year_yield', 'N/A')}%
Кривая доходности: {fed_data.get('yield_curve_spread', 'N/A')}%

=== ИНДЕКС СТРАХА И ЖАДНОСТИ ===
Значение: {fear_greed.get('value', 'N/A')}/100
Интерпретация: {fear_greed.get('interpretation', 'N/A')}

🎯 КОНТЕКСТ: Это анализ для КРИПТОВАЛЮТНОГО канала! Фокус на том, как традиционные рынки влияют на криптовалюты.

ЗАДАЧА: Создай ПОНЯТНЫЙ анализ состоящий из:

1. 📊 ОБЩЕЕ СОСТОЯНИЕ РЫНКА (как традиционные рынки влияют на крипто)
2. 🔍 КЛЮЧЕВЫЕ ФАКТОРЫ (что из макроэкономики влияет на Bitcoin и альткоины)
3. 💡 АНАЛИЗ ДАННЫХ (что означают показатели для криптоинвесторов)
4. 🎯 РЕКОМЕНДАЦИИ (стратегия для КРИПТОИНВЕСТИЦИЙ: покупать/продавать/ждать крипто)
5. ⚠️ РИСКИ (предупреждения для криптоинвесторов)

🚨 ВАЖНО: 
- Рекомендации только по КРИПТОВАЛЮТАМ (Bitcoin, Ethereum, альткоины)
- НЕ советуй покупать акции/облигации! 
- Объясни как макроданные влияют на крипторынок
- Используй термины: "биткоин", "альткоины", "DeFi", "крипторынок"

Отвечай на русском языке, используй эмодзи, пиши понятно для обычных людей, но профессионально.
"""
        return prompt
    
    def analyze_market_data(self, market_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Анализ рыночных данных с помощью AI
        Возвращает краткий и полный анализ
        """
        try:
            if not self.client:
                raise Exception("OpenAI клиент не настроен")
                
            prompt = self.create_analysis_prompt(market_data)
            
            # Запрос к OpenAI (новый синтаксис)
            response = self.client.chat.completions.create(
                model=self.config.AI_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты опытный финансовый аналитик, специализирующийся на анализе американских рынков. Даёшь структурированные, понятные анализы с конкретными рекомендациями."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            full_analysis = response.choices[0].message.content.strip()
            
            # Создаем краткую версию (более детальную)
            short_prompt = f"""
На основе этого анализа создай ДЕТАЛЬНУЮ краткую сводку для Telegram (максимум 800 символов):

{full_analysis}

Формат краткой сводки должен включать:
📊 [2-3 предложения о состоянии рынка с конкретными цифрами]
🎯 [Конкретная рекомендация с обоснованием]
⚠️ [Главный риск с объяснением почему]
💡 [Ключевой инсайт или возможность]

Используй больше конкретных данных и цифр. Будь информативен но лаконичен.
"""
            
            short_response = self.client.chat.completions.create(
                model=self.config.AI_MODEL,
                messages=[
                    {"role": "user", "content": short_prompt}
                ],
                max_tokens=250,
                temperature=0.3
            )
            
            short_analysis = short_response.choices[0].message.content.strip()
            
            # Добавляем сырые данные к полному анализу
            full_analysis_with_data = self._add_raw_data_to_analysis(full_analysis, market_data)
            
            logger.info("AI анализ успешно выполнен")
            return short_analysis, full_analysis_with_data
            
        except Exception as e:
            logger.error(f"Ошибка AI анализа: {e}")
            
            # Fallback - простой анализ без AI
            fallback_short, fallback_full = self._create_fallback_analysis(market_data)
            return fallback_short, fallback_full
    
    def _add_raw_data_to_analysis(self, ai_analysis: str, market_data: Dict[str, Any]) -> str:
        """
        Добавляет сырые данные к AI анализу
        """
        yahoo_data = market_data.get('yahoo_finance', {})
        fed_data = market_data.get('fed_rates', {})
        fear_greed = market_data.get('fear_greed_index', {})
        
        raw_data_section = f"""

═══════════════════════════════════════
📊 ДАННЫЕ ИСПОЛЬЗОВАННЫЕ В АНАЛИЗЕ
═══════════════════════════════════════

🏛️ ОСНОВНЫЕ ИНДЕКСЫ США:
• S&P 500: {yahoo_data.get('sp500', {}).get('current_price', 'N/A')} ({yahoo_data.get('sp500', {}).get('change_percent', 'N/A'):+.2f}%)
• NASDAQ: {yahoo_data.get('nasdaq', {}).get('current_price', 'N/A')} ({yahoo_data.get('nasdaq', {}).get('change_percent', 'N/A'):+.2f}%)
• Dow Jones: {yahoo_data.get('dow', {}).get('current_price', 'N/A')} ({yahoo_data.get('dow', {}).get('change_percent', 'N/A'):+.2f}%)

📈 ВОЛАТИЛЬНОСТЬ И ДОЛЛАР:
• VIX (страх рынка): {yahoo_data.get('vix', {}).get('current_price', 'N/A')}
• DXY (индекс доллара): {yahoo_data.get('dxy', {}).get('current_price', 'N/A')} ({yahoo_data.get('dxy', {}).get('change_percent', 'N/A'):+.2f}%)

🥇 СЫРЬЕВЫЕ ТОВАРЫ:
• Золото: ${yahoo_data.get('gold', {}).get('current_price', 'N/A')} ({yahoo_data.get('gold', {}).get('change_percent', 'N/A'):+.2f}%)
• Нефть WTI: ${yahoo_data.get('oil', {}).get('current_price', 'N/A')} ({yahoo_data.get('oil', {}).get('change_percent', 'N/A'):+.2f}%)

🏦 ПРОЦЕНТНЫЕ СТАВКИ ФРС:
• 3-месячные Treasury: {fed_data.get('current_rate', 'N/A')}%
• 10-летние Treasury: {fed_data.get('ten_year_yield', 'N/A')}%
• Кривая доходности: {fed_data.get('yield_curve_spread', 'N/A')}% 
  {'🔴 Инверсия!' if fed_data.get('yield_curve_spread', 0) < 0 else '🟢 Нормальная'}

😱 НАСТРОЕНИЯ КРИПТОРЫНКА:
• Fear & Greed Index: {fear_greed.get('value', 'N/A')}/100
• Интерпретация: {fear_greed.get('interpretation', 'N/A')}
• Влияние на рынок: {'Высокое' if fear_greed.get('value', 50) > 70 or fear_greed.get('value', 50) < 30 else 'Умеренное'}

⏰ Данные обновлены: {datetime.now().strftime('%d.%m.%Y в %H:%M')} МСК
📡 Источники: Yahoo Finance, ФРС США, Alternative.me
        """
        
        return ai_analysis + raw_data_section
    
    def _create_fallback_analysis(self, market_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Резервный анализ без AI (на случай проблем с API)
        """
        yahoo_data = market_data.get('yahoo_finance', {})
        fed_data = market_data.get('fed_rates', {})
        fear_greed = market_data.get('fear_greed_index', {})
        
        # Простая логика анализа
        sp500_change = yahoo_data.get('sp500', {}).get('change_percent', 0)
        fear_value = fear_greed.get('value', 50)
        fed_rate = fed_data.get('current_rate', 0)
        
        if fear_value < 25:
            sentiment = "Крайний страх на рынке 😰"
            recommendation = "Возможность для покупок на падении"
        elif fear_value > 75:
            sentiment = "Крайняя жадность 🚀"
            recommendation = "Осторожность, возможна коррекция"
        else:
            sentiment = "Нейтральные настроения 😐"
            recommendation = "Выжидательная позиция"
        
        short_analysis = f"""
📊 {sentiment} S&P 500: {sp500_change:+.1f}%, ставка ФРС: {fed_rate}%. Волатильность: {yahoo_data.get('vix', {}).get('current_price', 'N/A')}.
🎯 {recommendation}. Следите за изменениями процентных ставок.
⚠️ Основной риск: изменения в политике ФРС могут повлиять на оценку активов.
💡 Диверсификация портфеля остаётся ключевой стратегией в текущих условиях.
"""
        
        full_analysis = f"""
📊 АВТОМАТИЧЕСКИЙ АНАЛИЗ
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}

🏛️ ТРАДИЦИОННЫЕ РЫНКИ:
Основные американские индексы показывают смешанную динамику. При текущих процентных ставках ФРС на уровне {fed_rate}% инвесторы оценивают перспективы роста компаний.

🎯 АВТОМАТИЧЕСКАЯ РЕКОМЕНДАЦИЯ: {recommendation}

⚠️ Примечание: ИИ анализ временно недоступен. Обратитесь к администратору для восстановления полного функционала.
        """
        
        # Добавляем сырые данные и к fallback анализу
        full_analysis_with_data = self._add_raw_data_to_analysis(full_analysis, market_data)
        
        return short_analysis, full_analysis_with_data
    
    # ================== МЕТОДЫ ДЛЯ АНАЛИЗА КРИПТОВАЛЮТ ==================
    
    def create_crypto_analysis_prompt(self, crypto_data: Dict[str, Any]) -> str:
        """Создает промпт для AI анализа криптоданных"""
        
        top_coins = crypto_data.get('top_cryptocurrencies', [])
        derivatives = crypto_data.get('derivatives_data', {})
        fear_greed = crypto_data.get('fear_greed_index', {})
        
        # Формируем данные по топ криптовалютам
        coins_info = "=== ТОП-10 КРИПТОВАЛЮТ ===\n"
        for i, coin in enumerate(top_coins[:10], 1):
            price_change_24h = coin.get('price_change_24h', 0) or 0
            change_emoji = "📈" if price_change_24h > 0 else "📉" if price_change_24h < 0 else "➡️"
            
            coins_info += f"{i}. {coin['name']} ({coin['symbol']})\n"
            coins_info += f"   Цена: ${coin['price_usd']:,.2f}\n"
            coins_info += f"   Изменение 24ч: {change_emoji} {price_change_24h:.2f}%\n"
            coins_info += f"   Рыночная кап: ${coin['market_cap']:,.0f}\n"
            coins_info += f"   Объём 24ч: ${coin['volume_24h']:,.0f}\n\n"
        
        # Формируем данные по деривативам
        derivatives_info = "=== ДАННЫЕ ПО ДЕРИВАТИВАМ (ТОП-5) ===\n"
        if derivatives:
            for symbol, data in derivatives.items():
                funding_rate = data.get('funding_rate', 0) * 100  # Конвертируем в проценты
                long_short = data.get('long_short_ratio', 0)
                
                derivatives_info += f"{symbol}:\n"
                derivatives_info += f"   Фьючерсная цена: ${data.get('futures_price', 0):,.2f}\n"
                derivatives_info += f"   Funding Rate: {funding_rate:.4f}%\n"
                derivatives_info += f"   Открытый интерес: ${data.get('open_interest_usd', 0):,.0f}\n"
                derivatives_info += f"   Long/Short соотношение: {long_short:.2f}\n\n"
        else:
            derivatives_info += "Данные по деривативам недоступны\n\n"
        
        # Индекс страха и жадности
        fear_greed_info = "=== ИНДЕКС СТРАХА И ЖАДНОСТИ ===\n"
        if fear_greed:
            fear_greed_info += f"Значение: {fear_greed.get('value', 'N/A')}/100\n"
            fear_greed_info += f"Интерпретация: {fear_greed.get('classification', 'N/A')}\n\n"
        else:
            fear_greed_info += "Данные недоступны\n\n"
        
        prompt = f"""
{coins_info}
{derivatives_info}
{fear_greed_info}

🎯 КОНТЕКСТ: Это детальный анализ КРИПТОВАЛЮТНОГО рынка для канала криптоинвесторов!

ЗАДАЧА: Создай профессиональный анализ состоящий из:

1. 📊 ОБЩЕЕ СОСТОЯНИЕ КРИПТОРЫНКА (как себя чувствует рынок в целом)
2. 🔍 КЛЮЧЕВЫЕ НАБЛЮДЕНИЯ (что происходит с топ монетами, интересные движения)  
3. 📈 АНАЛИЗ ДЕРИВАТИВОВ (что показывает фандинг рейт, открытый интерес, настроения)
4. 💡 ТЕХНИЧЕСКИЙ АНАЛИЗ (уровни поддержки/сопротивления, тренды)
5. 🎯 ТОРГОВЫЕ РЕКОМЕНДАЦИИ (конкретные действия: покупать/продавать/ждать)
6. ⚠️ РИСКИ И ВОЗМОЖНОСТИ (на что обратить внимание)

🚨 ВАЖНЫЕ ТРЕБОВАНИЯ:
- Рекомендации ТОЛЬКО по криптовалютам (Bitcoin, Ethereum, альткоины)
- Используй профессиональную терминологию: "лонг", "шорт", "бычий", "медвежий"
- Анализируй фандинг рейты и открытый интерес для понимания настроений
- Учитывай индекс страха и жадности
- Давай конкретные ценовые уровни где возможно
- Будь объективным - не всегда нужно покупать!

Отвечай на русском языке, используй эмодзи, пиши для криптоинвесторов понятно но профессионально.
        """
        
        return prompt
    
    def analyze_crypto_data(self, crypto_data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Анализирует криптоданные с помощью AI
        
        Args:
            crypto_data: Словарь с данными о криптовалютах
            
        Returns:
            Кортеж (короткий_анализ, полный_анализ)
        """
        try:
            if not crypto_data:
                logger.warning("Нет данных для криптоанализа")
                return self._create_crypto_fallback_analysis({})
            
            # Создаем промпт для анализа
            prompt = self.create_crypto_analysis_prompt(crypto_data)
            
            if self.config.AI_PROVIDER == 'openai' and self.config.OPENAI_API_KEY:
                return self._analyze_crypto_with_openai(prompt, crypto_data)
            elif self.config.AI_PROVIDER == 'anthropic' and self.config.ANTHROPIC_API_KEY:
                return self._analyze_crypto_with_anthropic(prompt, crypto_data)
            else:
                logger.warning("AI провайдер не настроен для криптоанализа")
                return self._create_crypto_fallback_analysis(crypto_data)
                
        except Exception as e:
            logger.error(f"Ошибка AI анализа криптоданных: {e}")
            return self._create_crypto_fallback_analysis(crypto_data)
    
    def _analyze_crypto_with_openai(self, prompt: str, crypto_data: Dict[str, Any]) -> Tuple[str, str]:
        """Анализ криптоданных через OpenAI"""
        try:
            logger.info("Создание AI анализа криптоданных через OpenAI...")
            
            # Короткий анализ
            short_response = self.client.chat.completions.create(
                model=self.config.AI_MODEL,
                messages=[{
                    "role": "user", 
                    "content": f"{prompt}\n\nСоздай КРАТКИЙ анализ (до 300 токенов) для публикации в канале."
                }],
                max_tokens=300,
                temperature=0.7
            )
            
            short_analysis = short_response.choices[0].message.content.strip()
            
            # Полный анализ
            full_response = self.client.chat.completions.create(
                model=self.config.AI_MODEL,
                messages=[{
                    "role": "user", 
                    "content": f"{prompt}\n\nСоздай ДЕТАЛЬНЫЙ анализ (до 1500 токенов) с конкретными рекомендациями."
                }],
                max_tokens=1500,
                temperature=0.7
            )
            
            full_analysis = full_response.choices[0].message.content.strip()
            
            # Добавляем сырые данные к полному анализу
            full_analysis_with_data = self._add_raw_crypto_data_to_analysis(full_analysis, crypto_data)
            
            logger.info("AI криптоанализ успешно выполнен")
            return short_analysis, full_analysis_with_data
            
        except Exception as e:
            logger.error(f"Ошибка OpenAI криптоанализа: {e}")
            return self._create_crypto_fallback_analysis(crypto_data)
    
    def _analyze_crypto_with_anthropic(self, prompt: str, crypto_data: Dict[str, Any]) -> Tuple[str, str]:
        """Анализ криптоданных через Anthropic (заглушка)"""
        logger.warning("Anthropic анализ криптоданных не реализован, используем fallback")
        return self._create_crypto_fallback_analysis(crypto_data)
    
    def _add_raw_crypto_data_to_analysis(self, analysis: str, crypto_data: Dict[str, Any]) -> str:
        """Добавляет сырые криптоданные к анализу"""
        
        raw_data_section = "\n\n" + "="*50 + "\n"
        raw_data_section += "📊 СЫРЫЕ ДАННЫЕ ДЛЯ АНАЛИЗА\n"
        raw_data_section += "="*50 + "\n\n"
        
        # Топ криптовалюты
        top_coins = crypto_data.get('top_cryptocurrencies', [])
        if top_coins:
            raw_data_section += "💰 ТОП-10 КРИПТОВАЛЮТ:\n"
            for i, coin in enumerate(top_coins[:10], 1):
                price_change = coin.get('price_change_24h', 0) or 0
                raw_data_section += f"{i:2d}. {coin['symbol']:8s} ${coin['price_usd']:>12,.2f} "
                raw_data_section += f"({price_change:+6.2f}%) Cap: ${coin['market_cap']:>15,.0f}\n"
            raw_data_section += "\n"
        
        # Деривативы
        derivatives = crypto_data.get('derivatives_data', {})
        if derivatives:
            raw_data_section += "📈 ДАННЫЕ ПО ДЕРИВАТИВАМ:\n"
            for symbol, data in derivatives.items():
                funding_rate = data.get('funding_rate', 0) * 100
                raw_data_section += f"{symbol:8s} Funding: {funding_rate:+7.4f}% "
                raw_data_section += f"OI: ${data.get('open_interest_usd', 0):>12,.0f} "
                raw_data_section += f"L/S: {data.get('long_short_ratio', 0):5.2f}\n"
            raw_data_section += "\n"
        
        # Индекс страха и жадности
        fear_greed = crypto_data.get('fear_greed_index', {})
        if fear_greed:
            raw_data_section += "😱 ИНДЕКС СТРАХА И ЖАДНОСТИ:\n"
            raw_data_section += f"Значение: {fear_greed.get('value', 'N/A')}/100 ({fear_greed.get('classification', 'N/A')})\n\n"
        
        # Источники данных
        sources = crypto_data.get('data_sources', {})
        if sources:
            working_sources = sum(sources.values())
            raw_data_section += f"📡 ИСТОЧНИКИ ДАННЫХ: {working_sources}/3 активны\n"
            raw_data_section += f"• CoinGecko: {'✅' if sources.get('coingecko') else '❌'}\n"
            raw_data_section += f"• Binance Derivatives: {'✅' if sources.get('binance_derivatives') else '❌'}\n"
            raw_data_section += f"• Fear & Greed Index: {'✅' if sources.get('fear_greed') else '❌'}\n"
        
        return analysis + raw_data_section
    
    def _create_crypto_fallback_analysis(self, crypto_data: Dict[str, Any]) -> Tuple[str, str]:
        """Создает резервный анализ криптоданных при недоступности AI"""
        
        top_coins = crypto_data.get('top_cryptocurrencies', [])
        fear_greed = crypto_data.get('fear_greed_index', {})
        
        # Определяем общий тренд по топ-5 монетам
        if top_coins:
            changes_24h = [coin.get('price_change_24h', 0) or 0 for coin in top_coins[:5]]
            avg_change = sum(changes_24h) / len(changes_24h)
            positive_count = sum(1 for change in changes_24h if change > 0)
            
            if avg_change > 2:
                market_mood = "🚀 Бычий"
                trend_emoji = "📈"
            elif avg_change < -2:
                market_mood = "🐻 Медвежий"  
                trend_emoji = "📉"
            else:
                market_mood = "🤔 Неопределенный"
                trend_emoji = "➡️"
        else:
            market_mood = "❓ Неопределенный"
            trend_emoji = "❓"
            avg_change = 0
            positive_count = 0
        
        # Короткий анализ
        short_analysis = f"""📊 КРИПТОРЫНОК {datetime.now().strftime('%d.%m.%Y')}

{trend_emoji} Общий тренд: {market_mood}
💰 Топ-5 монет: {positive_count}/5 в плюсе
📈 Средний рост: {avg_change:+.1f}%
"""
        
        if fear_greed:
            short_analysis += f"😱 Страх/Жадность: {fear_greed.get('value', 'N/A')}/100"
        
        short_analysis += "\n\n⚠️ Данные получены без AI анализа"
        
        # Полный анализ
        full_analysis = f"""📋 ПОЛНЫЙ КРИПТОАНАЛИЗ

📊 СОСТОЯНИЕ РЫНКА:
Общий тренд рынка: {market_mood}
Средняя динамика топ-5: {avg_change:+.2f}%
Монет в росте: {positive_count} из 5

"""
        
        if top_coins:
            full_analysis += "💰 ТОП КРИПТОВАЛЮТЫ:\n"
            for i, coin in enumerate(top_coins[:5], 1):
                change = coin.get('price_change_24h', 0) or 0
                emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                full_analysis += f"{i}. {coin['symbol']}: ${coin['price_usd']:,.2f} {emoji} {change:+.2f}%\n"
        
        if fear_greed:
            full_analysis += f"\n😱 НАСТРОЕНИЯ:\nИндекс страха/жадности: {fear_greed.get('value', 'N/A')}/100 ({fear_greed.get('classification', 'N/A')})\n"
        
        full_analysis += """
🎯 РЕКОМЕНДАЦИИ:
• Следите за динамикой Bitcoin как лидера рынка
• Учитывайте общие рыночные настроения
• Применяйте риск-менеджмент

⚠️ Примечание: Анализ выполнен без AI из-за технических проблем.
        """
        
        # Добавляем сырые данные и к fallback анализу
        full_analysis_with_data = self._add_raw_crypto_data_to_analysis(full_analysis, crypto_data)
        
        return short_analysis, full_analysis_with_data

def test_ai_analysis():
    """Тест AI анализа с примерными данными"""
    
    # Пример данных для тестирования
    test_data = {
        'yahoo_finance': {
            'sp500': {'current_price': 4500, 'change_percent': 1.2},
            'nasdaq': {'current_price': 15000, 'change_percent': 0.8},
            'dow': {'current_price': 35000, 'change_percent': 1.1},
            'vix': {'current_price': 15.5},
            'dxy': {'current_price': 103.2, 'change_percent': 0.3},
            'gold': {'current_price': 2050, 'change_percent': -0.5},
            'oil': {'current_price': 72.5, 'change_percent': 1.8}
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
    short, full = analyzer.analyze_market_data(test_data)
    
    print("=== КРАТКИЙ АНАЛИЗ ===")
    print(short)
    print("\n=== ПОЛНЫЙ АНАЛИЗ ===")
    print(full)

if __name__ == "__main__":
    test_ai_analysis() 