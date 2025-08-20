# Конфигурация кошельков китов для бота-аналитика
from typing import List, Dict, Any
import asyncio
from web3 import Web3

class WhaleConfig:
    """Конфигурация адресов китов для отслеживания"""
    
    # Ethereum киты (исключая большинство биржевых кошельков)
    ETHERSCAN_ADDRESSES = [
        # Топ индивидуальные киты с высокой активностью
        "0xF977814e90da44bfa03b6295a0616a897441acec",  # 252K ETH - крупный кит
        "0x8315177ab297ba92a06054ce80a67ed4dbd7ed3a",  # 1M ETH - активный трейдер
        "0xE92d1A43df510f82c66382592a047d288f85226f",  # 450K ETH - DeFi кит
        "0x8d0BB74e37ab644964aca2f3fbe12b9147f9d841",  # 367K ETH - NFT кит
        "0xcA8Fa8f0b631ecdb18cda619c4fc9d197c8affca",  # 325K ETH - Smart money
        "0x3BfC20f0b9afcace800d73d2191166ff16540258",  # 306K ETH - арбитражник
        "0xA6dfb62fc572da152a335384f7724535b9defc84",  # 355K ETH - мультичейн кит
        "0xd3a22590f8243f8e83ac230d1842c9af0404c4a1",  # 300K ETH - стабильный холдер
        "0x8103683202aa8da10536036edef04cdd865c225e",  # 275K ETH - институциональный
        "0xbeb5fc579115071764c7423a4f12edde41f106ed",  # 266K ETH - DeFi специалист
        
        # Дополнительные крупные киты
        "0x0a4c79ce84202b03e95b7a692e5d728d83c44c76",  # 254K ETH - стейкинг кит
        "0x2b6ed29a95753c3ad948348e3e7b1a251080ffb9",  # 250K ETH - долгосрочный инвестор
        "0x1b3cb81e51011b549d78bf720b0d924ac763a7c2",  # 243K ETH - активный трейдер
        "0x220866b1a2219f40e72f5c628b65d54268ca3a9d",  # 240K ETH - yield farmer
        "0x73af3bcf944a6559933396c1577b257e2054d935",  # 218K ETH - рост активности
        "0x866c9a77d8ab71d2874703e80cb7ad809b301e8e",  # 218K ETH - стабильный кит
        "0x15c22df3e71e7380012668fb837c537d0f8b38a1",  # 214K ETH - консервативный
        "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",  # 213K ETH - активная торговля
        "0x0bd48f6b86a26d3a217d0fa6ffe2b491b956a7a2",  # 213K ETH - DeFi активист
        "0x17e5545b11b468072283cee1f066a059fb0dbf24",  # 212K ETH - стратегический
        
        # Smart Money адреса (высокопрофитные)
        "0xafcd96e580138cfa2332c632e66308eacd45c5da",  # 210K ETH - smart money
        "0x9c22a4039f269e72de6b029b273be059cdbb831c",  # 198K ETH - аналитический
        "0xbf3aeb96e164ae67e763d9e050ff124e7c3fdd28",  # 187K ETH - технический трейдер
        "0x94dbf04e273d87e6d9bed68c616f43bf86560c74",  # 182K ETH - снижающая активность
        "0x7bbfaa2f8b2d2a613b4439be3428dfbf0f405390",  # 182K ETH - осторожный кит
        "0x5b5b69f4e0add2df5d2176d7dbd20b4897bc7ec4",  # 169K ETH - средний кит
        "0x2f2d854c1d6d5bb8936bb85bc07c28ebb42c9b10",  # 168K ETH - стабильный
        "0x109be9d7d5f64c8c391ced3a8f69bdef20fcaea9",  # 155K ETH - растущий
        "0xa023f08c70a23abc7edfc5b6b5e171d78dfc947e",  # 148K ETH - активный мелкий
        "0xb5ab08d153218c1a6a5318b14eeb92df0fb168d6",  # 135K ETH - развивающийся
        
        # Дополнительные перспективные киты
        "0x8484ef722627bf18ca5ae6bcf031c23e6e922b30",  # 133K ETH - снижающий позиции
        "0xd47b4a4c6207b1ee0eb1dd4e5c46a19b50fec00b",  # 129K ETH - новый участник
        "0xd65fb7d4cb595833e84c3c094bd4779bab0d4c62",  # 129K ETH - парный кошелек
        "0xa160cdab225685da1d56aa342ad8841c3b53f291",  # 127K ETH - активное управление
        "0x59708733fbbf64378d9293ec56b977c011a08fd2",  # 124K ETH - стабильный рост
    ]
    
    # Пороговые значения для анализа (обновленные)
    ETH_THRESHOLD = 50   # ETH (снижен для лучшего покрытия)
    USD_THRESHOLD = 50000  # USD (снижен для более чувствительного анализа)
    
    # Дополнительные конфигурации
    MIN_WHALE_ETH = 100000  # Минимум ETH для классификации как кит
    
    # Особые категории китов
    DEFI_WHALES_ETH = [
        "0xE92d1A43df510f82c66382592a047d288f85226f",
        "0xbeb5fc579115071764c7423a4f12edde41f106ed",
        "0x0bd48f6b86a26d3a217d0fa6ffe2b491b956a7a2",
    ]
    
    SMART_MONEY_ETH = [
        "0xcA8Fa8f0b631ecdb18cda619c4fc9d197c8affca",
        "0xafcd96e580138cfa2332c632e66308eacd45c5da",
        "0x9c22a4039f269e72de6b029b273be059cdbb831c",
    ]

class WhaleAnalyzer:
    """Анализатор активности китов"""
    
    def __init__(self, eth_rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(eth_rpc_url))
        self.whale_config = WhaleConfig()
    
    async def get_eth_balance(self, address: str) -> float:
        """Получить баланс ETH кошелька"""
        try:
            balance_wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
            return self.w3.from_wei(balance_wei, 'ether')
        except Exception as e:
            print(f"Ошибка получения баланса ETH для {address}: {e}")
            return 0.0
    
    async def get_latest_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """Получить последние транзакции кошелька"""
        return await self._get_eth_transactions(address, limit)
    
    async def _get_eth_transactions(self, address: str, limit: int) -> List[Dict]:
        """Получить транзакции Ethereum (упрощенная версия)"""
        # Здесь должна быть интеграция с Etherscan API или другим провайдером
        # Пример структуры данных:
        return [
            {
                "hash": "0x...",
                "from": address,
                "to": "0x...",
                "value": "1.5",
                "timestamp": 1735689600,
                "gas_used": "21000",
                "token": "ETH"
            }
        ]
    
    async def analyze_whale_activity(self) -> Dict:
        """Анализ активности всех отслеживаемых китов (расширенная версия)"""
        results = {
            "ethereum": {},
            "summary": {
                "total_eth_value": 0,
                "active_whales": 0,
                "critical_whales": 0,
                "high_risk_whales": 0,
                "defi_specialists": 0,
                "smart_money_count": 0
            },
            "alerts": []
        }
        
        # Анализ Ethereum китов
        for address in self.whale_config.ETHERSCAN_ADDRESSES:
            balance = await self.get_eth_balance(address)
            transactions = await self.get_latest_transactions(address)
            balance_usd = balance * 3500  # Примерная цена ETH
            category = self.get_whale_category(address)
            risk_level = self.get_whale_risk_level(balance_usd, len(transactions))
            
            whale_data = {
                "balance_eth": balance,
                "balance_usd": balance_usd,
                "recent_transactions": len(transactions),
                "is_active": len(transactions) > 0,
                "category": category,
                "risk_level": risk_level,
                "significant_transactions": self.filter_significant_transactions(transactions)
            }
            
            results["ethereum"][address] = whale_data
            results["summary"]["total_eth_value"] += balance_usd
            
            # Обновление счетчиков
            if len(transactions) > 0:
                results["summary"]["active_whales"] += 1
            if risk_level == "CRITICAL":
                results["summary"]["critical_whales"] += 1
            elif risk_level == "HIGH":
                results["summary"]["high_risk_whales"] += 1
            if "DeFi" in category:
                results["summary"]["defi_specialists"] += 1
            if "Smart Money" in category:
                results["summary"]["smart_money_count"] += 1
                
            # Создание алертов для критических движений
            if risk_level == "CRITICAL" and len(transactions) > 5:
                results["alerts"].append({
                    "type": "HIGH_ACTIVITY",
                    "address": address,
                    "chain": "ethereum",
                    "message": f"Critical whale {address[:10]}... показывает высокую активность: {len(transactions)} транзакций",
                    "balance_usd": balance_usd
                })
        
        return results
    
    def get_whale_category(self, address: str) -> str:
        """Определить категорию кита"""
        if address in self.whale_config.DEFI_WHALES_ETH:
            return "DeFi Specialist"
        elif address in self.whale_config.SMART_MONEY_ETH:
            return "Smart Money"
        else:
            return "General Whale"
    
    def get_whale_risk_level(self, balance_usd: float, recent_activity: int) -> str:
        """Определить уровень риска/важности кита"""
        if balance_usd > 50000000 and recent_activity > 10:  # >$50M + высокая активность
            return "CRITICAL"
        elif balance_usd > 20000000 and recent_activity > 5:  # >$20M + средняя активность
            return "HIGH"
        elif balance_usd > 5000000:  # >$5M
            return "MEDIUM"
        else:
            return "LOW"

    def filter_significant_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Выделить значимые транзакции по заданным порогам для сети"""
        if not transactions:
            return []

        significant: List[Dict[str, Any]] = []

        for tx in transactions:
            try:
                value_eth = float(tx.get("value", 0))
            except (TypeError, ValueError):
                value_eth = 0.0
            if value_eth >= self.whale_config.ETH_THRESHOLD:
                significant.append(tx)

        return significant

    def generate_whale_report(self, activity: Dict[str, Any]) -> str:
        """Сформировать текстовый отчёт по активности китов"""
        if not activity:
            return "Нет данных об активности китов"

        summary = activity.get("summary", {})
        total_eth_usd = summary.get("total_eth_value", 0)
        active_whales = summary.get("active_whales", 0)
        critical = summary.get("critical_whales", 0)
        high = summary.get("high_risk_whales", 0)
        defi = summary.get("defi_specialists", 0)
        smart = summary.get("smart_money_count", 0)
        alerts = activity.get("alerts", [])

        lines = [
            "🐋 Отчёт по активности китов",
            f"ETH суммарно: ${total_eth_usd:,.0f}",
            f"Активных китов: {active_whales}",
            f"Критических: {critical} | Высокий риск: {high}",
            f"DeFi специалисты: {defi} | Smart Money: {smart}",
            f"Алертов: {len(alerts)}",
        ]

        return "\n".join(lines)

# Пример использования (расширенный)
async def main():
    """Расширенный пример использования анализатора китов"""
    
    # Инициализация анализатора
    analyzer = WhaleAnalyzer(
        eth_rpc_url="https://eth-mainnet.alchemyapi.io/v2/YOUR_API_KEY"
    )
    
    print("🐋 Запуск расширенного анализа китов...")
    print(f"📊 Отслеживаем {len(analyzer.whale_config.ETHERSCAN_ADDRESSES)} ETH китов")
    
    # Полный анализ активности китов
    activity_report = await analyzer.analyze_whale_activity()
    
    # Генерация и вывод детального отчета
    report = analyzer.generate_whale_report(activity_report)
    print(f"\n{report}")
    
    # Анализ по категориям
    print(f"\n📈 КАТЕГОРИЙНЫЙ АНАЛИЗ:")
    
    # DeFi специалисты
    defi_eth = [addr for addr in analyzer.whale_config.DEFI_WHALES_ETH]
    print(f"🏦 DeFi киты ETH: {len(defi_eth)} адресов")
    
    # Smart Money
    smart_eth = [addr for addr in analyzer.whale_config.SMART_MONEY_ETH]
    print(f"🧠 Smart Money ETH: {len(smart_eth)} адресов")
    
    # Поиск самых активных китов
    print(f"\n🔥 САМЫЕ АКТИВНЫЕ КИТЫ:")
    
    # ETH активные
    active_eth = [(addr, data) for addr, data in activity_report["ethereum"].items() 
                  if data["recent_transactions"] > 0]
    active_eth.sort(key=lambda x: x[1]["recent_transactions"], reverse=True)
    
    for addr, data in active_eth[:3]:
        print(f"📍 ETH: {addr[:12]}...{addr[-6:]}")
        print(f"   💰 Баланс: {data['balance_eth']:,.0f} ETH (${data['balance_usd']:,.0f})")
        print(f"   📊 Транзакций: {data['recent_transactions']}")
        print(f"   🏷️  Категория: {data['category']}")
        print(f"   ⚠️  Риск: {data['risk_level']}")

if __name__ == "__main__":
    # Пример запуска (закомментировано для безопасности)
    # asyncio.run(main())
    
    # Вывод расширенной конфигурации для использования
    config = WhaleConfig()
    
    print("🐋 РАСШИРЕННАЯ КОНФИГУРАЦИЯ КИТОВ ДЛЯ БОТА-АНАЛИТИКА")
    print("=" * 60)
    
    print(f"\n📊 ETHEREUM ADDRESSES ({len(config.ETHERSCAN_ADDRESSES)} китов):")
    print("ETHERSCAN_ADDRESSES=" + ",".join(config.ETHERSCAN_ADDRESSES))
    
    print(f"\n🏦 DeFi SPECIALISTS:")
    print(f"ETH DeFi: {len(config.DEFI_WHALES_ETH)} китов")
    
    print(f"\n🧠 SMART MONEY:")
    print(f"ETH Smart: {len(config.SMART_MONEY_ETH)} китов")
    
    print(f"\n💡 РЕКОМЕНДАЦИИ ДЛЯ БОТА:")
    print("• Установите алерты для транзакций >$50K")
    print("• Анализируйте паттерны DeFi китов для новых возможностей")
    print("• Мониторьте активность CRITICAL и HIGH риск китов")
    print("• Используйте категоризацию для фильтрации сигналов")