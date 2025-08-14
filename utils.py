import streamlit as st
import pandas as pd
import os

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
    """Retourne une liste plate de tous les tickers disponibles."""
    categories = get_tickers_by_category()
    all_tickers = []
    for ticker_list in categories.values():
        all_tickers.extend(ticker_list)
    return sorted(list(set(all_tickers))) # Utilise set pour dédupliquer

@st.cache_data
def load_data(ticker):
    # ... (Le reste de la fonction load_data ne change pas) ...
    csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    try:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        df.index.name = 'Date'
        for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['Close'], inplace=True)
        return df
    except Exception as e:
        return None