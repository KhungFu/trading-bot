#!/bin/bash
echo "🎯 Ubuntu 25.04 Trading Bot - Ein-Klick Installation"

# Bot herunterladen und installieren
cd /tmp
git clone https://github.com/KhungFu/trading-bot.git
cd trading-bot

# Installation ausführen
chmod +x install_trading_bot_simple.sh
./install_trading_bot_simple.sh

echo "✅ Installation abgeschlossen!"
echo "📝 Vergiss nicht deine API Keys in /opt/trading-bot/.env einzutragen"
echo "🚀 Starte dann mit: sudo systemctl start trading-bot"
