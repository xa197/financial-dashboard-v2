import streamlit as st
import pandas as pd
import numpy as np
import xgboost as xgb
import yfinance as yf
from utils import get_tickers_by_category
import os
from datetime import datetime
import pandas_ta as ta

# --- Configuration et Constantes ---
st.set_page_config(layout="wide", page_title="Prédictions IA")
PREDICTIONS_LOG_FILE = "predictions_log.csv"
HORIZONS = {"Court Terme (2h)": 2, "Intraday (8h)": 8, "1 Jour": 24, "2 Jours": 48, "1 Semaine": 168}
LOG_COLUMNS = [
    "Timestamp", "Ticker", "Horizon", "Prix Actuel", "Prix Prédit", "Date Cible",
    "Prix Réel", "Erreur (%)", "Direction Correcte", "Dans Marge 5%", "Dans Marge 10%",
    "Statut", "SPY_RSI_au_lancement", "VIX_au_lancement"
]

# --- Fonctions de Traitement de Données et de Modélisation (Mises en Cache) ---

@st.cache_data(ttl=1800) # Cache de 30 minutes
def get_hourly_data(ticker):
    """Télécharge 60 jours de données horaires pour un ticker. Fonction sécurisée et cachée."""
    try:
        data = yf.download(ticker, period="60d", interval="1h", progress=False)
        if data.empty:
            return pd.DataFrame()
        # S'assurer que l'index est un DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        return data
    except Exception:
        return pd.DataFrame()

def create_features(df):
    """Crée des features techniques pour le modèle."""
    df['hour'] = df.index.hour
    df['dayofweek'] = df.index.dayofweek
    df.ta.rsi(length=14, append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    return df

def train_predict_model(df, horizon_hours):
    """Entraîne un modèle XGBoost et retourne la prédiction sur les données les plus récentes."""
    FEATURES = ['hour', 'dayofweek', 'RSI_14', 'EMA_20b', 'EMA_50b'] # Noms de colonnes de pandas_ta
    TARGET = 'target'
    
    df_features = create_features(df.copy())
    df_features[TARGET] = df_features['Close'].shift(-horizon_hours)
    df_features.dropna(inplace=True)
    
    if len(df_features) < 100: # Seuil de sécurité
        return None

    X, y = df_features[FEATURES], df_features[TARGET]
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Prédiction sur la dernière ligne de données disponibles
    latest_features = create_features(df.copy())[FEATURES].iloc[-1:].values
    prediction = model.predict(latest_features)
    return float(prediction[0])

@st.cache_data(ttl=3600) # Cache de 1 heure pour le contexte marché
def get_market_context():
    """Récupère des indicateurs sur l'état général du marché (S&P 500 et VIX)."""
    try:
        spy = yf.Ticker('^GSPC').history(period='3mo', auto_adjust=True)
        vix = yf.Ticker('^VIX').history(period='3mo', auto_adjust=True)
        spy_rsi = ta.rsi(spy['Close'], length=14).iloc[-1]
        vix_value = vix['Close'].iloc[-1]
        return spy_rsi, vix_value
    except Exception:
        return np.nan, np.nan

def log_prediction(timestamp, ticker, horizon_label, predicted_price, current_price):
    """Enregistre une nouvelle prédiction dans le fichier de log CSV."""
    spy_rsi, vix_value = get_market_context()
    target_date = timestamp + pd.Timedelta(hours=HORIZONS[horizon_label])
    
    new_entry = {
        "Timestamp": timestamp, "Ticker": ticker, "Horizon": horizon_label,
        "Prix Actuel": current_price, "Prix Prédit": predicted_price,
        "Date Cible": target_date, "Prix Réel": np.nan, "Erreur (%)": np.nan,
        "Direction Correcte": pd.NA, "Dans Marge 5%": pd.NA, "Dans Marge 10%": pd.NA,
        "Statut": "En attente", "SPY_RSI_au_lancement": spy_rsi, "VIX_au_lancement": vix_value
    }
    
    try:
        if not os.path.exists(PREDICTIONS_LOG_FILE):
            pd.DataFrame([new_entry], columns=LOG_COLUMNS).to_csv(PREDICTIONS_LOG_FILE, index=False)
        else:
            pd.DataFrame([new_entry], columns=LOG_COLUMNS).to_csv(PREDICTIONS_LOG_FILE, mode='a', header=False, index=False)
    except Exception as e:
        st.error(f"Erreur lors de l'écriture dans le log : {e}")

# --- Interface Streamlit ---
st.title("🧠 Générateur de Prédictions par IA (XGBoost)")
st.markdown("Scanne les actifs par secteur pour prédire les variations de prix à différents horizons.")

tickers_by_category = get_tickers_by_category()

if not tickers_by_category or "ERREUR" in tickers_by_category:
    st.error("Impossible de lire les catégories depuis `tickers.txt`.")
else:
    category_tabs = st.tabs(list(tickers_by_category.keys()))
    for i, category in enumerate(tickers_by_category):
        with category_tabs[i]:
            st.subheader(f"Actifs du secteur : {category}")
            tickers_in_category = tickers_by_category[category]
            
            # Le scan se lance automatiquement dans chaque onglet
            with st.spinner(f"Préparation des prédictions pour le secteur {category}..."):
                prediction_time = datetime.now()
                all_results = []
                progress_bar = st.progress(0, text="Initialisation...")

                for j, ticker in enumerate(tickers_in_category):
                    progress_bar.progress((j + 1) / len(tickers_in_category), text=f"Analyse de {ticker}...")
                    
                    hourly_data = get_hourly_data(ticker)
                    
                    if hourly_data.empty:
                        continue # On passe au ticker suivant si pas de données

                    current_price = hourly_data['Close'].iloc[-1]
                    result_row = {"Actif": ticker, "Prix Actuel": current_price}

                    for horizon_label, horizon_h in HORIZONS.items():
                        predicted_price = train_predict_model(hourly_data, horizon_h)
                        
                        if predicted_price is not None:
                            change_pct = ((predicted_price - current_price) / current_price) * 100
                            result_row[horizon_label] = change_pct
                            log_prediction(prediction_time, ticker, horizon_label, predicted_price, current_price)
                        else:
                            result_row[horizon_label] = np.nan
                    
                    all_results.append(result_row)
                
                progress_bar.empty()

            if all_results:
                df_results = pd.DataFrame(all_results).set_index("Actif")
                
                # Formatage pour l'affichage
                format_dict = {'Prix Actuel': '${:,.2f}'}
                for col in df_results.columns:
                    if col != 'Prix Actuel':
                        format_dict[col] = '{:+.2f}%'
                
                st.dataframe(df_results.style.format(format_dict, na_rep="-").background_gradient(
                    cmap='RdYlGn', 
                    subset=[col for col in df_results.columns if col != 'Prix Actuel']
                ), use_container_width=True)
            else:
                st.info("Aucune prédiction n'a pu être générée pour ce secteur.")