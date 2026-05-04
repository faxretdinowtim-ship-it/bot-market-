# bot.py — ВЕРСИЯ ДЛЯ WEB SERVICE (с Flask)
import threading
import logging
from flask import Flask, request, jsonify

# ==================== FLASK ДЛЯ RENDER ====================
web_app = Flask(__name__)

@web_app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Legal Arbitrage Bot</title></head>
    <body style="background:#0a0e27;color:#fff;text-align:center;padding:50px;">
        <h1 style="color:#00ff88">⚖️ Legal Arbitrage Bot</h1>
        <p>Бот работает!</p>
        <p>Telegram: <a href="https://t.me/legal_arbitrage_bot" style="color:#00ff88">@legal_arbitrage_bot</a></p>
    </body>
    </html>
    '''

@web_app.route('/health')
def health():
    return {"status": "ok"}

def run_flask():
    web_app.run(host='0.0.0.0', port=10000, debug=False)

# Запускаем Flask в фоне
threading.Thread(target=run_flask, daemon=True).start()
print("🌐 Flask запущен на порту 10000")

# ==================== TELEGRAM БОТ ====================
import requests
import re
import time
import random
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"

class PriceScanner:
    def scan_wb(self, nm_id: int) -> Optional[int]:
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            return int(data['data']['products'][0]['salePriceU'] / 100)
        except:
            return None
    
    def find_price_errors(self) -> List[Dict]:
        errors = []
        targets = [
            {"market": "WB", "id": 139155295, "name": "iPhone 13", "expected": 45000},
            {"market": "WB", "id": 147590042, "name": "PS5", "expected": 50000},
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

async def start(update: Update, context):
    await update.message.reply_text("⚖️ Legal Arbitrage Bot\n\nОтправь /scan для поиска ошибок")

async def scan_command(update: Update, context):
    await update.message.reply_text("🔍 Сканирую Wildberries...")
    global found_errors
    found_errors = scanner.find_price_errors()
    if not found_errors:
        await update.message.reply_text("❌ Ошибок не найдено")
        return
    msg = "🚨 Найдено:\n\n"
    for e in found_errors:
        msg += f"📦 {e['product']}\n💰 {e['price']:,} ₽ (скидка {e['discount']}%)\n\n"
    await update.message.reply_text(msg)

async def analyze_command(update: Update, context):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ /analyze [рынок] [ошибка]\nПример: /analyze 100000 5000")
        return
    try:
        market = int(args[0])
        error = int(args[1])
        discount = (market - error) / market * 100
        if discount > 85:
            verdict = "🔴 РИСКОВАННО (шанс 30%)"
        elif discount > 70:
            verdict = "🟠 СРЕДНИЙ РИСК (шанс 65%)"
        else:
            verdict = "🟢 БЕРИ СМЕЛО (шанс 90%)"
        await update.message.reply_text(f"📊 Анализ:\nСкидка: {discount:.1f}%\n{verdict}\n\nСт. 435-438 ГК РФ — договор заключён!")
    except:
        await update.message.reply_text("❌ Ошибка")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
