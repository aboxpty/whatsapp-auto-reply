from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.environ.get("TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

VERIFY_TOKEN = "ABOX_WHATSAPP_2026"

@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Error de verificación", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    try:
        if "entry" in data:
            value = data["entry"][0]["changes"][0]["value"]

            if "messages" in value:
                numero = value["messages"][0]["from"]

                mensaje = """Hola 👋

Este número es exclusivo para notificaciones automáticas de ABOX PTY 📦

Para atención personalizada al:
👉 https://wa.me/50768181081

¡Con gusto te atenderemos! 🙌
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

                requests.post(url, headers=headers, json=payload)

    except Exception as e:
        print("Error:", e)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
