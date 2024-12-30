from flask import Flask, jsonify
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os

app = Flask(__name__)

# URL de l'API CoinGecko
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Cache pour stocker les prix des cryptos
prices_cache = {}

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Fonction pour récupérer les paires convertibles en USDT
def get_usdt_pairs():
    try:
        logging.info("Tentative de récupération des paires USDT...")
        response = requests.get(f"{COINGECKO_API_URL}/coins/markets", params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "sparkline": False
        })
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Données brutes reçues pour les marchés : {data[:5]}")  # Afficher les 5 premiers éléments
        pairs = [coin['id'] for coin in data]
        logging.info(f"Récupéré {len(pairs)} cryptos.")
        return pairs
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de la récupération des paires USDT : {e}")
        return []

# Fonction pour récupérer les prix des cryptos
def get_crypto_prices(pairs):
    try:
        # Regrouper les IDs dans une seule requête
        ids = ",".join(pairs[:50])  # Limiter à 50 pour respecter les limites d'URL
        response = requests.get(f"{COINGECKO_API_URL}/simple/price", params={
            "ids": ids,
            "vs_currencies": "usd"
        })
        response.raise_for_status()
        data = response.json()
        logging.info(f"Récupéré les prix de {len(data)} cryptos.")
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de la récupération des prix : {e}")
        return {}



# Fonction pour mettre à jour les prix périodiquement
def update_prices_periodically():
    global prices_cache
    logging.info("Début de la mise à jour périodique des prix.")
    pairs = get_usdt_pairs()
    if pairs:
        prices_cache = get_crypto_prices(pairs)
    logging.info(f"Mise à jour terminée. Données en cache : {prices_cache}")



# Initialiser le planificateur pour actualiser toutes les 15 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(update_prices_periodically, 'interval', minutes=15)
scheduler.start()

@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "API de cryptomonnaies", "endpoints": ["/prices", "/update"]})

# Endpoint pour récupérer les prix mis en cache
@app.route('/prices', methods=['GET'])
def get_cached_prices():
    return jsonify(prices_cache)

# Endpoint pour déclencher manuellement une mise à jour
@app.route('/update', methods=['GET'])
def manual_update():
    update_prices_periodically()
    return jsonify({"message": "Mise à jour effectuée", "data": prices_cache})

@app.route('/test-coingecko', methods=['GET'])
def test_coingecko():
    try:
        response = requests.get(f"{COINGECKO_API_URL}/ping")
        response.raise_for_status()
        return jsonify({"status": "success", "data": response.json()})
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Démarrer l'application Flask
if __name__ == '__main__':
    update_prices_periodically()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
