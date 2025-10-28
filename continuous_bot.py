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
import sys
from datetime import datetime

class AutoTradingBot:
    def __init__(self):
        self.setup_logging()
        self.running = True
        self.load_config()
        self.session = requests.Session()
        
        # Wechselkurs
        self.eur_usd_rate = 1.08
        
        # Trading-Assets mit spezifischen Einstellungen
        self.trading_assets = {
            "BTC": {"epic": "BTCUSD", "type": "crypto", "leverage": self.crypto_leverage, "lot_size": 0.01},
            "ETH": {"epic": "ETHUSD", "type": "crypto", "leverage": self.crypto_leverage, "lot_size": 0.1},
            "SOL": {"epic": "SOLUSD", "type": "crypto", "leverage": self.crypto_leverage, "lot_size": 1},
            "XRP": {"epic": "XRPUSD", "type": "crypto", "leverage": self.crypto_leverage, "lot_size": 100},
            "DOGE": {"epic": "DOGEUSD", "type": "crypto", "leverage": self.crypto_leverage, "lot_size": 1000},
            "BNB": {"epic": "BNBUSD", "type": "crypto", "leverage": self.crypto_leverage, "lot_size": 1},
            "KUPFER": {"epic": "COPPER", "type": "commodity", "leverage": self.commodity_leverage, "lot_size": 1},
            "GAS": {"epic": "NATGAS", "type": "commodity", "leverage": self.commodity_leverage, "lot_size": 1}
        }
        
        # Trading-Status
        self.open_positions = {}
        self.trade_history = []
        self.last_analysis = {}
        
    def setup_logging(self):
        """Setup Logging"""
        try:
            log_file = '/tmp/trading-bot.log'
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout)
                ]
            )
            self.logger = logging.getLogger('TradingBot')
            self.logger.info(f"✅ Logging initialisiert: {log_file}")
            
        except Exception as e:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            self.logger = logging.getLogger('TradingBot')
        
    def load_config(self):
        """Lädt Konfiguration"""
        self.api_key = os.getenv('CAPITAL_API_KEY', '').strip()
        self.api_secret = os.getenv('CAPITAL_API_SECRET', '').strip()
        self.account_id = os.getenv('CAPITAL_ACCOUNT_ID', '').strip()
        self.account_currency = os.getenv('ACCOUNT_CURRENCY', 'EUR')
        self.demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true'
        self.auto_trading = os.getenv('AUTO_TRADING', 'True').lower() == 'true'
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        # Hebel-Einstellungen
        self.crypto_leverage = int(os.getenv('CRYPTO_LEVERAGE', '2'))
        self.commodity_leverage = int(os.getenv('COMMODITY_LEVERAGE', '20'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.05'))
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '0.8'))
        
        # Trading-Parameter
        self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', '0.02'))
        self.take_profit_percent = float(os.getenv('TAKE_PROFIT_PERCENT', '0.04'))
        self.max_open_trades = int(os.getenv('MAX_OPEN_TRADES', '3'))
        self.enable_crypto = os.getenv('ENABLE_CRYPTO', 'True').lower() == 'true'
        self.enable_commodities = os.getenv('ENABLE_COMMODITIES', 'True').lower() == 'true'
        
        self.logger.info("✅ Auto-Trading Bot Konfiguration geladen")
        self.logger.info(f"🔧 Auto-Trading: {self.auto_trading}")
        self.logger.info(f"⚡ Krypto-Handel: {self.enable_crypto}, Rohstoff-Handel: {self.enable_commodities}")
        
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
        """Macht API Request"""
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
            
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = self.session.post(url, data=body, headers=headers, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code != 200:
                self.logger.error(f"❌ API Error {response.status_code}: {response.text}")
                return None
                
            return response.json()
            
        except Exception as e:
            self.logger.error(f"❌ API request failed: {str(e)}")
            return None
    
    def get_account_balance(self):
        """Ermittelt Depotwert"""
        try:
            response = self.api_request("GET", f"/accounts/{self.account_id}")
            if response:
                balance = response.get('balance', 0)
                available = response.get('available', 0)
                profit_loss = response.get('profitLoss', 0)
                currency = response.get('currency', 'EUR')
                
                balance_usd = balance * self.eur_usd_rate
                
                self.logger.info(f"💰 Depotwert: €{balance:,.2f} {currency}")
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
        """Ermittelt offene Positionen"""
        try:
            response = self.api_request("GET", "/positions")
            if response and 'positions' in response:
                positions = response['positions']
                
                # Aktualisiere unsere Positions-Datenbank
                self.open_positions = {}
                for position in positions:
                    epic = position.get('epic', 'Unknown')
                    deal_id = position.get('position', {}).get('dealId')
                    
                    # Finde Asset-Namen
                    asset_name = "Unknown"
                    for name, info in self.trading_assets.items():
                        if info['epic'] == epic:
                            asset_name = name
                            break
                    
                    if deal_id and asset_name != "Unknown":
                        self.open_positions[asset_name] = {
                            'deal_id': deal_id,
                            'epic': epic,
                            'direction': position.get('position', {}).get('direction', 'UNKNOWN'),
                            'size': position.get('position', {}).get('size', 0),
                            'profit': position.get('position', {}).get('profit', 0),
                            'open_level': position.get('position', {}).get('openLevel', 0)
                        }
                
                self.logger.info(f"📊 Offene Positionen: {len(self.open_positions)}")
                
                if self.open_positions:
                    total_pl = 0
                    for asset, pos in self.open_positions.items():
                        profit_color = "🟢" if pos['profit'] >= 0 else "🔴"
                        self.logger.info(f"   {profit_color} {asset:8} | {pos['direction']:4} | Size: {pos['size']:6.2f} | P&L: €{pos['profit']:8.2f}")
                        total_pl += pos['profit']
                    
                    self.logger.info(f"   📈 Gesamt-P&L: €{total_pl:8.2f}")
                else:
                    self.logger.info("   Keine offenen Positionen")
                    
                return self.open_positions
            else:
                self.logger.info("📊 Keine offenen Positionen gefunden")
                return {}
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abrufen der Positionen: {str(e)}")
            return {}
    
    def calculate_position_size(self, balance_eur, asset_type, current_price):
        """Berechnet Positionsgröße basierend auf Risiko und Preis"""
        risk_amount_eur = balance_eur * self.risk_per_trade
        
        if asset_type == "crypto":
            leverage = self.crypto_leverage
        else:
            leverage = self.commodity_leverage
            
        # Positionsgröße in Basiswährung berechnen
        position_value_eur = risk_amount_eur * leverage
        position_size = position_value_eur / current_price
        
        # Auf Lot-Größe anpassen
        lot_size = self.trading_assets.get(asset_type, {}).get('lot_size', 1)
        position_size = max(lot_size, (position_size // lot_size) * lot_size)
        
        return position_size, leverage, position_value_eur
    
    def execute_trade(self, asset, direction, current_price):
        """Führt einen Trade aus"""
        try:
            # Prüfe ob bereits eine Position in diesem Asset existiert
            if asset in self.open_positions:
                self.logger.info(f"⏭️  Trade übersprungen: Bereits Position in {asset}")
                return None
            
            # Prüfe maximale Anzahl offener Trades
            if len(self.open_positions) >= self.max_open_trades:
                self.logger.info(f"⏭️  Trade übersprungen: Maximale Anzahl offener Trades ({self.max_open_trades}) erreicht")
                return None
            
            balance_eur, _, _, _ = self.get_account_balance()
            if balance_eur <= 0:
                self.logger.error("❌ Trade abgebrochen: Kein Guthaben verfügbar")
                return None
            
            asset_info = self.trading_assets.get(asset)
            if not asset_info:
                self.logger.error(f"❌ Unbekanntes Asset: {asset}")
                return None
            
            # Positionsgröße berechnen
            position_size, leverage, position_value = self.calculate_position_size(
                balance_eur, asset_info['type'], current_price
            )
            
            # Stop-Loss und Take-Profit berechnen
            if direction == "BUY":
                stop_loss = current_price * (1 - self.stop_loss_percent)
                take_profit = current_price * (1 + self.take_profit_percent)
            else:  # SELL
                stop_loss = current_price * (1 + self.stop_loss_percent)
                take_profit = current_price * (1 - self.take_profit_percent)
            
            # Trade-Daten vorbereiten
            trade_data = {
                "epic": asset_info['epic'],
                "expiry": "-",
                "direction": direction,
                "size": position_size,
                "orderType": "MARKET",
                "timeInForce": "FILL_OR_KILL",
                "level": current_price,
                "guaranteedStop": False,
                "stopLevel": round(stop_loss, 4),
                "stopDistance": 0,
                "trailingStop": False,
                "profitLevel": round(take_profit, 4),
                "profitDistance": 0,
                "currencyCode": "USD"
            }
            
            self.logger.info(f"🎯 EXECUTING TRADE: {asset} {direction}")
            self.logger.info(f"   📏 Size: {position_size} | Leverage: {leverage}:1")
            self.logger.info(f"   💰 Value: €{position_value:,.2f}")
            self.logger.info(f"   🛑 Stop-Loss: {stop_loss:.4f}")
            self.logger.info(f"   🎯 Take-Profit: {take_profit:.4f}")
            
            # Trade ausführen
            response = self.api_request("POST", "/positions", trade_data)
            
            if response and 'dealReference' in response:
                self.logger.info(f"✅ TRADE ERFOLGREICH: Deal Reference: {response['dealReference']}")
                
                # Trade zur History hinzufügen
                trade_record = {
                    'timestamp': datetime.now(),
                    'asset': asset,
                    'direction': direction,
                    'size': position_size,
                    'price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'deal_reference': response['dealReference']
                }
                self.trade_history.append(trade_record)
                
                return response
            else:
                self.logger.error(f"❌ TRADE FEHLGESCHLAGEN: {response}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Trade-Execution: {str(e)}")
            return None
    
    def close_position(self, deal_id):
        """Schließt eine Position"""
        try:
            close_data = {
                "dealId": deal_id,
                "direction": "SELL",  # Für Long-Positionen
                "size": 1.0,  # Komplette Position schließen
                "orderType": "MARKET"
            }
            
            response = self.api_request("POST", "/positions/otc", close_data)
            
            if response and 'dealReference' in response:
                self.logger.info(f"✅ POSITION GESCHLOSSEN: Deal Reference: {response['dealReference']}")
                return response
            else:
                self.logger.error(f"❌ POSITION SCHLIESSEN FEHLGESCHLAGEN: {response}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Schließen der Position: {str(e)}")
            return None
    
    def analyze_market(self):
        """Einfache Marktanalyse für Trading-Signale"""
        import random
        
        signals = {}
        
        # Hier würde eine echte Analyse stattfinden
        # Für jetzt: Zufällige Signale basierend auf Asset-Typ
        for asset, info in self.trading_assets.items():
            # Filtere Assets basierend auf Konfiguration
            if info['type'] == 'crypto' and not self.enable_crypto:
                continue
            if info['type'] == 'commodity' and not self.enable_commodities:
                continue
            
            # Zufälliges Signal (später durch echte Analyse ersetzen)
            signal_choice = random.choices(
                ['BUY', 'SELL', 'HOLD'], 
                weights=[0.4, 0.4, 0.2], 
                k=1
            )[0]
            
            # Simulierter Preis
            if info['type'] == 'crypto':
                if asset == "BTC":
                    price = random.uniform(60000, 70000)
                elif asset == "ETH":
                    price = random.uniform(3000, 4000)
                elif asset == "SOL":
                    price = random.uniform(120, 180)
                else:
                    price = random.uniform(1, 1000)
            else:
                if asset == "KUPFER":
                    price = random.uniform(3.0, 4.5)
                elif asset == "GAS":
                    price = random.uniform(2.0, 3.5)
            
            signals[asset] = {
                'signal': signal_choice,
                'price': price,
                'type': info['type']
            }
        
        return signals
    
    def monitor_market(self):
        """Haupt-Monitoring Loop mit Auto-Trading"""
        self.logger.info("🚀 AUTO-TRADING BOT GESTARTET")
        self.logger.info(f"🔧 Auto-Trading: {self.auto_trading}")
        self.logger.info(f"⚡ Krypto: {self.enable_crypto} | Rohstoffe: {self.enable_commodities}")
        self.logger.info(f"🎯 Max. Trades: {self.max_open_trades} | Risiko: {self.risk_per_trade*100}%")
        
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                self.logger.info("=" * 70)
                self.logger.info(f"🔄 Auto-Trading Zyklus #{cycle} - {current_time}")
                
                # 1. Depotwert abrufen
                balance_eur, balance_usd, available, profit_loss = self.get_account_balance()
                
                # 2. Offene Positionen aktualisieren
                self.get_open_positions()
                
                # 3. Marktanalyse durchführen
                signals = self.analyze_market()
                self.last_analysis = signals
                
                # 4. Trading-Signale anzeigen
                self.logger.info("🎯 TRADING SIGNALE:")
                
                crypto_signals = {k: v for k, v in signals.items() if v['type'] == 'crypto'}
                commodity_signals = {k: v for k, v in signals.items() if v['type'] == 'commodity'}
                
                if crypto_signals and self.enable_crypto:
                    self.logger.info("₿  KRYPTO:")
                    for asset, data in crypto_signals.items():
                        signal_icon = "🟢" if data['signal'] == 'BUY' else "🔴" if data['signal'] == 'SELL' else "🟡"
                        self.logger.info(f"   {signal_icon} {asset:6} | ${data['price']:8.2f} | {data['signal']:4}")
                
                if commodity_signals and self.enable_commodities:
                    self.logger.info("🔧 ROHSTOFFE:")
                    for asset, data in commodity_signals.items():
                        signal_icon = "🟢" if data['signal'] == 'BUY' else "🔴" if data['signal'] == 'SELL' else "🟡"
                        self.logger.info(f"   {signal_icon} {asset:6} | ${data['price']:8.3f} | {data['signal']:4}")
                
                # 5. AUTO-TRADING: Trades ausführen
                if self.auto_trading and balance_eur > 0:
                    self.logger.info("🤖 AUTO-TRADING AKTIV - Prüfe Trade-Möglichkeiten...")
                    
                    trades_executed = 0
                    for asset, data in signals.items():
                        if data['signal'] in ['BUY', 'SELL'] and asset not in self.open_positions:
                            if trades_executed < 1:  # Max 1 Trade pro Zyklus
                                result = self.execute_trade(asset, data['signal'], data['price'])
                                if result:
                                    trades_executed += 1
                                    time.sleep(2)  # Kurze Pause zwischen Trades
                
                # 6. Risikomanagement-Info
                risk_eur = balance_eur * self.risk_per_trade
                risk_usd = balance_usd * self.risk_per_trade
                
                self.logger.info("📊 ZUSAMMENFASSUNG:")
                self.logger.info(f"   Offene Trades: {len(self.open_positions)}/{self.max_open_trades}")
                self.logger.info(f"   Risiko pro Trade: €{risk_eur:,.2f} (${risk_usd:,.2f})")
                self.logger.info(f"   Gesamt Trades: {len(self.trade_history)}")
                
                self.logger.info(f"⏰ Nächster Handels-Zyklus in {self.check_interval} Sekunden...")
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Fehler in Trading-Zyklus: {str(e)}")
                time.sleep(30)
    
    def start(self):
        """Startet den Bot"""
        self.logger.info("🤖 Starte Auto-Trading Bot...")
        
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
        self.logger.info("🛑 Auto-Trading Bot gestoppt")
        self.logger.info(f"📈 Handels-Historie: {len(self.trade_history)} Trades")

if __name__ == "__main__":
    try:
        bot = AutoTradingBot()
        bot.start()
    except Exception as e:
        print(f"❌ Bot konnte nicht gestartet werden: {str(e)}")
        sys.exit(1)
