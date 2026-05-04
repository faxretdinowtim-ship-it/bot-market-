import threading
import requests
import time
import re
import json
import os
from flask import Flask
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== FLASK ДЛЯ RENDER ====================
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
        <p>🛒 Сканирую: WB | Ozon | Avito | Яндекс.Маркет | DNS</p>
        <p>⚖️ Ст. 435-438 ГК РФ — договор заключён!</p>
    </body>
    </html>
    '''

@web_app.route('/health')
def health():
    return {"status": "ok"}

def run_flask():
    web_app.run(host='0.0.0.0', port=10000, debug=False)

threading.Thread(target=run_flask, daemon=True).start()
print("🌐 Flask запущен на порту 10000")

# ==================== TELEGRAM БОТ ====================
BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"
bot = telebot.TeleBot(BOT_TOKEN)

# Файл для хранения настроек
SETTINGS_FILE = "settings.json"

# Настройки по умолчанию
settings = {
    "autoscan_enabled": False,
    "autoscan_interval": 600,
    "last_scan": None,
    "total_errors_found": 0
}

def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings.update(json.load(f))
        except:
            pass
    print(f"📁 Настройки: Автосканирование = {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}")

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

# ==================== СКАНЕР ЦЕН ====================
class PriceScanner:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def scan_wb(self, nm_id):
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            return int(data['data']['products'][0]['salePriceU'] / 100)
        except:
            return None
    
    def scan_ozon(self, product_id):
        url = f"https://www.ozon.ru/product/{product_id}/"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            match = re.search(r'"price":"(\d+)"', resp.text)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def scan_avito(self, query, max_price=20000):
        url = f"https://www.avito.ru/moskva?q={query}&p=1"
        results = []
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('div', {'data-marker': 'item'})
            for item in items[:5]:
                price_tag = item.find('span', {'class': 'price'})
                if price_tag:
                    price_text = re.sub(r'[^\d]', '', price_tag.get_text())
                    if price_text:
                        price = int(price_text)
                        if price < max_price:
                            title_tag = item.find('h3')
                            title = title_tag.get_text(strip=True) if title_tag else query
                            results.append({
                                'market': 'Avito',
                                'product': title[:30],
                                'price': price,
                                'expected': max_price,
                                'discount': int((1 - price/max_price) * 100),
                            })
        except Exception as e:
            print(f"Avito error: {e}")
        return results
    
    def find_price_errors(self):
        errors = []
        # WB
        wb_targets = [
            {"name": "iPhone 13", "id": 139155295, "expected": 45000},
            {"name": "PS5", "id": 147590042, "expected": 50000},
        ]
        for t in wb_targets:
            price = self.scan_wb(t["id"])
            if price and price < t["expected"] * 0.7:
                errors.append({
                    "market": "WB",
                    "product": t["name"],
                    "price": price,
                    "expected": t["expected"],
                    "discount": int((1 - price/t["expected"]) * 100),
                })
            time.sleep(0.3)
        # Ozon
        ozon_targets = [
            {"name": "iPhone 14", "id": 142523308, "expected": 60000},
        ]
        for t in ozon_targets:
            price = self.scan_ozon(t["id"])
            if price and price < t["expected"] * 0.7:
                errors.append({
                    "market": "Ozon",
                    "product": t["name"],
                    "price": price,
                    "expected": t["expected"],
                    "discount": int((1 - price/t["expected"]) * 100),
                })
            time.sleep(0.5)
        # Avito
        errors.extend(self.scan_avito("iphone", 15000))
        return errors

scanner = PriceScanner()
found_errors = []
autoscan_running = False
autoscan_thread = None

def autoscan_loop():
    global autoscan_running, found_errors
    while autoscan_running:
        try:
            print(f"🔍 Автосканирование в {time.strftime('%H:%M:%S')}")
            errors = scanner.find_price_errors()
            if errors:
                settings["total_errors_found"] += len(errors)
                save_settings()
                msg = "🔔 *АВТОМАТИЧЕСКОЕ УВЕДОМЛЕНИЕ*\n\n"
                msg += f"🚨 Найдено {len(errors)} ошибок!\n\n"
                for e in errors[:3]:
                    msg += f"🛒 {e['market']}: {e['product']}\n💰 {e['price']:,} ₽\n\n"
                bot.send_message(1279722309, msg, parse_mode='Markdown')
                found_errors = errors
            else:
                print("❌ Ошибок не найдено")
        except Exception as e:
            print(f"Ошибка: {e}")
        time.sleep(600)  # 10 минут

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
    keyboard.add(InlineKeyboardButton("🔍 Найти ошибки", callback_data="scan_now"))
    keyboard.add(InlineKeyboardButton("🔄 Автопоиск", callback_data="autoscan_menu"))
    bot.reply_to(message, "⚖️ Legal Arbitrage Bot\n\nВыбери действие:", reply_markup=keyboard)

@bot.message_handler(commands=['autoscan'])
def autoscan_menu(message):
    status = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    keyboard = InlineKeyboardMarkup()
    if not settings["autoscan_enabled"]:
        keyboard.add(InlineKeyboardButton("✅ ВКЛЮЧИТЬ", callback_data="autoscan_on"))
    else:
        keyboard.add(InlineKeyboardButton("❌ ВЫКЛЮЧИТЬ", callback_data="autoscan_off"))
    bot.reply_to(message, f"🔄 Автопоиск: {status}\n\nИнтервал: 10 минут", reply_markup=keyboard)

@bot.message_handler(commands=['scan'])
def scan_command(message):
    bot.reply_to(message, "🔍 Сканирую...")
    global found_errors
    found_errors = scanner.find_price_errors()
    if not found_errors:
        bot.reply_to(message, "❌ Ошибок не найдено")
        return
    msg = "🚨 НАЙДЕНЫ ОШИБКИ!\n\n"
    for e in found_errors:
        msg += f"🛒 {e['market']}: {e['product']}\n💰 {e['price']:,} ₽\n\n"
    bot.reply_to(message, msg)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "scan_now":
        scan_command(call.message)
    elif call.data == "autoscan_menu":
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

print("🤖 Бот запущен!")
print(f"🔄 Автопоиск: {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}")

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
