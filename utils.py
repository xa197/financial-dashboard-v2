import streamlit as st
import pandas as pd
import os

DATA_DIR = "data"

@st.cache_data
def load_data(ticker):
    csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    try:
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        df.index.name = 'Date'
        # CETTE BOUCLE EST CRUCIALE
        for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=['Close'], inplace=True)
        return df
    except Exception as e:
        st.error(f"Erreur lors de la lecture de {ticker}.csv: {e}")
        return None

def get_available_tickers():
    if not os.path.exists(DATA_DIR): return []
    files = os.listdir(DATA_DIR)
    return sorted([f.split('.csv')[0] for f in files if f.endswith('.csv')])