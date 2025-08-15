import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from utils import load_data, get_available_tickers

# --- Configuration de la page ---
st.set_page_config(layout="wide", page_title="Prédiction de Tendance")

# --- Dictionnaire des horizons de prédiction ---
HORIZON_OPTIONS = {
    "3 Jours": 3, "1 Semaine": 7, "2 Semaines": 14, "1 Mois": 30,
    "2 Mois": 60, "3 Mois": 90, "6 Mois": 182, "1 An": 365
}

# --- Initialisation de la variable ticker ---
selected_ticker = None

# --- Interface Utilisateur (Sidebar) ---
st.sidebar.header("Paramètres de Prédiction")
available_tickers = get_available_tickers()

if available_tickers:
    selected_ticker = st.sidebar.selectbox(
        "Sélectionnez un actif",
        options=available_tickers,
        help="Choisissez l'actif pour lequel vous souhaitez une prédiction de tendance."
    )
    selected_horizon_label = st.sidebar.selectbox(
        "Choisissez l'horizon de prédiction",
        options=list(HORIZON_OPTIONS.keys())
    )
    prediction_days = HORIZON_OPTIONS[selected_horizon_label]
else:
    st.sidebar.error("Aucun actif trouvé. Veuillez vérifier votre fichier `tickers.txt`.")

# --- Corps Principal de la Page ---
st.title("🔮 Prédiction de Tendance par Régression Linéaire")

# On ne continue que si un ticker a été correctement sélectionné
if selected_ticker:
    st.header(f"Analyse pour : {selected_ticker}")
    
    # 1. Chargement des données via la fonction sécurisée
    data = load_data(selected_ticker)
    
    # 2. On vérifie si le DataFrame retourné n'est PAS vide avant de continuer
    if not data.empty:
        st.info(f"Horizon de prédiction sélectionné : **{selected_horizon_label}**.")
        
        df_pred = data.copy().reset_index()
        
        # Le reste du code s'exécute en toute sécurité
        df_pred['Date'] = pd.to_datetime(df_pred['Date']) # Sécurité supplémentaire
        df_pred['Days'] = (df_pred['Date'] - df_pred['Date'].min()).dt.days
        
        X = df_pred[['Days']]
        y = df_pred['Close']

        model = LinearRegression().fit(X, y)

        # Préparation des jours et dates futurs pour la prédiction
        last_day = X['Days'].iloc[-1]
        future_days = np.arange(last_day + 1, last_day + 1 + prediction_days).reshape(-1, 1)
        future_predictions = model.predict(future_days)
        
        last_date = df_pred['Date'].iloc[-1]
        future_dates = [last_date + timedelta(days=x) for x in range(1, prediction_days + 1)]
        df_future = pd.DataFrame({'Date': future_dates, 'Prédiction': future_predictions})
        
        # --- Affichage du graphique interactif ---
        st.subheader("Graphique de Tendance et Prédiction")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_pred['Date'], y=y, mode='lines', name='Cours Historique'))
        fig.add_trace(go.Scatter(x=df_pred['Date'], y=model.predict(X), mode='lines', name='Tendance (Régression)', line=dict(dash='dash', color='orange')))
        fig.add_trace(go.Scatter(x=df_future['Date'], y=df_future['Prédiction'], mode='lines', name='Prédiction', line=dict(color='red', width=3)))
        
        fig.update_layout(
            title=f"Tendance et Prédiction pour {selected_ticker}",
            xaxis_title="Date",
            yaxis_title="Prix de Clôture (USD)", # À adapter si vous gérez d'autres devises
            xaxis_rangeslider_visible=True,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Affichage des données brutes de prédiction ---
        with st.expander("Afficher les données de prédiction détaillées"):
            st.dataframe(df_future.style.format({'Prédiction': '{:.2f}$'}), use_container_width=True)
            
    # 3. Ce bloc s'exécute si load_data a retourné un DataFrame vide
    else:
        # L'erreur spécifique est déjà affichée par la fonction load_data.
        # On ajoute simplement un message pour guider l'utilisateur.
        st.warning(f"Impossible d'afficher les prédictions car les données pour **{selected_ticker}** sont manquantes ou vides.")

else:
    st.info("Veuillez sélectionner un actif dans le menu de gauche pour commencer l'analyse.")