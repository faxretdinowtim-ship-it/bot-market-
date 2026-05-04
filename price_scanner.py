# price_scanner.py
import requests
import re
import time
import random
from typing import List, Dict, Optional

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
except ImportError:
    ua = None

class PriceScanner:
    """Реальный сканер цен с маркетплейсов"""
    
    def __init__(self):
        self.session = requests.Session()
    
    def _get_headers(self) -> dict:
        if ua:
            return {'User-Agent': ua.random}
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def scan_wb(self, nm_id: int) -> Optional[int]:
        """Сканирование Wildberries"""
        url = f"https://card.wb.ru/cards/detail?appType=1&curr=rub&nm={nm_id}"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=10)
            data = resp.json()
            price = data['data']['products'][0]['salePriceU'] / 100
            return int(price)
        except Exception as e:
            print(f"WB error: {e}")
            return None
    
    def scan_ozon(self, product_id: int) -> Optional[int]:
        """Сканирование Ozon"""
        url = f"https://www.ozon.ru/product/{product_id}/"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=10)
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
        except Exception as e:
            print(f"Ozon error: {e}")
        return None
    
    def find_price_errors(self) -> List[Dict]:
        """Поиск ценовых ошибок"""
        errors = []
        
        scan_targets = [
            {"market": "WB", "id": 139155295, "name": "iPhone 13", "expected": 45000, "type": "wb"},
            {"market": "WB", "id": 147590042, "name": "PS5", "expected": 50000, "type": "wb"},
            {"market": "Ozon", "id": 142523308, "name": "iPhone 14", "expected": 60000, "type": "ozon"},
            {"market": "Ozon", "id": 145128307, "name": "AirPods Pro", "expected": 15000, "type": "ozon"},
        ]
        
        for target in scan_targets:
            if target["type"] == "wb":
                price = self.scan_wb(target["id"])
            else:
                price = self.scan_ozon(target["id"])
            
            if price and price < target["expected"] * 0.7:
                discount = int((1 - price / target["expected"]) * 100)
                errors.append({
                    "market": target["market"],
                    "product": target["name"],
                    "price": price,
                    "expected_price": target["expected"],
                    "discount": discount,
                    "url": f"https://www.wildberries.ru/product/{target['id']}/" if target["type"] == "wb" else f"https://www.ozon.ru/product/{target['id']}/",
                    "timestamp": time.time()
                })
            
            time.sleep(random.uniform(0.5, 1.5))
        
        return errors
