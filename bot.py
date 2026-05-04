import requests
import telebot
import time
import random
import json
import os
import threading
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"
ADMIN_ID = 1279722309
bot = telebot.TeleBot(BOT_TOKEN)

# Папка для скриншотов
SCREENSHOTS_FOLDER = "screenshots"
os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)

# Настройки
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
    print(f"📁 Настройки: Автопоиск = {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}")

def save_settings():
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

load_settings()

# ==================== ФУНКЦИЯ СКРИНШОТА (упрощённая) ====================
def take_screenshot_simple(url, filename):
    """Простой скриншот через requests + сохранение HTML"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        
        # Сохраняем HTML как "скриншот" (альтернатива для Render)
        filepath = os.path.join(SCREENSHOTS_FOLDER, f"{filename}.html")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(r.text)
        
        # Также сохраняем мета-информацию
        info_path = os.path.join(SCREENSHOTS_FOLDER, f"{filename}.json")
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "status_code": r.status_code
            }, f, indent=2)
        
        return filepath
    except Exception as e:
        print(f"Скриншот не удался: {e}")
        return None

# ==================== РЕАЛЬНЫЙ СКАНЕР ЦЕН ====================
def scan_wb(nm_id):
    url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data['data']['products'][0]['salePriceU'] / 100
        return int(price)
    except:
        return None

def scan_ozon(product_id):
    url = f"https://www.ozon.ru/product/{product_id}/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        import re
        match = re.search(r'"price":"(\d+)"', r.text)
        if match:
            return int(match.group(1))
    except:
        pass
    return None

def find_errors():
    errors = []
    
    products = [
        {"market": "WB", "name": "iPhone 13", "id": 139155295, "expected": 45000, "type": "wb"},
        {"market": "WB", "name": "iPhone 14", "id": 281447899, "expected": 60000, "type": "wb"},
        {"market": "WB", "name": "PS5", "id": 147590042, "expected": 55000, "type": "wb"},
        {"market": "WB", "name": "MacBook Pro", "id": 158280717, "expected": 100000, "type": "wb"},
        {"market": "WB", "name": "Samsung S23", "id": 169242181, "expected": 70000, "type": "wb"},
        {"market": "WB", "name": "iPad Pro", "id": 149147870, "expected": 70000, "type": "wb"},
        {"market": "Ozon", "name": "iPhone 15", "id": 153491311, "expected": 80000, "type": "ozon"},
        {"market": "Ozon", "name": "MacBook Air", "id": 142523308, "expected": 65000, "type": "ozon"},
        {"market": "Ozon", "name": "AirPods Pro", "id": 145128307, "expected": 20000, "type": "ozon"},
    ]
    
    for p in products:
        if p["type"] == "wb":
            price = scan_wb(p["id"])
        else:
            price = scan_ozon(p["id"])
        
        if price and price < p["expected"] * 0.7:
            errors.append({
                "market": p["market"],
                "name": p["name"],
                "price": price,
                "expected": p["expected"],
                "discount": int((1 - price / p["expected"]) * 100),
                "url": f"https://www.wildberries.ru/product/{p['id']}" if p["type"] == "wb" else f"https://www.ozon.ru/product/{p['id']}"
            })
        
        time.sleep(random.uniform(0.3, 0.7))
    
    return errors

# ==================== АВТОМАТИЧЕСКАЯ ОБРАБОТКА ====================
def process_error(error):
    """Автоматическая обработка найденной ошибки"""
    print(f"🔄 Обрабатываю: {error['name']}")
    
    # Делаем "скриншот" (HTML)
    screenshot_file = take_screenshot_simple(error['url'], f"{error['name'].replace(' ', '_')}_{int(time.time())}")
    
    # Формируем сообщение
    message = f"""
🚨 *СРОЧНО! НАЙДЕНА ЦЕНОВАЯ ОШИБКА!*

━━━━━━━━━━━━━━━━━━━━━
📦 *Товар:* {error['name']}
🛒 *Маркетплейс:* {error['market']}
💰 *Цена:* {error['price']:,} ₽
📊 *Рыночная цена:* ~{error['expected']:,} ₽
⚡ *Скидка:* {error['discount']}%

━━━━━━━━━━━━━━━━━━━━━
🔗 *ССЫЛКА ДЛЯ ПОКУПКИ:*
{error['url']}

━━━━━━━━━━━━━━━━━━━━━
⚖️ *ЮРИДИЧЕСКАЯ ЗАЩИТА (скопируй и отправь продавцу):*

«Здравствуйте! Мной совершена покупка и произведена полная оплата.

В соответствии со ст. 435 ГК РФ, размещение товара с указанием цены является публичной офертой.

Моя оплата (ст. 438 ГК РФ) является акцептом, что означает заключение договора купли-продажи.

Ст. 310 ГК РФ запрещает односторонний отказ от исполнения обязательства.

У меня есть скриншот страницы с ценой и подтверждение оплаты.

Требую исполнить договор. В случае отказа буду вынужден обратиться в суд.»

━━━━━━━━━━━━━━━━━━━━━
💡 *ДЕЙСТВУЙ БЫСТРО!*
1. Перейди по ссылке
2. Оформи заказ
3. Оплати
4. При отмене используй скрипт выше

🔥 *ПРОДАВЕЦ НЕ ИМЕЕТ ПРАВА ОТМЕНИТЬ ЗАКАЗ ПО ЗАКОНУ!*
"""
    
    # Отправляем в Telegram
    bot.send_message(ADMIN_ID, message, parse_mode='Markdown', disable_web_page_preview=True)
    
    # Отправляем HTML-файл как "скриншот"
    if screenshot_file:
        with open(screenshot_file, 'r', encoding='utf-8') as f:
            try:
                bot.send_document(ADMIN_ID, f, caption=f"📄 Сохранённая страница {error['name']}")
            except:
                pass
    
    return message

# ==================== АВТОСКАНИРОВАНИЕ ====================
autoscan_running = False
autoscan_thread = None

def autoscan_loop():
    global autoscan_running
    while autoscan_running:
        try:
            print(f"🔍 Автосканирование в {time.strftime('%H:%M:%S')}")
            errors = find_errors()
            
            if errors:
                settings["total_errors_found"] += len(errors)
                save_settings()
                
                for error in errors:
                    process_error(error)
                    time.sleep(2)
                
                bot.send_message(ADMIN_ID, f"📊 *Всего найдено ошибок:* {settings['total_errors_found']}", parse_mode='Markdown')
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
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🔍 НАЙТИ ОШИБКИ", callback_data="scan"),
        InlineKeyboardButton("🔄 АВТОПОИСК", callback_data="autoscan")
    )
    keyboard.row(
        InlineKeyboardButton("⚖️ ЮР. ЗАЩИТА", callback_data="legal"),
        InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="stats")
    )
    
    bot.reply_to(message,
        "⚡ *АРБИТРАЖНЫЙ БОТ*\n\n"
        "🔍 *Команды:*\n"
        "/scan — найти ошибки сейчас\n"
        "/autoscan — автопоиск каждые 10 минут\n"
        "/analyze — юр. анализ любой цены\n"
        "/stats — статистика\n\n"
        "⚖️ Ст. 435-438 ГК РФ — договор заключён!\n"
        "💡 Продавец НЕ МОЖЕТ отменить заказ!",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['scan'])
def scan_command(message):
    bot.reply_to(message, "🔍 *Сканирую маркетплейсы...*\n⏱️ 15-20 секунд", parse_mode='Markdown')
    
    errors = find_errors()
    
    if not errors:
        bot.reply_to(message, "❌ *Ценовых ошибок не найдено*\n\nПопробуй позже!", parse_mode='Markdown')
        return
    
    for error in errors:
        process_error(error)
        time.sleep(2)
    
    bot.reply_to(message, f"✅ *Найдено {len(errors)} ошибок!*\n\nСсылки и инструкции выше ↑", parse_mode='Markdown')

@bot.message_handler(commands=['autoscan'])
def autoscan_menu(message):
    status = "🟢 ВКЛЮЧЕН" if settings["autoscan_enabled"] else "🔴 ВЫКЛЮЧЕН"
    
    keyboard = InlineKeyboardMarkup()
    if not settings["autoscan_enabled"]:
        keyboard.add(InlineKeyboardButton("✅ ВКЛЮЧИТЬ АВТОПОИСК", callback_data="autoscan_on"))
    else:
        keyboard.add(InlineKeyboardButton("❌ ВЫКЛЮЧИТЬ АВТОПОИСК", callback_data="autoscan_off"))
    
    bot.reply_to(message,
        f"🔄 *АВТОПОИСК*\n\n"
        f"Статус: {status}\n"
        f"⏱️ Интервал: 10 минут\n"
        f"📊 Всего ошибок: {settings['total_errors_found']}",
        parse_mode='Markdown',
        reply_markup=keyboard)

@bot.message_handler(commands=['analyze'])
def analyze_command(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ /analyze [рыночная_цена] [цена_ошибки]\nПример: /analyze 100000 5000")
        return
    
    try:
        market = int(args[1])
        error = int(args[2])
        discount = (market - error) / market * 100
        
        if error <= 100:
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
            f"⚖️ Ст. 435-438 ГК РФ — договор заключён!",
            parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Ошибка! Используй числа.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    status = "ВКЛЮЧЕН" if settings["autoscan_enabled"] else "ВЫКЛЮЧЕН"
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА*\n\n"
        f"📊 Всего ошибок: {settings['total_errors_found']}\n"
        f"🔄 Автопоиск: {status}\n"
        f"⏱️ Интервал: 10 минут\n"
        f"⚖️ Закон: Ст. 435-438 ГК РФ",
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
            "• Ст. 310 — отказ запрещён\n\n"
            "💡 *При отмене заказа:*\n"
            "1. Скриншот цены\n"
            "2. Напиши продавцу скрипт из /scan\n"
            "3. Обратись в поддержку\n"
            "4. Роспотребнадзор\n\n"
            "🔥 Продавец НЕ МОЖЕТ отменить заказ!",
            parse_mode='Markdown')
    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        stats_command(call.message)
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
if settings["autoscan_enabled"]:
    start_autoscan()

print("=" * 50)
print("🤖 БОТ ЗАПУЩЕН")
print("🔍 Ищу ценовые ошибки на WB и Ozon")
print("📸 Сохраняю страницы для юр. защиты")
print(f"🔄 Автопоиск: {'ВКЛ' if settings['autoscan_enabled'] else 'ВЫКЛ'}")
print("=" * 50)

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
