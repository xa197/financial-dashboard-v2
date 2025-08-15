# pages/5_🧠_Générateur_de_Prédictions.py (Version avec Achat Direct)

import streamlit as st
import pandas as pd
import numpy as np
import xgboost as xgb
import yfinance as yf
from utils import get_tickers_by_category, add_virtual_transaction # NOUVEAUTÉ: Import de la fonction d'achat
import os
from datetime import datetime
import pandas_ta as ta

# ... (Tout le code de configuration et les fonctions de prédiction restent exactement les mêmes) ...
# --- Configuration et Constantes ---
st.set_page_config(layout="wide", page_title="Prédictions IA")
PREDICTIONS_LOG_FILE = "predictions_log.csv"
HORIZONS = {"Court Terme (2h)": 2, "Intraday (8h)": 8, "1 Jour": 24, "2 Jours": 48, "1 Semaine": 168}
LOG_COLUMNS = [
    "Timestamp", "Ticker", "Horizon", "Prix Actuel", "Prix Prédit", "Date Cible",
    "Prix Réel", "Erreur (%)", "Direction Correcte", "Dans Marge 5%", "Dans Marge 10%",
    "Statut", "SPY_RSI_au_lancement", "VIX_au_lancement"
]

@st.cache_data(ttl=1800)
def get_hourly_data(ticker):
    try:
        data = yf.download(ticker, period="60d", interval="1h", progress=False)
        if isinstance(data.columns, pd.MultiIndex): data.columns = [col[0] for col in data.columns]
        if data.empty: return pd.DataFrame()
        if not isinstance(data.index, pd.DatetimeIndex): data.index = pd.to_datetime(data.index)
        return data
    except Exception: return pd.DataFrame()

def create_features(df):
    df['hour'] = df.index.hour; df['dayofweek'] = df.index.dayofweek
    df.ta.rsi(length=14, append=True); df.ta.ema(length=20, append=True); df.ta.ema(length=50, append=True)
    return df

def train_predict_model(df, horizon_hours):
    FEATURES = ['hour', 'dayofweek', 'RSI_14', 'EMA_20', 'EMA_50']; TARGET = 'target'
    df_features = create_features(df.copy()); df_features[TARGET] = df_features['Close'].shift(-horizon_hours)
    df_features.dropna(inplace=True)
    if len(df_features) < 100: return None
    df_features.rename(columns={'EMA_20b': 'EMA_20', 'EMA_50b': 'EMA_50'}, inplace=True)
    X, y = df_features[FEATURES], df_features[TARGET]
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42).fit(X, y)
    latest_features_df = create_features(df.copy()); latest_features_df.rename(columns={'EMA_20b': 'EMA_20', 'EMA_50b': 'EMA_50'}, inplace=True)
    latest_features = latest_features_df[FEATURES].iloc[-1:].values
    prediction = model.predict(latest_features)
    return float(prediction[0])

@st.cache_data(ttl=3600)
def get_market_context():
    try:
        spy = yf.Ticker('^GSPC').history(period='3mo', auto_adjust=True); vix = yf.Ticker('^VIX').history(period='3mo', auto_adjust=True)
        spy_rsi = ta.rsi(spy['Close'], length=14).iloc[-1]; vix_value = vix['Close'].iloc[-1]
        return spy_rsi, vix_value
    except Exception: return np.nan, np.nan

def create_log_entry(timestamp, ticker, horizon_label, predicted_price, current_price):
    spy_rsi, vix_value = get_market_context()
    target_date = timestamp + pd.Timedelta(hours=HORIZONS[horizon_label])
    return {
        "Timestamp": timestamp, "Ticker": ticker, "Horizon": horizon_label, "Prix Actuel": current_price,
        "Prix Prédit": predicted_price, "Date Cible": target_date, "Prix Réel": np.nan, "Erreur (%)": np.nan,
        "Direction Correcte": pd.NA, "Dans Marge 5%": pd.NA, "Dans Marge 10%": pd.NA, "Statut": "En attente",
        "SPY_RSI_au_lancement": spy_rsi, "VIX_au_lancement": vix_value
    }

def append_logs_to_file(log_entries):
    if not log_entries: return
    df_new_logs = pd.DataFrame(log_entries)
    try:
        if not os.path.exists(PREDICTIONS_LOG_FILE):
            df_new_logs.to_csv(PREDICTIONS_LOG_FILE, index=False)
        else:
            df_new_logs.to_csv(PREDICTIONS_LOG_FILE, mode='a', header=False, index=False)
        st.success(f"{len(log_entries)} prédictions enregistrées !")
    except Exception as e:
        st.error(f"Erreur d'écriture dans le log : {e}")

if 'ai_scan_results' not in st.session_state: st.session_state.ai_scan_results = None
if 'ai_log_entries' not in st.session_state: st.session_state.ai_log_entries = []

st.title("🧠 Générateur de Prédictions par IA (XGBoost)")

if st.session_state.ai_scan_results is not None:
    st.subheader("Derniers Résultats du Scan")
    df_results = st.session_state.ai_scan_results
    format_dict = {'Prix Actuel': '${:,.2f}'}; [format_dict.update({col: '{:+.2f}%'}) for col in df_results.columns if col not in ['Actif', 'Prix Actuel']]
    st.dataframe(df_results.style.format(format_dict, na_rep="-").background_gradient(cmap='RdYlGn', subset=[c for c in df_results.columns if c not in ['Actif', 'Prix Actuel']]), use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Envoyer au Suivi de Performance"):
            append_logs_to_file(st.session_state.ai_log_entries)
            st.session_state.ai_log_entries = []
            st.toast("Prédictions enregistrées !")
            
    with col2:
        if st.button("🔄 Lancer un nouveau scan"):
            st.session_state.ai_scan_results = None
            st.session_state.ai_log_entries = []
            st.rerun()

    # --- NOUVEAUTÉ : La section pour agir ---
    st.markdown("---")
    st.subheader("⚡️ Agir sur une Prédiction")
    
    # On propose les tickers avec les meilleures prédictions à court terme
    short_term_horizon = "Court Terme (2h)"
    if short_term_horizon in df_results.columns:
        best_tickers = df_results.sort_values(by=short_term_horizon, ascending=False)['Actif'].tolist()
    else:
        best_tickers = df_results['Actif'].tolist()
        
    col_act, col_montant, col_btn = st.columns([2, 1, 1])
    
    with col_act:
        selected_ticker = st.selectbox("Choisir un actif à acheter", options=best_tickers)
    with col_montant:
        investment_amount = st.number_input("Montant (€)", min_value=10.0, step=10.0, value=100.0)
    with col_btn:
        st.write("‎") # Pour aligner le bouton verticalement
        if st.button("Acheter (Port. Virtuel)"):
            if selected_ticker and investment_amount > 0:
                success, message = add_virtual_transaction(selected_ticker, investment_amount)
                if success:
                    st.success(message + " [Voir le portefeuille](/Portefeuille_Virtuel)")
                else:
                    st.error(message)

else:
    # --- Interface de scan (inchangée) ---
    st.info("Sélectionnez un secteur et lancez le scan pour générer des prédictions.")
    tickers_by_category = get_tickers_by_category()
    if not tickers_by_category or "ERREUR" in tickers_by_category:
        st.error("Impossible de lire les catégories depuis `tickers.txt`.")
    else:
        category_tabs = st.tabs(list(tickers_by_category.keys()))
        for i, category in enumerate(tickers_by_category):
            with category_tabs[i]:
                st.subheader(f"Actifs du secteur : {category}")
                tickers_in_category = tickers_by_category[category]
                if st.button(f"🚀 Lancer les prédictions pour {category}", key=f"scan_{category}"):
                    with st.spinner(f"Scan en cours pour le secteur {category}..."):
                        prediction_time = datetime.now()
                        all_results, log_entries_to_save = [], []
                        progress_bar = st.progress(0, text="Initialisation...")
                        for j, ticker in enumerate(tickers_in_category):
                            progress_bar.progress((j + 1) / len(tickers_in_category), text=f"Analyse de {ticker}...")
                            hourly_data = get_hourly_data(ticker)
                            if hourly_data.empty: continue
                            current_price = hourly_data['Close'].iloc[-1]
                            result_row = {"Actif": ticker, "Prix Actuel": current_price}
                            for horizon_label, horizon_h in HORIZONS.items():
                                predicted_price = train_predict_model(hourly_data, horizon_h)
                                if predicted_price is not None:
                                    change_pct = ((predicted_price - current_price) / current_price) * 100
                                    result_row[horizon_label] = change_pct
                                    log_entries_to_save.append(create_log_entry(prediction_time, ticker, horizon_label, predicted_price, current_price))
                                else:
                                    result_row[horizon_label] = np.nan
                            all_results.append(result_row)
                        progress_bar.empty()
                    st.session_state.ai_scan_results = pd.DataFrame(all_results)
                    st.session_state.ai_log_entries = log_entries_to_save
                    st.rerun()