# Alte Datei löschen
sudo rm /opt/trading-bot/continuous_bot.py

# Korrigierte Datei erstellen
sudo tee /opt/trading-bot/continuous_bot.py > /dev/null << 'EOF'
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

class SimpleTradingBot:
    def __init__(self):
        self.load_config()
        self.setup_logging()
        self.session = requests.Session()
        self.running = True
        
        # Trading pairs
        self.crypto_epics = {
            "BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD",
            "XRP": "XRPUSD", "DOGE": "DOGEUSD", "BNB": "BNBUSD"
        }
        
    def load_config(self):
        """Load configuration from environment variables"""
        self.api_key = os.getenv('CAPITAL_API_KEY', '')
        self.api_secret = os.getenv('CAPITAL_API_SECRET', '')
        self.account_id = os.getenv('CAPITAL_ACCOUNT_ID', '')
        self.demo_mode = os.getenv('DEMO_MODE', 'True').lower() == 'true'
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        if not self.api_key:
            raise ValueError("CAPITAL_API_KEY not set!")
    
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/var/log/trading-bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('TradingBot')
    
    def generate_signature(self, method, path, body=""):
        """Generate API signature"""
        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + path + body
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return timestamp, signature
    
    def api_request(self, method, endpoint, data=None):
        """Make API request"""
        try:
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
            self.logger.error(f"API Error: {str(e)}")
            return None
    
    def get_account_info(self):
        """Get account information"""
        return self.api_request("GET", f"/accounts/{self.account_id}")
    
    def get_positions(self):
        """Get open positions"""
        return self.api_request("GET", "/positions")
    
    def monitor_market(self):
        """Main monitoring loop"""
        self.logger.info(f"Trading Bot started (Interval: {self.check_interval}s)")
        
        while self.running:
            try:
                # Check account status
                account_info = self.get_account_info()
                if account_info:
                    balance = account_info.get('balance', 'Unknown')
                    self.logger.info(f"Account Balance: ${balance}")
                
                # Check positions
                positions = self.get_positions()
                if positions:
                    open_positions = positions.get('positions', [])
                    self.logger.info(f"Open Positions: {len(open_positions)}")
                    
                    for position in open_positions:
                        epic = position.get('epic', '')
                        coin = next((k for k, v in self.crypto_epics.items() if v == epic), 'Unknown')
                        profit = position.get('position', {}).get('profit', 0)
                        self.logger.info(f"   {coin}: ${profit:.2f}")
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring Error: {str(e)}")
                time.sleep(30)  # Wait 30 seconds on error
    
    def start(self):
        """Start the bot"""
        try:
            # Test login
            self.logger.info("Connecting to Capital.com...")
            account_info = self.get_account_info()
            if account_info:
                self.logger.info("Successfully connected!")
                
                # Start monitoring in separate thread
                monitor_thread = threading.Thread(target=self.monitor_market)
                monitor_thread.daemon = True
                monitor_thread.start()
                
                # Keep main thread alive
                while self.running:
                    time.sleep(1)
                    
            else:
                self.logger.error("Connection failed!")
                
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            self.logger.error(f"Start failed: {str(e)}")
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        self.logger.info("Bot stopped")

if __name__ == "__main__":
    bot = SimpleTradingBot()
    bot.start()
EOF
