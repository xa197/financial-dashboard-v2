import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from utils import load_data, get_available_tickers

st.set_page_config(layout="wide", page_title="Prédiction de Tendance")

# --- Dictionnaire des horizons de prédiction ---
HORIZON_OPTIONS = {
    "3 Jours": 3, "1 Semaine": 7, "2 Semaines": 14, "1 Mois": 30,
    "2 Mois": 60, "3 Mois": 90, "6 Mois": 182, "1 An": 365
}

# --- INTERFACE (SIDEBAR) ---
available_tickers = get_available_tickers()
if available_tickers:
    selected_ticker = st.sidebar.selectbox("Sélectionnez un actif", options=available_tickers)
    selected_horizon_label = st.sidebar.selectbox("Choisissez l'horizon de prédiction", options=list(HORIZON_OPTIONS.keys()))
    prediction_days = HORIZON_OPTIONS[selected_horizon_label]
else:
    selected_ticker = None

# --- CORPS DE LA PAGE ---
st.title(f"🔮 Prédiction de Tendance pour {selected_ticker}")

if selected_ticker:
    st.info(f"Horizon de prédiction : **{selected_horizon_label}**.")
    data = load_data(selected_ticker)
    
    if data is not None and not data.empty:
        df_pred = data.copy().reset_index()
        
        # --- LIGNE DE SÉCURITÉ APPLIQUÉE ICI ---
        # On force la conversion de la colonne 'Date' en datetime, quoi qu'il arrive.
        # C'est la solution définitive au problème 'str' - 'str'.
        df_pred['Date'] = pd.to_datetime(df_pred['Date'])
        
        # Le reste du code peut maintenant s'exécuter en toute sécurité
        df_pred['Days'] = (df_pred['Date'] - df_pred['Date'].min()).dt.days
        
        X = df_pred[['Days']]
        y = df_pred['Close']

        model = LinearRegression().fit(X, y)

        last_day = X['Days'].iloc[-1]
        future_days = np.arange(last_day + 1, last_day + 1 + prediction_days).reshape(-1, 1)
        future_predictions = model.predict(future_days)
        
        last_date = df_pred['Date'].iloc[-1]
        future_dates = pd.to_datetime([last_date + timedelta(days=x) for x in range(1, prediction_days + 1)])
        df_future = pd.DataFrame({'Date': future_dates, 'Prediction': future_predictions})
        
        # --- AFFICHAGE ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_pred['Date'], y=y, mode='lines', name='Historique'))
        fig.add_trace(go.Scatter(x=df_pred['Date'], y=model.predict(X), mode='lines', name='Tendance', line=dict(dash='dash')))
        fig.add_trace(go.Scatter(x=df_future['Date'], y=df_future['Prediction'], mode='lines', name='Prédiction', line=dict(color='red')))
        fig.update_layout(xaxis_rangeslider_visible=True)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Voir les données de prédiction"):
            st.dataframe(df_future)
            
    else:
        st.error(f"Les données pour {selected_ticker} n'ont pas pu être chargées.")