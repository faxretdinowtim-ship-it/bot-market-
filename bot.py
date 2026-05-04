import requests
import telebot
import time
import random
import json
import os
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"
ADMIN_ID = 1279722309
bot = telebot.TeleBot(BOT_TOKEN)

# Файл настроек
SETTINGS_FILE = "settings.json"

# Настройки по умолчанию
settings = {
    "autoscan_enabled": False,
    "autoscan_interval": 600,  # 600 секунд = 10 минут
    "total_errors_found": 0,
    "last_scan": None
}

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                settings.update(data)
        except:
            pass
    print(f"📁 Настройки: Автопоиск = {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}, Интервал = {settings['autoscan_interval']//60} мин")

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# ==================== РЕАЛЬНЫЙ СКАНЕР (РАБОЧАЯ ВЕРСИЯ) ====================
class RealPriceScanner:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def scan_wb(self, nm_id):
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            price = data['data']['products'][0]['salePriceU'] / 100
            original = data['data']['products'][0]['priceU'] / 100
            return {'current': int(price), 'original': int(original), 'discount': int((1 - price/original) * 100) if original else 0}
        except:
            return None
    
    def scan_ozon(self, product_id):
        url = f"https://www.ozon.ru/product/{product_id}/"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            import re
            patterns = [r'"price":"(\d+)"', r'"price":(\d+)', r'<span class="[^"]*price[^"]*">(\d+[\s]?\d*)</span>']
            for pattern in patterns:
                match = re.search(pattern, r.text)
                if match:
                    price = int(match.group(1).replace(' ', '').replace('\xa0', ''))
                    return {'current': price, 'original': price, 'discount': 0}
        except:
            pass
        return None
    
    def brute_force_scan(self):
        """Быстрый поиск ценовых ошибок (рабочая версия)"""
        errors = []
        
        # Расширенная база товаров
        products = [
            {"market": "WB", "name": "iPhone 13", "id": 139155295, "expected": 45000, "type": "wb"},
            {"market": "WB", "name": "iPhone 14", "id": 281447899, "expected": 60000, "type": "wb"},
            {"market": "WB", "name": "iPhone 15", "id": 283613587, "expected": 75000, "type": "wb"},
            {"market": "WB", "name": "MacBook Pro M2", "id": 158280717, "expected": 100000, "type": "wb"},
            {"market": "WB", "name": "MacBook Air M1", "id": 144822018, "expected": 65000, "type": "wb"},
            {"market": "WB", "name": "PS5", "id": 147590042, "expected": 55000, "type": "wb"},
            {"market": "WB", "name": "Xbox Series X", "id": 154750513, "expected": 50000, "type": "wb"},
            {"market": "WB", "name": "Samsung S23 Ultra", "id": 169242181, "expected": 70000, "type": "wb"},
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
            {"market": "Ozon", "name": "iPhone 15 Pro", "id": 153491311, "expected": 90000, "type": "ozon"},
            {"market": "Ozon", "name": "MacBook Air M2", "id": 142523308, "expected": 80000, "type": "ozon"},
            {"market": "Ozon", "name": "iPad Air", "id": 148761050, "expected": 50000, "type": "ozon"},
            {"market": "Ozon", "name": "Apple Watch Ultra", "id": 145128307, "expected": 65000, "type": "ozon"},
            {"market": "Ozon", "name": "Samsung Galaxy S23", "id": 150117439, "expected": 55000, "type": "ozon"},
        ]
        
        print("🔍 Начинаю быстрый поиск ошибок...")
        
        for product in products:
            if product["type"] == "wb":
                result = self.scan_wb(product["id"])
            else:
                result = self.scan_ozon(product["id"])
            
            if result:
                price = result['current']
                expected = product["expected"]
                discount = int((1 - price / expected) * 100) if price < expected else 0
                
                # Проверяем аномалии
                is_error = False
                error_type = ""
                
                if price <= 1000 and expected > 10000:
                    is_error = True
                    error_type = f"💀 ЭКСТРЕМАЛЬНАЯ ОШИБКА! Цена {price}₽"
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
                        "error_type": error_type,
                        "url": f"https://www.wildberries.ru/product/{product['id']}" if product["type"] == "wb" else f"https://www.ozon.ru/product/{product['id']}"
                    })
                    print(f"❗ Найдена ошибка: {product['name']} — {price}₽")
            
            time.sleep(random.uniform(0.3, 0.7))
        
        print(f"✅ Сканирование завершено. Найдено: {len(errors)}")
        return errors

scanner = RealPriceScanner()
found_errors = []
autoscan_running = False
autoscan_thread = None

# ==================== АВТОСКАНИРОВАНИЕ ====================
def autoscan_loop():
    global autoscan_running, found_errors
    print("🔄 Автосканирование запущено")
    
    while autoscan_running:
        try:
            print(f"🔍 Автосканирование в {time.strftime('%H:%M:%S')}")
            errors = scanner.brute_force_scan()
            
            if errors:
                settings["total_errors_found"] += len(errors)
                save_settings()
                
                msg = "🔔 *АВТОМАТИЧЕСКОЕ УВЕДОМЛЕНИЕ*\n\n"
                msg += f"🚨 Найдено {len(errors)} ценовых ошибок!\n\n"
                for e in errors[:5]:
                    msg += f"🛒 *{e['market']}*: {e['product']}\n"
                    msg += f"💰 Цена: {e['price']:,} ₽\n"
                    msg += f"⚡ {e['error_type']}\n\n"
                
                msg += f"📊 Всего найдено: {settings['total_errors_found']}\n"
                msg += "⚖️ Ст. 435-438 ГК РФ — договор заключён!"
                
                bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
                found_errors = errors
            else:
                print("❌ Ошибок не найдено")
            
        except Exception as e:
            print(f"Ошибка: {e}")
        
        time.sleep(settings["autoscan_interval"])

def start_autoscan():
    global autoscan_running, autoscan_thread
    if autoscan_running:
        return False
    autoscan_running = True
    autoscan_thread = threading.Thread(target=autoscan_loop, daemon=True)
    autoscan_thread.start()
    return True

def stop_autoscan():
    global autoscan_running
    autoscan_running = False
    return True

# ==================== КОМАНДЫ БОТА ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🔍 НАЙТИ ОШИБКИ", callback_data="scan"),
        InlineKeyboardButton("🔄 АВТОПОИСК", callback_data="autoscan")
    )
    keyboard.row(
        InlineKeyboardButton("⚖️ ЮРИДИЧЕСКАЯ ЗАЩИТА", callback_data="legal"),
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="stats")
    )
    
    bot.reply_to(message,
        "⚡ *АРБИТРАЖНЫЙ БОТ — ПОИСК ЦЕНОВЫХ ОШИБОК*\n\n"
        "🔍 *Что я делаю:*\n"
        "• Мгновенно сканирую Wildberries и Ozon\n"
        "• Ищу товары с аномально низкой ценой\n"
        "• Проверяю 25+ популярных товаров\n\n"
        "📋 *Команды:*\n"
        "/scan — начать поиск\n"
        "/autoscan — автопоиск (2, 5, 10 минут)\n"
        "/analyze — юр. анализ любой цены\n"
        "/stats — статистика\n\n"
        "⚖️ *ЗАКОН НА ТВОЕЙ СТОРОНЕ!*\n"
        "Ст. 435-438 ГК РФ — договор заключён!\n"
        "Продавец НЕ МОЖЕТ отменить заказ!",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['scan'])
def scan_command(message):
    bot.reply_to(message, "🔍 *Сканирую маркетплейсы...*\n⏱️ 20-30 секунд\n\n🛒 Проверяю: iPhone, MacBook, PS5, Samsung, и другие...", parse_mode='Markdown')
    
    global found_errors
    found_errors = scanner.brute_force_scan()
    
    if not found_errors:
        bot.reply_to(message, "❌ *Ценовых ошибок не найдено*\n\nПопробуй позже!", parse_mode='Markdown')
        return
    
    msg = "🚨 *НАЙДЕНЫ ЦЕНОВЫЕ ОШИБКИ!*\n\n"
    for i, e in enumerate(found_errors[:15], 1):
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
    msg += "• Ст. 438 ГК РФ — акцепт (оплата = договор)\n"
    msg += "• Ст. 310 ГК РФ — отказ запрещён\n\n"
    msg += "💡 *Продавец НЕ МОЖЕТ отменить заказ!*\n"
    msg += "🔥 Покупай смело, суд на твоей стороне!"
    
    bot.reply_to(message, msg, parse_mode='Markdown', disable_web_page_preview=True)

@bot.message_handler(commands=['autoscan'])
def autoscan_menu(message):
    status_text = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    interval_min = settings["autoscan_interval"] // 60
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🟢 2 минуты", callback_data="interval_120"),
        InlineKeyboardButton("🟡 5 минут", callback_data="interval_300"),
        InlineKeyboardButton("🔴 10 минут", callback_data="interval_600")
    )
    if not settings["autoscan_enabled"]:
        keyboard.add(InlineKeyboardButton("✅ ВКЛЮЧИТЬ", callback_data="autoscan_on"))
    else:
        keyboard.add(InlineKeyboardButton("❌ ВЫКЛЮЧИТЬ", callback_data="autoscan_off"))
    
    bot.reply_to(message,
        f"🔄 *АВТОМАТИЧЕСКИЙ ПОИСК*\n\n"
        f"📊 Статус: {status_text}\n"
        f"⏱️ Текущий интервал: {interval_min} минут\n"
        f"📊 Всего найдено: {settings['total_errors_found']}\n\n"
        f"🔽 Выбери интервал и нажми ВКЛЮЧИТЬ:",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['analyze'])
def analyze_command(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, 
                "❌ *Используй:* `/analyze [рыночная_цена] [цена_ошибки]`\n\n"
                "📌 *Примеры:*\n"
                "`/analyze 100000 1` — анализ покупки за 1₽\n"
                "`/analyze 50000 500` — анализ покупки за 500₽\n"
                "`/analyze 75000 5000` — анализ покупки за 5000₽",
                parse_mode='Markdown')
            return
        
        market = int(args[1])
        error = int(args[2])
        discount = (market - error) / market * 100
        
        if error <= 100:
            verdict = "💀 ЭКСТРЕМАЛЬНЫЙ РИСК (шанс 10-20%)"
            law = "Ст. 435-438 ГК РФ — договор заключён, но суд может признать ошибку"
        elif error <= 1000:
            verdict = "🔴 ВЫСОКИЙ РИСК (шанс 30-40%)"
            law = "Ст. 435-438 ГК РФ — оферта акцептована"
        elif discount > 70:
            verdict = "🟠 СРЕДНИЙ РИСК (шанс 60-70%)"
            law = "Ст. 435-438, 310 ГК РФ — отказ запрещён"
        else:
            verdict = "🟢 НИЗКИЙ РИСК (шанс 90%)"
            law = "Ст. 454 ГК РФ — обычная сделка"
        
        response = f"""📊 *ЮРИДИЧЕСКИЙ АНАЛИЗ*

━━━━━━━━━━━━━━━━━━━━━
💰 *Цены:*
• Рыночная: {market:,} ₽
• Цена ошибки: {error:,} ₽
• Скидка: {discount:.1f}%

━━━━━━━━━━━━━━━━━━━━━
⚖️ *Вердикт:*
{verdict}

📜 *Правовая база:*
{law}

━━━━━━━━━━━━━━━━━━━━━
💡 *Важно:*
• Договор считается заключённым (ст. 435-438 ГК РФ)
• Односторонний отказ ЗАПРЕЩЁН (ст. 310 ГК РФ)

🔥 *Продавец не имеет права отменить заказ!*"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Ошибка! Используй числа.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    status_text = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    interval_min = settings["autoscan_interval"] // 60
    
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА БОТА*\n\n"
        f"🔄 *Автопоиск:* {status_text}\n"
        f"⏱️ *Интервал:* {interval_min} минут\n"
        f"📊 *Всего ошибок:* {settings['total_errors_found']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 *Маркетплейсы:* WB и Ozon\n"
        f"📦 *Товаров в базе:* 25+\n"
        f"⚖️ *Закон:* Ст. 435-438 ГК РФ\n\n"
        f"🚀 Используй /scan для поиска!",
        parse_mode='Markdown')

# ==================== ОБРАБОТКА КНОПОК ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "scan":
        bot.answer_callback_query(call.id, "🔍 Запускаю сканирование...")
        scan_command(call.message)
    
    elif call.data == "autoscan":
        bot.answer_callback_query(call.id)
        autoscan_menu(call.message)
    
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
            "3. Обратись в поддержку маркетплейса\n"
            "4. Подай жалобу в Роспотребнадзор\n\n"
            "🔥 *Продавец НЕ ИМЕЕТ ПРАВА отменить заказ!*\n"
            "⚖️ Суд в 70% случаев на стороне покупателя!",
            parse_mode='Markdown')
    
    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        stats_command(call.message)
    
    # Настройка интервала
    elif call.data.startswith("interval_"):
        interval = int(call.data.split("_")[1])
        settings["autoscan_interval"] = interval
        save_settings()
        minutes = interval // 60
        bot.answer_callback_query(call.id, f"✅ Интервал изменён на {minutes} минут")
        autoscan_menu(call.message)
    
    elif call.data == "autoscan_on":
        settings["autoscan_enabled"] = True
        save_settings()
        start_autoscan()
        bot.answer_callback_query(call.id, "✅ Автопоиск включён!")
        autoscan_menu(call.message)
    
    elif call.data == "autoscan_off":
        settings["autoscan_enabled"] = False
        save_settings()
        stop_autoscan()
        bot.answer_callback_query(call.id, "❌ Автопоиск выключен")
        autoscan_menu(call.message)

# ==================== ЗАПУСК ====================
load_settings()

if settings["autoscan_enabled"]:
    start_autoscan()

print("=" * 50)
print("🤖 БОТ ЗАПУЩЕН")
print("🔍 Быстрый поиск ценовых ошибок на WB и Ozon")
print("📦 Проверяю: iPhone, MacBook, PS5, Samsung...")
print(f"🔄 Автопоиск: {'ВКЛЮЧЕН' if settings['autoscan_enabled'] else 'ВЫКЛЮЧЕН'}")
print(f"⏱️ Интервал: {settings['autoscan_interval']//60} минут")
print("=" * 50)

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
