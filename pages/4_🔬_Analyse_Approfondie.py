import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from utils import load_data, get_available_tickers

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Analyse Approfondie")
st.title("🔬 Analyse Approfondie d'un Actif")

# --- Fonctions mises en cache pour les appels API ---
@st.cache_data(ttl=3600) # Cache de 1 heure
def get_ticker_info(ticker_symbol):
    """Récupère les informations fondamentales d'un ticker."""
    try:
        return yf.Ticker(ticker_symbol).info
    except Exception as e:
        st.error(f"Erreur API lors de la récupération des infos pour {ticker_symbol}: {e}")
        return {}

@st.cache_data(ttl=1800) # Cache de 30 minutes
def get_ticker_news(ticker_symbol):
    """Récupère les dernières actualités d'un ticker."""
    try:
        return yf.Ticker(ticker_symbol).news
    except Exception as e:
        st.error(f"Erreur API lors de la récupération des actualités pour {ticker_symbol}: {e}")
        return []

# --- Interface Utilisateur (Sidebar) ---
st.sidebar.header("Sélection de l'Actif")
selected_ticker = None
available_tickers = get_available_tickers()

if available_tickers:
    selected_ticker = st.sidebar.selectbox(
        "Choisissez un actif à analyser", 
        options=available_tickers, 
        key="deep_analysis_ticker"
    )
else:
    st.sidebar.error("Aucun actif trouvé. Vérifiez `tickers.txt`.")

# --- Corps principal de l'application ---
if selected_ticker:
    st.header(f"Analyse pour : {selected_ticker}")

    # 1. On charge les données principales UNE SEULE FOIS
    data = load_data(selected_ticker)

    # 2. On vérifie si les données de base existent AVANT de créer les onglets
    if not data.empty:
        # Création des onglets
        tab1, tab2, tab3 = st.tabs(["📊 Résumé & Cours", "📈 Indicateurs Techniques", "📰 Actualités"])

        # --- ONGLET 1: RÉSUMÉ & COURS ---
        with tab1:
            st.subheader("Graphique en Chandelier")
            # Création d'un graphique Candlestick plus pertinent
            fig_candle = go.Figure(data=[go.Candlestick(x=data.index,
                                                      open=data['Open'],
                                                      high=data['High'],
                                                      low=data['Low'],
                                                      close=data['Close'],
                                                      name=selected_ticker)])
            fig_candle.update_layout(
                title=f'Cours de {selected_ticker}',
                xaxis_title='Date',
                yaxis_title='Prix (USD)', # A adapter si multi-devises
                xaxis_rangeslider_visible=False # Le slider est souvent redondant avec le zoom de plotly
            )
            st.plotly_chart(fig_candle, use_container_width=True)

            # --- Données fondamentales via la fonction cachée ---
            st.subheader("Données Fondamentales Clés")
            with st.spinner("Chargement des données fondamentales..."):
                ticker_info = get_ticker_info(selected_ticker)
            
            if ticker_info:
                col1, col2, col3 = st.columns(3)
                market_cap = ticker_info.get('marketCap', 0)
                pe_ratio = ticker_info.get('trailingPE')
                
                col1.metric("Capitalisation", f"${market_cap:,.0f}" if market_cap else "N/A")
                col2.metric("Ratio Cours/Bénéfice (PER)", f"{pe_ratio:.2f}" if pe_ratio else "N/A")
                col3.metric("Secteur", ticker_info.get('sector', 'N/A'))
                
                st.subheader("Description de l'entreprise")
                st.write(ticker_info.get('longBusinessSummary', 'Description non disponible.'))
            else:
                st.warning("Données fondamentales non disponibles pour cet actif.")

        # --- ONGLET 2: INDICATEURS TECHNIQUES ---
        with tab2:
            st.subheader("Analyse Technique")
            # On vérifie qu'il y a assez de données pour les calculs
            if len(data) > 200:
                # Calcul des indicateurs avec pandas_ta
                data.ta.sma(length=50, append=True)
                data.ta.sma(length=200, append=True)
                data.ta.rsi(length=14, append=True)
                
                # Graphique des Moyennes Mobiles
                st.write("#### Moyennes Mobiles (SMA 50 & 200)")
                fig_sma = go.Figure()
                fig_sma.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Prix', line=dict(color='lightblue')))
                fig_sma.add_trace(go.Scatter(x=data.index, y=data['SMA_50'], name='SMA 50 Jours', line=dict(color='orange')))
                fig_sma.add_trace(go.Scatter(x=data.index, y=data['SMA_200'], name='SMA 200 Jours', line=dict(color='red')))
                st.plotly_chart(fig_sma, use_container_width=True)

                # Graphique du RSI
                st.write("#### Indice de Force Relative (RSI)")
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=data.index, y=data['RSI_14'], name='RSI', line=dict(color='purple')))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Zone de Surachat", annotation_position="bottom right")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Zone de Survente", annotation_position="bottom right")
                fig_rsi.update_yaxes(range=[0, 100])
                st.plotly_chart(fig_rsi, use_container_width=True)
            else:
                st.warning("Pas assez de données historiques (< 200 jours) pour calculer les indicateurs techniques.")

        # --- ONGLET 3: ACTUALITÉS ---
        with tab3:
            st.subheader("Dernières Actualités")
            with st.spinner("Chargement des actualités..."):
                news = get_ticker_news(selected_ticker)
            
            if news:
                # Affichage des 10 premières actualités
                for item in news[:10]:
                    st.markdown(f"**[{item['title']}]({item['link']})**")
                    st.caption(f"Source: {item['publisher']} | Publié le: {pd.to_datetime(item['providerPublishTime'], unit='s').strftime('%d/%m/%Y %H:%M')}")
                    st.markdown("---")
            else:
                st.info("Aucune actualité récente trouvée pour cet actif.")

    # 3. Message affiché si les données de base n'ont pas pu être chargées
    else:
        st.error(f"Les données pour **{selected_ticker}** n'ont pas pu être chargées. Impossible d'afficher l'analyse.")
        st.warning("Veuillez vérifier que le fichier de données existe et n'est pas vide, ou lancez `data_collector.py`.")
else:
    st.info("👋 Bienvenue sur la page d'analyse. Veuillez sélectionner un actif dans le menu de gauche pour commencer.")