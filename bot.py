import threading
import requests
import time
import json
import os
import re
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== НАСТРОЙКИ ПОРТА ДЛЯ RENDER ====================
PORT = int(os.environ.get("PORT", 10000))

# ==================== FLASK ДЛЯ ВЕБ-СТРАНИЦЫ ====================
web_app = Flask(__name__)

@web_app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Legal Arbitrage Bot</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial; background: #0a0e27; color: #fff; text-align: center; padding: 50px; }
            h1 { color: #00ff88; }
            .status { color: #00ff88; }
            a { color: #00ff88; }
        </style>
    </head>
    <body>
        <h1>⚖️ Legal Arbitrage Bot</h1>
        <p>Статус: <span class="status">✅ БОТ РАБОТАЕТ</span></p>
        <p>Telegram: <a href="https://t.me/legal_arbitrage_bot">@legal_arbitrage_bot</a></p>
        <hr>
        <p>📋 Команды: /start, /scan, /autoscan, /analyze, /stats</p>
        <p>🛒 Ищу: 1₽, 10₽, 50₽, 100₽, 500₽ и любые аномалии на WB и Ozon</p>
        <p>⚖️ Ст. 435-438 ГК РФ — договор заключён! Продавец НЕ МОЖЕТ отменить заказ!</p>
    </body>
    </html>
    '''

@web_app.route('/health')
def health():
    return {"status": "ok"}

def run_flask():
    web_app.run(host='0.0.0.0', port=PORT, debug=False)

threading.Thread(target=run_flask, daemon=True).start()
print(f"🌐 Flask запущен на порту {PORT}")

# ==================== TELEGRAM БОТ ====================
BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"
ADMIN_ID = 1279722309
bot = telebot.TeleBot(BOT_TOKEN)

# Файл для хранения настроек
SETTINGS_FILE = "settings.json"

settings = {
    "autoscan_enabled": False,
    "autoscan_interval": 600,
    "total_errors_found": 0
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
    print(f"📁 Настройки: Автосканирование = {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}")

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# ==================== СКАНЕР ЭКСТРЕМАЛЬНЫХ ЦЕН ====================
class ExtremePriceScanner:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def scan_wb(self, nm_id):
        """Сканирование Wildberries"""
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            price = data['data']['products'][0]['salePriceU'] / 100
            return int(price)
        except Exception as e:
            print(f"WB error {nm_id}: {e}")
            return None
    
    def scan_ozon(self, product_id):
        """Сканирование Ozon"""
        url = f"https://www.ozon.ru/product/{product_id}/"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            match = re.search(r'"price":"(\d+)"', resp.text)
            if match:
                return int(match.group(1))
        except Exception as e:
            print(f"Ozon error {product_id}: {e}")
        return None
    
    def find_extreme_errors(self):
        """Поиск экстремальных цен (1₽, 10₽, 50₽ и т.д.)"""
        errors = []
        
        # Товары для проверки
        targets = [
            {"market": "WB", "name": "iPhone 13", "id": 139155295, "real_price": 75000, "type": "wb"},
            {"market": "WB", "name": "iPhone 14", "id": 281447899, "real_price": 65000, "type": "wb"},
            {"market": "WB", "name": "MacBook Pro", "id": 158280717, "real_price": 100000, "type": "wb"},
            {"market": "WB", "name": "PS5", "id": 147590042, "real_price": 55000, "type": "wb"},
            {"market": "WB", "name": "Samsung S23", "id": 169242181, "real_price": 70000, "type": "wb"},
            {"market": "WB", "name": "iPad Pro", "id": 149147870, "real_price": 80000, "type": "wb"},
            {"market": "Ozon", "name": "iPhone 15", "id": 153491311, "real_price": 80000, "type": "ozon"},
            {"market": "Ozon", "name": "MacBook Air", "id": 142523308, "real_price": 65000, "type": "ozon"},
            {"market": "Ozon", "name": "Apple Watch", "id": 148761050, "real_price": 55000, "type": "ozon"},
            {"market": "Ozon", "name": "AirPods Pro", "id": 145128307, "real_price": 20000, "type": "ozon"},
        ]
        
        extreme_prices = [1, 10, 50, 100, 500, 1000, 2000, 3000, 5000]
        
        for t in targets:
            if t["type"] == "wb":
                price = self.scan_wb(t["id"])
            else:
                price = self.scan_ozon(t["id"])
            
            if price:
                # Проверяем, является ли цена экстремальной
                is_extreme = False
                extreme_type = ""
                
                if price in extreme_prices:
                    is_extreme = True
                    extreme_type = f"💀 ЭКСТРЕМАЛЬНАЯ ОШИБКА! Цена {price}₽"
                elif price < t["real_price"] * 0.05:
                    is_extreme = True
                    extreme_type = f"🔴 КРИТИЧЕСКАЯ ОШИБКА! Скидка {int((1 - price/t['real_price'])*100)}%"
                elif price < t["real_price"] * 0.3:
                    is_extreme = True
                    extreme_type = f"⚠️ БОЛЬШАЯ СКИДКА {int((1 - price/t['real_price'])*100)}%"
                
                if is_extreme:
                    errors.append({
                        "market": t["market"],
                        "product": t["name"],
                        "price": price,
                        "expected": t["real_price"],
                        "discount": int((1 - price/t["real_price"]) * 100),
                        "extreme_type": extreme_type,
                        "url": f"https://www.wildberries.ru/product/{t['id']}" if t["type"] == "wb" else f"https://www.ozon.ru/product/{t['id']}"
                    })
            
            time.sleep(0.5)
        
        return errors

scanner = ExtremePriceScanner()
found_errors = []
autoscan_running = False
autoscan_thread = None

# ==================== АВТОСКАНИРОВАНИЕ ====================
def autoscan_loop():
    global autoscan_running, found_errors
    print("🔄 Поток автосканирования запущен")
    
    while autoscan_running:
        try:
            print(f"🔍 Автосканирование в {time.strftime('%H:%M:%S')}")
            errors = scanner.find_extreme_errors()
            
            if errors:
                settings["total_errors_found"] += len(errors)
                save_settings()
                
                msg = "🔔 *АВТОМАТИЧЕСКОЕ УВЕДОМЛЕНИЕ*\n\n"
                msg += f"🚨 Найдено {len(errors)} ЦЕНОВЫХ ОШИБОК!\n\n"
                for e in errors[:5]:
                    msg += f"🛒 *{e['market']}*: {e['product']}\n"
                    msg += f"{e['extreme_type']}\n"
                    msg += f"💰 Цена: {e['price']:,} ₽\n"
                    msg += f"📊 Рыночная: {e['expected']:,} ₽\n"
                    msg += f"⚡ Скидка: {e['discount']}%\n\n"
                
                msg += "━━━━━━━━━━━━━━━━━━━━━\n"
                msg += "⚖️ Ст. 435-438 ГК РФ — договор заключён!\n"
                msg += "💡 Продавец НЕ МОЖЕТ отменить заказ!"
                
                bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
                found_errors = errors
            else:
                print("❌ Экстремальных ошибок не найдено")
            
        except Exception as e:
            print(f"Ошибка автосканирования: {e}")
        
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
        InlineKeyboardButton("🔍 Найти ошибки", callback_data="scan_now"),
        InlineKeyboardButton("🔄 Автопоиск", callback_data="autoscan_menu")
    )
    keyboard.row(
        InlineKeyboardButton("⚖️ Анализ цены", callback_data="analyze"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats")
    )
    
    bot.reply_to(message, 
        "⚖️ *LEGAL ARBITRAGE BOT*\n\n"
        "🔍 *Что я умею:*\n"
        "✅ Искать товары по сумасшедшим ценам (1₽, 10₽, 50₽, 100₽ и т.д.)\n"
        "✅ Находить ошибки с любой ценой (хоть 1 рубль!)\n"
        "✅ Юридически защищать твою покупку\n\n"
        "📋 *Команды:*\n"
        "/scan - найти все ценовые ошибки\n"
        "/autoscan - включить автопоиск каждые 10 минут\n"
        "/analyze [цена1] [цена2] - юр. анализ\n"
        "/stats - статистика\n\n"
        "⚖️ *ЗАКОН НА ТВОЕЙ СТОРОНЕ!*\n"
        "Ст. 435-438 ГК РФ — договор заключён с момента оплаты!\n"
        "Продавец НЕ ИМЕЕТ ПРАВА отменить заказ!",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['autoscan'])
def autoscan_menu(message):
    status_text = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    
    keyboard = InlineKeyboardMarkup()
    if not settings["autoscan_enabled"]:
        keyboard.add(InlineKeyboardButton("✅ ВКЛЮЧИТЬ автопоиск", callback_data="autoscan_on"))
    else:
        keyboard.add(InlineKeyboardButton("❌ ВЫКЛЮЧИТЬ автопоиск", callback_data="autoscan_off"))
    
    bot.reply_to(message,
        f"🔄 *АВТОМАТИЧЕСКИЙ ПОИСК ЭКСТРЕМАЛЬНЫХ ЦЕН*\n\n"
        f"📊 Статус: {status_text}\n"
        f"⏱️ Интервал: 10 минут\n"
        f"🔍 Ищу: 1₽, 10₽, 50₽, 100₽, 500₽ и любые аномалии\n"
        f"📊 Всего найдено ошибок: {settings['total_errors_found']}\n\n"
        f"При включении бот будет САМ искать ошибки\n"
        f"и присылать уведомления в этот чат!",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['scan'])
def scan_command(message):
    bot.reply_to(message, 
        "🔍 *Сканирую экстремальные цены...*\n"
        "⏱️ Это займёт 30-40 секунд\n\n"
        "🛒 Проверяю: WB и Ozon\n\n"
        "💰 Ищу цены: 1₽, 10₽, 50₽, 100₽, 500₽\n"
        "📊 Любые аномалии со скидкой >70%",
        parse_mode='Markdown')
    
    global found_errors
    found_errors = scanner.find_extreme_errors()
    
    if not found_errors:
        bot.reply_to(message, 
            "❌ *Экстремальных ценовых ошибок не найдено*\n\n"
            "Попробуй позже! Автопоиск будет искать каждые 10 минут.",
            parse_mode='Markdown')
        return
    
    # Формируем отчёт
    msg = "🚨 *НАЙДЕНЫ ЭКСТРЕМАЛЬНЫЕ ЦЕНОВЫЕ ОШИБКИ!*\n\n"
    
    for e in found_errors[:10]:
        if e['price'] <= 100:
            emoji = "💀"
        elif e['price'] <= 500:
            emoji = "🔴"
        elif e['discount'] > 90:
            emoji = "🟠"
        else:
            emoji = "🟡"
        
        msg += f"{emoji} *{e['product']}*\n"
        msg += f"🛒 {e['market']}\n"
        msg += f"💰 *Цена: {e['price']:,} ₽*\n"
        msg += f"📊 Рыночная: ~{e['expected']:,} ₽\n"
        msg += f"⚡ Скидка: {e['discount']}%\n"
        msg += f"⚠️ {e['extreme_type']}\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚖️ *ЮРИДИЧЕСКАЯ ЗАЩИТА:*\n"
    msg += "• Ст. 435 ГК РФ — публичная оферта\n"
    msg += "• Ст. 438 ГК РФ — акцепт (оплата = договор)\n"
    msg += "• Ст. 310 ГК РФ — односторонний отказ ЗАПРЕЩЁН\n\n"
    msg += "💡 Продавец НЕ МОЖЕТ отменить заказ по закону!"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['analyze'])
def analyze_command(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, 
                "❌ *Используй:* `/analyze [рыночная_цена] [цена_ошибки]`\n\n"
                "📌 *Примеры:*\n"
                "`/analyze 100000 1` — анализ покупки за 1₽\n"
                "`/analyze 50000 50` — анализ покупки за 50₽\n"
                "`/analyze 75000 500` — анализ покупки за 500₽",
                parse_mode='Markdown')
            return
        
        market = int(args[1])
        error = int(args[2])
        discount = (market - error) / market * 100
        
        # Юридический анализ для любой цены
        if error <= 50:
            verdict = "💀 ЭКСТРЕМАЛЬНЫЙ РИСК (шанс 5-10%)"
            law = "Ст. 435-438 ГК РФ — договор заключён"
        elif error <= 500:
            verdict = "🔴 ВЫСОКИЙ РИСК (шанс 20-30%)"
            law = "Ст. 435-438 ГК РФ — оферта акцептована"
        elif discount > 70:
            verdict = "🟠 СРЕДНИЙ РИСК (шанс 60-70%)"
            law = "Ст. 435-438, 310 ГК РФ"
        else:
            verdict = "🟢 НИЗКИЙ РИСК (шанс 90%)"
            law = "Ст. 454 ГК РФ — обычная сделка"
        
        response = f"""📊 *ЮРИДИЧЕСКИЙ АНАЛИЗ ЭКСТРЕМАЛЬНОЙ ЦЕНЫ*

━━━━━━━━━━━━━━━━━━━━━
💰 *Цены:*
• Рыночная: {market:,} ₽
• Ваша цена: {error:,} ₽
• Скидка: {discount:.1f}%

━━━━━━━━━━━━━━━━━━━━━
⚖️ *Юридическая оценка:*
{verdict}

📜 *Правовая база:*
{law}

━━━━━━━━━━━━━━━━━━━━━
💡 *ВАЖНО:* 
• Договор считается заключённым (ст. 435-438 ГК РФ)
• Односторонний отказ ЗАПРЕЩЁН (ст. 310 ГК РФ)
• Скриншоты и чек — главное доказательство

🔥 *Продавец не имеет права отменить заказ!*"""
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    status_text = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА ЭКСТРЕМАЛЬНЫХ ЦЕН*\n\n"
        f"🔄 *Автопоиск:* {status_text}\n"
        f"⏱️ Интервал: 10 минут\n"
        f"📊 Всего ошибок: {settings['total_errors_found']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 Маркетплейсы: WB и Ozon\n"
        f"💰 Ищу: 1₽, 10₽, 50₽, 100₽, 500₽\n"
        f"⚖️ Закон: Ст. 435-438 ГК РФ\n\n"
        f"🚀 Используй /scan для поиска ошибок от 1₽!",
        parse_mode='Markdown')

# ==================== ОБРАБОТКА КНОПОК ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "scan_now":
        bot.answer_callback_query(call.id, "🔍 Запускаю сканирование...")
        scan_command(call.message)
    
    elif call.data == "autoscan_menu":
        bot.answer_callback_query(call.id)
        autoscan_menu(call.message)
    
    elif call.data == "autoscan_on":
        settings["autoscan_enabled"] = True
        save_settings()
        start_autoscan()
        bot.answer_callback_query(call.id, "✅ Автопоиск включён! Буду искать каждые 10 минут")
        autoscan_menu(call.message)
    
    elif call.data == "autoscan_off":
        settings["autoscan_enabled"] = False
        save_settings()
        stop_autoscan()
        bot.answer_callback_query(call.id, "❌ Автопоиск выключен")
        autoscan_menu(call.message)
    
    elif call.data == "analyze":
        bot.answer_callback_query(call.id)
        bot.reply_to(call.message, 
            "📊 *Юридический анализ цены*\n\n"
            "Используй команду:\n"
            "`/analyze [рыночная_цена] [цена_ошибки]`\n\n"
            "Пример: `/analyze 100000 1` — анализ покупки за 1₽",
            parse_mode='Markdown')
    
    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        stats_command(call.message)

# ==================== ЗАПУСК ====================
load_settings()

if settings["autoscan_enabled"]:
    start_autoscan()

print("=" * 50)
print("🤖 TELEGRAM БОТ ЗАПУЩЕН")
print("⚖️ Legal Arbitrage Bot — ПОИСК ЭКСТРЕМАЛЬНЫХ ЦЕН")
print("🛒 Сканирую: WB, Ozon")
print("💰 Ищу: 1₽, 10₽, 50₽, 100₽, 500₽ и любые аномалии")
print(f"🔄 Автопоиск: {'ВКЛЮЧЕН' if settings['autoscan_enabled'] else 'ВЫКЛЮЧЕН'}")
print("=" * 50)

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
