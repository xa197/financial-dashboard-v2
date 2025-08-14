import streamlit as st
import pandas as pd
import numpy as np
import xgboost as xgb
import yfinance as yf
from utils import get_available_tickers
import os
from datetime import datetime

st.set_page_config(layout="wide", page_title="Générateur de Prédictions IA")

# --- PARAMÈTRES ---
PREDICTIONS_LOG_FILE = "predictions_log.csv"
HORIZONS_MINUTES = {"5 min": 5, "15 min": 15, "30 min": 30, "45 min": 45, "1 heure": 60}
HORIZONS_HOURS = {"2h": 2, "8h": 8, "1j": 24, "2j": 48, "7j": 168, "14j": 336, "28j": 672}

# --- MOTEUR XGBOOST ---
def create_features_manual(df):
    df['hour'] = df.index.hour; df['minute'] = df.index.minute
    df['dayofweek'] = df.index.dayofweek
    delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean(); rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs)); df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    return df

@st.cache_data(ttl=60)
def train_and_predict_xgboost(ticker, horizon_value, time_unit='minutes'):
    if time_unit == 'minutes':
        data = yf.download(ticker, period="7d", interval="1m", progress=False)
        if data.empty:
            data = yf.download(ticker, period="30d", interval="5m", progress=False)
            if data.empty: return None, None
            shift_periods = int(horizon_value / 5)
        else:
            shift_periods = int(horizon_value)
    else: # hours
        data = yf.download(ticker, period="730d", interval="1h", progress=False)
        if data.empty: return None, None
        shift_periods = int(horizon_value)

    if isinstance(data.index, pd.MultiIndex): data.index = data.index.get_level_values('Datetime')
    
    data_with_features = create_features_manual(data.copy())
    data_with_features['target'] = data_with_features['Close'].shift(-shift_periods)
    data_with_features.dropna(inplace=True)

    if len(data_with_features) < 50: return None, None
    
    FEATURES = ['hour', 'minute', 'dayofweek', 'RSI_14', 'EMA_20', 'EMA_50']
    TARGET = 'target'
    X, y = data_with_features[FEATURES], data_with_features[TARGET]

    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100).fit(X, y)
    latest_data_for_pred = create_features_manual(data.copy()).iloc[-1:]
    latest_features = latest_data_for_pred[FEATURES].values
    prediction = model.predict(latest_features)[0]
    current_price = data['Close'].iloc[-1]
    return float(prediction), float(current_price)

def log_prediction(log_file, timestamp, ticker, horizon_label, horizon_value, time_unit, predicted_price, current_price):
    if time_unit == 'minutes': target_date = timestamp + pd.Timedelta(minutes=horizon_value)
    else: target_date = timestamp + pd.Timedelta(hours=horizon_value)
        
    new_entry = pd.DataFrame([{"Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),"Ticker": ticker,"Horizon": horizon_label,"Prix Actuel": current_price,"Prix Prédit": predicted_price,"Date Cible": target_date.strftime('%Y-%m-%d %H:%M:%S'),"Prix Réel": np.nan,"Erreur (%)": np.nan,"Statut": "En attente"}])
    if not os.path.exists(log_file): new_entry.to_csv(log_file, index=False)
    else: new_entry.to_csv(log_file, mode='a', header=False, index=False)

# --- INTERFACE ---
st.title("🧠 Prédictions & Scan par IA (XGBoost)")
available_tickers = get_available_tickers()

st.subheader("Analyse Rapide à la Demande")
prediction_mode = st.radio("Choisissez le type d'horizon", ("Court Terme (minutes)", "Long Terme (heures/jours)"), horizontal=True)

if prediction_mode == "Court Terme (minutes)":
    horizons_to_use = HORIZONS_MINUTES; time_unit = 'minutes'
else:
    horizons_to_use = HORIZONS_HOURS; time_unit = 'hours'

with st.form("quick_analysis_form"):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        quick_tickers = st.multiselect("Actifs à analyser", options=available_tickers, default=available_tickers[0] if available_tickers else None)
    with col2:
        quick_horizons = st.multiselect("Horizons de prédiction", options=list(horizons_to_use.keys()), default=list(horizons_to_use.keys()))
    with col3:
        submitted = st.form_submit_button("🚀 Lancer l'Analyse")

if submitted and quick_tickers and quick_horizons:
    st.write("---")
    for ticker in quick_tickers:
        st.write(f"**Analyse de {ticker}...**")
        prediction_time = datetime.now()
        cols = st.columns(len(quick_horizons) if quick_horizons else 1)
        for i, horizon_label in enumerate(quick_horizons):
            with cols[i]:
                with st.spinner(f"{horizon_label}..."):
                    horizon_value = horizons_to_use[horizon_label]
                    predicted_price, current_price = train_and_predict_xgboost(ticker, horizon_value, time_unit)
                    if predicted_price is not None:
                        change_pct = ((predicted_price - current_price) / current_price) * 100
                        st.metric(label=f"{horizon_label}", value=f"${predicted_price:,.2f}", delta=f"{change_pct:+.2f}%")
                        log_prediction(PREDICTIONS_LOG_FILE, prediction_time, ticker, horizon_label, horizon_value, time_unit, predicted_price, current_price)
                    else:
                        st.warning("Échec")
    st.success("Analyse rapide terminée et sauvegardée.")