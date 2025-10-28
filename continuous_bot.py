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

class EURTradingBot:
    def __init__(self):
        self.setup_logging()
        self.running = True
        self.load_config()
        self.session = requests.Session()
        
        # Wechselkurs EUR/USD (könnte auch von API bezogen werden)
        self.eur_usd_rate = 1.08  # Aktueller Wechselkurs - könnte dynamisch bezogen werden
        
        # Trading-Assets (alle in USD denominert)
        self.trading_assets = {
            # Kryptowährungen (2:1 Hebel)
            "BTC": {"epic": "BTCUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "ETH": {"epic": "ETHUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "SOL": {"epic": "SOLUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "XRP": {"epic": "XRPUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "DOGE": {"epic": "DOGEUSD", "type": "crypto", "leverage": self.crypto_leverage},
            "BNB": {"epic": "BNBUSD", "type": "crypto", "leverage": self.crypto_leverage},
            
            # Rohstoffe (20:1 Hebel)
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
        """Lädt Konfiguration mit Währungseinstellung"""
        self.api_key = os.getenv('CAPITAL_API_KEY', 'demo_key')
        self.api_secret = os.getenv('CAPITAL_API_SECRET', 'demo_secret')
        self.account_id = os.getenv('CAPITAL_ACCOUNT_ID', 'demo_account')
        self.account_currency = os.getenv('ACCOUNT_CURRENCY', 'EUR')
        self.demo_mode = os.getenv('DEMO_MODE', 'True').lower() == 'true'
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        # Hebel-Einstellungen
        self.crypto_leverage = int(os.getenv('CRYPTO_LEVERAGE', '2'))
        self.commodity_leverage = int(os.getenv('COMMODITY_LEVERAGE', '20'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.1'))
        
        self.logger.info(f"✅ Konfiguration geladen - Konto: {self.account_currency}")
        self.logger.info(f"⚖️  Hebel: Krypto {self.crypto_leverage}:1, Rohstoffe {self.commodity_leverage}:1")
        
    def generate_signature(self, method, path, body=""):
        """Generiert API Signature"""
        try:
            timestamp = str(int(time.time() * 1000))
            message = timestamp + method + path + body
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return timestamp, signature
        except Exception as e:
            self.logger.error(f"Signature error: {str(e)}")
            return "0", "invalid"
    
    def api_request(self, method, endpoint, data=None):
        """Macht API Request"""
        try:
            # Demo-Modus Simulation
            if self.demo_mode or self.api_key in ['demo_key', 'demo_mode_active']:
                return self.simulate_api_response(endpoint)
                
            base_url = "https://api-capital.backend-capital.com" if self.demo_mode else "https://api-capital.backend-capital.com"
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
            
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, data=body, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"API request failed: {str(e)}")
            return {"error": str(e)}
    
    def simulate_api_response(self, endpoint):
        """Simuliert API Responses für Demo-Modus"""
        if "/accounts/" in endpoint:
            # Simuliert Kontostand in EUR
            return {
                "balance": 10000.0,
                "available": 9800.0,
                "deposit": 10000.0,
                "profitLoss": 0.0,
                "currency": "EUR"
            }
        elif "/positions" in endpoint:
            # Simuliert offene Positionen
            return {"positions": []}
        else:
            return {"status": "DEMO", "message": "Simulated response"}
    
    def get_account_balance(self):
        """Ermittelt den aktuellen Depotwert in EUR und USD"""
        try:
            response = self.api_request("GET", f"/accounts/{self.account_id}")
            if response and 'balance' in response:
                balance_eur = response['balance']
                balance_usd = balance_eur * self.eur_usd_rate
                
                self.logger.info(f"💰 Depotwert: €{balance_eur:,.2f} (${balance_usd:,.2f} USD)")
                return balance_eur, balance_usd
            else:
                self.logger.warning("⚠️  Depotwert konnte nicht ermittelt werden, verwende Standardwert")
                return 10000.0, 10800.0  # Fallback in EUR und USD
        except Exception as e:
            self.logger.error(f"❌ Fehler bei Depotwert-Abfrage: {str(e)}")
            return 10000.0, 10800.0  # Fallback
    
    def convert_eur_to_usd(self, amount_eur):
        """Konvertiert EUR zu USD"""
        return amount_eur * self.eur_usd_rate
    
    def convert_usd_to_eur(self, amount_usd):
        """Konvertiert USD zu EUR"""
        return amount_usd / self.eur_usd_rate
    
    def calculate_position_size(self, balance_eur, balance_usd, asset_type):
        """Berechnet Positionsgröße basierend auf Depotwert und Hebel"""
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
    
    def get_market_analysis(self, balance_eur, balance_usd):
        """Erweiterte Marktanalyse mit Währungsumrechnung"""
        import random
        
        analysis = {}
        for asset, info in self.trading_assets.items():
            # Berechne Positionsgröße für dieses Asset
            position_size_usd, position_size_eur, leverage = self.calculate_position_size(
                balance_eur, balance_usd, info["type"]
            )
            
            # Simuliere Preise basierend auf Asset-Typ
            if info["type"] == "crypto":
                if asset == "BTC":
                    price = random.uniform(65000, 70000)
                elif asset == "ETH":
                    price = random.uniform(3500, 4000)
                elif asset == "SOL":
                    price = random.uniform(140, 160)
                else:
                    price = random.uniform(1, 1000)
            else:  # Rohstoffe
                if asset == "KUPFER":
                    price = random.uniform(3.5, 4.5)
                elif asset == "GAS":
                    price = random.uniform(2.0, 3.0)
            
            analysis[asset] = {
                "price": round(price, 3),
                "signal": random.choice(["LONG", "SHORT", "HOLD"]),
                "position_size_usd": round(position_size_usd, 2),
                "position_size_eur": round(position_size_eur, 2),
                "leverage": leverage,
                "type": info["type"],
                "epic": info["epic"]
            }
            
        return analysis
        
    def monitor_market(self):
        """Haupt-Monitoring Loop mit Währungsunterstützung"""
        self.logger.info("🚀 EUR-TRADING BOT GESTARTET")
        self.logger.info(f"💰 Kontowährung: {self.account_currency}")
        self.logger.info(f"📊 Handelsassets: {list(self.trading_assets.keys())}")
        self.logger.info(f"💱 Wechselkurs: 1 EUR = {self.eur_usd_rate:.2f} USD")
        
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # Depotwert ermitteln (in EUR und USD)
                balance_eur, balance_usd = self.get_account_balance()
                
                self.logger.info("=" * 70)
                self.logger.info(f"🔄 Analyse #{cycle} - {current_time}")
                self.logger.info(f"💶 Aktueller Depotwert: €{balance_eur:,.2f} EUR")
                self.logger.info(f"💵 Entspricht: ${balance_usd:,.2f} USD")
                
                # Erweiterte Marktanalyse
                analysis = self.get_market_analysis(balance_eur, balance_usd)
                
                # Trenne Ausgabe nach Asset-Typ mit beiden Währungen
                self.logger.info("🔧 ROHSTOFFE (20:1 Hebel) - Preise in USD:")
                for asset, data in analysis.items():
                    if data["type"] == "commodity":
                        signal_icon = "🟢" if data["signal"] == "LONG" else "🔴" if data["signal"] == "SHORT" else "🟡"
                        self.logger.info(f"   {signal_icon} {asset:6} | ${data['price']:7.3f} | {data['signal']:5} | Size: ${data['position_size_usd']:7.2f} (€{data['position_size_eur']:7.2f}) | {data['leverage']:2}:1")
                
                self.logger.info("₿  KRYPTO (2:1 Hebel) - Preise in USD:")
                for asset, data in analysis.items():
                    if data["type"] == "crypto":
                        signal_icon = "🟢" if data["signal"] == "LONG" else "🔴" if data["signal"] == "SHORT" else "🟡"
                        self.logger.info(f"   {signal_icon} {asset:6} | ${data['price']:7.2f} | {data['signal']:5} | Size: ${data['position_size_usd']:7.2f} (€{data['position_size_eur']:7.2f}) | {data['leverage']:2}:1")
                
                # Risikomanagement Info in beiden Währungen
                total_risk_eur = balance_eur * self.risk_per_trade
                total_risk_usd = balance_usd * self.risk_per_trade
                self.logger.info(f"🎯 Risikomanagement: €{total_risk_eur:,.2f} (${total_risk_usd:,.2f}) pro Trade ({self.risk_per_trade*100}% des Depots)")
                self.logger.info(f"⏰ Nächste Analyse in {self.check_interval} Sekunden...")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Fehler in Monitoring: {str(e)}")
                time.sleep(30)
    
    def start(self):
        """Startet den Bot"""
        self.logger.info("🤖 Starte EUR-Trading Bot...")
        
        try:
            monitor_thread = threading.Thread(target=self.monitor_market)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Hauptthread am Leben erhalten
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
    bot = EURTradingBot()
    bot.start()
