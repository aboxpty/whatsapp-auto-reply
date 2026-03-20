from flask import Flask, request
import requests
import os
import logging
import sys

app = Flask(__name__)

# 🔹 LOGS (para Render)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# 🔐 WhatsApp
TOKEN = os.environ.get("TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

# 🔐 Odoo
ODOO_URL = os.environ.get("ODOO_URL")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_USER = os.environ.get("ODOO_USER")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")

VERIFY_TOKEN = "ABOX_WHATSAPP_2026"


# 🔹 Verificación webhook
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200
    return "Error", 403


# 🔹 Login Odoo
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
        logger.info(f"LOGIN ODOO: {res}")

        return res.get("result")

    except Exception as e:
        logger.exception(f"LOGIN ERROR: {e}")
        return None


# 🔹 Buscar o crear contacto (ABOX PTY)
def get_or_create_partner(uid, numero):
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
    ids = res.get("result")

    if ids:
        return ids[0]

    # Crear contacto en ABOX (company_id = 2)
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
                    "mobile": numero,
                    "company_id": 2,
                    "company_type": "person"
                }]
            ]
        }
    }

    res = requests.post(url, json=create_payload).json()
    return res.get("result")


# 🔹 Enviar a DISCUSS (Odoo moderno)
def send_to_discuss(uid, partner_id, texto):
    try:
        url = f"{ODOO_URL}/jsonrpc"

        # Crear canal de chat
        create_channel_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_API_KEY,
                    "discuss.channel",
                    "create",
                    [{
                        "name": f"WhatsApp {partner_id}",
                        "channel_type": "chat",
                        "channel_partner_ids": [(4, partner_id)]
                    }]
                ]
            }
        }

        res = requests.post(url, json=create_channel_payload).json()
        logger.info(f"CHANNEL CREATE: {res}")

        channel_id = res.get("result")

        if not channel_id:
            return

        # Enviar mensaje al chat
        message_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_API_KEY,
                    "discuss.channel",
                    "message_post",
                    [channel_id],
                    {
                        "body": texto,
                        "message_type": "comment"
                    }
                ]
            }
        }

        res = requests.post(url, json=message_payload).json()
        logger.info(f"DISCUSS MESSAGE: {res}")

    except Exception as e:
        logger.exception(f"DISCUSS ERROR: {e}")


# 🔹 Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logger.info(f"DATA: {data}")

    try:
        if data and "entry" in data:
            value = data["entry"][0]["changes"][0]["value"]

            if "messages" in value:
                mensaje_data = value["messages"][0]

                numero = mensaje_data["from"]
                texto = mensaje_data.get("text", {}).get("body", "")

                logger.info(f"NUMERO: {numero}")
                logger.info(f"TEXTO: {texto}")

                # 🔹 Respuesta automática WhatsApp
                mensaje = """Hola 👋

Este número es exclusivo para notificaciones automáticas de ABOX PTY 📦

Para atención personalizada:
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

                requests.post(url, headers=headers, json=payload)

                # 🔹 Odoo
                uid = login_odoo()

                if uid:
                    partner_id = get_or_create_partner(uid, numero)

                    if partner_id:
                        send_to_discuss(uid, partner_id, texto)

            else:
                logger.info("Evento sin messages")

    except Exception as e:
        logger.exception(f"ERROR GENERAL: {e}")

    return "ok", 200


if __name__ == "__main__":
    logger.info("Servidor iniciado")
    app.run(host="0.0.0.0", port=5000)
