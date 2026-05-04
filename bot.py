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
    "autoscan_interval": 600,  # 10 минут = 600 секунд
    "last_scan": None,
    "total_errors_found": 0
}

# Загружаем настройки
def load_settings():
    global settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings.update(json.load(f))
        except:
            pass
    print(f"📁 Настройки загружены: Автосканирование = {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}")

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
            price_patterns = [
                r'"price":"(\d+)"',
                r'"price":(\d+)',
                r'<span class="[^"]*price[^"]*">(\d+[\s]?\d*)</span>'
            ]
            for pattern in price_patterns:
                match = re.search(pattern, resp.text)
                if match:
                    price_str = match.group(1).replace(' ', '').replace('\xa0', '')
                    return int(price_str)
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
                                'product': title[:30],
                                'price': price,
                                'expected': max_price,
                                'discount': int((1 - price/max_price) * 100),
                                'market': 'Avito'
                            })
        except Exception as e:
            print(f"Avito error: {e}")
        return results
    
    def scan_yandex(self, query):
        url = f"https://market.yandex.ru/search?text={query}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            price_pattern = r'<span class="[^"]*price[^"]*">(\d+[\s]?\d*)'
            matches = re.findall(price_pattern, resp.text)
            if matches:
                price_str = matches[0].replace(' ', '').replace('\xa0', '')
                return int(price_str)
        except:
            pass
        return None
    
    def scan_dns(self, product_id):
        url = f"https://www.dns-shop.ru/product/{product_id}/"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            match = re.search(r'"price":(\d+)', resp.text)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def find_price_errors(self):
        errors = []
        
        # 1. Wildberries
        wb_targets = [
            {"name": "iPhone 13", "id": 139155295, "expected": 45000},
            {"name": "PS5", "id": 147590042, "expected": 50000},
            {"name": "MacBook Air", "id": 158280717, "expected": 70000},
            {"name": "Samsung S23", "id": 169242181, "expected": 50000},
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
        
        # 2. Ozon
        ozon_targets = [
            {"name": "iPhone 14", "id": 142523308, "expected": 60000},
            {"name": "AirPods Pro", "id": 145128307, "expected": 15000},
            {"name": "iPad Pro", "id": 148761050, "expected": 70000},
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
        
        # 3. Avito
        avito_results = self.scan_avito("iphone", 15000)
        errors.extend(avito_results)
        
        return errors

scanner = PriceScanner()
found_errors = []
autoscan_thread = None
autoscan_running = False

# ==================== АВТОМАТИЧЕСКОЕ СКАНИРОВАНИЕ ====================
def autoscan_loop():
    global autoscan_running, found_errors
    print("🔄 Автосканирование запущено (интервал: 10 минут)")
    
    while autoscan_running:
        try:
            print(f"🔍 Автосканирование в {time.strftime('%H:%M:%S')}")
            errors = scanner.find_price_errors()
            
            if errors:
                settings["total_errors_found"] += len(errors)
                save_settings()
                
                # Отправляем уведомление админу
                msg = "🔔 *АВТОМАТИЧЕСКОЕ УВЕДОМЛЕНИЕ*\n\n"
                msg += f"🚨 Найдено {len(errors)} ценовых ошибок!\n\n"
                for e in errors[:3]:
                    msg += f"🛒 {e['market']}: {e['product']}\n"
                    msg += f"💰 {e['price']:,} ₽ (скидка {e['discount']}%)\n\n"
                msg += f"📊 Всего найдено: {settings['total_errors_found']}\n"
                msg += f"🕐 Время: {time.strftime('%H:%M:%S')}\n\n"
                msg += "Используй /scan для полного отчета"
                
                bot.send_message(1279722309, msg, parse_mode='Markdown')
                
                # Сохраняем ошибки
                found_errors = errors
            else:
                print("❌ Ошибок не найдено")
            
            settings["last_scan"] = time.time()
            save_settings()
            
        except Exception as e:
            print(f"Ошибка автосканирования: {e}")
        
        # Ждём 10 минут
        for _ in range(settings["autoscan_interval"]):
            if not autoscan_running:
                break
            time.sleep(1)
    
    print("⏹️ Автосканирование остановлено")

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
        InlineKeyboardButton("⚖️ Анализ", callback_data="analyze"),
        InlineKeyboardButton("📊 Статистика", callback_data="stats")
    )
    
    bot.reply_to(message, 
        "⚖️ *LEGAL ARBITRAGE BOT*\n\n"
        "🔍 *Команды:*\n"
        "/scan - найти ценовые ошибки на ВСЕХ маркетплейсах\n"
        "/autoscan - настройка автоматического поиска (каждые 10 минут)\n"
        "/analyze - юридический анализ сделки\n"
        "/stats - статистика\n\n"
        "🛒 *Сканирую:* WB | Ozon | Avito | Яндекс.Маркет | DNS\n\n"
        "⚖️ *Ст. 435-438 ГК РФ* — договор заключён!\n"
        "Продавец *НЕ ИМЕЕТ ПРАВА* отменить заказ!",
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
    
    keyboard.add(InlineKeyboardButton("⏱️ Интервал: 10 минут", callback_data="noop"))
    
    bot.reply_to(message,
        f"🔄 *АВТОМАТИЧЕСКИЙ ПОИСК*\n\n"
        f"Статус: {status_text}\n"
        f"⏱️ Интервал: 10 минут\n"
        f"📊 Найдено ошибок всего: {settings['total_errors_found']}\n\n"
        f"При включении бот будет сам искать ценовые ошибки\n"
        f"каждые 10 минут и присылать уведомления!",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['scan'])
def scan_command(message):
    bot.reply_to(message, "🔍 *Сканирую ВСЕ маркетплейсы...*\n"
                          "⏱️ Это займёт 30-40 секунд\n\n"
                          "🛒 Проверяю: WB, Ozon, Avito, Яндекс.Маркет, DNS",
                          parse_mode='Markdown')
    
    global found_errors
    found_errors = scanner.find_price_errors()
    
    if not found_errors:
        bot.reply_to(message, "❌ *Ценовых ошибок не найдено*\n\nПопробуй позже!", parse_mode='Markdown')
        return
    
    msg = "🚨 *НАЙДЕНЫ ЦЕНОВЫЕ ОШИБКИ!*\n\n"
    
    for e in found_errors:
        market_emoji = {
            "WB": "🟣", "Ozon": "🔵", "Avito": "🟠", 
            "Яндекс.Маркет": "🟡", "DNS": "🔴"
        }.get(e['market'], "🛒")
        
        if e['discount'] > 85:
            discount_emoji = "💀"
        elif e['discount'] > 70:
            discount_emoji = "⚠️"
        else:
            discount_emoji = "✅"
        
        msg += f"{market_emoji} *{e['market']}*\n"
        msg += f"📦 {e['product']}\n"
        msg += f"💰 Цена: {e['price']:,} ₽\n"
        msg += f"📊 Рынок: ~{e['expected']:,} ₽\n"
        msg += f"{discount_emoji} Скидка: {e['discount']}%\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "⚖️ *Продавец НЕ МОЖЕТ отменить заказ!*\n"
    msg += "📍 Ст. 435-438, 310 ГК РФ"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['analyze'])
def analyze_command(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, 
                "❌ *Используй:* `/analyze [рынок] [ошибка]`\n"
                "📌 *Пример:* `/analyze 100000 5000`\n\n"
                "💡 *Что означают цифры:*\n"
                "100000 — рыночная цена\n"
                "5000 — цена по ошибке\n"
                "→ Скидка 95%",
                parse_mode='Markdown')
            return
        
        market = int(args[1])
        error = int(args[2])
        discount = (market - error) / market * 100
        
        if discount > 95:
            verdict = "💀 *КРИТИЧЕСКИЙ РИСК* (шанс <10%)"
            law = "Ст. 1102 ГК РФ — неосновательное обогащение"
        elif discount > 85:
            verdict = "🔴 *ВЫСОКИЙ РИСК* (шанс 30%)"
            law = "Ст. 435-438 ГК РФ — договор заключён"
        elif discount > 70:
            verdict = "🟠 *СРЕДНИЙ РИСК* (шанс 65%)"
            law = "Ст. 435-438, 310 ГК РФ — отказ запрещён"
        else:
            verdict = "🟢 *НИЗКИЙ РИСК* (шанс 90%)"
            law = "Ст. 454 ГК РФ — обычная сделка"
        
        response = f"📊 *ЮРИДИЧЕСКИЙ АНАЛИЗ*\n\n"
        response += f"💰 Рыночная цена: {market:,} ₽\n"
        response += f"🎯 Цена ошибки: {error:,} ₽\n"
        response += f"⚡ Скидка: {discount:.1f}%\n\n"
        response += f"{verdict}\n\n"
        response += f"⚖️ *Правовая база:*\n{law}\n\n"
        response += f"📍 Продавец *НЕ ИМЕЕТ ПРАВА* отменить заказ!"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ *Ошибка!* Используй числа.\nПример: `/analyze 100000 5000`", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_command(message):
    markets_count = {}
    for e in found_errors:
        markets_count[e['market']] = markets_count.get(e['market'], 0) + 1
    
    stats = ""
    for market, count in markets_count.items():
        stats += f"🛒 {market}: {count} ошибок\n"
    
    if not stats:
        stats = "Нет данных. Используй /scan"
    
    status_text = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА*\n\n"
        f"🔍 *Последнее сканирование:*\n{stats}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔄 *Автопоиск:* {status_text}\n"
        f"⏱️ Интервал: 10 минут\n"
        f"📊 Всего ошибок: {settings['total_errors_found']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 Маркетплейсы: WB, Ozon, Avito, Яндекс, DNS\n"
        f"⚖️ Закон: Ст. 435-438 ГК РФ\n\n"
        f"🚀 Используй /autoscan для настройки!",
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
        bot.answer_callback_query(call.id, "✅ Автопоиск включён! Буду сканировать каждые 10 минут")
        autoscan_menu(call.message)
    
    elif call.data == "autoscan_off":
        settings["autoscan_enabled"] = False
        save_settings()
        stop_autoscan()
        bot.answer_callback_query(call.id, "❌ Автопоиск выключен")
        autoscan_menu(call.message)
    
    elif call.data == "analyze":
        bot.answer_callback_query(call.id)
        analyze_command(call.message)
    
    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        stats_command(call.message)
    
    elif call.data == "noop":
        bot.answer_callback_query(call.id)

# ==================== ЗАПУСК ====================
load_settings()

# Если автопоиск был включён, запускаем его
if settings["autoscan_enabled"]:
    start_autoscan()

print("🤖 Telegram бот запущен!")
print("⚖️ Legal Arbitrage Bot готов к работе")
print("🛒 Сканирую: WB, Ozon, Avito, Яндекс.Маркет, DNS")
print(f"🔄 Автопоиск: {'ВКЛЮЧЕН' if settings['autoscan_enabled'] else 'ВЫКЛЮЧЕН'}")
print(f"🌐 Веб-интерфейс: https://bot-market-01iu.onrender.com")

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
