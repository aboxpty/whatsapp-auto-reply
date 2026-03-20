from flask import Flask, request
import requests
import os
import logging
import sys

app = Flask(__name__)

# 🔹 LOGS (IMPORTANTE PARA RENDER)
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

# 🔹 VERIFICACIÓN WEBHOOK
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info("GET webhook verify")

    if token == VERIFY_TOKEN:
        return challenge, 200
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
        logger.info(f"LOGIN RESPONSE ODOO: {res}")

        return res.get("result")

    except Exception as e:
        logger.exception(f"LOGIN ERROR: {e}")
        return None


# 🔹 BUSCAR O CREAR CONTACTO
def get_or_create_partner(uid, numero):
    try:
        url = f"{ODOO_URL}/jsonrpc"

        # Buscar contacto
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
        logger.info(f"SEARCH RESPONSE ODOO: {res}")

        ids = res.get("result")

        if ids:
            return ids[0]

        # Crear contacto en ABOX PTY (company_id = 2)
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
        logger.info(f"CREATE RESPONSE ODOO: {res}")

        return res.get("result")

    except Exception as e:
        logger.exception(f"PARTNER ERROR: {e}")
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
        logger.info(f"MESSAGE RESPONSE ODOO: {res}")

    except Exception as e:
        logger.exception(f"MESSAGE ERROR: {e}")


# 🔹 WEBHOOK PRINCIPAL
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logger.info(f"DATA COMPLETA: {data}")

    try:
        if data and "entry" in data:
            value = data["entry"][0]["changes"][0]["value"]
            logger.info(f"VALUE: {value}")

            # Solo si hay mensajes
            if "messages" in value:
                mensaje_data = value["messages"][0]
                numero = mensaje_data["from"]
                texto = mensaje_data.get("text", {}).get("body", "")

                logger.info(f"NUMERO: {numero}")
                logger.info(f"MENSAJE: {texto}")

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

                wa_res = requests.post(url, headers=headers, json=payload)
                logger.info(f"WHATSAPP RESPONSE: {wa_res.status_code} {wa_res.text}")

                # 🔹 ODOO
                uid = login_odoo()
                logger.info(f"UID ODOO: {uid}")

                if uid:
                    partner_id = get_or_create_partner(uid, numero)
                    logger.info(f"PARTNER ID: {partner_id}")

                    if partner_id and texto:
                        save_message(uid, partner_id, texto)

            else:
                logger.info("Evento sin mensajes (status u otro)")

    except Exception as e:
        logger.exception(f"ERROR GENERAL: {e}")

    return "ok", 200


if __name__ == "__main__":
    logger.info("Iniciando servidor Flask...")
    app.run(host="0.0.0.0", port=5000)
