#!/bin/bash
# Einfaches Management Script für den Trading Bot

case "$1" in
    start)
        echo "🚀 Starte Trading Bot..."
        sudo systemctl start trading-bot
        ;;
    stop)
        echo "🛑 Stoppe Trading Bot..."
        sudo systemctl stop trading-bot
        ;;
    status)
        echo "📊 Bot Status:"
        sudo systemctl status trading-bot
        ;;
    logs)
        echo "📋 Zeige Logs:"
        journalctl -u trading-bot -f
        ;;
    restart)
        echo "🔁 Neustart Trading Bot..."
        sudo systemctl restart trading-bot
        ;;
    config)
        echo "⚙️ Öffne Konfiguration..."
        nano /opt/trading-bot/.env
        ;;
    update)
        echo "📥 Aktualisiere Bot..."
        cd /opt/trading-bot
        git pull
        sudo systemctl restart trading-bot
        ;;
    *)
        echo "Verwendung: $0 {start|stop|status|logs|restart|config|update}"
        echo ""
        echo "Beispiele:"
        echo "  $0 start    - Bot starten"
        echo "  $0 logs     - Logs anzeigen" 
        echo "  $0 config   - Konfiguration bearbeiten"
        echo "  $0 update   - Bot aktualisieren"
        exit 1
esac
