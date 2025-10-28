#!/bin/bash
echo "🤖 Trading Bot Installation für Ubuntu 25.04"

# Farben für Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# System aktualisieren
echo -e "${BLUE}🔧 System wird aktualisiert...${NC}"
sudo apt update && sudo apt upgrade -y

# Python und Abhängigkeiten installieren
echo -e "${BLUE}🐍 Installiere Python und Abhängigkeiten...${NC}"
sudo apt install -y python3 python3-pip python3-venv git curl

# Trading Bot Verzeichnis erstellen
echo -e "${BLUE}📁 Erstelle Bot-Verzeichnis...${NC}"
sudo mkdir -p /opt/trading-bot
sudo chown $USER:$USER /opt/trading-bot
cd /opt/trading-bot

# Python Virtual Environment erstellen
echo -e "${BLUE}🐍 Python Virtual Environment wird eingerichtet...${NC}"
python3 -m venv bot-env
source bot-env/bin/activate

# Bot Dateien herunterladen
echo -e "${BLUE}📥 Lade Bot-Code herunter...${NC}"
curl -L https://raw.githubusercontent.com/KhungFu/trading-bot/main/continuous_bot.py -o continuous_bot.py
curl -L https://raw.githubusercontent.com/KhungFu/trading-bot/main/requirements.txt -o requirements.txt

# Abhängigkeiten installieren
echo -e "${BLUE}📚 Installiere Python-Pakete...${NC}"
pip install -r requirements.txt

# Konfigurationsdatei erstellen
echo -e "${BLUE}⚙️ Erstelle Konfiguration...${NC}"
cat > .env << EOF
# Deine echten Capital.com API Daten HIER EINTRAGEN:
CAPITAL_API_KEY=dein_echter_api_key
CAPITAL_API_SECRET=dein_echter_api_secret
CAPITAL_ACCOUNT_ID=deine_echte_account_id

# Auf LIVE umstellen:
DEMO_MODE=False
ACCOUNT_CURRENCY=EUR
CHECK_INTERVAL=60

# Hebel-Einstellungen
CRYPTO_LEVERAGE=2
COMMODITY_LEVERAGE=20

# Risikomanagement
RISK_PER_TRADE=0.1
MAX_POSITION_SIZE=0.8
EOF

# Systemd Service erstellen
echo -e "${BLUE}🎯 Erstelle Systemd Service...${NC}"
sudo tee /etc/systemd/system/trading-bot.service > /dev/null << EOF
[Unit]
Description=Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/trading-bot
Environment=PATH=/opt/trading-bot/bot-env/bin
ExecStart=/opt/trading-bot/bot-env/bin/python3 /opt/trading-bot/continuous_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable trading-bot

echo -e "${GREEN}✅ Installation abgeschlossen!${NC}"
echo ""
echo -e "${BLUE}📋 Nächste Schritte:${NC}"
echo "1. Bearbeite die Konfiguration: nano /opt/trading-bot/.env"
echo "2. Setze deine Capital.com API Keys"
echo "3. Starte den Bot: sudo systemctl start trading-bot"
echo "4. Prüfe Status: sudo systemctl status trading-bot"
echo "5. Logs anzeigen: journalctl -u trading-bot -f"
