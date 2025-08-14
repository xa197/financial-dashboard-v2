import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from utils import load_data, get_available_tickers

st.set_page_config(layout="wide", page_title="Analyse Approfondie")

st.title("🔬 Analyse Approfondie d'un Actif")

# --- INTERFACE (SIDEBAR) ---
available_tickers = get_available_tickers()
if available_tickers:
    selected_ticker = st.sidebar.selectbox(
        "Sélectionnez un actif", 
        options=available_tickers, 
        key="deep_analysis_ticker"
    )
else:
    selected_ticker = None

if selected_ticker:
    st.header(f"Analyse pour : {selected_ticker}")

    # --- Création des onglets ---
    tab1, tab2, tab3 = st.tabs(["📊 Résumé & Cours", "📈 Indicateurs Techniques", "📰 Actualités"])

    # --- ONGLET 1: RÉSUMÉ & COURS ---
    with tab1:
        data = load_data(selected_ticker)
        if data is not None and not data.empty:
            st.subheader("Graphique du Cours")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Cours de Clôture'))
            fig.update_layout(xaxis_rangeslider_visible=True)
            st.plotly_chart(fig, use_container_width=True)

            # --- Appel API pour les données fondamentales ---
            st.subheader("Données Fondamentales")
            try:
                with st.spinner("Chargement des données fondamentales..."):
                    ticker_info = yf.Ticker(selected_ticker).info
                
                # Affichage en 2 colonnes pour une meilleure lisibilité
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Secteur :** {ticker_info.get('sector', 'N/A')}")
                    st.write(f"**Industrie :** {ticker_info.get('industry', 'N/A')}")
                    st.write(f"**Pays :** {ticker_info.get('country', 'N/A')}")
                    st.write(f"**Site Web :** {ticker_info.get('website', 'N/A')}")
                with col2:
                    market_cap = ticker_info.get('marketCap', 0)
                    pe_ratio = ticker_info.get('trailingPE')
                    st.write(f"**Capitalisation :** ${market_cap:,.0f}")
                    if pe_ratio:
                        st.write(f"**Ratio Cours/Bénéfice (PER) :** {pe_ratio:.2f}")

                st.subheader("Description de l'entreprise")
                st.write(ticker_info.get('longBusinessSummary', 'Description non disponible.'))

            except Exception:
                st.warning("Impossible de charger les données fondamentales. L'API est peut-être indisponible.")
    
    # --- ONGLET 2: INDICATEURS TECHNIQUES ---
    with tab2:
        data = load_data(selected_ticker)
        if data is not None and not data.empty and len(data) > 200:
            st.subheader("Moyennes Mobiles (SMA)")
            data['SMA50'] = ta.sma(data['Close'], length=50)
            data['SMA200'] = ta.sma(data['Close'], length=200)
            
            fig_sma = go.Figure()
            fig_sma.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Prix'))
            fig_sma.add_trace(go.Scatter(x=data.index, y=data['SMA50'], name='SMA 50 Jours'))
            fig_sma.add_trace(go.Scatter(x=data.index, y=data['SMA200'], name='SMA 200 Jours'))
            st.plotly_chart(fig_sma, use_container_width=True)

            st.subheader("Indice de Force Relative (RSI)")
            data['RSI'] = ta.rsi(data['Close'], length=14)
            
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI'], name='RSI'))
            fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Surachat")
            fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Survente")
            st.plotly_chart(fig_rsi, use_container_width=True)
            
        else:
            st.warning("Pas assez de données historiques pour calculer les indicateurs techniques.")

    # --- ONGLET 3: ACTUALITÉS ---
    with tab3:
        st.subheader("Dernières Actualités")
        try:
            with st.spinner("Chargement des actualités..."):
                news = yf.Ticker(selected_ticker).news
            
            if news:
                for item in news[:10]: # On affiche les 10 premières actualités
                    st.write(f"**[{item['title']}]({item['link']})**")
                    st.caption(f"Source: {item['publisher']} - {pd.to_datetime(item['providerPublishTime'], unit='s').strftime('%Y-%m-%d %H:%M')}")
                    st.write("---")
            else:
                st.info("Aucune actualité récente trouvée pour cet actif.")
        except Exception:
            st.warning("Impossible de charger les actualités. L'API est peut-être indisponible.")

else:
    st.warning("Veuillez sélectionner un actif dans la barre latérale pour commencer l'analyse.")