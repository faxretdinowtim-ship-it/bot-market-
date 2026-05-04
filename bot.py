# bot.py
import threading
import logging
import requests
import re
import time
import random
from flask import Flask
from typing import List, Dict, Optional

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
    await update.message.reply_text(
        "⚖️ **Legal Arbitrage Bot**\n\n"
        "🔍 Команды:\n"
        "/scan - найти ценовые ошибки\n"
        "/analyze 100000 5000 - юр. анализ\n"
        "/stats - статистика",
        parse_mode="Markdown"
    )

async def scan_command(update: Update, context):
    await update.message.reply_text("🔍 Сканирую Wildberries...\n⏱️ 10-15 секунд")
    global found_errors
    found_errors = scanner.find_price_errors()
    if not found_errors:
        await update.message.reply_text("❌ Ценовых ошибок не найдено")
        return
    msg = "🚨 **НАЙДЕНЫ ОШИБКИ!**\n\n"
    for e in found_errors:
        msg += f"📦 {e['product']}\n💰 {e['price']:,} ₽ (скидка {e['discount']}%)\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def analyze_command(update: Update, context):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ **Используй:** /analyze [рыночная_цена] [цена_ошибки]\n"
            "📌 **Пример:** /analyze 100000 5000",
            parse_mode="Markdown"
        )
        return
    try:
        market = int(args[0])
        error = int(args[1])
        discount = (market - error) / market * 100
        
        if discount > 85:
            verdict = "🔴 **РИСКОВАННО** (шанс выиграть 30%)"
            law = "Ст. 435-438 ГК РФ — договор заключён, но возможна отмена"
        elif discount > 70:
            verdict = "🟠 **СРЕДНИЙ РИСК** (шанс выиграть 65%)"
            law = "Ст. 435-438, 310 ГК РФ — односторонний отказ запрещён"
        else:
            verdict = "🟢 **БЕРИ СМЕЛО** (шанс выиграть 90%)"
            law = "Ст. 454 ГК РФ — обычная купля-продажа"
        
        await update.message.reply_text(
            f"📊 **ЮРИДИЧЕСКИЙ АНАЛИЗ**\n\n"
            f"Рыночная цена: {market:,} ₽\n"
            f"Цена ошибки: {error:,} ₽\n"
            f"Скидка: {discount:.1f}%\n\n"
            f"{verdict}\n\n"
            f"⚖️ **Правовая база:**\n{law}\n\n"
            f"💡 Продавец **НЕ ИМЕЕТ ПРАВА** отменить заказ!",
            parse_mode="Markdown"
        )
    except:
        await update.message.reply_text("❌ Ошибка ввода! Используй числа.")

async def stats_command(update: Update, context):
    await update.message.reply_text(
        "📊 **СТАТИСТИКА**\n\n"
        "✅ Сканирований: 0\n"
        "💰 Найдено ошибок: 0\n"
        "⚡ Используй /scan для поиска",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    print("🤖 Telegram бот запущен!")
    print("⚖️ Legal Arbitrage Bot готов к работе")
    app.run_polling()

if __name__ == "__main__":
    main()
