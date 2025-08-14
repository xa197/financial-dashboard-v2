import streamlit as st
import pandas as pd
import yfinance as yf
import time
from utils import get_tickers_by_category

st.set_page_config(layout="wide", page_title="Scanner de Recommandations")

@st.cache_data(ttl=4*3600)
def scan_recommendations(tickers_list):
    """Scanne une liste de tickers et retourne leurs recommandations."""
    results = []
    for ticker_symbol in tickers_list:
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            reco_mean = info.get('recommendationMean')
            reco_key = info.get('recommendationKey')
            if reco_mean and reco_key:
                results.append({"Ticker": ticker_symbol, "Recommandation": reco_key.replace('_', ' ').title(), "Note Moyenne": reco_mean})
            time.sleep(0.1)
        except Exception: continue
    return pd.DataFrame(results)

st.title("🏆 Scanner de Recommandations par Secteur")

tickers_by_category = get_tickers_by_category()

if not tickers_by_category or "ERREUR" in tickers_by_category:
    st.error("Impossible de lire les catégories depuis `tickers.txt`.")
else:
    # On retire les cryptos car elles n'ont pas de recommandations
    action_categories = {cat: tickers for cat, tickers in tickers_by_category.items() if cat != "CRYPTOMONNAIES"}
    
    # Création des onglets pour chaque catégorie
    category_tabs = st.tabs(list(action_categories.keys()))

    for i, category in enumerate(action_categories):
        with category_tabs[i]:
            st.subheader(f"Analyse du secteur : {category}")
            tickers_in_category = action_categories[category]
            
            if st.button(f"🚀 Lancer le Scan pour {category}", key=f"scan_{category}"):
                
                with st.spinner(f"Scan en cours pour {len(tickers_in_category)} actifs..."):
                    df_results = scan_recommendations(tickers_in_category)

                if not df_results.empty:
                    df_sorted = df_results.sort_values(by="Note Moyenne")
                    st.dataframe(
                        df_sorted.style.format({"Note Moyenne": "{:.2f}"})
                                       .background_gradient(cmap='RdYlGn_r', subset=['Note Moyenne']),
                        use_container_width=True
                    )
                else:
                    st.warning("Aucun résultat pour ce secteur.")