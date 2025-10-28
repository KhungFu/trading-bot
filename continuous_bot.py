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

class FlexibleTradingBot:
    def __init__(self):
        self.setup_logging()
        self.running = True
        self.load_config()
        
        self.crypto_epics = {
            "BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD",
            "XRP": "XRPUSD", "DOGE": "DOGEUSD", "BNB": "BNBUSD"
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
        self.api_key = os.getenv('CAPITAL_API_KEY', 'demo_key')
        self.api_secret = os.getenv('CAPITAL_API_SECRET', 'demo_secret')
        self.account_id = os.getenv('CAPITAL_ACCOUNT_ID', 'unknown')
        self.demo_mode = os.getenv('DEMO_MODE', 'True').lower() == 'true'
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        self.logger.info(f"Config loaded - Account ID: {self.account_id}")
        
    def get_market_analysis(self):
        """Marktanalyse ohne API Calls"""
        analysis = {
            "BTC": {"price": 69250, "signal": "LONG", "tp": 72500, "sl": 66500},
            "ETH": {"price": 3520, "signal": "HOLD", "tp": 3800, "sl": 3400},
            "SOL": {"price": 148.50, "signal": "LONG", "tp": 165, "sl": 135},
            "XRP": {"price": 0.532, "signal": "HOLD", "tp": 0.58, "sl": 0.50},
            "DOGE": {"price": 0.128, "signal": "SHORT", "tp": 0.115, "sl": 0.140},
            "BNB": {"price": 615, "signal": "LONG", "tp": 650, "sl": 590}
        }
        return analysis
        
    def monitor_market(self):
        """Haupt-Monitoring Loop"""
        self.logger.info("🚀 Trading Bot gestartet!")
        self.logger.info("💡 Aktuell im Demo-Modus ohne API Verbindung")
        self.logger.info("📝 So findest du deine Account ID:")
        self.logger.info("   1. Logge dich auf capital.com ein")
        self.logger.info("   2. Gehe zu 'Einstellungen' → 'API Management'") 
        self.logger.info("   3. Erstelle einen neuen API Key")
        self.logger.info("   4. Kopiere Account ID, API Key und Secret")
        
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                self.logger.info(f"🔄 Zyklus #{cycle} - {current_time}")
                self.logger.info("📊 AKTUELLE MARKTANALYSE:")
                
                # Simulierte Marktanalyse
                analysis = self.get_market_analysis()
                for coin, data in analysis.items():
                    signal_icon = "📈" if data["signal"] == "LONG" else "📉" if data["signal"] == "SHORT" else "⏸️"
                    self.logger.info(f"   {signal_icon} {coin}: ${data['price']} | {data['signal']} | TP: ${data['tp']} | SL: ${data['sl']}")
                
                # Kontostand-Info
                self.logger.info(f"💰 Simulierter Kontostand: $10,000")
                self.logger.info(f"⏰ Nächste Analyse in {self.check_interval} Sekunden...")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Fehler: {str(e)}")
                time.sleep(30)
    
    def start(self):
        """Startet den Bot"""
        self.logger.info("🤖 Starte Trading Bot...")
        
        monitor_thread = threading.Thread(target=self.monitor_market)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stoppt den Bot"""
        self.running = False
        self.logger.info("🛑 Bot gestoppt")

if __name__ == "__main__":
    bot = FlexibleTradingBot()
    bot.start()
