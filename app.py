from flask import Flask, request
import requests
import os

app = Flask(__name__)

# 🔐 WhatsApp
TOKEN = os.environ.get("TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

# 🔐 Odoo
ODOO_URL = os.environ.get("ODOO_URL")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_USER = os.environ.get("ODOO_USER")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

VERIFY_TOKEN = "ABOX_WHATSAPP_2026"

# 🔹 Verificación
@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Error", 403

# 🔹 LOGIN ODOO
def login_odoo():
    try:
        url = f"{ODOO_URL}/jsonrpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [ODOO_DB, ODOO_USER, ODOO_API_KEY]
            }
        }

        res = requests.post(url, json=payload).json()
        print("LOGIN RESPONSE:", res)

        return res.get("result")

    except Exception as e:
        print("LOGIN ERROR:", e)
        return None

# 🔹 BUSCAR O CREAR CONTACTO
def get_or_create_partner(uid, numero):
    try:
        url = f"{ODOO_URL}/jsonrpc"

        # Buscar
        search_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_API_KEY,
                    "res.partner",
                    "search",
                    [[["mobile", "=", numero]]]
                ]
            }
        }

        res = requests.post(url, json=search_payload).json()
        print("SEARCH RESPONSE:", res)

        ids = res.get("result")

        if ids:
            return ids[0]

        # Crear
        create_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_API_KEY,
                    "res.partner",
                    "create",
                    [{
                        "name": numero,
                        "mobile": numero
                    }]
                ]
            }
        }

        res = requests.post(url, json=create_payload).json()
        print("CREATE RESPONSE:", res)

        return res.get("result")

    except Exception as e:
        print("PARTNER ERROR:", e)
        return None

# 🔹 GUARDAR MENSAJE
def save_message(uid, partner_id, texto):
    try:
        url = f"{ODOO_URL}/jsonrpc"

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_API_KEY,
                    "mail.message",
                    "create",
                    [{
                        "body": texto,
                        "message_type": "comment",
                        "partner_ids": [(4, partner_id)]
                    }]
                ]
            }
        }

        res = requests.post(url, json=payload).json()
        print("MESSAGE RESPONSE:", res)

    except Exception as e:
        print("MESSAGE ERROR:", e)

# 🔹 WEBHOOK
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    try:
        print("DATA RECIBIDA:", data)

        if "entry" in data:
            value = data["entry"][0]["changes"][0]["value"]

            if "messages" in value:
                mensaje_data = value["messages"][0]
                numero = mensaje_data["from"]
                texto = mensaje_data["text"]["body"]

                print("NUMERO:", numero)
                print("MENSAJE:", texto)

                # 🔹 RESPUESTA AUTOMÁTICA
                mensaje = """Hola 👋

Este número es exclusivo para notificaciones automáticas de ABOX PTY 📦

Para atención personalizada escríbenos al:
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
                    "text": {"body": mensaje}
                }

                wa_response = requests.post(url, headers=headers, json=payload)
                print("WHATSAPP RESPONSE:", wa_response.status_code, wa_response.text)

                # 🔹 ODOO
                uid = login_odoo()
                print("UID:", uid)

                if uid:
                    partner_id = get_or_create_partner(uid, numero)
                    print("PARTNER ID:", partner_id)

                    if partner_id:
                        save_message(uid, partner_id, texto)

    except Exception as e:
        print("ERROR GENERAL:", e)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
