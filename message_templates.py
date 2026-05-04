# message_templates.py

class MessageTemplates:
    """Шаблоны сообщений"""
    
    @staticmethod
    def get_full_legal_notice(product: str, price: int, market_price: int, order_id: str = "НОМЕР") -> str:
        discount = int((1 - price / market_price) * 100)
        
        return f"""
⚖️ ЮРИДИЧЕСКОЕ УВЕДОМЛЕНИЕ

Товар: {product}
Цена: {price:,} ₽
Рынок: {market_price:,} ₽
Скидка: {discount}%

В соответствии со ст. 435-438, 310 ГК РФ:

1. Размещение товара с ценой = публичная оферта
2. Оплата = акцепт (договор заключён)
3. Односторонний отказ = НЕДОПУСТИМ

Требую исполнить договор купли-продажи.

Заказ №{order_id}
"""
    
    @staticmethod
    def get_support_message(product: str, price: int) -> str:
        return f"""
📞 ОБРАЩЕНИЕ В ПОДДЕРЖКУ

Заказ: {product}
Цена: {price:,} ₽

Продавец отменяет заказ, ссылаясь на ошибку.

Моя позиция: ст. 435-438 ГК РФ - договор заключён с момента оплаты.

Прошу разобраться.
"""
    
    @staticmethod
    def get_judge_argument(product: str, price: int, market_price: int) -> str:
        return f"""
⚖️ АРГУМЕНТ ДЛЯ СУДЬИ:

Покупатель действовал добросовестно.
Цена {price:,} ₽ (скидка {(1-price/market_price)*100:.0f}%) 
возможна при распродаже/уценке.

Согласно ст. 435-438 ГК РФ, договор заключён.
Прошу обязать ответчика исполнить обязательства.
"""
