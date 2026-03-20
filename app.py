from flask import Flask, request
import requests
import os
import logging
import sys

app = Flask(__name__)

# 🔹 LOGS
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


# 🔹 VERIFICACIÓN
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge, 200
    return "Error", 403


# 🔹 LOGIN ODOO
def login_odoo():
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
    logger.info(f"LOGIN: {res}")

    return res.get("result")


# 🔹 BUSCAR O CREAR CONTACTO (ABOX)
def get_or_create_partner(uid, numero):
    url = f"{ODOO_URL}/jsonrpc"

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


# 🔹 CHAT UNIFICADO (DISCUSS)
def send_to_discuss(uid, partner_id, texto):
    try:
        url = f"{ODOO_URL}/jsonrpc"

        # 🔹 1. BUSCAR SI YA EXISTE CHAT
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
                    "discuss.channel",
                    "search",
                    [[["channel_partner_ids", "in", [partner_id]]]]
                ]
            }
        }

        res = requests.post(url, json=search_payload).json()
        channel_ids = res.get("result")

        if channel_ids:
            channel_id = channel_ids[0]
            logger.info(f"CANAL EXISTENTE: {channel_id}")

        else:
            # 🔹 2. CREAR NUEVO CHAT
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

            res = requests.post(url, json=create_payload).json()
            channel_id = res.get("result")

            logger.info(f"CANAL NUEVO: {channel_id}")

        # 🔹 3. ENVIAR MENSAJE
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
        logger.info(f"MENSAJE ENVIADO: {res}")

    except Exception as e:
        logger.exception(f"ERROR DISCUSS: {e}")


# 🔹 WEBHOOK
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

                # 🔹 RESPUESTA AUTOMÁTICA
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

                # 🔹 ODOO
                uid = login_odoo()

                if uid:
                    partner_id = get_or_create_partner(uid, numero)

                    if partner_id:
                        send_to_discuss(uid, partner_id, texto)

            else:
                logger.info("Evento sin mensajes")

    except Exception as e:
        logger.exception(f"ERROR GENERAL: {e}")

    return "ok", 200


if __name__ == "__main__":
    logger.info("Servidor iniciado")
    app.run(host="0.0.0.0", port=5000)
