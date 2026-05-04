import threading
import requests
import time
import os
from flask import Flask

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
        <p>📋 Команды: /start, /scan, /analyze 100000 5000</p>
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

# ==================== TELEGRAM БОТ (простая версия) ====================
import telebot

BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"

# Создаём бота
bot = telebot.TeleBot(BOT_TOKEN)

# Класс для сканирования цен
class PriceScanner:
    def scan_wb(self, nm_id):
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            return int(data['data']['products'][0]['salePriceU'] / 100)
        except:
            return None
    
    def find_price_errors(self):
        errors = []
        targets = [
            {"name": "iPhone 13", "id": 139155295, "expected": 45000},
            {"name": "PS5", "id": 147590042, "expected": 50000},
            {"name": "MacBook Air", "id": 158280717, "expected": 70000},
        ]
        for t in targets:
            price = self.scan_wb(t["id"])
            if price and price < t["expected"] * 0.7:
                errors.append({
                    "product": t["name"],
                    "price": price,
                    "expected": t["expected"],
                    "discount": int((1 - price/t["expected"]) * 100),
                })
            time.sleep(0.5)
        return errors

scanner = PriceScanner()
found_errors = []

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "⚖️ *LEGAL ARBITRAGE BOT*\n\n"
        "🔍 *Команды:*\n"
        "/scan - найти ценовые ошибки на WB\n"
        "/analyze 100000 5000 - юридический анализ\n"
        "/stats - статистика\n\n"
        "⚖️ *Ст. 435-438 ГК РФ* — договор заключён!\n"
        "Продавец *НЕ ИМЕЕТ ПРАВА* отменить заказ!",
        parse_mode='Markdown')

@bot.message_handler(commands=['scan'])
def scan_command(message):
    bot.reply_to(message, "🔍 Сканирую Wildberries...\n⏱️ 15-20 секунд")
    
    global found_errors
    found_errors = scanner.find_price_errors()
    
    if not found_errors:
        bot.reply_to(message, "❌ Ценовых ошибок не найдено.\nПопробуй позже!")
        return
    
    msg = "🚨 *НАЙДЕНЫ ЦЕНОВЫЕ ОШИБКИ!*\n\n"
    for e in found_errors:
        if e['discount'] > 85:
            emoji = "🔴"
        elif e['discount'] > 70:
            emoji = "🟠"
        else:
            emoji = "🟢"
        
        msg += f"{emoji} *{e['product']}*\n"
        msg += f"💰 Цена: {e['price']:,} ₽\n"
        msg += f"📊 Рынок: ~{e['expected']:,} ₽\n"
        msg += f"⚡ Скидка: {e['discount']}%\n\n"
    
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
                "📌 *Пример:* `/analyze 100000 5000`",
                parse_mode='Markdown')
            return
        
        market = int(args[1])
        error = int(args[2])
        discount = (market - error) / market * 100
        
        if discount > 85:
            verdict = "🔴 *ВЫСОКИЙ РИСК* (шанс 30%)"
            law = "Ст. 435-438 ГК РФ — договор заключён"
        elif discount > 70:
            verdict = "🟠 *СРЕДНИЙ РИСК* (шанс 65%)"
            law = "Ст. 435-438, 310 ГК РФ — отказ запрещён"
        else:
            verdict = "🟢 *НИЗКИЙ РИСК* (шанс 90%)"
            law = "Ст. 454 ГК РФ — обычная сделка"
        
        response = f"📊 *ЮРИДИЧЕСКИЙ АНАЛИЗ*\n\n"
        response += f"Рыночная цена: {market:,} ₽\n"
        response += f"Цена ошибки: {error:,} ₽\n"
        response += f"Скидка: {discount:.1f}%\n\n"
        response += f"{verdict}\n\n"
        response += f"⚖️ {law}\n\n"
        response += f"💡 Продавец *НЕ ИМЕЕТ ПРАВА* отменить заказ!"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Ошибка! Используй числа.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА*\n\n"
        f"✅ Найдено ошибок: {len(found_errors)}\n"
        f"⚡ Статус: Работает\n"
        f"🔍 Используй /scan для поиска",
        parse_mode='Markdown')

# ========== ЗАПУСК ==========
print("🤖 Telegram бот запущен!")
print("⚖️ Legal Arbitrage Bot готов к работе")
print(f"🌐 Веб-интерфейс: https://bot-market-01iu.onrender.com")

# Бесконечный цикл для бота
while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
