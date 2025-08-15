import streamlit as st
import pandas as pd
import os
import yfinance as yf
import pytz

# --- Constantes pour une maintenance facile ---
DATA_DIR = "data"
TICKER_FILE = "tickers.txt"

def get_tickers_by_category():
    """
    Lit le fichier tickers.txt et retourne un dictionnaire où les clés
    sont les catégories et les valeurs sont les listes de tickers.
    Gère le cas où le fichier est introuvable.
    """
    categories = {}
    current_category = "SANS CATÉGORIE"
    try:
        with open(TICKER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_category = line[1:-1].strip().upper()
                    categories[current_category] = []
                else:
                    if current_category not in categories:
                        categories[current_category] = []
                    categories[current_category].append(line.upper())
        return categories
    except FileNotFoundError:
        st.error(f"Fichier de configuration '{TICKER_FILE}' introuvable.")
        return {"ERREUR": []}

def get_available_tickers():
    """
    Retourne une liste plate, unique et triée de tous les tickers
    disponibles dans le fichier de configuration.
    """
    categories = get_tickers_by_category()
    all_tickers = []
    for ticker_list in categories.values():
        all_tickers.extend(ticker_list)
    return sorted(list(set(all_tickers)))

# --- FONCTION PRINCIPALE MISE À JOUR POUR LA ROBUSTESSE ---
def load_data(ticker):
    """
    Charge les données d'un actif depuis son fichier CSV local.
    Cette fonction est sécurisée contre les fichiers manquants ou corrompus.
    
    Args:
        ticker (str): Le symbole de l'actif (ex: 'AAPL').

    Returns:
        pd.DataFrame: Un DataFrame contenant les données de l'actif.
                      Retourne un DataFrame VIDE si les données ne peuvent pas être chargées,
                      permettant ainsi des vérifications sécurisées avec `df.empty`.
    """
    if not isinstance(ticker, str) or not ticker:
        st.error("Un nom de ticker valide est requis.")
        return pd.DataFrame()
        
    csv_path = os.path.join(DATA_DIR, f"{ticker.upper()}.csv")

    # 1. Vérifier si le fichier existe avant toute chose.
    if not os.path.exists(csv_path):
        st.error(f"Fichier de données introuvable pour {ticker} : '{csv_path}'")
        st.warning("Veuillez lancer ou vérifier le script `data_collector.py`.")
        return pd.DataFrame()

    try:
        # 2. Essayer de lire le fichier.
        df = pd.read_csv(csv_path, index_col='Date', parse_dates=True)
        
        # 3. Vérifier si le fichier, bien qu'existant, est vide.
        if df.empty:
            st.warning(f"Le fichier de données pour {ticker} est vide.")
            return pd.DataFrame()

        # Nettoyage et typage des données pour éviter les erreurs de calcul
        for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.dropna(subset=['Close'], inplace=True)
        return df

    except Exception as e:
        # 4. Gérer toute autre erreur de lecture (fichier corrompu, etc.)
        st.error(f"Erreur critique lors de la lecture du fichier {csv_path}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600) # On met en cache le taux de change pour 1 heure
def get_eur_usd_rate():
    """
    Récupère le dernier taux de change EUR/USD via yfinance.
    Utilise un cache pour limiter les appels API.
    Retourne un taux de 1.0 en cas d'échec pour ne pas bloquer l'application.
    """
    try:
        eur_usd = yf.Ticker("EURUSD=X")
        # Utiliser une période un peu plus longue pour plus de robustesse
        history = eur_usd.history(period="5d")
        if not history.empty:
            return history['Close'].iloc[-1]
        else:
            st.warning("Aucune donnée de taux de change EUR/USD reçue.")
            return 1.0
    except Exception as e:
        # --- LIGNE CORRIGÉE ---
        # La parenthèse manquante a été ajoutée ici.
        st.error(f"Impossible de récupérer le taux de change EUR/USD : {e}")
        st.info("Un taux de 1.0 sera utilisé par défaut.")
        return 1.0