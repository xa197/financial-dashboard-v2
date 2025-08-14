import streamlit as st
from utils import load_data, get_available_tickers # On importe nos fonctions !

st.set_page_config(layout="wide", page_title="Accueil", page_icon="🏠")

st.title("🏠 Dashboard Financier V2")
st.write("Bienvenue sur votre nouveau dashboard.")

available_tickers = get_available_tickers()

if not available_tickers:
    st.error("Aucune donnée trouvée. Lancez d'abord `data_collector.py`.")
else:
    st.info(f"Données disponibles pour {len(available_tickers)} actifs. Sélectionnez un actif dans la barre latérale.")

st.sidebar.title("Paramètres")
selected_ticker = st.sidebar.selectbox("Sélectionnez un actif", options=available_tickers)