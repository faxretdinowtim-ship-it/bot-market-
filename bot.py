import threading
import requests
import time
import re
from flask import Flask
from bs4 import BeautifulSoup

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
import telebot

BOT_TOKEN = "8285727455:AAHZ3X8s7enoZC5csZxryGnZGuxSe-3Naig"
bot = telebot.TeleBot(BOT_TOKEN)

class PriceScanner:
    """Сканер всех маркетплейсов"""
    
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # ========== WILDBERRIES ==========
    def scan_wb(self, nm_id):
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            return int(data['data']['products'][0]['salePriceU'] / 100)
        except:
            return None
    
    # ========== OZON ==========
    def scan_ozon(self, product_id):
        url = f"https://www.ozon.ru/product/{product_id}/"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            # Ищем цену в JSON
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
    
    # ========== AVITO ==========
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
    
    # ========== ЯНДЕКС.МАРКЕТ ==========
    def scan_yandex(self, query):
        url = f"https://market.yandex.ru/search?text={query}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            # Ищем цены в HTML
            price_pattern = r'<span class="[^"]*price[^"]*">(\d+[\s]?\d*)'
            matches = re.findall(price_pattern, resp.text)
            if matches:
                price_str = matches[0].replace(' ', '').replace('\xa0', '')
                return int(price_str)
        except:
            pass
        return None
    
    # ========== DNS ==========
    def scan_dns(self, product_id):
        url = f"https://www.dns-shop.ru/product/{product_id}/"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            # Ищем цену в JSON-LD
            match = re.search(r'"price":(\d+)', resp.text)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    # ========== ПОЛНОЕ СКАНИРОВАНИЕ ==========
    def find_price_errors(self):
        errors = []
        
        # 1. Wildberries
        print("🔍 Сканирую Wildberries...")
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
        print("🔍 Сканирую Ozon...")
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
        print("🔍 Сканирую Avito...")
        avito_results = self.scan_avito("iphone", 15000)
        errors.extend(avito_results)
        
        # 4. Яндекс.Маркет
        print("🔍 Сканирую Яндекс.Маркет...")
        yandex_price = self.scan_yandex("iphone")
        if yandex_price and yandex_price < 40000:
            errors.append({
                "market": "Яндекс.Маркет",
                "product": "iPhone (популярный)",
                "price": yandex_price,
                "expected": 50000,
                "discount": int((1 - yandex_price/50000) * 100),
            })
        
        # 5. DNS
        print("🔍 Сканирую DNS...")
        dns_price = self.scan_dns("produkt/163503")
        if dns_price and dns_price < 30000:
            errors.append({
                "market": "DNS",
                "product": "Товар DNS",
                "price": dns_price,
                "expected": 50000,
                "discount": int((1 - dns_price/50000) * 100),
            })
        
        return errors

scanner = PriceScanner()
found_errors = []

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
        "⚖️ *LEGAL ARBITRAGE BOT*\n\n"
        "🔍 *Команды:*\n"
        "/scan - найти ценовые ошибки на ВСЕХ маркетплейсах\n"
        "/analyze - юридический анализ сделки\n"
        "/stats - статистика\n\n"
        "🛒 *Сканирую:* WB | Ozon | Avito | Яндекс.Маркет | DNS\n\n"
        "⚖️ *Ст. 435-438 ГК РФ* — договор заключён!\n"
        "Продавец *НЕ ИМЕЕТ ПРАВА* отменить заказ!",
        parse_mode='Markdown')

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
    
    # Группируем по маркетплейсам
    msg = "🚨 *НАЙДЕНЫ ЦЕНОВЫЕ ОШИБКИ!*\n\n"
    
    for e in found_errors:
        # Эмодзи маркетплейса
        market_emoji = {
            "WB": "🟣", "Ozon": "🔵", "Avito": "🟠", 
            "Яндекс.Маркет": "🟡", "DNS": "🔴"
        }.get(e['market'], "🛒")
        
        # Эмодзи скидки
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
    msg += "📍 Ст. 435-438, 310 ГК РФ\n"
    msg += "💡 Сохрани скриншот цены!"
    
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
            advice = "⚠️ НЕ РЕКОМЕНДУЕТСЯ"
        elif discount > 85:
            verdict = "🔴 *ВЫСОКИЙ РИСК* (шанс 30%)"
            law = "Ст. 435-438 ГК РФ — договор заключён"
            advice = "⚠️ Рискованно, но можно"
        elif discount > 70:
            verdict = "🟠 *СРЕДНИЙ РИСК* (шанс 65%)"
            law = "Ст. 435-438, 310 ГК РФ — отказ запрещён"
            advice = "✅ Можно брать"
        elif discount > 50:
            verdict = "🟢 *НИЗКИЙ РИСК* (шанс 90%)"
            law = "Ст. 454 ГК РФ — обычная сделка"
            advice = "✅ Бери смело!"
        else:
            verdict = "✅ *БЕЗОПАСНО* (шанс 99%)"
            law = "Стандартная сделка"
            advice = "✅ Абсолютно законно"
        
        response = f"📊 *ЮРИДИЧЕСКИЙ АНАЛИЗ*\n\n"
        response += f"💰 Рыночная цена: {market:,} ₽\n"
        response += f"🎯 Цена ошибки: {error:,} ₽\n"
        response += f"⚡ Скидка: {discount:.1f}%\n\n"
        response += f"{verdict}\n\n"
        response += f"⚖️ *Правовая база:*\n{law}\n\n"
        response += f"💡 *Рекомендация:* {advice}\n\n"
        response += f"📍 Продавец *НЕ ИМЕЕТ ПРАВА* отменить заказ!"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ *Ошибка!* Используй числа.\nПример: `/analyze 100000 5000`", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_command(message):
    # Считаем статистику по маркетплейсам
    markets_count = {}
    for e in found_errors:
        markets_count[e['market']] = markets_count.get(e['market'], 0) + 1
    
    stats = ""
    for market, count in markets_count.items():
        stats += f"🛒 {market}: {count} ошибок\n"
    
    if not stats:
        stats = "Нет данных. Используй /scan"
    
    bot.reply_to(message,
        f"📊 *СТАТИСТИКА*\n\n"
        f"🔍 Последнее сканирование:\n{stats}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Статус: Работает\n"
        f"🛒 Маркетплейсы: WB, Ozon, Avito, Яндекс, DNS\n"
        f"⚖️ Закон: Ст. 435-438 ГК РФ\n\n"
        f"🚀 Используй /scan для поиска!",
        parse_mode='Markdown')

# ========== ЗАПУСК ==========
print("🤖 Telegram бот запущен!")
print("⚖️ Legal Arbitrage Bot готов к работе")
print("🛒 Сканирую: WB, Ozon, Avito, Яндекс.Маркет, DNS")
print(f"🌐 Веб-интерфейс: https://bot-market-01iu.onrender.com")

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)
