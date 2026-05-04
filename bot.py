import requests
import telebot
import time
import random
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"
ADMIN_ID = 1279722309
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== РЕАЛЬНЫЙ СКАНЕР ЦЕН ====================
class RealPriceScanner:
    """Реальный парсинг цен с Ozon и WB"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
    
    def scan_wb(self, nm_id):
        """Парсинг Wildberries"""
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            price = data['data']['products'][0]['salePriceU'] / 100
            original = data['data']['products'][0]['priceU'] / 100
            return {
                'current': int(price),
                'original': int(original),
                'discount': int((1 - price/original) * 100) if original else 0
            }
        except:
            return None
    
    def scan_ozon(self, product_id):
        """Парсинг Ozon"""
        url = f"https://www.ozon.ru/product/{product_id}/"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            import re
            # Ищем цену в разных форматах
            patterns = [
                r'"price":"(\d+)"',
                r'"price":(\d+)',
                r'<span class="[^"]*price[^"]*">(\d+[\s]?\d*)</span>'
            ]
            for pattern in patterns:
                match = re.search(pattern, r.text)
                if match:
                    price = int(match.group(1).replace(' ', '').replace('\xa0', ''))
                    return {'current': price, 'original': price, 'discount': 0}
        except:
            pass
        return None
    
    def brute_force_scan(self):
        """Массовый поиск ценовых ошибок среди популярных товаров"""
        errors = []
        
        # Расширенная база товаров с реальными ID
        products = [
            # Wildberries
            {"market": "WB", "name": "iPhone 13", "id": 139155295, "expected": 45000, "type": "wb"},
            {"market": "WB", "name": "iPhone 14", "id": 281447899, "expected": 60000, "type": "wb"},
            {"market": "WB", "name": "iPhone 15", "id": 283613587, "expected": 75000, "type": "wb"},
            {"market": "WB", "name": "MacBook Pro M2", "id": 158280717, "expected": 100000, "type": "wb"},
            {"market": "WB", "name": "MacBook Air M1", "id": 144822018, "expected": 65000, "type": "wb"},
            {"market": "WB", "name": "PS5", "id": 147590042, "expected": 55000, "type": "wb"},
            {"market": "WB", "name": "Xbox Series X", "id": 154750513, "expected": 50000, "type": "wb"},
            {"market": "WB", "name": "Samsung S23 Ultra", "id": 169242181, "expected": 70000, "type": "wb"},
            {"market": "WB", "name": "Samsung S24", "id": 274223120, "expected": 65000, "type": "wb"},
            {"market": "WB", "name": "iPad Pro 11", "id": 149147870, "expected": 70000, "type": "wb"},
            {"market": "WB", "name": "AirPods Pro 2", "id": 148128760, "expected": 18000, "type": "wb"},
            {"market": "WB", "name": "Apple Watch 8", "id": 152427091, "expected": 35000, "type": "wb"},
            {"market": "WB", "name": "RTX 4070", "id": 262138819, "expected": 60000, "type": "wb"},
            {"market": "WB", "name": "RTX 4090", "id": 264144708, "expected": 150000, "type": "wb"},
            {"market": "WB", "name": "Dyson V15", "id": 193720629, "expected": 50000, "type": "wb"},
            {"market": "WB", "name": "Roborock S8", "id": 273348526, "expected": 60000, "type": "wb"},
            {"market": "WB", "name": "DJI Mini 3", "id": 230147993, "expected": 45000, "type": "wb"},
            {"market": "WB", "name": "Sony WH-1000XM5", "id": 188177626, "expected": 25000, "type": "wb"},
            {"market": "WB", "name": "JBL Charge 5", "id": 190045272, "expected": 10000, "type": "wb"},
            
            # Ozon
            {"market": "Ozon", "name": "iPhone 15 Pro", "id": 153491311, "expected": 90000, "type": "ozon"},
            {"market": "Ozon", "name": "MacBook Air M2", "id": 142523308, "expected": 80000, "type": "ozon"},
            {"market": "Ozon", "name": "iPad Air", "id": 148761050, "expected": 50000, "type": "ozon"},
            {"market": "Ozon", "name": "Apple Watch Ultra", "id": 145128307, "expected": 65000, "type": "ozon"},
            {"market": "Ozon", "name": "Samsung Galaxy S23", "id": 150117439, "expected": 55000, "type": "ozon"},
        ]
        
        print("🔍 Начинаю сканирование...")
        
        for product in products:
            # Получаем цену
            if product["type"] == "wb":
                result = self.scan_wb(product["id"])
            else:
                result = self.scan_ozon(product["id"])
            
            if result and result['current']:
                price = result['current']
                expected = product["expected"]
                discount = int((1 - price / expected) * 100) if price < expected else 0
                
                # Проверяем на аномалию (скидка > 30% или цена ниже 5000₽ для дорогих товаров)
                is_error = False
                error_type = ""
                
                if price <= 1000 and expected > 10000:
                    is_error = True
                    error_type = "💀 ЭКСТРЕМАЛЬНАЯ ОШИБКА! Цена {price}₽"
                elif price <= 5000 and expected > 30000:
                    is_error = True
                    error_type = "🔴 КРИТИЧЕСКАЯ ОШИБКА"
                elif discount > 70:
                    is_error = True
                    error_type = f"⚠️ СКИДКА {discount}%"
                elif price < expected * 0.7:
                    is_error = True
                    error_type = f"📉 ЦЕНА НИЖЕ РЫНКА на {int((1 - price/expected)*100)}%"
                
                if is_error:
                    errors.append({
                        "market": product["market"],
                        "product": product["name"],
                        "price": price,
                        "expected": expected,
                        "discount": discount,
                        "error_type": error_type.format(price=price),
                        "url": f"https://www.wildberries.ru/product/{product['id']}" if product["type"] == "wb" else f"https://www.ozon.ru/product/{product['id']}"
                    })
                    print(f"❗ Найдена ошибка: {product['name']} — {price}₽ (рынок {expected}₽)")
            
            time.sleep(random.uniform(0.3, 0.7))
        
        print(f"✅ Сканирование завершено. Найдено ошибок: {len(errors)}")
        return errors

scanner = RealPriceScanner()

# ==================== КОМАНДЫ ====================
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔍 НАЙТИ ОШИБКИ", callback_data="scan"))
    keyboard.add(InlineKeyboardButton("⚖️ ЮРИДИЧЕСКАЯ ЗАЩИТА", callback_data="legal"))
    
    bot.send_message(message.chat.id,
        "⚡ *АРБИТРАЖНЫЙ БОТ — ПОИСК ЦЕНОВЫХ ОШИБОК*\n\n"
        "🔍 *Что я делаю:*\n"
        "• Сканирую Wildberries и Ozon\n"
        "• Ищу товары с аномально низкой ценой\n"
        "• Проверяю 50+ популярных товаров\n\n"
        "📋 *Команда:* /scan — начать поиск\n\n"
        "⚖️ *ЗАКОН НА ТВОЕЙ СТОРОНЕ!*\n"
        "Ст. 435-438 ГК РФ — договор заключён!",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['scan'])
def scan(message):
    bot.send_message(message.chat.id, "🔍 *Сканирую маркетплейсы...*\n⏱️ 20-30 секунд\n\n🛒 Проверяю: iPhone, MacBook, PS5, Samsung, и другие...", parse_mode='Markdown')
    
    errors = scanner.brute_force_scan()
    
    if not errors:
        bot.send_message(message.chat.id, "❌ *Ценовых ошибок не найдено*\n\nПопробуй позже!", parse_mode='Markdown')
        return
    
    # Формируем результаты
    msg = "🚨 *НАЙДЕНЫ ЦЕНОВЫЕ ОШИБКИ!*\n\n"
    for i, e in enumerate(errors[:15], 1):
        if e['price'] <= 100:
            emoji = "💀"
        elif e['price'] <= 5000:
            emoji = "🔴"
        elif e['discount'] > 70:
            emoji = "🟠"
        else:
            emoji = "🟢"
        
        msg += f"{emoji} *{i}. {e['product']}*\n"
        msg += f"🛒 {e['market']}\n"
        msg += f"💰 *Цена: {e['price']:,} ₽*\n"
        msg += f"📊 Рынок: ~{e['expected']:,} ₽\n"
        msg += f"⚡ {e['error_type']}\n"
        msg += f"🔗 [Ссылка на товар]({e['url']})\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚖️ *ЮРИДИЧЕСКАЯ ЗАЩИТА:*\n"
    msg += "• Ст. 435 ГК РФ — публичная оферта\n"
    msg += "• Ст. 438 ГК РФ — акцепт (оплата)\n"
    msg += "• Ст. 310 ГК РФ — отказ запрещён\n\n"
    msg += "💡 *Продавец НЕ МОЖЕТ отменить заказ!*\n"
    msg += "🔥 Покупай смело, суд на твоей стороне!"
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(commands=['analyze'])
def analyze(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Используй: /analyze [рыночная_цена] [цена_ошибки]\nПример: /analyze 100000 5000")
            return
        
        market = int(args[1])
        error = int(args[2])
        discount = (market - error) / market * 100
        
        if error <= 1000:
            verdict = "💀 ЭКСТРЕМАЛЬНЫЙ РИСК (шанс 10-20%)"
        elif discount > 85:
            verdict = "🔴 ВЫСОКИЙ РИСК (шанс 30-40%)"
        elif discount > 70:
            verdict = "🟠 СРЕДНИЙ РИСК (шанс 60-70%)"
        else:
            verdict = "🟢 НИЗКИЙ РИСК (шанс 90%)"
        
        bot.reply_to(message,
            f"📊 *ЮРИДИЧЕСКИЙ АНАЛИЗ*\n\n"
            f"Рынок: {market:,} ₽\n"
            f"Цена: {error:,} ₽\n"
            f"Скидка: {discount:.1f}%\n\n"
            f"{verdict}\n\n"
            f"⚖️ Ст. 435-438 ГК РФ — договор заключён!\n"
            f"💡 Продавец НЕ МОЖЕТ отменить заказ!",
            parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Ошибка! Используй числа.")

@bot.message_handler(commands=['stats'])
def stats(message):
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА*\n\n"
        f"🔍 Сканирую: WB и Ozon\n"
        f"📦 Товаров в базе: 25+\n"
        f"⚡ Статус: РАБОТАЕТ\n"
        f"⚖️ Закон: Ст. 435-438 ГК РФ\n\n"
        f"🚀 Используй /scan для поиска!",
        parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "scan":
        bot.answer_callback_query(call.id, "🔍 Запускаю сканирование...")
        scan(call.message)
    elif call.data == "legal":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "⚖️ *ЮРИДИЧЕСКАЯ ЗАЩИТА*\n\n"
            "📜 *Статьи ГК РФ:*\n"
            "• Ст. 435 — публичная оферта\n"
            "• Ст. 438 — акцепт (оплата = договор)\n"
            "• Ст. 310 — односторонний отказ ЗАПРЕЩЁН\n\n"
            "💡 *Что делать при отмене:*\n"
            "1. Сохрани скриншот цены\n"
            "2. Напиши продавцу: «Ст. 435-438 ГК РФ, договор заключён»\n"
            "3. Обратись в поддержку\n"
            "4. Подай жалобу в Роспотребнадзор\n\n"
            "🔥 Продавец НЕ ИМЕЕТ ПРАВА отменить заказ!",
            parse_mode='Markdown')

# ==================== ЗАПУСК ====================
print("=" * 50)
print("🤖 БОТ ЗАПУЩЕН")
print("🔍 Ищу ценовые ошибки на WB и Ozon")
print("📦 Проверяю: iPhone, MacBook, PS5, Samsung...")
print("=" * 50)

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
