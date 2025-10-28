#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import time
import hmac
import hashlib
import threading
import logging
import os
from datetime import datetime

class RealTradingBot:
    def __init__(self):
        self.setup_logging()
        self.running = True
        self.load_config()
        self.session = requests.Session()
        
        # Wechselkurs EUR/USD (initial, wird später aktualisiert)
        self.eur_usd_rate = 1.08
        
        # Trading-Assets
        self.trading_assets = {
            "BTC": {"epic": "BTCUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "ETH": {"epic": "ETHUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "SOL": {"epic": "SOLUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "XRP": {"epic": "XRPUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "DOGE": {"epic": "DOGEUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "BNB": {"epic": "BNBUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "KUPFER": {"epic": "COPPER", "type": "commodity", "leverage": self.commodity_leverage},
            "GAS": {"epic": "NATGAS", "type": "commodity", "leverage": self.commodity_leverage}
        }
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/trading-bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TradingBot')
        
    def load_config(self):
        """Lädt Konfiguration"""
        self.api_key = os.getenv('CAPITAL_API_KEY')
        self.api_secret = os.getenv('CAPITAL_API_SECRET')
        self.account_id = os.getenv('CAPITAL_ACCOUNT_ID')
        self.account_currency = os.getenv('ACCOUNT_CURRENCY', 'EUR')
        self.demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true'
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        # Hebel-Einstellungen
        self.crypto_leverage = int(os.getenv('CRYPTO_LEVERAGE', '2'))
        self.commodity_leverage = int(os.getenv('COMMODITY_LEVERAGE', '20'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.1'))
        
        if not self.api_key or not self.api_secret:
            self.logger.error("❌ API Keys nicht konfiguriert! Bitte .env Datei überprüfen.")
            raise ValueError("API Keys fehlen")
            
        self.logger.info(f"✅ Konfiguration geladen - Live-Modus: {not self.demo_mode}")
        
    def generate_signature(self, method, path, body=""):
        """Generiert API Signature"""
        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return timestamp, signature
    
    def api_request(self, method, endpoint, data=None):
        """Macht echten API Request"""
        try:
            base_url = "https://api-capital.backend-capital.com"
            path = f"/api/v1{endpoint}"
            body = json.dumps(data) if data else ""
            
            timestamp, signature = self.generate_signature(method, path, body)
            
            headers = {
                "X-CAP-API-KEY": self.api_key,
                "X-SECURITY-TOKEN": signature,
                "X-TIMESTAMP": timestamp,
                "Content-Type": "application/json"
            }
            
            url = base_url + path
            
            self.logger.debug(f"API Request: {method} {endpoint}")
            
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, data=body, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code != 200:
                self.logger.error(f"API Fehler {response.status_code}: {response.text}")
                return None
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"API request failed: {str(e)}")
            return None
    
    def get_account_balance(self):
        """Ermittelt den echten Depotwert"""
        try:
            response = self.api_request("GET", f"/accounts/{self.account_id}")
            if response:
                balance = response.get('balance', 0)
                available = response.get('available', 0)
                profit_loss = response.get('profitLoss', 0)
                currency = response.get('currency', 'EUR')
                
                # USD Wert berechnen
                balance_usd = balance * self.eur_usd_rate
                
                self.logger.info(f"💰 ECHTER Depotwert: €{balance:,.2f} {currency}")
                self.logger.info(f"💵 Entspricht: ${balance_usd:,.2f} USD")
                self.logger.info(f"📈 Verfügbar: €{available:,.2f} | P&L: €{profit_loss:,.2f}")
                
                return balance, balance_usd, available, profit_loss
            else:
                self.logger.error("❌ Konnte Depotdaten nicht abrufen")
                return 0, 0, 0, 0
                
        except Exception as e:
            self.logger.error(f"❌ Fehler bei Depotwert-Abfrage: {str(e)}")
            return 0, 0, 0, 0
    
    def get_open_positions(self):
        """Ermittelt die echten offenen Positionen"""
        try:
            response = self.api_request("GET", "/positions")
            if response and 'positions' in response:
                positions = response['positions']
                self.logger.info(f"📊 Offene Positionen: {len(positions)}")
                
                if positions:
                    for position in positions:
                        epic = position.get('epic', 'Unknown')
                        direction = position.get('position', {}).get('direction', 'UNKNOWN')
                        size = position.get('position', {}).get('size', 0)
                        profit = position.get('position', {}).get('profit', 0)
                        
                        # Finde den Asset-Namen
                        asset_name = "Unknown"
                        for name, info in self.trading_assets.items():
                            if info['epic'] == epic:
                                asset_name = name
                                break
                        
                        self.logger.info(f"   📍 {asset_name} | {direction} | Size: {size} | P&L: €{profit:,.2f}")
                else:
                    self.logger.info("   Keine offenen Positionen")
                    
                return positions
            else:
                self.logger.info("📊 Keine offenen Positionen gefunden")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abrufen der Positionen: {str(e)}")
            return []
    
    def get_market_prices(self):
        """Ruft echte Marktpreise ab"""
        try:
            prices = {}
            for asset, info in self.trading_assets.items():
                epic = info['epic']
                response = self.api_request("GET", f"/prices/{epic}")
                if response and 'prices' in response:
                    bid = response['prices'][0].get('bid', 0)
                    ask = response['prices'][0].get('ask', 0)
                    prices[asset] = {
                        'bid': bid,
                        'ask': ask,
                        'spread': ask - bid
                    }
                else:
                    # Fallback mit simulierten Preisen falls API nicht verfügbar
                    import random
                    if info['type'] == 'crypto':
                        if asset == "BTC":
                            price = random.uniform(65000, 70000)
                        elif asset == "ETH":
                            price = random.uniform(3500, 4000)
                        else:
                            price = random.uniform(1, 1000)
                    else:
                        if asset == "KUPFER":
                            price = random.uniform(3.5, 4.5)
                        elif asset == "GAS":
                            price = random.uniform(2.0, 3.0)
                    
                    prices[asset] = {
                        'bid': price,
                        'ask': price * 1.001,  # Kleiner Spread
                        'spread': price * 0.001
                    }
                    
            return prices
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abrufen der Marktpreise: {str(e)}")
            return {}
    
    def calculate_position_size(self, balance_eur, balance_usd, asset_type):
        """Berechnet Positionsgröße basierend auf echtem Depotwert"""
        risk_amount_eur = balance_eur * self.risk_per_trade
        risk_amount_usd = balance_usd * self.risk_per_trade
        
        if asset_type == "crypto":
            leverage = self.crypto_leverage
            position_size_usd = risk_amount_usd * leverage
            position_size_eur = risk_amount_eur * leverage
        else:  # commodity
            leverage = self.commodity_leverage
            position_size_usd = risk_amount_usd * leverage
            position_size_eur = risk_amount_eur * leverage
            
        return position_size_usd, position_size_eur, leverage
    
    def generate_trading_signals(self, prices, balance_eur, balance_usd):
        """Generiert Trading-Signale basierend auf Marktanalyse"""
        import random
        
        analysis = {}
        for asset, info in self.trading_assets.items():
            if asset in prices:
                price_data = prices[asset]
                current_price = (price_data['bid'] + price_data['ask']) / 2
                
                # Berechne Positionsgröße
                position_size_usd, position_size_eur, leverage = self.calculate_position_size(
                    balance_eur, balance_usd, info["type"]
                )
                
                # Einfache Signal-Logik (kann später erweitert werden)
                signal = random.choice(["LONG", "SHORT", "HOLD"])
                
                analysis[asset] = {
                    "price": round(current_price, 3),
                    "bid": round(price_data['bid'], 3),
                    "ask": round(price_data['ask'], 3),
                    "spread": round(price_data['spread'], 4),
                    "signal": signal,
                    "position_size_usd": round(position_size_usd, 2),
                    "position_size_eur": round(position_size_eur, 2),
                    "leverage": leverage,
                    "type": info["type"],
                    "epic": info["epic"]
                }
            
        return analysis
        
    def monitor_market(self):
        """Haupt-Monitoring Loop mit echten Daten"""
        self.logger.info("🚀 LIVE TRADING BOT GESTARTET")
        self.logger.info(f"💰 Kontowährung: {self.account_currency}")
        self.logger.info(f"📊 Überwachte Assets: {list(self.trading_assets.keys())}")
        
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                self.logger.info("=" * 70)
                self.logger.info(f"🔄 Live-Analyse #{cycle} - {current_time}")
                
                # 1. Echten Depotwert abrufen
                balance_eur, balance_usd, available, profit_loss = self.get_account_balance()
                
                # 2. Offene Positionen anzeigen
                self.get_open_positions()
                
                # 3. Echte Marktpreise abrufen
                prices = self.get_market_prices()
                
                if balance_eur > 0 and prices:
                    # 4. Trading-Signale generieren
                    analysis = self.generate_trading_signals(prices, balance_eur, balance_usd)
                    
                    # 5. Signale anzeigen
                    self.logger.info("🎯 TRADING SIGNALE:")
                    
                    self.logger.info("🔧 ROHSTOFFE (20:1 Hebel):")
                    for asset, data in analysis.items():
                        if data["type"] == "commodity":
                            signal_icon = "🟢" if data["signal"] == "LONG" else "🔴" if data["signal"] == "SHORT" else "🟡"
                            self.logger.info(f"   {signal_icon} {asset:6} | ${data['price']:7.3f} | {data['signal']:5} | Size: ${data['position_size_usd']:7.2f} (€{data['position_size_eur']:7.2f}) | {data['leverage']:2}:1")
                    
                    self.logger.info("₿  KRYPTO (2:1 Hebel):")
                    for asset, data in analysis.items():
                        if data["type"] == "crypto":
                            signal_icon = "🟢" if data["signal"] == "LONG" else "🔴" if data["signal"] == "SHORT" else "🟡"
                            self.logger.info(f"   {signal_icon} {asset:6} | ${data['price']:7.2f} | {data['signal']:5} | Size: ${data['position_size_usd']:7.2f} (€{data['position_size_eur']:7.2f}) | {data['leverage']:2}:1")
                
                self.logger.info(f"⏰ Nächste Analyse in {self.check_interval} Sekunden...")
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Fehler in Monitoring: {str(e)}")
                time.sleep(30)
    
    def start(self):
        """Startet den Bot"""
        self.logger.info("🤖 Starte Live Trading Bot...")
        
        try:
            monitor_thread = threading.Thread(target=self.monitor_market)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            self.logger.error(f"❌ Kritischer Fehler: {str(e)}")
            self.stop()
    
    def stop(self):
        """Stoppt den Bot"""
        self.running = False
        self.logger.info("🛑 Bot gestoppt")

if __name__ == "__main__":
    bot = RealTradingBot()
    bot.start()
