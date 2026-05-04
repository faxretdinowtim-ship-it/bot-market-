# bot.py
import threading
import requests
import time
import json
import re
from flask import Flask
from typing import List, Dict, Optional

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
            a { color: #00ff88; }
            .status { color: #00ff88; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>⚖️ Legal Arbitrage Bot</h1>
        <p>Статус: <span class="status">✅ БОТ РАБОТАЕТ</span></p>
        <p>Telegram: <a href="https://t.me/legal_arbitrage_bot">@legal_arbitrage_bot</a></p>
        <hr>
        <p>📋 <strong>Команды бота:</strong></p>
        <pre>
/start     - Главное меню
/scan      - Поиск ценовых ошибок
/analyze 100000 5000 - Юридический анализ
/stats     - Статистика
        </pre>
        <p>⚖️ <strong>Ст. 435-438 ГК РФ</strong> — договор заключён с момента оплаты!</p>
    </body>
    </html>
    '''

@web_app.route('/health')
def health():
    return {"status": "ok", "bot": "running"}

def run_flask():
    web_app.run(host='0.0.0.0', port=10000, debug=False)

# Запускаем Flask в фоне
threading.Thread(target=run_flask, daemon=True).start()
print("🌐 Flask сервер запущен на порту 10000")

# ==================== TELEGRAM БОТ ====================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ТВОЙ ТОКЕН
BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"

class PriceScanner:
    """Сканер цен на Wildberries"""
    
    def scan_wb(self, nm_id: int) -> Optional[int]:
        """Получить цену товара по артикулу WB"""
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            price = data['data']['products'][0]['salePriceU'] / 100
            return int(price)
        except Exception as e:
            print(f"WB error {nm_id}: {e}")
            return None
    
    def find_price_errors(self) -> List[Dict]:
        """Поиск аномально низких цен"""
        errors = []
        
        # Список товаров для проверки
        targets = [
            {"name": "iPhone 13", "id": 139155295, "expected": 45000},
            {"name": "iPhone 14", "id": 281447899, "expected": 60000},
            {"name": "PS5", "id": 147590042, "expected": 50000},
            {"name": "MacBook Air M1", "id": 158280717, "expected": 70000},
            {"name": "Samsung Galaxy S23", "id": 169242181, "expected": 50000},
            {"name": "AirPods Pro", "id": 148128760, "expected": 15000},
            {"name": "iPad Pro 11", "id": 149147870, "expected": 70000},
        ]
        
        for target in targets:
            price = self.scan_wb(target["id"])
            if price and price < target["expected"] * 0.7:  # Скидка >30%
                discount = int((1 - price / target["expected"]) * 100)
                errors.append({
                    "product": target["name"],
                    "price": price,
                    "expected": target["expected"],
                    "discount": discount,
                    "url": f"https://www.wildberries.ru/product/{target['id']}"
                })
            time.sleep(0.5)  # Защита от бана
        
        return errors

# Инициализация
scanner = PriceScanner()
found_errors = []

# ========== КОМАНДЫ БОТА ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        [InlineKeyboardButton("🔍 Найти ошибки", callback_data="scan")],
        [InlineKeyboardButton("⚖️ Юр. анализ", callback_data="analyze")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚖️ **LEGAL ARBITRAGE BOT**\n\n"
        "Я ищу ценовые ошибки на Wildberries\n"
        "и помогаю юридически их защитить.\n\n"
        "📌 **Что я умею:**\n"
        "✅ Находить товары с аномальной ценой\n"
        "✅ Анализировать шансы в суде\n"
        "✅ Давать скрипты для продавца\n\n"
        "⚖️ **Ст. 435-438 ГК РФ** — договор заключён!\n"
        "Продавец **НЕ ИМЕЕТ ПРАВА** отменить заказ!\n\n"
        "🔽 Выбери действие:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск ценовых ошибок"""
    await update.message.reply_text(
        "🔍 **Сканирую Wildberries...**\n"
        "⏱️ Это займёт 20-30 секунд\n\n"
        "Проверяю: iPhone, PS5, MacBook, Samsung...",
        parse_mode="Markdown"
    )
    
    global found_errors
    found_errors = scanner.find_price_errors()
    
    if not found_errors:
        await update.message.reply_text(
            "❌ **Ценовых ошибок не найдено**\n\n"
            "Попробуй позже или используй /analyze для ручного анализа.",
            parse_mode="Markdown"
        )
        return
    
    # Формируем сообщение с результатами
    message = "🚨 **НАЙДЕНЫ ЦЕНОВЫЕ ОШИБКИ!**\n\n"
    for i, err in enumerate(found_errors[:5], 1):
        # Эмодзи в зависимости от скидки
        if err['discount'] > 85:
            emoji = "🔴"
        elif err['discount'] > 70:
            emoji = "🟠"
        else:
            emoji = "🟢"
        
        message += f"{emoji} **{i}. {err['product']}**\n"
        message += f"   💰 Цена: {err['price']:,} ₽\n"
        message += f"   📊 Рынок: ~{err['expected']:,} ₽\n"
        message += f"   ⚡ Скидка: {err['discount']}%\n"
        message += f"   🔗 [Ссылка на товар]({err['url']})\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━\n"
    message += "⚖️ **Юридическая защита:**\n"
    message += "• Ст. 435 ГК РФ — публичная оферта\n"
    message += "• Ст. 438 ГК РФ — акцепт (оплата)\n"
    message += "• Ст. 310 ГК РФ — отказ запрещён\n\n"
    message += "💡 Продавец **НЕ МОЖЕТ** отменить заказ!"
    
    await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручной анализ цены"""
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text(
            "❌ **Используй команду так:**\n"
            "`/analyze [рыночная_цена] [цена_ошибки]`\n\n"
            "📌 **Примеры:**\n"
            "`/analyze 100000 5000` — скидка 95%\n"
            "`/analyze 50000 15000` — скидка 70%\n"
            "`/analyze 45000 25000` — скидка 44%",
            parse_mode="Markdown"
        )
        return
    
    try:
        market_price = int(args[0])
        error_price = int(args[1])
        discount = (market_price - error_price) / market_price * 100
        
        # Юридическая оценка
        if discount > 95:
            verdict = "💀 **КРИТИЧЕСКИЙ РИСК** (шанс выиграть <10%)"
            law = "Ст. 1102 ГК РФ — неосновательное обогащение"
            action = "⚠️ НЕ РЕКОМЕНДУЕТСЯ"
        elif discount > 85:
            verdict = "🔴 **ВЫСОКИЙ РИСК** (шанс выиграть 30%)"
            law = "Ст. 435-438 ГК РФ — договор заключён"
            action = "⚠️ Рискованно, но можно попробовать"
        elif discount > 70:
            verdict = "🟠 **СРЕДНИЙ РИСК** (шанс выиграть 65%)"
            law = "Ст. 435-438, 310 ГК РФ — отказ запрещён"
            action = "✅ Можно брать"
        elif discount > 50:
            verdict = "🟢 **НИЗКИЙ РИСК** (шанс выиграть 90%)"
            law = "Ст. 454 ГК РФ — обычная купля-продажа"
            action = "✅ Бери смело!"
        else:
            verdict = "✅ **БЕЗОПАСНО** (шанс выиграть 99%)"
            law = "Стандартная рыночная сделка"
            action = "✅ Абсолютно законно"
        
        # Скрипт для продавца
        seller_script = f"Здравствуйте! Мой заказ оплачен по цене {error_price:,} ₽. Согласно ст. 435-438 ГК РФ, договор считается заключённым. Прошу исполнить обязательства."
        
        response = f"""
📊 **ЮРИДИЧЕСКИЙ АНАЛИЗ СДЕЛКИ**

━━━━━━━━━━━━━━━━━━━━━
💰 **Цены:**
• Рыночная: {market_price:,} ₽
• Ваша цена: {error_price:,} ₽
• Скидка: {discount:.1f}%

━━━━━━━━━━━━━━━━━━━━━
⚖️ **Оценка рисков:**
{verdict}

📜 **Правовая база:**
{law}

🎯 **Рекомендация:**
{action}

━━━━━━━━━━━━━━━━━━━━━
📝 **Скрипт для продавца:**
`{seller_script}`

━━━━━━━━━━━━━━━━━━━━━
💡 **Что делать при отмене:**
1. Сохрани скриншот цены
2. Напиши продавцу этот скрипт
3. Обратись в поддержку
4. Подай жалобу в Роспотребнадзор
"""
        await update.message.reply_text(response, parse_mode="Markdown")
        
    except ValueError:
        await update.message.reply_text("❌ Ошибка! Цены должны быть числами.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика"""
    c = scanner.find_price_errors()
    
    await update.message.reply_text(
        f"📊 **СТАТИСТИКА БОТА**\n\n"
        f"🔍 Последнее сканирование: {len(found_errors)} ошибок\n"
        f"✅ Статус: Работает\n"
        f"⚖️ Закон: Ст. 435-438 ГК РФ\n\n"
        f"📈 **Всего найдено ошибок:** {len(found_errors)} за последний запуск\n\n"
        f"🚀 Используй /scan для нового поиска!",
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "scan":
        await scan_command(update, context)
    elif query.data == "analyze":
        await analyze_command(update, context)
    elif query.data == "stats":
        await stats_command(update, context)

# ========== ЗАПУСК ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("=" * 50)
    print("🤖 TELEGRAM БОТ ЗАПУЩЕН")
    print("⚖️ Legal Arbitrage Bot готов к работе")
    print(f"🌐 Веб-интерфейс: https://bot-market-01iu.onrender.com")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
