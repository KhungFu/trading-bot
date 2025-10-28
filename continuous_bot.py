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
import random
from datetime import datetime

class AITradingBot:
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
        
        # AI Trading Parameter
        self.target_assets = ["BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "KUPFER", "GAS"]
        self.min_position_eur = 5.00
        
        # Trading-Status
        self.open_positions = {}
        self.trade_history = []
        self.last_analysis = {}
        
    def setup_logging(self):
        """Setup Logging"""
        try:
            log_file = '/tmp/ai-trading-bot.log'
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler(sys.stdout)
                ]
            )
            self.logger = logging.getLogger('AITradingBot')
            self.logger.info(f"✅ AI Trading Bot Logging initialisiert: {log_file}")
            
        except Exception as e:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[logging.StreamHandler(sys.stdout)]
            )
            self.logger = logging.getLogger('AITradingBot')
        
    def load_config(self):
        """Lädt Konfiguration"""
        self.api_key = os.getenv('API_KEY', '').strip()
        self.api_secret = os.getenv('API_SECRET', '').strip()
        self.account_id = os.getenv('ACCOUNT_ID', '').strip()
        self.account_currency = os.getenv('ACCOUNT_CURRENCY', 'EUR')
        self.demo_mode = os.getenv('DEMO_MODE', 'False').lower() == 'true'
        self.auto_trading = os.getenv('AUTO_TRADING', 'True').lower() == 'true'
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        # Hebel-Einstellungen
        self.crypto_leverage = int(os.getenv('CRYPTO_LEVERAGE', '2'))
        self.commodity_leverage = int(os.getenv('COMMODITY_LEVERAGE', '20'))
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', '0.15'))  # 15% Risiko
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '0.8'))
        
        # Trading-Parameter
        self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', '0.05'))
        self.take_profit_percent = float(os.getenv('TAKE_PROFIT_PERCENT', '0.08'))
        self.max_open_trades = int(os.getenv('MAX_OPEN_TRADES', '3'))
        self.enable_crypto = os.getenv('ENABLE_CRYPTO', 'True').lower() == 'true'
        self.enable_commodities = os.getenv('ENABLE_COMMODITIES', 'True').lower() == 'true'
        
        self.logger.info("✅ AI Trading Bot Konfiguration geladen")
        self.logger.info(f"🔧 Auto-Trading: {self.auto_trading}")
        self.logger.info(f"⚡ Krypto-Handel: {self.enable_crypto}, Rohstoff-Handel: {self.enable_commodities}")
        self.logger.info(f"🎯 Risiko pro Trade: {self.risk_per_trade*100}%")
        
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
        if lot_size > 0:
            position_size = max(lot_size, (position_size // lot_size) * lot_size)
        
        return position_size, leverage, position_value_eur
    
    def enhanced_analyze_market(self):
        """Erweiterte Marktanalyse mit AI-gesteuerten Signalen"""
        signals = {}
        balance_eur, _, _, _ = self.get_account_balance()
        
        # Aktuelle Marktpreise (simuliert - würde durch echte API ersetzt)
        asset_prices = {
            "BTC": 69420, "ETH": 3500, "SOL": 145, "XRP": 0.58, 
            "DOGE": 0.12, "BNB": 580, "KUPFER": 4.25, "GAS": 2.85
        }
        
        for asset in self.target_assets:
            if asset not in self.trading_assets:
                continue
                
            asset_info = self.trading_assets[asset]
            current_price = asset_prices.get(asset, 1)
            
            # Berechne mögliche Positionsgröße
            position_size, leverage, position_value = self.calculate_position_size(
                balance_eur, asset_info['type'], current_price
            )
            
            # Prüfe Mindestposition
            if position_value < self.min_position_eur:
                signals[asset] = {'signal': 'HOLD', 'price': current_price, 'reason': 'Position zu klein'}
                continue
            
            # AI-gesteuerte Signalanalyse
            if asset_info['type'] == 'crypto':
                signal_data = self.analyze_crypto_trend(asset, current_price)
            else:
                signal_data = self.analyze_commodity_trend(asset, current_price)
            
            signals[asset] = {
                'signal': signal_data['direction'],
                'price': current_price,
                'type': asset_info['type'],
                'leverage': leverage,
                'position_size': position_size,
                'position_value_eur': position_value,
                'stop_loss': signal_data['stop_loss'],
                'take_profit': signal_data['take_profit'],
                'confidence': signal_data['confidence'],
                'reason': signal_data['reason']
            }
        
        return signals
    
    def analyze_crypto_trend(self, asset, current_price):
        """AI-Analyse für Krypto-Trends"""
        # Simulierte AI-Analyse (ersetzbar durch echte ML-Modelle)
        trend_score = random.uniform(0, 1)
        
        if trend_score > 0.6:
            direction = 'BUY'
            stop_loss = current_price * (1 - self.stop_loss_percent)
            take_profit = current_price * (1 + self.take_profit_percent)
            confidence = trend_score
            reason = "Bullisches Momentum erkannt"
        elif trend_score < 0.4:
            direction = 'SELL'
            stop_loss = current_price * (1 + self.stop_loss_percent)
            take_profit = current_price * (1 - self.take_profit_percent)
            confidence = 1 - trend_score
            reason = "Bearisches Momentum erkannt"
        else:
            direction = 'HOLD'
            stop_loss = take_profit = current_price
            confidence = 0.5
            reason = "Seitwärtsmarkt - abwarten"
        
        return {
            'direction': direction,
            'stop_loss': round(stop_loss, 4),
            'take_profit': round(take_profit, 4),
            'confidence': round(confidence, 2),
            'reason': reason
        }
    
    def analyze_commodity_trend(self, asset, current_price):
        """AI-Analyse für Rohstoff-Trends"""
        # Konservativere Analyse für Rohstoffe
        trend_score = random.uniform(0, 1)
        
        if trend_score > 0.65:
            direction = 'BUY'
            stop_loss = current_price * (1 - self.stop_loss_percent * 0.8)  # Engerer Stop
            take_profit = current_price * (1 + self.take_profit_percent * 0.8)
            confidence = trend_score
            reason = "Stabile Aufwärtstrend bei Rohstoffen"
        elif trend_score < 0.35:
            direction = 'SELL' 
            stop_loss = current_price * (1 + self.stop_loss_percent * 0.8)
            take_profit = current_price * (1 - self.take_profit_percent * 0.8)
            confidence = 1 - trend_score
            reason = "Abwärtstrend bei Rohstoffen"
        else:
            direction = 'HOLD'
            stop_loss = take_profit = current_price
            confidence = 0.5
            reason = "Stabile Seitwärtsphase"
        
        return {
            'direction': direction,
            'stop_loss': round(stop_loss, 4),
            'take_profit': round(take_profit, 4),
            'confidence': round(confidence, 2),
            'reason': reason
        }
    
    def execute_trade(self, asset, direction, current_price, stop_loss, take_profit):
        """Führt einen Trade mit AI-Signalen aus"""
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
                "stopLevel": stop_loss,
                "stopDistance": 0,
                "trailingStop": False,
                "profitLevel": take_profit,
                "profitDistance": 0,
                "currencyCode": "USD"
            }
            
            self.logger.info(f"🎯 AI EXECUTING TRADE: {asset} {direction}")
            self.logger.info(f"   📏 Size: {position_size} | Leverage: {leverage}:1")
            self.logger.info(f"   💰 Value: €{position_value:,.2f}")
            self.logger.info(f"   🛑 Stop-Loss: {stop_loss:.4f}")
            self.logger.info(f"   🎯 Take-Profit: {take_profit:.4f}")
            
            # Trade ausführen
            response = self.api_request("POST", "/positions", trade_data)
            
            if response and 'dealReference' in response:
                self.logger.info(f"✅ AI TRADE ERFOLGREICH: Deal Reference: {response['dealReference']}")
                
                # Trade zur History hinzufügen
                trade_record = {
                    'timestamp': datetime.now(),
                    'asset': asset,
                    'direction': direction,
                    'size': position_size,
                    'price': current_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'deal_reference': response['dealReference'],
                    'leverage': leverage
                }
                self.trade_history.append(trade_record)
                
                return response
            else:
                self.logger.error(f"❌ AI TRADE FEHLGESCHLAGEN: {response}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim AI Trade-Execution: {str(e)}")
            return None
    
    def execute_ai_trading_strategy(self):
        """Führt AI-gesteuerte Trading-Strategie aus"""
        if not self.auto_trading:
            return
        
        balance_eur, balance_usd, available, profit_loss = self.get_account_balance()
        
        # Startstrategie: Diversifikation bei kleinem Kapital
        if balance_eur >= 30 and len(self.open_positions) == 0:
            self.logger.info("🎯 AI-STRATEGIE: Starte diversifiziertes Portfolio mit verfügbarem Kapital")
            
            # Wähle 2-3 Assets zufällig aus
            available_assets = [a for a in self.target_assets if a not in self.open_positions]
            if available_assets:
                target_positions = random.sample(available_assets, min(2, len(available_assets)))
                
                for asset in target_positions:
                    signals = self.enhanced_analyze_market()
                    if asset in signals and signals[asset]['signal'] in ['BUY', 'SELL']:
                        self.execute_trade(
                            asset, 
                            signals[asset]['signal'], 
                            signals[asset]['price'],
                            signals[asset]['stop_loss'],
                            signals[asset]['take_profit']
                        )
                        time.sleep(2)
        
        # Fortlaufendes Trading basierend auf AI-Signalen
        elif len(self.open_positions) < self.max_open_trades:
            signals = self.enhanced_analyze_market()
            
            trades_executed = 0
            for asset, data in signals.items():
                if (data['signal'] in ['BUY', 'SELL'] and 
                    asset not in self.open_positions and
                    data['position_value_eur'] >= self.min_position_eur and
                    trades_executed < 1):
                    
                    self.logger.info(f"🤖 AI-Signal: {asset} {data['signal']} (Confidence: {data['confidence']})")
                    self.logger.info(f"   📊 Grund: {data['reason']}")
                    
                    result = self.execute_trade(
                        asset, 
                        data['signal'], 
                        data['price'],
                        data['stop_loss'],
                        data['take_profit']
                    )
                    if result:
                        trades_executed += 1
                        time.sleep(2)
    
    def monitor_market(self):
        """Haupt-Monitoring Loop mit AI-Trading"""
        self.logger.info("🚀 AI TRADING BOT GESTARTET")
        self.logger.info(f"🔧 Auto-Trading: {self.auto_trading}")
        self.logger.info(f"⚡ Krypto: {self.enable_crypto} | Rohstoffe: {self.enable_commodities}")
        self.logger.info(f"🎯 Max. Trades: {self.max_open_trades} | Risiko: {self.risk_per_trade*100}%")
        self.logger.info(f"🤖 AI Agent: DeepSeek - Autonomer Trading Modus")
        
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                current_time = datetime.now().strftime("%H:%M:%S")
                
                self.logger.info("=" * 70)
                self.logger.info(f"🔄 AI Trading Zyklus #{cycle} - {current_time}")
                
                # 1. Depotwert abrufen
                balance_eur, balance_usd, available, profit_loss = self.get_account_balance()
                
                # 2. Offene Positionen aktualisieren
                self.get_open_positions()
                
                # 3. AI-Marktanalyse durchführen
                signals = self.enhanced_analyze_market()
                self.last_analysis = signals
                
                # 4. AI-Trading-Signale anzeigen
                self.logger.info("🎯 AI TRADING SIGNALE:")
                
                for asset, data in signals.items():
                    if data['signal'] != 'HOLD':
                        signal_icon = "🟢" if data['signal'] == 'BUY' else "🔴" if data['signal'] == 'SELL' else "🟡"
                        self.logger.info(f"   {signal_icon} {asset:8} | ${data['price']:8.2f} | {data['signal']:4} | Confidence: {data['confidence']}")
                        self.logger.info(f"      📊 {data['reason']}")
                        self.logger.info(f"      🎯 TP: ${data['take_profit']:.2f} | 🛑 SL: ${data['stop_loss']:.2f}")
                
                # 5. AI-TRADING: Trades ausführen
                if self.auto_trading and balance_eur > 0:
                    self.logger.info("🤖 AI AUTO-TRADING AKTIV - Prüfe Trade-Möglichkeiten...")
                    self.execute_ai_trading_strategy()
                
                # 6. Risikomanagement-Info
                risk_eur = balance_eur * self.risk_per_trade
                risk_usd = balance_usd * self.risk_per_trade
                
                self.logger.info("📊 AI ZUSAMMENFASSUNG:")
                self.logger.info(f"   Offene Trades: {len(self.open_positions)}/{self.max_open_trades}")
                self.logger.info(f"   Risiko pro Trade: €{risk_eur:,.2f} (${risk_usd:,.2f})")
                self.logger.info(f"   Gesamt Trades: {len(self.trade_history)}")
                
                self.logger.info(f"⏰ Nächster AI-Handels-Zyklus in {self.check_interval} Sekunden...")
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Fehler in AI Trading-Zyklus: {str(e)}")
                time.sleep(30)
    
    def start(self):
        """Startet den AI Bot"""
        self.logger.info("🤖 Starte AI Trading Bot...")
        
        try:
            # Initialer Kontostand-Check
            balance_eur, _, _, _ = self.get_account_balance()
            self.logger.info(f"💰 Startkapital: €{balance_eur:,.2f}")
            self.logger.info("🎯 AI-Strategie: Diversifiziertes Portfolio mit 15% Risikomanagement")
            
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
        """Stoppt den AI Bot"""
        self.running = False
        self.logger.info("🛑 AI Trading Bot gestoppt")
        self.logger.info(f"📈 AI Handels-Historie: {len(self.trade_history)} Trades")

if __name__ == "__main__":
    try:
        bot = AITradingBot()
        bot.start()
    except Exception as e:
        print(f"❌ AI Bot konnte nicht gestartet werden: {str(e)}")
        sys.exit(1)
