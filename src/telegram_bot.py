"""
Telegram бот для финансовой аналитики
"""
import logging
import json
import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
from telegram.error import BadRequest, Forbidden
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Добавляем путь к корневой папке для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_manager import CacheManager
from ai_analyzer import AIAnalyzer
from config import Config

# Настройка логирования (убираем спам HTTP запросов)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL)
)

# Отключаем логи HTTP запросов
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class FinanceBot:
    """Основной класс Telegram бота"""
    
    def __init__(self):
        self.config = Config()
        self.cache_manager = CacheManager()
        self.ai_analyzer = AIAnalyzer()
        
        # Кэш для хранения последних анализов для кнопок
        self.analysis_cache = {}
        self.last_analysis = None  # Последний анализ для публикации
        self.last_crypto_analysis = None  # Последний криптоанализ для публикации
        
        # Планировщик для автоматической публикации
        self.scheduler = None
        
        # Проверяем конфигурацию
        try:
            self.config.validate()
        except ValueError as e:
            logger.error(f"Ошибка конфигурации: {e}")
            raise
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        
        channel_status = "✅ Подключен" if self.config.TELEGRAM_CHANNEL_ID else "❌ Не настроен"
        
        # Получаем информацию о кэше
        cache_info = self.cache_manager.get_cache_info()
        cache_status = "✅ Активен" if cache_info['is_valid'] else "⚠️ Требует обновления"
        
        welcome_text = f"""
🤖 Добро пожаловать в Crypto Finance Bot!

Я помогу вам анализировать финансовые рынки с помощью AI.

📊 Доступные команды:
/metric - Анализ традиционных рынков (макроэкономика)
/crypto - Анализ криптовалютного рынка (топ-10 + деривативы)  
/publish - Опубликовать анализ в канал
/channel - Управление каналом
/cache - Информация о кэше данных
/help - Справка

📺 Канал для публикаций: {channel_status}
💾 Кэш данных: {cache_status}

🔍 Что я анализирую:
• Традиционные рынки (S&P 500, NASDAQ, VIX)
• Процентные ставки ФРС
• Индекс страха и жадности
• Сырьевые товары (золото, нефть)

💡 Нажмите /metric для анализа в этом чате или /publish для публикации в канал!
        """
        
        await update.message.reply_text(welcome_text)
        logger.info(f"Новый пользователь: {update.effective_user.id}")
    
    async def cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /cache - информация о кэше"""
        
        cache_info = self.cache_manager.get_cache_info()
        
        if not cache_info['exists']:
            status_text = """
💾 КЭШИРОВАНИЕ ДАННЫХ

❌ Кэш пуст
🔄 Первый запрос создаст кэш

📅 Расписание обновлений:
• 09:00 МСК (утренние данные)
• 21:00 МСК (вечерние данные)

💡 Это экономит API запросы и ускоряет работу бота.
            """
        else:
            last_update = cache_info['last_update']
            next_update = cache_info['next_update']
            
            status_icon = "✅" if cache_info['is_valid'] else "⚠️"
            
            status_text = f"""
💾 КЭШИРОВАНИЕ ДАННЫХ

{status_icon} Статус: {'Актуален' if cache_info['is_valid'] else 'Требует обновления'}
📊 Источников данных: {cache_info.get('data_sources', 0)}/3

⏰ Последнее обновление:
{last_update.strftime('%d.%m.%Y в %H:%M') if last_update else 'Никогда'}

🔄 Следующее обновление:
{next_update.strftime('%d.%m.%Y в %H:%M')}

📅 Расписание: 09:00 и 21:00 МСК
💡 Данные обновляются автоматически 2 раза в день
            """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Принудительное обновление", callback_data="force_cache_update")],
            [InlineKeyboardButton("📊 Получить анализ", callback_data="get_metric_analysis")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(status_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        
        help_text = """
📋 СПРАВКА ПО КОМАНДАМ

🔍 АНАЛИЗ РЫНКОВ:
/metric - Анализ традиционных рынков (макроэкономика)
/crypto - Анализ криптовалютного рынка (топ-10 + деривативы)
/publish - Опубликовать анализ в канал

📺 УПРАВЛЕНИЕ КАНАЛОМ:
/channel - Информация о канале
/cache - Состояние кэша данных

ℹ️ СПРАВКА:
/start - Приветствие и описание
/help - Показать эту справку

🎯 КАК РАБОТАЕТ:
1. /metric - анализ традиционных рынков (ФРС, индексы, золото)
2. /crypto - анализ крипторынка (топ-10 монет + деривативы) 
3. /publish - публикует последний анализ в канал
4. Данные обновляются автоматически 2 раза в день

📊 ИСТОЧНИКИ ДАННЫХ:
• Yahoo Finance - акции, индексы, сырьё
• ФРС - процентные ставки США
• Fear & Greed Index - настроения крипторынка

⚡ Кэширование обеспечивает быструю работу

❓ При проблемах обращайтесь к администратору.
        """
        
        await update.message.reply_text(help_text)
    
    async def metric_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /metric - анализ в личном чате"""
        
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил анализ /metric")
        
        # Отправляем сообщение о загрузке
        loading_message = await update.message.reply_text(
            "📊 Получаю данные и анализирую рынки...\n⏳ Это займёт несколько секунд"
        )
        
        try:
            # Получаем данные из кэша (или обновляем при необходимости)
            market_data = self.cache_manager.get_market_data()
            
            # Проверяем качество данных
            data_quality = market_data.get('data_quality', {})
            success_rate = data_quality.get('sources_available', 0)
            
            if success_rate == 0:
                await loading_message.edit_text(
                    "❌ Не удалось получить данные из источников.\n"
                    "Попробуйте позже или обратитесь к администратору."
                )
                return
            
            # Получаем AI анализ
            short_analysis, full_analysis = self.ai_analyzer.analyze_market_data(market_data)
            
            # Сохраняем последний анализ для публикации
            self.last_analysis = {
                'short_analysis': short_analysis,
                'full_analysis': full_analysis,
                'market_data': market_data,
                'timestamp': datetime.now(),
                'success_rate': success_rate
            }
            
            # Сохраняем в кэш для кнопки "Полный отчёт"
            cache_key = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            self.analysis_cache[cache_key] = self.last_analysis
            
            # Создаём клавиатуру
            keyboard = [
                [InlineKeyboardButton("📋 Полный отчёт", callback_data=f"full_report_{cache_key}")],
                [
                    InlineKeyboardButton("📺 Опубликовать в канал", callback_data="publish_to_channel"),
                    InlineKeyboardButton("🔄 Обновить", callback_data="refresh_metric")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем информацию о кэше
            cache_info = self.cache_manager.get_cache_info()
            cache_source = "📦 Кэш" if cache_info['is_valid'] else "🔄 Обновлено"
            
            # Формируем итоговое сообщение
            final_message = f"""
📊 АНАЛИЗ РЫНКОВ

{short_analysis}

📈 Источники: {success_rate}/3
{cache_source}
⏰ Обновлено: {datetime.now().strftime('%H:%M')}
            """
            
            # Удаляем сообщение загрузки и отправляем результат
            await loading_message.delete()
            await update.message.reply_text(
                final_message, 
                reply_markup=reply_markup
            )
            
            logger.info(f"Анализ отправлен пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении /metric: {e}")
            await loading_message.edit_text(
                f"❌ Произошла ошибка при анализе:\n{str(e)}\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )
    
    async def crypto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /crypto - анализ криптовалютного рынка"""
        
        user_id = update.effective_user.id
        logger.info(f"Пользователь {user_id} запросил криптоанализ /crypto")
        
        # Отправляем сообщение о загрузке
        loading_message = await update.message.reply_text(
            "📊 Анализирую криптовалютный рынок...\n"
            "🔄 Получение данных с CoinGecko и Binance\n"
            "⏳ Подождите немного..."
        )
        
        try:
            # Получаем криптоданные из кэша или обновляем
            crypto_data = self.cache_manager.get_crypto_data()
            
            if not crypto_data:
                await loading_message.edit_text(
                    "❌ Не удалось получить криптоданные.\n"
                    "Попробуйте позже или обратитесь к администратору."
                )
                return
            
            # Проверяем какие источники данных работают
            sources = crypto_data.get('data_sources', {})
            working_sources = sum(sources.values())
            
            if working_sources == 0:
                await loading_message.edit_text(
                    "❌ Все источники криптоданных недоступны.\n"
                    "Попробуйте позже или обратитесь к администратору."
                )
                return
            
            # Обновляем сообщение загрузки
            await loading_message.edit_text(
                "🤖 Создание AI анализа крипторынка...\n"
                f"📊 Источников данных: {working_sources}/3\n"
                "⏳ Анализируем..."
            )
            
            # Получаем AI анализ криптоданных
            short_analysis, full_analysis = self.ai_analyzer.analyze_crypto_data(crypto_data)
            
            # Сохраняем последний криптоанализ для публикации
            self.last_crypto_analysis = {
                'short_analysis': short_analysis,
                'full_analysis': full_analysis,
                'crypto_data': crypto_data,
                'timestamp': datetime.now(),
                'working_sources': working_sources
            }
            
            # Сохраняем в кэш для кнопки "Полный отчёт"
            cache_key = f"crypto_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
            self.analysis_cache[cache_key] = self.last_crypto_analysis
            
            # Создаём клавиатуру
            keyboard = [
                [InlineKeyboardButton("📋 Полный криптоотчёт", callback_data=f"full_report_{cache_key}")],
                [
                    InlineKeyboardButton("📺 Опубликовать в канал", callback_data="publish_crypto_to_channel"),
                    InlineKeyboardButton("🔄 Обновить крипто", callback_data="refresh_crypto")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем информацию о криптокэше
            crypto_cache_info = self.cache_manager.get_crypto_cache_info()
            cache_source = "📦 Кэш" if crypto_cache_info.get('is_valid', False) else "🔄 Обновлено"
            
            # Формируем итоговое сообщение
            final_message = f"""
🪙 АНАЛИЗ КРИПТОВАЛЮТ

{short_analysis}

📊 Источники: {working_sources}/3
{cache_source}
⏰ Обновлено: {datetime.now().strftime('%H:%M')}
            """
            
            # Удаляем сообщение загрузки и отправляем результат
            await loading_message.delete()
            await update.message.reply_text(
                final_message, 
                reply_markup=reply_markup
            )
            
            logger.info(f"Криптоанализ отправлен пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении /crypto: {e}")
            await loading_message.edit_text(
                f"❌ Произошла ошибка при криптоанализе:\n{str(e)}\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )
    
    async def publish_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /publish - публикация анализа в канал"""
        
        if not self.config.TELEGRAM_CHANNEL_ID:
            await update.message.reply_text(
                "❌ Канал не настроен!\n\n"
                "Администратор должен добавить TELEGRAM_CHANNEL_ID в конфигурацию."
            )
            return
        
        if not self.last_analysis:
            await update.message.reply_text(
                "❌ Нет готового анализа для публикации!\n\n"
                "Сначала выполните команду /metric для создания анализа."
            )
            return
        
        await self._publish_to_channel(update, context)
    
    async def _publish_to_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Внутренняя функция для публикации в канал"""
        
        try:
            loading_msg = await update.effective_message.reply_text("📺 Публикую анализ в канал...")
            
            analysis = self.last_analysis
            timestamp = analysis['timestamp']
            
            # Формируем сообщение для канала (более официальное)
            channel_message = f"""
📊 РЫНОЧНАЯ АНАЛИТИКА

{analysis['short_analysis']}

📈 Качество данных: {analysis['success_rate']}/3 источника
🤖 Анализ выполнен ИИ
⏰ {timestamp.strftime('%d.%m.%Y в %H:%M')} МСК

#анализ #рынки #инвестиции #ИИ
            """
            
            # Создаём кнопку для полного отчёта в канале
            channel_cache_key = f"channel_{datetime.now().strftime('%Y%m%d_%H%M')}"
            self.analysis_cache[channel_cache_key] = analysis
            
            keyboard = [
                [InlineKeyboardButton("📋 Полный отчёт", callback_data=f"full_report_{channel_cache_key}")],
                [InlineKeyboardButton("🔄 Обновить анализ", url=f"https://t.me/{context.bot.username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем в канал
            await context.bot.send_message(
                chat_id=self.config.TELEGRAM_CHANNEL_ID,
                text=channel_message,
                reply_markup=reply_markup
            )
            
            await loading_msg.edit_text(
                f"✅ Анализ успешно опубликован в канал!\n"
                f"🕒 {timestamp.strftime('%H:%M')}"
            )
            
            logger.info(f"Анализ опубликован в канал {self.config.TELEGRAM_CHANNEL_ID}")
            
        except Forbidden:
            await loading_msg.edit_text(
                "❌ Нет доступа к каналу!\n\n"
                "Убедитесь что:\n"
                "• Бот добавлен в канал как администратор\n"
                "• ID канала указан правильно"
            )
        except BadRequest as e:
            await loading_msg.edit_text(
                f"❌ Ошибка отправки в канал:\n{str(e)}\n\n"
                "Проверьте ID канала в настройках."
            )
        except Exception as e:
            logger.error(f"Ошибка публикации в канал: {e}")
            await loading_msg.edit_text(
                f"❌ Неожиданная ошибка:\n{str(e)}"
            )
    
    async def _publish_crypto_to_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Публикация криптоанализа в канал"""
        
        if not self.config.TELEGRAM_CHANNEL_ID:
            await update.effective_message.reply_text(
                "❌ Канал не настроен!\n\n"
                "Администратор должен добавить TELEGRAM_CHANNEL_ID в конфигурацию."
            )
            return
        
        if not self.last_crypto_analysis:
            await update.effective_message.reply_text(
                "❌ Нет криптоанализа для публикации!\n\n"
                "Сначала выполните команду /crypto"
            )
            return
        
        try:
            loading_msg = await update.effective_message.reply_text("📺 Публикую криптоанализ в канал...")
            
            analysis = self.last_crypto_analysis
            timestamp = analysis['timestamp']
            
            # Формируем сообщение для канала
            channel_message = f"""
🪙 КРИПТОВАЛЮТНЫЙ АНАЛИЗ

{analysis['short_analysis']}

📊 Качество данных: {analysis['working_sources']}/3 источника
🤖 Анализ выполнен ИИ GPT-4 Turbo
⏰ {timestamp.strftime('%d.%m.%Y в %H:%M')} МСК

#криптоанализ #bitcoin #ethereum #альткоины #ИИ #деривативы
            """
            
            # Создаём кнопку для полного отчёта в канале
            channel_cache_key = f"crypto_channel_{datetime.now().strftime('%Y%m%d_%H%M')}"
            self.analysis_cache[channel_cache_key] = analysis
            
            keyboard = [
                [InlineKeyboardButton("📋 Полный криптоотчёт", callback_data=f"full_report_{channel_cache_key}")],
                [InlineKeyboardButton("🔄 Обновить крипто", url=f"https://t.me/{context.bot.username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем в канал
            await context.bot.send_message(
                chat_id=self.config.TELEGRAM_CHANNEL_ID,
                text=channel_message,
                reply_markup=reply_markup
            )
            
            await loading_msg.edit_text(
                f"✅ Криптоанализ успешно опубликован в канал!\n"
                f"🕒 {timestamp.strftime('%H:%M')}"
            )
            
            logger.info(f"Криптоанализ опубликован в канал {self.config.TELEGRAM_CHANNEL_ID}")
            
        except Forbidden:
            await loading_msg.edit_text(
                "❌ Нет доступа к каналу!\n\n"
                "Убедитесь что:\n"
                "• Бот добавлен в канал как администратор\n"
                "• ID канала указан правильно"
            )
        except BadRequest as e:
            await loading_msg.edit_text(
                f"❌ Ошибка отправки в канал:\n{str(e)}\n\n"
                "Проверьте ID канала в настройках."
            )
        except Exception as e:
            logger.error(f"Ошибка публикации криптоанализа в канал: {e}")
            await loading_msg.edit_text(
                f"❌ Неожиданная ошибка:\n{str(e)}"
            )
    
    async def channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Команда /channel - информация о канале"""
        
        channel_id = self.config.TELEGRAM_CHANNEL_ID
        
        if not channel_id:
            await update.message.reply_text(
                "❌ Канал не настроен!\n\n"
                "💡 Для настройки канала:\n"
                "1. Добавьте бота в канал как администратора\n"
                "2. Добавьте TELEGRAM_CHANNEL_ID в .env файл\n"
                "3. Перезапустите бота"
            )
            return
        
        # Проверяем доступ к каналу
        try:
            chat = await context.bot.get_chat(channel_id)
            
            keyboard = [
                [InlineKeyboardButton("🧪 Тест канала", callback_data="test_channel")],
                [InlineKeyboardButton("📊 Опубликовать анализ", callback_data="publish_to_channel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            info_text = f"""
📺 ИНФОРМАЦИЯ О КАНАЛЕ

📋 Название: {chat.title}
🆔 ID: {channel_id}
👥 Участников: {chat.member_count if hasattr(chat, 'member_count') else 'Неизвестно'}

✅ Статус: Подключен
🤖 Бот имеет доступ к каналу

⚙️ Настройки:
• Автопубликация: {'Включена' if self.config.ENABLE_AUTO_PUBLISH else 'Отключена'}
• Расписание: {'Ежедневно в 18:00 МСК' if self.config.ENABLE_AUTO_PUBLISH else 'Отключено'}
• Кнопки в канале: Включены (Полный отчёт)
            """
            
            await update.message.reply_text(info_text, reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка доступа к каналу!\n\n"
                f"ID канала: {channel_id}\n"
                f"Ошибка: {str(e)}\n\n"
                "💡 Проверьте:\n"
                "• Правильность ID канала\n"
                "• Права администратора для бота"
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий на inline кнопки"""
        
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("full_report_"):
            # Показываем полный отчёт
            cache_key = query.data.replace("full_report_", "")
            
            if cache_key in self.analysis_cache:
                cached_data = self.analysis_cache[cache_key]
                full_analysis = cached_data['full_analysis']
                
                # Создаём кнопки для навигации
                navigation_keyboard = [
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
                    [
                        InlineKeyboardButton("🔄 Обновить анализ", callback_data="refresh_metric"),
                        InlineKeyboardButton("📺 В канал", callback_data="publish_to_channel")
                    ]
                ]
                navigation_markup = InlineKeyboardMarkup(navigation_keyboard)
                
                # Разбиваем длинный текст на части если нужно
                if len(full_analysis) > 4000:
                    parts = [full_analysis[i:i+4000] for i in range(0, len(full_analysis), 4000)]
                    
                    for i, part in enumerate(parts):
                        if i == 0:
                            await query.edit_message_text(
                                f"📋 ПОЛНЫЙ ОТЧЁТ (часть {i+1}/{len(parts)})\n\n{part}",
                                reply_markup=navigation_markup if i == len(parts) - 1 else None
                            )
                        else:
                            message_text = f"📋 ПОЛНЫЙ ОТЧЁТ (часть {i+1}/{len(parts)})\n\n{part}"
                            
                            if i == len(parts) - 1:
                                # Последняя часть - добавляем кнопки
                                await query.message.reply_text(message_text, reply_markup=navigation_markup)
                            else:
                                await query.message.reply_text(message_text)
                else:
                    await query.edit_message_text(
                        f"📋 ПОЛНЫЙ ОТЧЁТ\n\n{full_analysis}",
                        reply_markup=navigation_markup
                    )
                
                logger.info(f"Полный отчёт отправлен пользователю {query.from_user.id}")
            else:
                await query.edit_message_text(
                    "❌ Отчёт устарел. Выполните команду /metric заново."
                )
        
        elif query.data == "main_menu":
            # Возвращаемся в главное меню
            await self._show_main_menu(query)
        
        elif query.data == "show_cache_info":
            # Показываем информацию о кэше (как команда /cache)
            await self._show_cache_info_inline(query)
        
        elif query.data == "show_channel_info":
            # Показываем информацию о канале (как команда /channel)
            await self._show_channel_info_inline(query)
        
        elif query.data == "show_help":
            # Показываем справку (как команда /help)
            await self._show_help_inline(query)
        
        elif query.data == "refresh_metric":
            # Обновляем анализ с принудительным обновлением кэша
            await query.edit_message_text("🔄 Принудительно обновляю данные...")
            
            # Принудительно обновляем кэш
            market_data = self.cache_manager.get_market_data(force_update=True)
            
            # Продолжаем как обычная команда /metric
            await self.metric_command(update, context)
        
        elif query.data == "refresh_crypto":
            # Обновляем криптоанализ с принудительным обновлением кэша
            await query.edit_message_text("🔄 Принудительно обновляю криптоданные...")
            
            # Принудительно обновляем криптокэш
            crypto_data = self.cache_manager.get_crypto_data(force_update=True)
            
            # Продолжаем как обычная команда /crypto
            await self.crypto_command(update, context)
        
        elif query.data == "publish_crypto_to_channel":
            # Публикуем криптоанализ в канал
            await self._publish_crypto_to_channel(update, context)
        
        elif query.data == "publish_to_channel":
            # Публикуем в канал
            await self._publish_to_channel(update, context)
        
        elif query.data == "test_channel":
            # Тестируем канал
            try:
                test_message = f"🧪 Тестовое сообщение от бота\n⏰ {datetime.now().strftime('%H:%M:%S')}"
                await context.bot.send_message(
                    chat_id=self.config.TELEGRAM_CHANNEL_ID,
                    text=test_message
                )
                await query.edit_message_text("✅ Тест канала прошёл успешно!")
            except Exception as e:
                await query.edit_message_text(f"❌ Ошибка теста канала:\n{str(e)}")
        
        elif query.data == "force_cache_update":
            # Принудительное обновление кэша
            await query.edit_message_text("🔄 Принудительно обновляю кэш...")
            
            try:
                self.cache_manager.get_market_data(force_update=True)
                cache_info = self.cache_manager.get_cache_info()
                
                await query.edit_message_text(
                    f"✅ Кэш успешно обновлён!\n\n"
                    f"📊 Источников данных: {cache_info.get('data_sources', 0)}/3\n"
                    f"⏰ Время обновления: {datetime.now().strftime('%H:%M')}"
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Ошибка обновления кэша:\n{str(e)}")
        
        elif query.data == "get_metric_analysis":
            # Получаем анализ из команды кэша
            await self.metric_command(update, context)
    
    async def _show_main_menu(self, query) -> None:
        """Показывает главное меню"""
        
        # Получаем информацию о состоянии
        channel_status = "✅ Подключен" if self.config.TELEGRAM_CHANNEL_ID else "❌ Не настроен"
        cache_info = self.cache_manager.get_cache_info()
        cache_status = "✅ Актуален" if cache_info.get('is_valid', False) else "⚠️ Требует обновления"
        
        main_menu_text = f"""
🤖 **Crypto Finance Bot** - Главное меню

📊 **Доступные функции:**

📈 Анализ рынков с ИИ
📺 Публикация в канал
💾 Система кэширования
🔧 Управление каналом

📌 **Текущий статус:**
📺 Канал: {channel_status}
💾 Кэш: {cache_status}

💡 Выберите действие из меню ниже:
        """
        
        # Главное меню с кнопками
        keyboard = [
            [
                InlineKeyboardButton("📊 Анализ рынков", callback_data="get_metric_analysis"),
                InlineKeyboardButton("📺 Публиковать", callback_data="publish_to_channel")
            ],
            [
                InlineKeyboardButton("💾 Кэш", callback_data="show_cache_info"),
                InlineKeyboardButton("🔧 Канал", callback_data="show_channel_info")
            ],
            [
                InlineKeyboardButton("❓ Справка", callback_data="show_help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(main_menu_text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception:
            # Если не получается отредактировать, отправляем новое сообщение
            await query.message.reply_text(main_menu_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_cache_info_inline(self, query) -> None:
        """Показывает информацию о кэше через inline кнопку"""
        
        cache_info = self.cache_manager.get_cache_info()
        
        if not cache_info.get('exists', False):
            status_text = """
💾 **КЭШИРОВАНИЕ ДАННЫХ**

❌ Кэш пуст
🔄 Первый запрос создаст кэш

📅 **Расписание обновлений:**
• 09:00 МСК (утренние данные)
• 21:00 МСК (вечерние данные)

💡 Это экономит API запросы и ускоряет работу бота.
            """
        else:
            last_update = cache_info.get('last_update')
            next_update = cache_info.get('next_update')
            
            status_icon = "✅" if cache_info.get('is_valid', False) else "⚠️"
            
            status_text = f"""
💾 **КЭШИРОВАНИЕ ДАННЫХ**

{status_icon} Статус: {'Актуален' if cache_info.get('is_valid', False) else 'Требует обновления'}
📊 Источников данных: {cache_info.get('data_sources', 0)}/3

⏰ **Последнее обновление:**
{last_update.strftime('%d.%m.%Y в %H:%M') if last_update else 'Никогда'}

🔄 **Следующее обновление:**
{next_update.strftime('%d.%m.%Y в %H:%M') if next_update else 'N/A'}

📅 Расписание: 09:00 и 21:00 МСК
💡 Данные обновляются автоматически 2 раза в день
            """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Принудительное обновление", callback_data="force_cache_update")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_channel_info_inline(self, query) -> None:
        """Показывает информацию о канале через inline кнопку"""
        
        channel_id = self.config.TELEGRAM_CHANNEL_ID
        
        if not channel_id:
            info_text = """
📺 **УПРАВЛЕНИЕ КАНАЛОМ**

❌ Канал не настроен!

💡 **Для настройки канала:**
1. Добавьте бота в канал как администратора
2. Добавьте TELEGRAM_CHANNEL_ID в .env файл
3. Перезапустите бота
            """
            
            keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
        else:
            try:
                # Здесь должна быть проверка канала, но упростим для inline
                info_text = f"""
📺 **ИНФОРМАЦИЯ О КАНАЛЕ**

🆔 ID: {channel_id}
✅ Статус: Подключен
🤖 Бот имеет доступ к каналу

⚙️ **Настройки:**
• Автопубликация: {'Включена' if self.config.ENABLE_AUTO_PUBLISH else 'Отключена'}
• Расписание: {'Ежедневно в 18:00 МСК' if self.config.ENABLE_AUTO_PUBLISH else 'Отключено'}
• Кнопки в канале: Включены
                """
                
                keyboard = [
                    [InlineKeyboardButton("🧪 Тест канала", callback_data="test_channel")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
            except:
                info_text = f"""
📺 **ОШИБКА КАНАЛА**

🆔 ID: {channel_id}
❌ Нет доступа к каналу

💡 **Проверьте:**
• Правильность ID канала
• Права администратора для бота
                """
                
                keyboard = [
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_help_inline(self, query) -> None:
        """Показывает справку через inline кнопку"""
        
        help_text = """
📋 **СПРАВКА ПО КОМАНДАМ**

🔍 **АНАЛИЗ РЫНКОВ:**
/metric - Получить анализ в этом чате
/publish - Опубликовать анализ в канал

📺 **УПРАВЛЕНИЕ КАНАЛОМ:**
/channel - Информация о канале
/cache - Состояние кэша данных

ℹ️ **СПРАВКА:**
/start - Приветствие и описание
/help - Показать эту справку

🎯 **КАК РАБОТАЕТ:**
1. /metric - анализ в личном чате с кнопками
2. /publish - публикует последний анализ в канал
3. Данные обновляются автоматически 2 раза в день

📊 **ИСТОЧНИКИ ДАННЫХ:**
• Yahoo Finance - акции, индексы, сырьё
• ФРС - процентные ставки США
• Fear & Greed Index - настроения крипторынка

⚡ Кэширование обеспечивает быструю работу

❓ При проблемах обращайтесь к администратору.
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик неизвестных команд"""
        
        await update.message.reply_text(
            "❓ Неизвестная команда.\n\n"
            "Доступные команды:\n"
            "/start - Начать работу\n"
            "/metric - Анализ традиционных рынков\n"
            "/crypto - Анализ криптовалют\n"
            "/publish - Опубликовать в канал\n"
            "/channel - Управление каналом\n"
            "/cache - Информация о кэше\n"
            "/help - Справка"
        )
    
    def _setup_auto_publish_scheduler(self, application: Application) -> None:
        """Настройка автоматической публикации по расписанию"""
        
        if not self.config.ENABLE_AUTO_PUBLISH or not self.config.TELEGRAM_CHANNEL_ID:
            logger.info("Автоматическая публикация отключена")
            return
        
        self.scheduler = BackgroundScheduler()
        
        # Публикация традиционного анализа: ежедневно в 18:00 МСК
        self.scheduler.add_job(
            func=self._auto_publish_analysis,
            trigger=CronTrigger(hour=18, minute=0, timezone="Europe/Moscow"),
            args=[application],
            id="daily_market_publish",
            replace_existing=True
        )
        
        # Публикация криптоанализа: 2 раза в день в 10:00 и 22:00 МСК  
        self.scheduler.add_job(
            func=self._auto_publish_crypto_analysis,
            trigger=CronTrigger(hour=10, minute=0, timezone="Europe/Moscow"),
            args=[application],
            id="morning_crypto_publish",
            replace_existing=True
        )
        
        self.scheduler.add_job(
            func=self._auto_publish_crypto_analysis,
            trigger=CronTrigger(hour=22, minute=0, timezone="Europe/Moscow"),
            args=[application],
            id="evening_crypto_publish",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Автоматическая публикация запущена:")
        logger.info("• Традиционные рынки: ежедневно в 18:00 МСК") 
        logger.info("• Криптоанализ: в 10:00 и 22:00 МСК")
    
    async def _auto_publish_analysis(self, application: Application) -> None:
        """Автоматическая публикация анализа в канал"""
        
        try:
            logger.info("Запуск автоматической публикации...")
            
            # Получаем свежие данные
            market_data = self.cache_manager.get_market_data(force_update=True)
            
            if not market_data:
                logger.error("Не удалось получить данные для автопубликации")
                return
            
            # Создаем анализ
            short_analysis, full_analysis = self.ai_analyzer.analyze_market_data(market_data)
            
            if not short_analysis:
                logger.error("Не удалось создать анализ для автопубликации")
                return
            
            # Создаем ключ для кнопки полного отчета
            analysis_key = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.analysis_cache[analysis_key] = {
                'short_analysis': short_analysis,
                'full_analysis': full_analysis,
                'timestamp': datetime.now()
            }
            
            # Кнопка для полного отчета
            keyboard = [
                [InlineKeyboardButton("📋 Полный отчёт", callback_data=f"full_report_{analysis_key}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем в канал
            await application.bot.send_message(
                chat_id=self.config.TELEGRAM_CHANNEL_ID,
                text=f"🤖 **АВТОМАТИЧЕСКИЙ АНАЛИЗ РЫНКОВ**\n\n{short_analysis}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info("Автоматическая публикация выполнена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка автоматической публикации: {e}")
    
    async def _auto_publish_crypto_analysis(self, application: Application) -> None:
        """Автоматическая публикация криптоанализа в канал"""
        
        try:
            logger.info("Запуск автоматической публикации криптоанализа...")
            
            # Получаем свежие криптоданные
            crypto_data = self.cache_manager.get_crypto_data(force_update=True)
            
            if not crypto_data:
                logger.error("Не удалось получить криптоданные для автопубликации")
                return
            
            # Создаем криптоанализ
            short_analysis, full_analysis = self.ai_analyzer.analyze_crypto_data(crypto_data)
            
            if not short_analysis:
                logger.error("Не удалось создать криптоанализ для автопубликации")
                return
            
            # Создаем ключ для кнопки полного отчета
            analysis_key = f"auto_crypto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            working_sources = sum(crypto_data.get('data_sources', {}).values())
            
            self.analysis_cache[analysis_key] = {
                'short_analysis': short_analysis,
                'full_analysis': full_analysis,
                'crypto_data': crypto_data,
                'timestamp': datetime.now(),
                'working_sources': working_sources
            }
            
            # Определяем время публикации
            current_hour = datetime.now().hour
            time_period = "🌅 УТРЕННИЙ" if current_hour < 16 else "🌙 ВЕЧЕРНИЙ"
            
            # Формируем сообщение для канала  
            channel_message = f"""
🪙 {time_period} КРИПТОАНАЛИЗ

{short_analysis}

📊 Источники: {working_sources}/3 активны
🤖 ИИ анализ: GPT-4 Turbo
⏰ {datetime.now().strftime('%d.%m.%Y в %H:%M')} МСК

#автокрипто #bitcoin #ethereum #альткоины #деривативы #ИИ
            """
            
            # Кнопка для полного отчета
            keyboard = [
                [InlineKeyboardButton("📋 Полный криптоотчёт", callback_data=f"full_report_{analysis_key}")],
                [InlineKeyboardButton("🔄 Обновить крипто", url=f"https://t.me/{application.bot.username}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем в канал
            await application.bot.send_message(
                chat_id=self.config.TELEGRAM_CHANNEL_ID,
                text=channel_message,
                reply_markup=reply_markup
            )
            
            logger.info("Автоматическая публикация криптоанализа выполнена успешно")
            
        except Exception as e:
            logger.error(f"Ошибка автоматической публикации криптоанализа: {e}")
    
    def stop_scheduler(self) -> None:
        """Остановка планировщика"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планировщик автопубликации остановлен")
    
    def run(self):
        """Запуск бота"""
        
        logger.info("Запуск Telegram бота...")
        
        # Создаём приложение
        application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("metric", self.metric_command))
        application.add_handler(CommandHandler("crypto", self.crypto_command))
        application.add_handler(CommandHandler("publish", self.publish_command))
        application.add_handler(CommandHandler("channel", self.channel_command))
        application.add_handler(CommandHandler("cache", self.cache_command))
        
        # Обработчик inline кнопок
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Обработчик неизвестных команд
        application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
        
        # Запускаем планировщик автопубликации
        self._setup_auto_publish_scheduler(application)
        
        # Запускаем бота
        logger.info("Бот запущен и готов к работе!")
        try:
            application.run_polling()
        finally:
            # Останавливаем планировщик при завершении
            self.stop_scheduler()

def main():
    """Точка входа"""
    bot = None
    try:
        bot = FinanceBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    finally:
        # Убеждаемся что планировщик остановлен
        if bot:
            bot.stop_scheduler()

if __name__ == "__main__":
    main() 