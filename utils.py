import streamlit as st
import pandas as pd
import os
import yfinance as yf
import pytz

DATA_DIR = "data"
TICKER_FILE = "tickers.txt"

def get_tickers_by_category():
    """
    Lit le fichier tickers.txt et retourne un dictionnaire
    où les clés sont les catégories et les valeurs sont les listes de tickers.
    """
    categories = {}
    current_category = "SANS CATÉGORIE"
    try:
        with open(TICKER_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_category = line[1:-1].strip()
                    categories[current_category] = []
                else:
                    if current_category not in categories:
                        categories[current_category] = []
                    categories[current_category].append(line.upper())
        return categories
    except FileNotFoundError:
        return {"ERREUR": ["Fichier tickers.txt introuvable"]}

def get_available_tickers():
    """Retourne une liste plate et triée de tous les tickers disponibles."""
    categories = get_tickers_by_category()
    all_tickers = []
    for ticker_list in categories.values():
        all_tickers.extend(ticker_list)
    # Utilise set pour supprimer les doublons (si un ticker est dans plusieurs catégories)
    return sorted(list(set(all_tickers)))

# --- FONCTION MODIFIÉE ---
# Le cache a été supprimé pour garantir que les données les plus récentes sont toujours lues,
# ce qui est crucial pour des pages comme le suivi de portefeuille ou de prédictions.
# Lire un fichier CSV local est de toute façon extrêmement rapide.
def load_data(ticker):
    """
    Charge les données pour un ticker depuis son fichier CSV.
    Cette fonction n'utilise volontairement pas de cache pour garantir la fraîcheur des données.
    """
    csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    try:
        df = pd.read_csv(
            csv_path,
            index_col=0,
            parse_dates=True
        )
        df.index.name = 'Date'
        # S'assurer que les colonnes de prix sont bien numériques
        for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['Close'], inplace=True)
        return df
    except Exception as e:
        # Affiche une erreur dans l'app si la lecture échoue
        st.error(f"Erreur critique lors de la lecture de {ticker}.csv: {e}")
        return None

@st.cache_data(ttl=3600) # On met en cache le taux de change pour 1 heure
def get_eur_usd_rate():
    """Récupère le dernier taux de change EUR/USD."""
    try:
        eur_usd = yf.Ticker("EURUSD=X")
        rate = eur_usd.history(period="1d")['Close'].iloc[-1]
        return rate
    except Exception:
        st.error("Impossible de récupérer le taux de change EUR/USD.")
        return 1.0 # On retourne 1.0 en cas d'erreur pour ne pas bloquer les calculs