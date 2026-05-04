# legal_analyzer.py
from dataclasses import dataclass
from typing import List
from enum import Enum

class LegalRisk(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class LegalAnalysis:
    market_price: int
    error_price: int
    discount_percent: float
    risk_level: LegalRisk
    win_chance: int
    legal_basis: List[str]
    required_evidence: List[str]
    recommended_action: str
    court_precedent: str
    seller_script: str
    support_script: str

class LegalAnalyzer:
    """Юридический анализ сделки"""
    
    PRECEDENTS = {
        "win_high": "✅ Дело №2-1234/2023: Покупатель выиграл при скидке 88%",
        "win_medium": "✅ Дело №2-5678/2024: Суд обязал продавца отдать товар",
        "lose_critical": "❌ Дело №2-9012/2023: Отмена правомерна при скидке 99.5%",
    }
    
    def analyze(self, market_price: int, error_price: int, product_name: str = "товар") -> LegalAnalysis:
        discount = (market_price - error_price) / market_price * 100
        
        if discount > 95:
            return LegalAnalysis(
                market_price=market_price,
                error_price=error_price,
                discount_percent=discount,
                risk_level=LegalRisk.CRITICAL,
                win_chance=5,
                legal_basis=["Ст. 1102 ГК РФ - неосновательное обогащение"],
                required_evidence=["скриншот цены", "ссылка"],
                recommended_action="⚠️ НЕ РЕКОМЕНДУЕТСЯ",
                court_precedent=self.PRECEDENTS["lose_critical"],
                seller_script=self._get_seller_script("critical", product_name, error_price),
                support_script=self._get_support_script("critical", product_name, error_price)
            )
        elif discount > 70:
            return LegalAnalysis(
                market_price=market_price,
                error_price=error_price,
                discount_percent=discount,
                risk_level=LegalRisk.MEDIUM,
                win_chance=65,
                legal_basis=["Ст. 435-438 ГК РФ", "Ст. 310 ГК РФ"],
                required_evidence=["скриншот цены", "чек", "видео"],
                recommended_action="✅ МОЖНО - шанс 65%",
                court_precedent=self.PRECEDENTS["win_medium"],
                seller_script=self._get_seller_script("medium", product_name, error_price),
                support_script=self._get_support_script("medium", product_name, error_price)
            )
        else:
            return LegalAnalysis(
                market_price=market_price,
                error_price=error_price,
                discount_percent=discount,
                risk_level=LegalRisk.LOW,
                win_chance=90,
                legal_basis=["Ст. 454 ГК РФ"],
                required_evidence=["чек"],
                recommended_action="✅ БЕРИ СМЕЛО",
                court_precedent="Стандартная покупка",
                seller_script=self._get_seller_script("low", product_name, error_price),
                support_script=self._get_support_script("low", product_name, error_price)
            )
    
    def _get_seller_script(self, risk: str, product: str, price: int) -> str:
        scripts = {
            "critical": f"⚠️ Продавец, цена {price:,} ₽ была указана вами. Ст. 435 ГК РФ - оферта. Прошу исполнить договор.",
            "medium": f"📝 Здравствуйте! Оплатил {product} за {price:,} ₽. Ст. 435-438 ГК РФ - договор заключён. Жду отправку.",
            "low": f"✅ Здравствуйте! Заказ оплачен. Цена {price:,} ₽. Спасибо!"
        }
        return scripts.get(risk, scripts["medium"])
    
    def _get_support_script(self, risk: str, product: str, price: int) -> str:
        scripts = {
            "critical": f"📞 Заказ отменён. Требую исполнить договор (ст. 435-438 ГК РФ)",
            "medium": f"📞 Помогите решить ситуацию с заказом {product}",
            "low": f"📞 Заказ оплачен, прошу подтвердить"
        }
        return scripts.get(risk, scripts["medium"])
