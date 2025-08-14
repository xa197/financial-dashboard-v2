import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from utils import load_data, get_available_tickers

st.set_page_config(layout="wide", page_title="Prédiction de Tendance")

available_tickers = get_available_tickers()
if available_tickers:
    selected_ticker = st.sidebar.selectbox("Sélectionez un actif", options=available_tickers)
    prediction_days = st.sidebar.slider("Jours de prédiction :", 30, 365, 90)
else:
    selected_ticker = None

st.title(f"🔮 Prédiction de Tendance pour {selected_ticker}")

if selected_ticker:
    data = load_data(selected_ticker)
    
    if data is not None and not data.empty:
        df_pred = data.copy().reset_index()
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
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_pred['Date'], y=y, mode='lines', name='Historique'))
        fig.add_trace(go.Scatter(x=df_pred['Date'], y=model.predict(X), mode='lines', name='Tendance'))
        fig.add_trace(go.Scatter(x=df_future['Date'], y=df_future['Prediction'], mode='lines', name='Prédiction'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Les données pour {selected_ticker} n'ont pas pu être chargées.")