"""
Модуль для сбора и анализа исторических данных криптовалют
"""

__version__ = "1.0.0"
__author__ = "Crypto Finance Bot Team"

from .historical_collector import HistoricalCollector
from .database_manager import DatabaseManager

__all__ = [
    'HistoricalCollector',
    'DatabaseManager'
] 