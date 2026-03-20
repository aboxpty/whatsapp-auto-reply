from flask import Flask, request
import requests
import os

app = Flask(__name__)

# 🔐 Variables de entorno (NO poner en el código)
TOKEN = os.environ.get("TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

# 🔑 Verify Token (debe coincidir con Meta)
VERIFY_TOKEN = "ABOX_WHATSAPP_2026"

# 🔹 Verificación del webhook (Meta)
@app.route('/webhook', methods=['GET'])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Verification failed", 403

# 🔹 Recibir mensajes y responder automáticamente
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    try:
        # Validar que venga mensaje
        if "entry" in data:
            changes = data["entry"][0]["changes"][0]["value"]

            if "messages" in changes:
                mensaje_data = changes["messages"][0]
                numero = mensaje_data["from"]

                mensaje = """Hola 👋

Este número es solo para notificaciones automáticas de ABOX 📦

Para atención personalizada:
👉 https://wa.me/68181081

Gracias 🙌
"""

                url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"

                headers = {
                    "Authorization": f"Bearer {TOKEN}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "messaging_product": "whatsapp",
                    "to": numero,
                    "type": "text",
                    "text": {
                        "body": mensaje
                    }
                }

                response = requests.post(url, headers=headers, json=payload)

                print("Respuesta enviada:", response.status_code, response.text)

    except Exception as e:
        print("Error:", str(e))

    return "ok", 200

# 🔹 Ejecutar local / Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
