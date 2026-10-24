
from flask import Flask, render_template, request, jsonify, make_response
import json
import os
import requests
import uuid

app = Flask(__name__)

CLIENTS_FILE = 'clients.json'

# Configuration Telegram pour Nexora Call
TELEGRAM_BOT_TOKEN = "8247690577:AAH0YMfJe3c-wIkJwOBOFcdCQjSs-4i1vmg"
TELEGRAM_CHAT_ID = "5160272648"

def envoyer_alerte_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Erreur Telegram :", e)

def charger_clients():
    if not os.path.exists(CLIENTS_FILE):
        return {}
    with open(CLIENTS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def sauvegarder_clients(data):
    with open(CLIENTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

ANNUAIRE_CONTACTS = {
    "0612345678": {"nom": "Jean Dupont", "type": "particulier", "securise": True},
    "0140000000": {"nom": "Banque Populaire", "type": "banque", "securise": True},
}

@app.route('/')
def index():
    client_key = request.args.get('key', '').strip()
    clients = charger_clients()

    # Récupération de l'IP
    current_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in current_ip:
        current_ip = current_ip.split(',')[0].strip()
    
    user_agent = request.headers.get('User-Agent', '').lower()
    
    # Détection d'un comportement de navigation privée stricte ou d'absence de clé
    is_private_mode = "private" in user_agent or "incognito" in user_agent or not client_key

    if not client_key:
        return render_template('index.html', is_authenticated=False)

    # Si la clé est valide
    if client_key in clients and clients[client_key].get('actif', False):
        
        # SÉCURITÉ : Test Telegram, mode privé ou paramètre 'mode=prive'
        if request.args.get('test') == '1' or is_private_mode or request.args.get('mode') == 'prive':
            alerte_msg = (
                f"🚨 *Alerte Nexora Call : Tentative suspecte / mode restreint détectée !*\n\n"
                f"🔑 Clé : `{client_key}`\n"
                f"🌐 IP : `{current_ip}`\n"
                f"⚠️ Sécurité déclenchée (Mode privé ou simulation de test)."
            )
            envoyer_alerte_telegram(alerte_msg)
            return render_template('index.html', is_authenticated=False, error_message="Accès refusé : Session non sécurisée ou mode privé détecté.")

        device_token = request.cookies.get('nexora_device_token')
        resp = make_response(render_template('index.html', is_authenticated=True, key=client_key))
        
        if not device_token:
            device_token = str(uuid.uuid4())
            resp.set_cookie('nexora_device_token', device_token, max_age=60*60*24*365, httponly=True, samesite='Lax')
            
        return resp
    else:
        return render_template('index.html', is_authenticated=False, error_message="Clé d'activation invalide ou expirée.")

@app.route('/api/verifier', methods=['POST'])
def verifier():
    client_key = request.args.get('key')
    if not client_key:
        return jsonify({"status": "alerte-rouge", "message": "Clé manquante"}), 403

    data = request.get_json() or {}
    numero = data.get('numero', '').strip()
    
    if not numero:
        return jsonify({
            "status": "neutre",
            "numero": "En attente d'appel",
            "societe": "Nexora Intelligence Engine",
            "subtitle": "Surveillance active",
            "message": "Ligne sécurisée."
        })

    contact_info = ANNUAIRE_CONTACTS.get(numero)
    if contact_info:
        resultat = {"status": "alerte-verte", "numero": numero, "societe": contact_info["nom"], "subtitle": "✅ SÉCURISÉ", "message": "Ligne sûre."}
    else:
        resultat = {"status": "alerte-rouge", "numero": numero, "societe": "Inconnu", "subtitle": "🚨 ALERTE", "message": "Numéro suspect."}
        
    return jsonify(resultat)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)