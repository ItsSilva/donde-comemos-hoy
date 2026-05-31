"""
app.py — Punto de entrada principal del servidor
Registra la API REST y el handler de Telegram en un solo proceso Flask.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from api.servidor import app
from api.telegram_handler import telegram_bp

# Registrar el blueprint de Telegram
app.register_blueprint(telegram_bp)

if __name__ == '__main__':
    port  = int(os.getenv('PORT', 5001))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    print(f"\n🍽️  ¿Dónde comemos hoy? corriendo en http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
