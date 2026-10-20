from flask import Flask, render_template, request, jsonify
import json
import os
import requests

app = Flask(__name__)

CLIENTS_FILE = 'clients.json'

# Configuration Telegram pour Nexora Call
TELEGRAM_BOT_TOKEN = "8247690577:AAGlSd1QLkkgjq57ew7f47YhQPGjt_fyxk8"
TELEGRAM_CHAT_ID = "5160272648"

def envoyer_alerte_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Erreur lors de l'envoi de l'alerte Telegram :", e)

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

# Base de données intelligente : associe un numéro à un nom de personne ou de société
ANNUAIRE_CONTACTS = {
    "0612345678": {"nom": "Jean Dupont", "type": "particulier", "securise": True},
    "0140000000": {"nom": "Banque Populaire (Service Officiel)", "type": "banque", "securise": True},
    "0150000000": {"nom": "Société Générale (Assistance)", "type": "banque", "securise": True},
}

@app.route('/')
def index():
    client_key = request.args.get('key', '').strip()
    clients = charger_clients()

    # Si aucune clé n'est fournie, on affiche l'écran de saisie du code
    if not client_key:
        return render_template('index.html', is_authenticated=False)

    # Vérification si la clé existe et est active
    if client_key in clients and clients[client_key].get('actif', False):
        return render_template('index.html', is_authenticated=True, key=client_key)
    else:
        # Clé inconnue ou expirée
        return render_template('index.html', is_authenticated=False, error_message="Clé d'activation invalide ou expirée.")

@app.route('/api/verifier', methods=['POST'])
def verifier():
    # --- SÉCURITÉ : VÉRIFICATION DE LA CLÉ CLIENT ET DE L'APPAREIL ---
    client_key = request.args.get('key')
    
    if not client_key:
        return jsonify({
            "status": "alerte-rouge",
            "numero": "Erreur",
            "societe": "Nexora Security",
            "subtitle": "🚨 ACCÈS NON AUTORISÉ",
            "message": "Clé d'activation manquante dans le lien."
        }), 403

    clients = charger_clients()

    if client_key not in clients:
        return jsonify({
            "status": "alerte-rouge",
            "numero": "Erreur",
            "societe": "Nexora Security",
            "subtitle": "🚨 CLÉ INVALIDE",
            "message": "Cette clé d'accès est inconnue ou a expiré."
        }), 403

    client_data = clients[client_key]
    
    # Récupération propre de l'IP réelle, même derrière le proxy de Railway
    current_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in current_ip:
        current_ip = current_ip.split(',')[0].strip()

    # Verrouillage sur le premier appareil qui utilise la clé
    if client_data.get("appareil_autorise") is None:
        client_data["appareil_autorise"] = current_ip
        sauvegarder_clients(clients)
    elif client_data["appareil_autorise"] != current_ip:
        # Envoi de l'alerte sur ton Telegram
        alerte_msg = (
            f"🚨 *Tentative d'accès suspecte sur Nexora Call !*\n\n"
            f"🔑 Clé concernée : `{client_key}`\n"
            f"🔒 IP autorisée d'origine : `{client_data['appareil_autorise']}`\n"
            f"❌ IP bloquée (suspecte) : {current_ip}"
        )
        envoyer_alerte_telegram(alerte_msg)

        return jsonify({
            "status": "alerte-rouge",
            "numero": "Erreur",
            "societe": "Nexora Security",
            "subtitle": "🚨 PARTAGE DÉTECTÉ",
            "message": "Cet abonnement est déjà utilisé sur un autre appareil."
        }), 403
    # -------------------------------------------------------------

    data = request.get_json() or {}
    numero = data.get('numero', '').strip()
    
    if not numero:
        return jsonify({
            "status": "neutre",
            "numero": "En attente d'appel",
            "societe": "Nexora Intelligence Engine",
            "subtitle": "Analyse des flux entrants en temps réel",
            "message": "La ligne est sécurisée. Surveillance active des vecteurs d'usurpation et de spoofing bancaire en arrière-plan."
        })

    # 1. Vérification si le numéro est connu dans l'annuaire
    contact_info = ANNUAIRE_CONTACTS.get(numero)

    if contact_info:
        resultat = {
            "status": "alerte-verte",
            "numero": numero,
            "societe": contact_info["nom"],
            "subtitle": "✅ CORRESPONDANT IDENTIFIÉ ET SÉCURISÉ",
            "message": f"Appel reconnu : {contact_info['nom']}. La ligne est totalement sûre."
        }
    elif numero.startswith('+') and not numero.startswith('+33'):
        resultat = {
            "status": "alerte-rouge",
            "numero": numero,
            "societe": "Inconnu / Réseau International",
            "subtitle": "🚨 ALERTE CRITIQUE : USURPATION D'IDENTITÉ",
            "message": "Ce n'est PAS votre banque qui appelle. L'appel provient d'un réseau international non sécurisé. Raccrochez immédiatement."
        }
    elif numero.startswith('01') or numero.startswith('09') or numero.startswith('+331') or numero.startswith('+339'):
        resultat = {
            "status": "alerte-rouge",
            "numero": numero,
            "societe": "Ligne Fixe / Non Répertorié",
            "subtitle": "⚠️ AVERTISSEMENT : RISQUE DE SPOOFING BANCAIRE",
            "message": "Attention : Ce numéro fixe simule un organisme. Si l'interlocuteur demande vos codes ou valide une opération, c'est une fraude caractérisée."
        }
    else:
        resultat = {
            "status": "neutre",
            "numero": numero,
            "societe": "Correspondant Non Enregistré",
            "subtitle": "🔍 ANALYSE EN COURS",
            "message": "Numéro non présent dans le répertoire de confiance. Restez vigilant si l'interlocuteur aborde des sujets financiers."
        }
        
    return jsonify(resultat)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)