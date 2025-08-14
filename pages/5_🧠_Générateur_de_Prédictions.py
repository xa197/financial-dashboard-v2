import streamlit as st
import pandas as pd
import numpy as np
import xgboost as xgb
import yfinance as yf
from utils import get_tickers_by_category, get_available_tickers
import os
from datetime import datetime

st.set_page_config(layout="wide", page_title="Scanner & Prédictions IA")

# --- PARAMÈTRES & MOTEUR XGBOOST (inchangés) ---
PREDICTIONS_LOG_FILE = "predictions_log.csv"
HORIZONS_HOURS = {"2h": 2, "8h": 8, "1j": 24, "2j": 48, "7j": 168, "14j": 336, "28j": 672}

def create_features_manual(df):
    df['hour'] = df.index.hour; df['dayofweek'] = df.index.dayofweek
    delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean(); rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs)); df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    return df

@st.cache_data(ttl=3600)
def train_and_predict_xgboost(ticker, horizon_hours):
    try:
        data = yf.download(ticker, period="730d", interval="1h", progress=False)
        if data.empty: return None, None
    except: return None, None
    if isinstance(data.index, pd.MultiIndex): data.index = data.index.get_level_values('Datetime')
    shift_periods = int(horizon_hours)
    data_with_features = create_features_manual(data.copy())
    data_with_features['target'] = data_with_features['Close'].shift(-shift_periods)
    data_with_features.dropna(inplace=True)
    if len(data_with_features) < 200: return None, None
    FEATURES = ['hour', 'dayofweek', 'RSI_14', 'EMA_20', 'EMA_50']; TARGET = 'target'
    X, y = data_with_features[FEATURES], data_with_features[TARGET]
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100).fit(X, y)
    latest_data_for_pred = create_features_manual(data.copy()).iloc[-1:]
    latest_features = latest_data_for_pred[FEATURES].values
    prediction = model.predict(latest_features)[0]
    current_price = data['Close'].iloc[-1]
    return float(prediction), float(current_price)

def log_prediction(log_file, timestamp, ticker, horizon_label, predicted_price, current_price):
    new_entry = pd.DataFrame([{"Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),"Ticker": ticker,"Horizon": horizon_label,"Prix Actuel": current_price,"Prix Prédit": predicted_price,"Date Cible": (timestamp + pd.Timedelta(hours=HORIZONS_HOURS[horizon_label])).strftime('%Y-%m-%d %H:%M:%S'),"Prix Réel": np.nan,"Erreur (%)": np.nan,"Statut": "En attente"}])
    if not os.path.exists(log_file): new_entry.to_csv(log_file, index=False)
    else: new_entry.to_csv(log_file, mode='a', header=False, index=False)

# --- INTERFACE ---
st.title("🧠 Prédictions & Scan par IA (XGBoost)")

available_tickers = get_available_tickers()

# --- SECTION 1 : ANALYSE RAPIDE À LA DEMANDE ---
st.subheader("Analyse Rapide")
with st.form("quick_analysis_form"):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        quick_tickers = st.multiselect("Actifs à analyser", options=available_tickers, help="Sélectionnez un ou plusieurs actifs.")
    with col2:
        quick_horizons = st.multiselect("Horizons de prédiction", options=list(HORIZONS_HOURS.keys()), default=list(HORIZONS_HOURS.keys())[:4])
    with col3:
        submitted = st.form_submit_button("🚀 Lancer l'Analyse Rapide")

if submitted:
    if not quick_tickers or not quick_horizons:
        st.warning("Veuillez sélectionner au moins un actif et un horizon.")
    else:
        st.write("---")
        results = []
        for ticker in quick_tickers:
            st.write(f"**Analyse de {ticker}...**")
            cols = st.columns(len(quick_horizons))
            for i, horizon_label in enumerate(quick_horizons):
                with cols[i]:
                    with st.spinner(f"{horizon_label}..."):
                        predicted_price, current_price = train_and_predict_xgboost(ticker, HORIZONS_HOURS[horizon_label])
                        if predicted_price is not None:
                            change_pct = ((predicted_price - current_price) / current_price) * 100
                            st.metric(label=f"{horizon_label}", value=f"${predicted_price:,.2f}", delta=f"{change_pct:+.2f}%")
                            log_prediction(PREDICTIONS_LOG_FILE, datetime.now(), ticker, horizon_label, predicted_price, current_price)
                        else:
                            st.warning("Échec")
        st.success("Analyse rapide terminée et sauvegardée.")


st.write("---")
# --- SECTION 2 : SCANNER PAR SECTEUR ---
st.subheader("Scanner par Secteur")
tickers_by_category = get_tickers_by_category()

if not tickers_by_category or "ERREUR" in tickers_by_category:
    st.error("Impossible de lire les catégories depuis `tickers.txt`.")
else:
    category_tabs = st.tabs(list(tickers_by_category.keys()))
    for i, category in enumerate(tickers_by_category):
        with category_tabs[i]:
            tickers_in_category = tickers_by_category[category]
            if st.button(f"🚀 Lancer les prédictions pour le secteur {category}", key=f"scan_{category}"):
                # La logique du scanner reste la même...
                prediction_time = datetime.now()
                all_results = []
                progress_bar = st.progress(0, text=f"Initialisation du scan pour {category}...")
                for j, ticker in enumerate(tickers_in_category):
                    progress_bar.progress((j + 1) / len(tickers_in_category), text=f"Analyse de {ticker}...")
                    try: current_price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
                    except: continue
                    result_row = {"Actif": ticker, "Prix Actuel": current_price}
                    for horizon_label, horizon_h in HORIZONS_HOURS.items():
                        predicted_price, _ = train_and_predict_xgboost(ticker, horizon_h)
                        if predicted_price is not None:
                            change_pct = ((predicted_price - current_price) / current_price) * 100
                            result_row[f"Var. {horizon_label}"] = change_pct
                            log_prediction(PREDICTIONS_LOG_FILE, prediction_time, ticker, horizon_label, predicted_price, current_price)
                        else:
                            result_row[f"Var. {horizon_label}"] = np.nan
                    all_results.append(result_row)
                
                st.success(f"Scan du secteur {category} terminé !")
                if all_results:
                    df_results = pd.DataFrame(all_results)
                    format_dict = {'Prix Actuel': '${:,.2f}'}; [format_dict.update({col: '{:+.2f}%'}) for col in df_results.columns if col.startswith("Var.")]
                    st.dataframe(df_results.style.format(format_dict).background_gradient(cmap='RdYlGn', subset=[c for c in df_results if c.startswith("Var.")]))